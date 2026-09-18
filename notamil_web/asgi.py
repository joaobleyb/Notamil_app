"""Configuração ASGI do projeto Notamil."""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "notamil_web.settings")

application = get_asgi_application()
