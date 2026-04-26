#!/usr/bin/env bats
# ASOFS - Tests de tamaños grandes virtuales

setup() {
    export MOUNTPOINT="/tmp/asofs_test_$$"
    export CONFIG="/tmp/asofs_config_$$.yaml"
    mkdir -p "$MOUNTPOINT"
    
    cat > "$CONFIG" << 'YAML'
root:
  - name: "pequeno.txt"
    type: file
    size: "1KB"
    content_type: text

  - name: "mediano.bin"
    type: file
    size: "10MB"
    content_type: pattern

  - name: "grande.img"
    type: file
    size: "1GB"
    content_type: pattern

  - name: "enorme.raw"
    type: file
    size: "1TB"
    content_type: zeros
YAML

    asofs mount "$MOUNTPOINT" -c "$CONFIG" &
    sleep 1
}

teardown() {
    fusermount -u "$MOUNTPOINT" 2>/dev/null || true
    rmdir "$MOUNTPOINT" 2>/dev/null || true
    rm -f "$CONFIG"
}

@test "fichero 1KB tiene tamaño correcto" {
    size=$(stat -c %s "$MOUNTPOINT/pequeno.txt")
    [ "$size" -eq 1024 ]
}

@test "fichero 10MB tiene tamaño correcto" {
    size=$(stat -c %s "$MOUNTPOINT/mediano.bin")
    [ "$size" -eq 10485760 ]
}

@test "fichero 1GB tiene tamaño correcto" {
    size=$(stat -c %s "$MOUNTPOINT/grande.img")
    [ "$size" -eq 1073741824 ]
}

@test "fichero 1TB tiene tamaño correcto" {
    size=$(stat -c %s "$MOUNTPOINT/enorme.raw")
    [ "$size" -eq 1099511627776 ]
}

@test "find -size +500M encuentra ficheros grandes" {
    run find "$MOUNTPOINT" -size +500M
    [[ "$output" == *"grande.img"* ]]
    [[ "$output" == *"enorme.raw"* ]]
}

@test "find -size +500G encuentra ficheros enormes" {
    run find "$MOUNTPOINT" -size +500G
    [[ "$output" == *"enorme.raw"* ]]
}

@test "head puede leer fichero grande con pattern" {
    run head -c 100 "$MOUNTPOINT/grande.img"
    [ "$status" -eq 0 ]
}

@test "content_type pattern genera contenido repetido" {
    content=$(head -c 20 "$MOUNTPOINT/mediano.bin")
    [[ "$content" == *"ASOFS"* ]]
}
