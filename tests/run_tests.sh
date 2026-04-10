#!/bin/bash
# ASOFS - Ejecutar todos los tests BATS

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BATS_DIR="$SCRIPT_DIR/bats"

echo "=========================================="
echo "ASOFS - Suite de tests"
echo "=========================================="
echo

# Verificar que ASOFS está instalado
if ! command -v asofs &> /dev/null; then
    echo "ERROR: asofs no está instalado"
    echo "Ejecuta: pip install -e ."
    exit 1
fi

# Verificar que BATS está instalado
if ! command -v bats &> /dev/null; then
    echo "ERROR: bats no está instalado"
    echo "Ejecuta: sudo apt install bats"
    exit 1
fi

# Ejecutar tests
if [ "$1" ]; then
    # Test específico
    bats "$BATS_DIR/$1"
else
    # Todos los tests
    bats "$BATS_DIR"/*.bats
fi
