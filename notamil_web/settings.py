"""Configurações do projeto Notamil.

Em produção, ajuste pelas variáveis de ambiente (veja o README):
DJANGO_DEBUG, DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS e DJANGO_CSRF_ORIGINS.
"""
import os
from pathlib import Path

from django.contrib.messages import constants as message_constants
from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent


def _lista(nome, padrao=""):
    """Variável de ambiente separada por vírgula -> lista, ignorando itens vazios."""
    return [item.strip() for item in os.getenv(nome, padrao).split(",") if item.strip()]


# Fora de produção continua ligado: rode com DJANGO_DEBUG=1 na sua máquina.
DEBUG = os.getenv("DJANGO_DEBUG", "0") == "1"

# Sem chave no ambiente, gera uma aleatória a cada boot (derruba sessões do admin).
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY") or (
    "django-insecure-notamil-desenvolvimento" if DEBUG else get_random_secret_key()
)

ALLOWED_HOSTS = _lista("DJANGO_ALLOWED_HOSTS", "*")

# Domínios https do site — obrigatório para os formulários funcionarem atrás de HTTPS.
CSRF_TRUSTED_ORIGINS = _lista("DJANGO_CSRF_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "simulados.apps.SimuladosConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "notamil_web.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "notamil_web.wsgi.application"
ASGI_APPLICATION = "notamil_web.asgi.application"

# Banco: MySQL por padrão. Para rodar sem o servidor MySQL (testes rápidos, notebook
# sem o serviço ligado), use DJANGO_DB_ENGINE=sqlite.
if os.getenv("DJANGO_DB_ENGINE", "mysql") == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.getenv("DJANGO_DB_NAME", "notamil"),
            "USER": os.getenv("DJANGO_DB_USER", "root"),
            "PASSWORD": os.getenv("DJANGO_DB_PASSWORD", ""),
            "HOST": os.getenv("DJANGO_DB_HOST", "127.0.0.1"),
            "PORT": os.getenv("DJANGO_DB_PORT", "3306"),
            "OPTIONS": {
                "charset": "utf8mb4",
                # Modo estrito evita que o MySQL corte texto silenciosamente.
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            },
            "CONN_MAX_AGE": 60,
            "TEST": {"CHARSET": "utf8mb4", "COLLATION": "utf8mb4_unicode_ci"},
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise serve os arquivos estáticos direto pelo Django, sem precisar de Nginx.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

if not DEBUG:
    # O host fica atrás de um proxy https (Render, PythonAnywhere, Nginx...).
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = os.getenv("DJANGO_SSL_REDIRECT", "0") == "1"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

# Alinha as tags das mensagens com as classes de alerta do Bootstrap
MESSAGE_TAGS = {message_constants.ERROR: "danger"}
