#!/usr/bin/env bash
# Instala o ELDEN no Linux: Python 3.10+ (pelo gerenciador de pacotes, se faltar), ambiente virtual em .venv,
# dependências e pré-geração dos recursos. Use PYTHON=/caminho/python para forçar um interpretador.
set -e
cd "$(dirname "$0")"

versao_ok() {   # $1 = interpretador; aceita 3.10+
    "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null
}

achar_python() {
    for c in ${PYTHON:-} python3 python3.14 python3.13 python3.12 python3.11 python3.10 python; do
        if command -v "$c" >/dev/null && versao_ok "$c"; then
            PY=$(command -v "$c")
            return 0
        fi
    done
    return 1
}

SUDO=""
[ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null && SUDO="sudo"

instalar_pacotes() {   # $1 = nome no apt; $2 = dnf; $3 = pacman; $4 = zypper; $5 = apk
    if command -v apt-get >/dev/null; then
        $SUDO apt-get update -qq && $SUDO apt-get install -y $1
    elif command -v dnf >/dev/null; then
        $SUDO dnf install -y $2
    elif command -v pacman >/dev/null; then
        $SUDO pacman -Sy --needed --noconfirm $3
    elif command -v zypper >/dev/null; then
        $SUDO zypper --non-interactive install $4
    elif command -v apk >/dev/null; then
        $SUDO apk add $5
    else
        return 1
    fi
}

if ! achar_python; then
    echo "== Instalando o Python pelo gerenciador de pacotes (pode pedir a senha) =="
    instalar_pacotes "python3 python3-pip python3-venv" "python3 python3-pip" "python python-pip" "python3 python3-pip" "python3 py3-pip" ||
        { echo "Gerenciador de pacotes não reconhecido. Instale o Python 3.10+ manualmente e rode de novo."; exit 1; }
    achar_python || { echo "Python 3.10+ não encontrado mesmo após a instalação."; exit 1; }
fi
# o Ursina chama "which" ao iniciar; instalações mínimas (Arch, contêineres) podem não ter
command -v which >/dev/null || instalar_pacotes debianutils which which which which || true
echo "Python: $PY ($("$PY" --version 2>&1))"

# ambiente virtual próprio do jogo (não mexe nos pacotes do sistema)
if [ ! -x .venv/bin/python ]; then
    echo "== Criando o ambiente virtual em .venv =="
    if ! "$PY" -m venv .venv 2>/dev/null; then
        rm -rf .venv
        # Debian/Ubuntu separam o venv num pacote próprio (python3.X-venv)
        if command -v apt-get >/dev/null; then
            VER=$("$PY" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')
            $SUDO apt-get install -y "python$VER-venv" || $SUDO apt-get install -y python3-venv || true
        fi
        "$PY" -m venv .venv 2>/dev/null || rm -rf .venv
    fi
fi

if [ -x .venv/bin/python ]; then
    VPY=.venv/bin/python
    echo "== Instalando dependências =="
    "$VPY" -m pip install --upgrade pip -q
    "$VPY" -m pip install -r requirements.txt
else
    # sem venv (ex.: sem sudo para instalar python3-venv): instala no usuário, como antes
    VPY=$PY
    echo "== Sem ambiente virtual; instalando dependências no usuário (pip --user) =="
    if ! "$VPY" -m pip install --user -r requirements.txt 2>/dev/null; then
        "$VPY" -m pip install --user --break-system-packages -r requirements.txt
    fi
fi

echo "== Gerando sprites, sons e músicas (só na primeira vez) =="
"$VPY" tools/gerar_assets.py "$@"
chmod +x jogar.sh
echo "Instalação concluída. Para jogar: ./jogar.sh"
