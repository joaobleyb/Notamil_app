"""Remoção das tentativas antigas, para o banco não crescer sem parar.

A maior parte das tentativas é abandonada no meio: cada uma guarda uma linha por
questão sorteada. Sem uma faxina periódica, essas linhas ficam para sempre.
"""
from datetime import timedelta

from django.utils import timezone

from ..models import ProvaCompartilhada, Tentativa


def limpar_tentativas_antigas(dias=30, incluir_finalizadas=False, incluir_provas=False):
    """Apaga tentativas anteriores ao corte e devolve (tentativas, provas) removidas."""
    corte = timezone.now() - timedelta(days=dias)

    tentativas = Tentativa.objects.filter(criada_em__lt=corte)
    if not incluir_finalizadas:
        tentativas = tentativas.filter(finalizada_em__isnull=True)
    total_tentativas = tentativas.count()
    tentativas.delete()  # as respostas somem junto, por cascade

    total_provas = 0
    if incluir_provas:
        # Só códigos de turma velhos que ninguém chegou a responder.
        provas = ProvaCompartilhada.objects.filter(
            criada_em__lt=corte, tentativas__isnull=True
        )
        total_provas = provas.count()
        provas.delete()

    return total_tentativas, total_provas
