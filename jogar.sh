#!/usr/bin/env bash
# Inicia o ELDEN no Linux. Opções: --tela-cheia, --resolucao 1600x900, --qualidade baixa|media|alta|ultra
cd "$(dirname "$0")"
DEPS="import ursina, panda3d, pygame, numpy, PIL"
if [ -x .venv/bin/python ] && .venv/bin/python -c "$DEPS" 2>/dev/null; then
    PY=.venv/bin/python
elif PY=${PYTHON:-python3}; command -v "$PY" >/dev/null && "$PY" -c "$DEPS" 2>/dev/null; then
    :   # instalação antiga (pip --user) continua valendo
else
    echo "Dependências ausentes; executando a instalação..."
    ./instalar.sh --rapido || exit 1
    PY=.venv/bin/python
fi
exec "$PY" main.py "$@"
