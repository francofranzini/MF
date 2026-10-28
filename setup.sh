#!/usr/bin/env bash
# Prepara el entorno para correr el proyecto.
# Uso: ./setup.sh   (después: ./setup.sh run  para abrir la interfaz)
set -euo pipefail

cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
    echo "Error: no se encontró $PYTHON. Instalá Python 3.10 o superior." >&2
    exit 1
fi

# tkinter no se instala con pip: hace falta el paquete del sistema
if ! "$PYTHON" -c "import tkinter" >/dev/null 2>&1; then
    echo "Error: falta tkinter. Instalalo con:" >&2
    echo "  Debian/Ubuntu: sudo apt install python3-tk python3-venv" >&2
    echo "  Fedora:        sudo dnf install python3-tkinter" >&2
    echo "  Arch:          sudo pacman -S tk" >&2
    echo "  macOS (brew):  brew install python-tk" >&2
    exit 1
fi

if [ ! -d .venv ]; then
    echo "Creando entorno virtual en .venv..."
    "$PYTHON" -m venv .venv
fi

echo "Instalando dependencias..."
.venv/bin/python -m pip install --upgrade pip >/dev/null
.venv/bin/python -m pip install -r requirements.txt

echo
echo "Listo. Para usar el proyecto:"
echo "  source .venv/bin/activate"
echo "  python interfaz.py   # interfaz gráfica"
echo "  python TP1V1.py      # simulación simple + orbita_tierra.gif"

if [ "${1:-}" = "run" ]; then
    exec .venv/bin/python interfaz.py
fi
