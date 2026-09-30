"""Define o idioma das questões de língua estrangeira gravadas sem idioma.

Sem idioma, a questão entra no sorteio de quem escolheu inglês e de quem escolheu
espanhol. Como na 0004, as linhas existentes são atualizadas (em vez de deixar o
seed criar outras), o que mantém as tentativas que já apontam para elas. Se o
seed novo já tiver criado a questão com o idioma, as tentativas são repassadas
para ela e a cópia sem idioma é apagada.
"""
from django.db import migrations

# (ano, número) -> idioma, conferido pelo texto de cada questão.
IDIOMAS = {
    (2011, 91): "ingles",
    (2011, 92): "ingles",
    (2011, 93): "ingles",
    (2011, 94): "ingles",
    (2011, 95): "espanhol",
    (2012, 94): "espanhol",
    (2016, 93): "ingles",
}


def definir_idioma(apps, schema_editor):
    Questao = apps.get_model("simulados", "Questao")
    RespostaTentativa = apps.get_model("simulados", "RespostaTentativa")
    ItemProvaCompartilhada = apps.get_model("simulados", "ItemProvaCompartilhada")
    for (ano, numero), idioma in IDIOMAS.items():
        chave = {"area": "Linguagens", "ano": ano, "numero": numero}
        for questao in Questao.objects.filter(idioma_estrangeiro="", **chave):
            certa = Questao.objects.filter(idioma_estrangeiro=idioma, **chave).first()
            if certa:
                RespostaTentativa.objects.filter(questao=questao).update(questao=certa)
                ItemProvaCompartilhada.objects.filter(questao=questao).update(questao=certa)
                questao.delete()
                continue
            questao.idioma_estrangeiro = idioma
            questao.save(update_fields=["idioma_estrangeiro"])


class Migration(migrations.Migration):

    dependencies = [
        ("simulados", "0006_corrige_area_das_questoes"),
    ]

    operations = [
        # Sem volta: não faz sentido devolver as questões ao sorteio dos dois idiomas.
        migrations.RunPython(definir_idioma, migrations.RunPython.noop),
    ]
