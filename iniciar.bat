@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo   NotaMil - instalacao e execucao
echo ==========================================
echo.

set "PY=py -3"
%PY% --version >nul 2>&1 || set "PY=python"
%PY% --version >nul 2>&1
if errorlevel 1 (
    echo Python nao encontrado.
    echo Instale em https://www.python.org/downloads/ marcando "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/4] Criando o ambiente virtual...
    %PY% -m venv .venv || goto :erro
) else (
    echo [1/4] Ambiente virtual ja existe.
)
set "VPY=.venv\Scripts\python.exe"

echo [2/4] Instalando as dependencias...
"%VPY%" -m pip install --upgrade pip --quiet
"%VPY%" -m pip install -r requirements.txt --quiet || goto :erro

set "PRIMEIRA_VEZ="
if not exist "db.sqlite3" set "PRIMEIRA_VEZ=1"

echo [3/4] Preparando o banco de dados...
"%VPY%" manage.py migrate --noinput || goto :erro
if defined PRIMEIRA_VEZ (
    echo       Carregando as 2643 questoes do ENEM. Demora ate 1 minuto, aguarde...
    "%VPY%" manage.py seed_questoes || goto :erro
) else (
    echo       Questoes ja carregadas.
)

set "DJANGO_DEBUG=1"
echo.
echo [4/4] Servidor iniciando. Abra no navegador:
echo.
echo       http://127.0.0.1:8000/
echo.
echo       Para parar o servidor: Ctrl + C
echo.
"%VPY%" manage.py runserver
pause
exit /b 0

:erro
echo.
echo ==========================================
echo   Algo deu errado. Leia a mensagem acima.
echo ==========================================
pause
exit /b 1
