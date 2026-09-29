"""Marca as questões 1 a 5 de Linguagens do ENEM 2024 como de inglês.

Elas foram gravadas sem idioma e apareciam também para quem escolhe espanhol.
Atualizar as linhas existentes (em vez de deixar o seed criar outras) evita
duplicar as questões e mantém as tentativas que já apontam para elas.
"""
from django.db import migrations


def marcar_ingles(apps, schema_editor):
    Questao = apps.get_model("simulados", "Questao")
    Questao.objects.filter(
        area="Linguagens", ano=2024, numero__lte=5, idioma_estrangeiro=""
    ).update(idioma_estrangeiro="ingles")


def desmarcar_ingles(apps, schema_editor):
    Questao = apps.get_model("simulados", "Questao")
    Questao.objects.filter(
        area="Linguagens", ano=2024, numero__lte=5, idioma_estrangeiro="ingles"
    ).update(idioma_estrangeiro="")


class Migration(migrations.Migration):

    dependencies = [
        ("simulados", "0003_provacompartilhada_embaralhar"),
    ]

    operations = [
        migrations.RunPython(marcar_ingles, desmarcar_ingles),
    ]
