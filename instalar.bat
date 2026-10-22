@echo off
setlocal
REM Instala o ELDEN no Windows: Python 3.12 (winget ou python.org, se faltar), ambiente virtual em .venv,
REM dependencias e pre-geracao dos recursos.
cd /d "%~dp0"
set "PYVER=3.12.10"

call :achar_python && goto tem_python
echo == Python 3.10+ nao encontrado: instalando o Python %PYVER% ==
where winget >nul 2>nul && winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
call :achar_python && goto tem_python
echo == Baixando o instalador em python.org ==
set "INST=%TEMP%\python-%PYVER%-amd64.exe"
set "URL=https://www.python.org/ftp/python/%PYVER%/python-%PYVER%-amd64.exe"
del "%INST%" >nul 2>nul
curl.exe -fL -o "%INST%" "%URL%" 2>nul || powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; Invoke-WebRequest -UseBasicParsing '%URL%' -OutFile '%INST%'"
if not exist "%INST%" goto erro_python
"%INST%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_pip=1 || goto erro_python
del "%INST%" >nul 2>nul
call :achar_python && goto tem_python
goto erro_python

:tem_python
echo Python: %PY%
if not exist ".venv\Scripts\python.exe" (
    echo == Criando o ambiente virtual em .venv ==
    "%PY%" -m venv .venv || goto erro
)
set "VPY=.venv\Scripts\python.exe"
echo == Instalando dependencias ==
"%VPY%" -m pip install --upgrade pip -q
"%VPY%" -m pip install -r requirements.txt || goto erro
echo == Gerando sprites, sons e musicas (so na primeira vez) ==
"%VPY%" tools\gerar_assets.py %*
echo Instalacao concluida. Para jogar: jogar.bat
if /i not "%~1"=="--rapido" pause
exit /b 0

REM Procura um Python 3.10+ (launcher py, PATH ou a pasta padrao da instalacao por usuario) e guarda o caminho em PY.
:achar_python
set "PY="
for %%c in ("py -3" python python3) do call :testar %%~c
for %%v in (314 313 312 311 310) do if exist "%LOCALAPPDATA%\Programs\Python\Python%%v\python.exe" call :testar "%LOCALAPPDATA%\Programs\Python\Python%%v\python.exe"
if defined PY exit /b 0
exit /b 1

:testar
if defined PY exit /b 0
for /f "delims=" %%i in ('call %* -c "import sys; print(sys.executable) if sys.version_info >= (3, 10) else None" 2^>nul') do set "PY=%%i"
exit /b 0

:erro_python
echo Nao foi possivel instalar o Python automaticamente.
echo Instale o Python 3.10+ em https://www.python.org/downloads/ (marque "Add Python to PATH") e rode de novo.
pause
exit /b 1

:erro
echo Falha ao instalar as dependencias. Verifique a conexao com a internet e rode de novo.
pause
exit /b 1
