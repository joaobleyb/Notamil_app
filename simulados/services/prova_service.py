"""Regras de negócio da geração e da execução do simulado."""
import random

from django.db import transaction
from django.db.models import Count, DurationField, ExpressionWrapper, F, Q
from django.utils import timezone

from ..models import (
    ItemProvaCompartilhada,
    ProvaCompartilhada,
    Questao,
    RespostaTentativa,
    Tentativa,
    gerar_codigo,
)


def contar_questoes_por_area():
    """Quantidade de questões cadastradas em cada área."""
    return {
        area: Questao.objects.filter(area=area).count()
        for area, _rotulo in Questao.AREAS
    }


def anos_disponiveis():
    """Anos de prova presentes no banco, do mais recente ao mais antigo."""
    return list(
        Questao.objects.order_by("-ano").values_list("ano", flat=True).distinct()
    )


def _sortear_por_area(area, quantidade, idioma_estrangeiro=None, anos=None):
    """Sorteia `quantidade` questões da área (opcionalmente só dos `anos` dados).

    O sorteio é feito sobre a lista de ids em vez de `ORDER BY ?`: no MySQL o
    `ORDER BY RAND()` percorre e ordena a tabela inteira a cada prova gerada.
    """
    if quantidade <= 0:
        return []

    questoes = Questao.objects.filter(area=area)
    if anos:
        questoes = questoes.filter(ano__in=anos)
    if idioma_estrangeiro:
        questoes = questoes.filter(
            Q(idioma_estrangeiro=idioma_estrangeiro) | Q(idioma_estrangeiro="")
        )

    ids = list(questoes.values_list("pk", flat=True))
    if len(ids) > quantidade:
        ids = random.sample(ids, quantidade)
    return list(Questao.objects.filter(pk__in=ids))


def sortear_questoes(
    qtd_linguagens, qtd_humanas, qtd_natureza, qtd_matematica, idioma_estrangeiro, anos=None
):
    """Monta a prova completa embaralhando as questões de todas as áreas.

    `anos` vazio ou None mantém o comportamento original: sorteia de todos os anos.
    """
    questoes = []
    questoes += _sortear_por_area(Questao.AREA_LINGUAGENS, qtd_linguagens, idioma_estrangeiro, anos)
    questoes += _sortear_por_area(Questao.AREA_HUMANAS, qtd_humanas, anos=anos)
    questoes += _sortear_por_area(Questao.AREA_NATUREZA, qtd_natureza, anos=anos)
    questoes += _sortear_por_area(Questao.AREA_MATEMATICA, qtd_matematica, anos=anos)
    random.shuffle(questoes)
    return questoes


@transaction.atomic
def criar_tentativa(questoes, idioma_estrangeiro, prova_compartilhada=None, nome_aluno=""):
    """Persiste a prova sorteada como uma tentativa pronta para ser respondida."""
    tentativa = Tentativa.objects.create(
        idioma_estrangeiro=idioma_estrangeiro,
        prova_compartilhada=prova_compartilhada,
        nome_aluno=nome_aluno,
    )
    RespostaTentativa.objects.bulk_create(
        [
            RespostaTentativa(tentativa=tentativa, questao=questao, ordem=indice)
            for indice, questao in enumerate(questoes, start=1)
        ]
    )
    return tentativa


def salvar_resposta(tentativa, ordem, alternativa):
    """Grava a alternativa marcada em uma questão da tentativa."""
    alternativa = (alternativa or "").upper()
    if alternativa not in Questao.ALTERNATIVAS:
        return None

    resposta = tentativa.respostas.filter(ordem=ordem).first()
    if resposta is None:
        return None

    resposta.alternativa = alternativa
    resposta.save(update_fields=["alternativa"])
    return resposta


def ordens_pendentes(tentativa):
    """Números das questões ainda sem alternativa marcada, em ordem."""
    return list(
        tentativa.respostas.filter(alternativa="")
        .order_by("ordem")
        .values_list("ordem", flat=True)
    )


