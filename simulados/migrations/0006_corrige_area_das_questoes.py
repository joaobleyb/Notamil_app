"""Move para a área certa as questões gravadas na área errada.

No caderno azul do ENEM cada área ocupa um bloco fixo de 45 questões, então o
número da questão define a área. 139 questões estavam fora do seu bloco (a
maioria marcada como Humanas). Atualizar as linhas existentes (em vez de deixar
o seed criar outras) evita duplicar as questões e mantém as tentativas que já
apontam para elas. Se o seed novo já tiver criado a questão na área certa, as
tentativas são repassadas para ela e a cópia na área errada é apagada.
"""
from django.db import migrations

# Áreas dos blocos 1-45, 46-90, 91-135 e 136-180 do caderno azul.
BLOCOS_2009 = ["Natureza", "Humanas", "Linguagens", "Matemática"]
BLOCOS_2010_A_2016 = ["Humanas", "Natureza", "Linguagens", "Matemática"]
BLOCOS_DESDE_2017 = ["Linguagens", "Humanas", "Natureza", "Matemática"]

# Questões de língua estrangeira que estavam em Humanas sem o idioma.
IDIOMAS = {(2015, 95): "ingles", (2020, 5): "espanhol"}


def area_pela_numeracao(ano, numero):
    if ano == 2009:
        blocos = BLOCOS_2009
    elif ano <= 2016:
        blocos = BLOCOS_2010_A_2016
    else:
        blocos = BLOCOS_DESDE_2017
    return blocos[(numero - 1) // 45]


def corrigir_areas(apps, schema_editor):
    Questao = apps.get_model("simulados", "Questao")
    RespostaTentativa = apps.get_model("simulados", "RespostaTentativa")
    ItemProvaCompartilhada = apps.get_model("simulados", "ItemProvaCompartilhada")
    for questao in Questao.objects.filter(ano__gte=2009, numero__range=(1, 180)):
        area = area_pela_numeracao(questao.ano, questao.numero)
        if area == questao.area:
            continue
        idioma = IDIOMAS.get((questao.ano, questao.numero), questao.idioma_estrangeiro)
        # Se o seed novo rodou antes desta migration, a questão já existe na área
        # certa: as tentativas passam a apontar para ela e a cópia errada sai.
        certa = Questao.objects.filter(
            area=area, ano=questao.ano, numero=questao.numero, idioma_estrangeiro=idioma
        ).first()
        if certa:
            RespostaTentativa.objects.filter(questao=questao).update(questao=certa)
            ItemProvaCompartilhada.objects.filter(questao=questao).update(questao=certa)
            questao.delete()
            continue
        questao.area = area
        questao.idioma_estrangeiro = idioma
        questao.save(update_fields=["area", "idioma_estrangeiro"])


class Migration(migrations.Migration):

    dependencies = [
        ("simulados", "0005_gestor_e_nome_aluno"),
    ]

    operations = [
        # Sem volta: não faz sentido devolver as questões para a área errada.
        migrations.RunPython(corrigir_areas, migrations.RunPython.noop),
    ]
