"""Models que guardam a tentativa do simulado e as respostas do usuário."""
import uuid

from django.db import models

from .prova_compartilhada import ProvaCompartilhada
from .questao import Questao


class Tentativa(models.Model):
    """Uma execução de simulado: as questões sorteadas e o estado da prova."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    criada_em = models.DateTimeField("criada em", auto_now_add=True)
    finalizada_em = models.DateTimeField("finalizada em", null=True, blank=True)
    idioma_estrangeiro = models.CharField(
        "idioma estrangeiro", max_length=10, choices=Questao.IDIOMAS, blank=True, default=""
    )
    prova_compartilhada = models.ForeignKey(
        ProvaCompartilhada,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tentativas",
        verbose_name="prova da turma",
    )

    class Meta:
        verbose_name = "tentativa"
        verbose_name_plural = "tentativas"
        ordering = ["-criada_em"]

    def __str__(self):
        return f"Tentativa de {self.criada_em:%d/%m/%Y %H:%M}"

    @property
    def total(self):
        return self.respostas.count()

    @property
    def acertos(self):
        return sum(1 for resposta in self.respostas.all() if resposta.correta)

    @property
    def percentual(self):
        total = self.total
        return (self.acertos * 100 / total) if total else 0

    @property
    def finalizada(self):
        return self.finalizada_em is not None


class RespostaTentativa(models.Model):
    """Questão sorteada para a tentativa e a alternativa marcada pelo usuário."""

    tentativa = models.ForeignKey(
        Tentativa, on_delete=models.CASCADE, related_name="respostas", verbose_name="tentativa"
    )
    questao = models.ForeignKey(
        Questao, on_delete=models.CASCADE, related_name="respostas", verbose_name="questão"
    )
    ordem = models.PositiveIntegerField("ordem na prova")
    alternativa = models.CharField("alternativa marcada", max_length=1, blank=True, default="")

    class Meta:
        verbose_name = "resposta"
        verbose_name_plural = "respostas"
        ordering = ["tentativa_id", "ordem"]
        constraints = [
            models.UniqueConstraint(
                fields=["tentativa", "ordem"], name="resposta_unica_por_ordem"
            )
        ]

    def __str__(self):
        return f"{self.ordem}. {self.alternativa or '-'}"

    @property
    def respondida(self):
        return bool(self.alternativa)

    @property
    def correta(self):
        return self.alternativa.upper() == self.questao.resposta_correta.upper() if self.alternativa else False