def finalizar_tentativa(tentativa):
    """Marca a tentativa como concluída e devolve o total de acertos."""
    if not tentativa.finalizada:
        tentativa.finalizada_em = timezone.now()
        tentativa.save(update_fields=["finalizada_em"])
    return tentativa.acertos


def _codigo_inedito(tentativas=10):
    """Gera um código de turma que ainda não está em uso."""
    for _ in range(tentativas):
        codigo = gerar_codigo()
        if not ProvaCompartilhada.objects.filter(codigo=codigo).exists():
            return codigo
    raise RuntimeError("Não foi possível gerar um código de turma disponível.")


@transaction.atomic
def criar_prova_compartilhada(questoes, idioma_estrangeiro, embaralhar=False):
    """Congela a prova sorteada em um código para a turma inteira responder."""
    prova = ProvaCompartilhada.objects.create(
        codigo=_codigo_inedito(), idioma_estrangeiro=idioma_estrangeiro, embaralhar=embaralhar
    )
    ItemProvaCompartilhada.objects.bulk_create(
        [
            ItemProvaCompartilhada(prova=prova, questao=questao, ordem=indice)
            for indice, questao in enumerate(questoes, start=1)
        ]
    )
    return prova


def buscar_prova_por_codigo(codigo):
    """Prova da turma correspondente ao código, ou None."""
    codigo = (codigo or "").strip().upper()
    if not codigo:
        return None
    return ProvaCompartilhada.objects.filter(codigo=codigo).first()


def iniciar_prova_da_turma(prova, nome_aluno=""):
    """Cria uma tentativa com as questões da prova da turma.

    Com `embaralhar` ligado, cada aluno recebe a mesma prova em uma ordem própria —
    as questões são as mesmas, mas a numeração não bate entre as carteiras.
    """
    questoes = prova.questoes_ordenadas()
    if prova.embaralhar:
        random.shuffle(questoes)
    return criar_tentativa(
        questoes, prova.idioma_estrangeiro, prova_compartilhada=prova, nome_aluno=nome_aluno
    )


def _tempo_legivel(duracao):
    """Duração da prova em texto curto: "8 min", "1 h 05 min"."""
    minutos = max(1, round(duracao.total_seconds() / 60))
    if minutos < 60:
        return f"{minutos} min"
    return f"{minutos // 60} h {minutos % 60:02d} min"


def ranking_da_turma(prova):
    """Quem finalizou a prova da turma, do maior para o menor número de acertos.

    Empate em acertos é desempatado pelo menor tempo de prova. Os acertos são
    contados no banco, numa consulta só, em vez de uma por aluno.
    """
    finalizadas = (
        prova.tentativas.filter(finalizada_em__isnull=False)
        .annotate(
            total_acertos=Count(
                "respostas",
                filter=Q(respostas__alternativa=F("respostas__questao__resposta_correta")),
            ),
            duracao=ExpressionWrapper(
                F("finalizada_em") - F("criada_em"), output_field=DurationField()
            ),
        )
        .order_by("-total_acertos", "duracao", "finalizada_em")
    )
    total = prova.total
    return [
        {
            "posicao": posicao,
            "tentativa_id": tentativa.id,
            "nome": tentativa.nome_aluno or "Sem nome",
            "acertos": tentativa.total_acertos,
            "total": total,
            "tempo": _tempo_legivel(tentativa.duracao),
        }
        for posicao, tentativa in enumerate(finalizadas, start=1)
    ]


def andamento_da_turma(prova):
    """Quem começou a prova da turma e ainda não finalizou, com o progresso de cada um."""
    em_andamento = (
        prova.tentativas.filter(finalizada_em__isnull=True)
        .annotate(respondidas=Count("respostas", filter=~Q(respostas__alternativa="")))
        .order_by("criada_em")
    )
    return [
        {
            "nome": tentativa.nome_aluno or "Sem nome",
            "respondidas": tentativa.respondidas,
            "iniciada_em": tentativa.criada_em,
        }
        for tentativa in em_andamento
    ]
