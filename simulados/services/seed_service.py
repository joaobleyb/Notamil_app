"""Carga inicial do banco de questões (equivale ao AdicionarQuestoesUtil.java)."""
import json
from pathlib import Path

from django.db import transaction

from ..models import ElementoQuestao, Questao

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "questoes.json"

CAMPOS = [
    "enunciado", "imagem", "texto_apoio", "fonte",
    "texto_apoio_1", "texto_apoio_2", "texto_apoio_3", "texto_apoio_4",
    "referencia_texto_1", "referencia_texto_2", "referencia_texto_3", "referencia_texto_4",
    "alternativa_a", "alternativa_b", "alternativa_c", "alternativa_d", "alternativa_e",
    "resposta_correta",
]


@transaction.atomic
def carregar_questoes_iniciais():
    """Insere (ou atualiza) as questões do arquivo de fixture.

    A deduplicação usa área + ano + número + idioma, como no app Android
    (que dedupe por área/ano/número; o idioma entra na chave porque as
    questões de Inglês e Espanhol repetem a numeração da prova).
    Retorna a tupla (criadas, atualizadas).
    """
    with FIXTURE.open(encoding="utf-8") as arquivo:
        dados = json.load(arquivo)

    criadas = atualizadas = 0
    for item in dados:
        questao, criada = Questao.objects.update_or_create(
            area=item["area"],
            ano=item["ano"],
            numero=item["numero"],
            idioma_estrangeiro=item.get("idioma_estrangeiro", ""),
            defaults={campo: item.get(campo, "") for campo in CAMPOS},
        )
        criadas += criada
        atualizadas += not criada

        questao.elementos.all().delete()
        ElementoQuestao.objects.bulk_create(
            [
                ElementoQuestao(
                    questao=questao,
                    ordem=indice,
                    tipo=elemento["tipo"],
                    conteudo=elemento["conteudo"],
                )
                for indice, elemento in enumerate(item.get("elementos", []))
            ]
        )

    return criadas, atualizadas
