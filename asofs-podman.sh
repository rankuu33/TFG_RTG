#!/bin/bash
set -e

IMAGE_NAME="asofs-container"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

build_image() {
    echo "Construyendo imagen $IMAGE_NAME..."
    podman build \
        -t "$IMAGE_NAME" \
        -f container/Containerfile \
        "$SCRIPT_DIR"
    echo "Imagen construida correctamente"
}

check_image() {
    if ! podman image exists "$IMAGE_NAME" 2>/dev/null; then
        echo "Imagen no encontrada. Construyendo..."
        build_image
    fi
}

if [ $# -eq 0 ]; then
    echo "ASOFS - Ejecución con Podman"
    echo ""
    echo "Uso:"
    echo "  $0 <fichero.yaml>        Ejecutar ASOFS con la configuración"
    echo "  $0 --build               Solo reconstruir la imagen"
    echo ""
    echo "Ejemplos:"
    echo "  $0 examples/usuarios.yaml"
    exit 0
fi

case "$1" in
    --build)
        build_image
        exit 0
        ;;
esac

CONFIG_FILE="$1"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: no se encuentra '$CONFIG_FILE'"
    exit 1
fi

if ! command -v podman &>/dev/null; then
    echo "Error: Podman no está instalado"
    echo "Instalar con: sudo apt install podman"
    exit 1
fi

check_image

CONFIG_ABS="$(cd "$(dirname "$CONFIG_FILE")" && pwd)/$(basename "$CONFIG_FILE")"
CONFIG_BASENAME="$(basename "$CONFIG_FILE")"

echo "Iniciando ASOFS en contenedor..."
echo ""

podman run -it --rm \
    --device /dev/fuse \
    --cap-add SYS_ADMIN \
    --security-opt label=disable \
    -v "$CONFIG_ABS:/config/$CONFIG_BASENAME:ro" \
    "$IMAGE_NAME" \
    "/config/$CONFIG_BASENAME"
