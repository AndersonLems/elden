#!/usr/bin/env bash
# Instala as dependências do ELDEN no Linux e pré-gera os recursos.
set -e
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
command -v "$PY" >/dev/null || { echo "Python 3 não encontrado. Instale python3 (3.10+)."; exit 1; }
echo "== Instalando dependências (pip --user) =="
if ! "$PY" -m pip install --user -r requirements.txt 2>/dev/null; then
    echo "(ambiente gerenciado pelo sistema: usando --break-system-packages)"
    "$PY" -m pip install --user --break-system-packages -r requirements.txt
fi
echo "== Gerando sprites, sons e músicas (só na primeira vez) =="
"$PY" tools/gerar_assets.py "$@"
chmod +x jogar.sh
echo "Instalação concluída. Para jogar: ./jogar.sh"
