#!/bin/bash
# NotaMil - instalacao e execucao em um comando (macOS e Linux).
set -e
cd "$(dirname "$0")"

erro() {
    echo
    echo "=========================================="
    echo "  Algo deu errado. Leia a mensagem acima."
    echo "=========================================="
    exit 1
}
trap erro ERR

echo "=========================================="
echo "  NotaMil - instalacao e execucao"
echo "=========================================="
echo

# O Django 5 exige Python 3.10 ou mais novo.
PY=""
for candidato in python3 python; do
    if command -v "$candidato" >/dev/null 2>&1 \
        && "$candidato" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
        PY="$candidato"
        break
    fi
done

if [ -z "$PY" ]; then
    echo "Python 3.10 ou mais novo nao encontrado."
    echo "No macOS:  brew install python"
    echo "Ou baixe em https://www.python.org/downloads/"
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "[1/4] Criando o ambiente virtual..."
    "$PY" -m venv .venv
else
    echo "[1/4] Ambiente virtual ja existe."
fi

VPY=".venv/bin/python"
[ -x "$VPY" ] || VPY=".venv/Scripts/python.exe"

echo "[2/4] Instalando as dependencias..."
"$VPY" -m pip install --upgrade pip --quiet
"$VPY" -m pip install -r requirements.txt --quiet

PRIMEIRA_VEZ=0
[ -f "db.sqlite3" ] || PRIMEIRA_VEZ=1

echo "[3/4] Preparando o banco de dados..."
"$VPY" manage.py migrate --noinput
if [ "$PRIMEIRA_VEZ" = "1" ]; then
    echo "      Carregando as 2643 questoes do ENEM. Demora ate 1 minuto, aguarde..."
    "$VPY" manage.py seed_questoes
else
    echo "      Questoes ja carregadas."
fi

export DJANGO_DEBUG=1
echo
echo "[4/4] Servidor iniciando. Abra no navegador:"
echo
echo "      http://127.0.0.1:8000/"
echo
echo "      Para parar o servidor: Control + C"
echo

# Sem o trap: o Control + C do professor nao e um erro.
trap - ERR
set +e
"$VPY" manage.py runserver
