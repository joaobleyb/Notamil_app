"""Prova fixa compartilhada com uma turma através de um código."""
import secrets

from django.db import models

from .questao import Questao

ALFABETO_CODIGO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sem caracteres ambíguos (O/0, I/1)
TAMANHO_CODIGO = 6


def gerar_codigo():
    """Código aleatório de turma, em maiúsculas."""
    return "".join(secrets.choice(ALFABETO_CODIGO) for _ in range(TAMANHO_CODIGO))


class ProvaCompartilhada(models.Model):
    """Conjunto fixo de questões que a turma inteira responde pelo mesmo código."""

    codigo = models.CharField("código", max_length=TAMANHO_CODIGO, unique=True)
    criada_em = models.DateTimeField("criada em", auto_now_add=True)
    idioma_estrangeiro = models.CharField(
        "idioma estrangeiro", max_length=10, choices=Questao.IDIOMAS, blank=True, default=""
    )
    embaralhar = models.BooleanField(
        "embaralhar ordem por aluno",
        default=False,
        help_text="Cada aluno recebe as mesmas questões em uma ordem diferente.",
    )
    questoes = models.ManyToManyField(
        Questao,
        through="ItemProvaCompartilhada",
        related_name="provas_compartilhadas",
        verbose_name="questões",
    )

    class Meta:
        verbose_name = "prova da turma"
        verbose_name_plural = "provas de turma"
        ordering = ["-criada_em"]

    def __str__(self):
        return f"Prova {self.codigo}"

    @property
    def total(self):
        return self.itens.count()

    def questoes_ordenadas(self):
        """Questões na mesma ordem para todos que entrarem com o código."""
        return [item.questao for item in self.itens.select_related("questao")]

    def resumo_por_area(self):
        """Quantidade de questões por área, para exibir na tela do código."""
        contagem = (
            self.itens.values("questao__area")
            .annotate(quantidade=models.Count("id"))
            .order_by("questao__area")
        )
        return [(linha["questao__area"], linha["quantidade"]) for linha in contagem]


class ItemProvaCompartilhada(models.Model):
    """Questão da prova compartilhada, com a ordem fixa da prova."""

    prova = models.ForeignKey(
        ProvaCompartilhada, on_delete=models.CASCADE, related_name="itens", verbose_name="prova"
    )
    questao = models.ForeignKey(
        Questao, on_delete=models.CASCADE, related_name="+", verbose_name="questão"
    )
    ordem = models.PositiveIntegerField("ordem na prova")

    class Meta:
        verbose_name = "questão da prova da turma"
        verbose_name_plural = "questões da prova da turma"
        ordering = ["prova_id", "ordem"]
        constraints = [
            models.UniqueConstraint(fields=["prova", "ordem"], name="item_unico_por_ordem")
        ]

    def __str__(self):
        return f"{self.prova.codigo} #{self.ordem}"
