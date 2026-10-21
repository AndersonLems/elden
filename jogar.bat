@echo off
REM Inicia o ELDEN no Windows. Opcoes: --tela-cheia, --resolucao 1600x900, --qualidade baixa|media|alta|ultra
cd /d "%~dp0"
where py >nul 2>nul && (set PY=py -3) || (set PY=python)
%PY% -c "import ursina, panda3d, pygame, numpy, PIL" 2>nul || call instalar.bat --rapido
%PY% main.py %*
