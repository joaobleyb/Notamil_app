"""Comando: python manage.py seed_questoes"""
from django.core.management.base import BaseCommand

from ...services import carregar_questoes_iniciais


class Command(BaseCommand):
    help = "Carrega o banco de questões do ENEM a partir do arquivo de fixture."

    def handle(self, *args, **options):
        criadas, atualizadas = carregar_questoes_iniciais()
        self.stdout.write(
            self.style.SUCCESS(
                f"Questões carregadas: {criadas} criadas, {atualizadas} atualizadas."
            )
        )
