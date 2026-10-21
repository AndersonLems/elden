#!/usr/bin/env bash
# Inicia o ELDEN no Linux. Opções: --tela-cheia, --resolucao 1600x900, --qualidade baixa|media|alta|ultra
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
if ! "$PY" -c "import ursina, panda3d, pygame, numpy, PIL" 2>/dev/null; then
    echo "Dependências ausentes; executando a instalação..."
    ./instalar.sh --rapido || exit 1
fi
exec "$PY" main.py "$@"
