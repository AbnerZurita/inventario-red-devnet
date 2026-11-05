#!/usr/bin/env bash
# setup.sh - Prepara el entorno del proyecto en la DEVASC VM (Linux).
# Uso: ./setup.sh
set -euo pipefail   # detener el script ante cualquier error

cd "$(dirname "$0")"
echo "== Directorio del proyecto: $(pwd)"

# 1. Verificar Python 3
if ! command -v python3 >/dev/null; then
    echo "ERROR: python3 no está instalado (sudo apt-get install python3)"; exit 1
fi
echo "== $(python3 -V) en $(which python3)"

# 2. Entorno virtual aislado (buena práctica: no ensuciar el Python del sistema)
if [ ! -d venv ]; then
    python3 -m venv venv
    echo "== Entorno virtual 'venv' creado"
fi
# shellcheck disable=SC1091
source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo "== Dependencias instaladas:"; pip freeze

# 3. Archivo de credenciales
if [ ! -f .env ]; then
    cp .env.example .env
    echo "== Se creó .env a partir de .env.example (revisa las credenciales)"
fi

# 4. Carpetas de trabajo
mkdir -p salidas logs

# 5. Permisos (principio de mínimo privilegio)
chmod 600 .env                      # solo el dueño lee/escribe credenciales
chmod 755 inventario.py setup.sh    # ejecutables
chmod 644 config.yaml requirements.txt README.md
chmod 750 salidas logs              # dueño y grupo; otros sin acceso
echo "== Permisos aplicados:"
ls -la .env inventario.py setup.sh config.yaml
ls -ld salidas logs

echo
echo "Listo. Ejecuta:  source venv/bin/activate && ./inventario.py"
