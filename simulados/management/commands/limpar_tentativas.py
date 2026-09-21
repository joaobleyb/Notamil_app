"""Comando: python manage.py limpar_tentativas [--dias 30]"""
from django.core.management.base import BaseCommand

from ...services import limpar_tentativas_antigas


class Command(BaseCommand):
    help = "Remove tentativas antigas (por padrão, as abandonadas com mais de 30 dias)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dias", type=int, default=30, help="Idade mínima, em dias, para remover."
        )
        parser.add_argument(
            "--incluir-finalizadas",
            action="store_true",
            help="Remove também as tentativas já concluídas.",
        )
        parser.add_argument(
            "--incluir-provas",
            action="store_true",
            help="Remove códigos de turma antigos que ninguém respondeu.",
        )

    def handle(self, *args, **options):
        tentativas, provas = limpar_tentativas_antigas(
            dias=options["dias"],
            incluir_finalizadas=options["incluir_finalizadas"],
            incluir_provas=options["incluir_provas"],
        )
        if options["verbosity"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Removidas: {tentativas} tentativas, {provas} provas de turma."
                )
            )
