@echo off
REM Instala as dependências do ELDEN no Windows e pré-gera os recursos.
cd /d "%~dp0"
where py >nul 2>nul && (set PY=py -3) || (set PY=python)
echo == Instalando dependencias ==
%PY% -m pip install --user -r requirements.txt || goto erro
echo == Gerando sprites, sons e musicas (so na primeira vez) ==
%PY% tools\gerar_assets.py %*
echo Instalacao concluida. Para jogar: jogar.bat
pause
exit /b 0
:erro
echo Falha ao instalar. Verifique se o Python 3.10+ esta instalado (marque "Add to PATH").
pause
exit /b 1
