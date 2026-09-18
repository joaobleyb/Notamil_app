"""Configuração WSGI do projeto Notamil."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "notamil_web.settings")

application = get_wsgi_application()
