@echo off
REM Inicia o ELDEN no Windows. Opcoes: --tela-cheia, --resolucao 1600x900, --qualidade baixa|media|alta|ultra
cd /d "%~dp0"
set "DEPS=import ursina, panda3d, pygame, numpy, PIL"
if exist ".venv\Scripts\python.exe" ".venv\Scripts\python.exe" -c "%DEPS%" 2>nul && goto venv
REM instalacao antiga (pip --user) continua valendo
where py >nul 2>nul && (set "PY=py -3") || (set "PY=python")
%PY% -c "%DEPS%" 2>nul && goto rodar
echo Dependencias ausentes; executando a instalacao...
call instalar.bat --rapido || exit /b 1
:venv
set PY=".venv\Scripts\python.exe"
:rodar
%PY% main.py %*
