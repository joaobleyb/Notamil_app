"""Views do NotaMil — uma função por tela do simulado."""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .forms import EntrarComCodigoForm, GerarProvaForm
from .models import ProvaCompartilhada, Questao, Tentativa
from .services import (
    contar_questoes_por_area,
    criar_prova_compartilhada,
    criar_tentativa,
    finalizar_tentativa,
    iniciar_prova_da_turma,
    salvar_resposta,
    sortear_questoes,
)


def menu_inicial(request):
    """Tela inicial com os atalhos do app."""
    return render(
        request,
        "simulados/menu_inicial.html",
        {"total_questoes": Questao.objects.count()},
    )


def gerar_prova(request):
    """Configuração do simulado: quantidade por área e idioma estrangeiro."""
    disponiveis = contar_questoes_por_area()

    if request.method == "POST":
        form = GerarProvaForm(request.POST)
        if form.is_valid():
            dados = form.cleaned_data
            idioma = dados["idioma_estrangeiro"]
            questoes = sortear_questoes(
                dados["quantidade_linguagens"],
                dados["quantidade_humanas"],
                dados["quantidade_natureza"],
                dados["quantidade_matematica"],
                idioma,
            )

            if not questoes:
                messages.error(request, "Não há questões disponíveis no banco de dados.")
            else:
                if len(questoes) < form.total:
                    messages.warning(
                        request, f"Apenas {len(questoes)} questões disponíveis no banco."
                    )
                if dados["gerar_codigo_turma"]:
                    prova = criar_prova_compartilhada(
                        questoes, idioma, embaralhar=dados["embaralhar_questoes"]
                    )
                    return redirect("simulados:prova_da_turma", codigo=prova.codigo)

                tentativa = criar_tentativa(questoes, idioma)
                return redirect("simulados:simulado", tentativa_id=tentativa.id, ordem=1)
        else:
            for erro in form.non_field_errors():
                messages.error(request, erro)
    else:
        form = GerarProvaForm()

    areas = [
        {
            "rotulo": rotulo,
            "campo": GerarProvaForm.CAMPOS_POR_AREA[area],
            "valor": form.data.get(GerarProvaForm.CAMPOS_POR_AREA[area], 0) or 0,
            "disponiveis": disponiveis.get(area, 0),
        }
        for area, rotulo in Questao.AREAS
    ]

    return render(
        request,
        "simulados/gerar_prova.html",
        {
            "form": form,
            "areas": areas,
            "idiomas": Questao.IDIOMAS,
            "idioma_selecionado": form.data.get("idioma_estrangeiro") or Questao.IDIOMA_INGLES,
            "gerar_codigo_turma": bool(form.data.get("gerar_codigo_turma")),
            "embaralhar_questoes": bool(form.data.get("embaralhar_questoes")),
            "total_disponivel": sum(disponiveis.values()),
        },
    )


def simulado(request, tentativa_id, ordem):
    """Resolução das questões, uma a uma."""
    tentativa = get_object_or_404(Tentativa, pk=tentativa_id)
    total = tentativa.total
    ordem = max(1, min(ordem, total))
    resposta = get_object_or_404(tentativa.respostas.select_related("questao"), ordem=ordem)

    if request.method == "POST":
        salvar_resposta(tentativa, ordem, request.POST.get("alternativa"))
        if request.POST.get("acao") == "finalizar":
            finalizar_tentativa(tentativa)
            return redirect("simulados:resultado", tentativa_id=tentativa.id)
        return redirect("simulados:simulado", tentativa_id=tentativa.id, ordem=ordem + 1)

    return render(
        request,
        "simulados/simulado.html",
        {
            "tentativa": tentativa,
            "resposta": resposta,
            "questao": resposta.questao,
            "corpo": resposta.questao.corpo(),
            "ordem": ordem,
            "total": total,
            "progresso": round(ordem * 100 / total) if total else 0,
            "respondidas": tentativa.respostas.exclude(alternativa="").count(),
            "ultima": ordem == total,
        },
    )


def resultado(request, tentativa_id):
    """Acertos, total e percentual de aproveitamento."""
    tentativa = get_object_or_404(Tentativa, pk=tentativa_id)
    acertos = tentativa.acertos
    total = tentativa.total
    return render(
        request,
        "simulados/resultado.html",
        {
            "tentativa": tentativa,
            "acertos": acertos,
            "erros": total - acertos,
            "total": total,
            "percentual": tentativa.percentual,
        },
    )


def analisar_tentativa(request, tentativa_id, ordem):
    """Revisão questão a questão com o gabarito destacado."""
    tentativa = get_object_or_404(Tentativa, pk=tentativa_id)
    total = tentativa.total
    ordem = max(1, min(ordem, total))
    resposta = get_object_or_404(tentativa.respostas.select_related("questao"), ordem=ordem)

    return render(
        request,
        "simulados/analisar_tentativa.html",
        {
            "tentativa": tentativa,
            "resposta": resposta,
            "questao": resposta.questao,
            "corpo": resposta.questao.corpo(),
            "ordem": ordem,
            "total": total,
            "tem_anterior": ordem > 1,
            "tem_proxima": ordem < total,
        },
    )


def redacao(request):
    """Tela de redação — ainda não implementada."""
    return render(request, "simulados/redacao.html")


def prova_da_turma(request, codigo):
    """Mostra o código gerado para compartilhar a prova com a turma."""
    prova = get_object_or_404(ProvaCompartilhada, codigo=codigo.upper())
    return render(
        request,
        "simulados/prova_da_turma.html",
        {
            "prova": prova,
            "link_prova": request.build_absolute_uri(),
            "resumo": prova.resumo_por_area(),
            "respondidas": prova.tentativas.filter(finalizada_em__isnull=False).count(),
        },
    )


def entrar_com_codigo(request):
    """Entrada na prova da turma a partir do código."""
    form = EntrarComCodigoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        tentativa = iniciar_prova_da_turma(form.prova)
        return redirect("simulados:simulado", tentativa_id=tentativa.id, ordem=1)
    return render(request, "simulados/entrar_com_codigo.html", {"form": form})
