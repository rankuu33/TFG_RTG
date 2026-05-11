#!/usr/bin/env bats
# ASOFS - Tests de nombres problemáticos

setup() {
    export MOUNTPOINT="/tmp/asofs_test_$$"
    export CONFIG="/tmp/asofs_config_$$.yaml"
    mkdir -p "$MOUNTPOINT"
    
    cat > "$CONFIG" << 'YAML'
root:
  - name: "fichero con espacios.txt"
    type: file
    content: "espacios"

  - name: "archivo-guion.txt"
    type: file
    content: "guion"

  - name: "-inicio_guion.txt"
    type: file
    content: "empieza con guion"

  - name: "información.txt"
    type: file
    content: "acentos"

  - name: "日本語.txt"
    type: file
    content: "japones"

  - name: "emoji_🎉.txt"
    type: file
    content: "emoji"

  - name: "Ñoño.txt"
    type: file
    content: "ene"

  - name: ".oculto"
    type: file
    content: "oculto"

  - name: "precio$50.txt"
    type: file
    content: "dolar"

  - name: "nombre_muy_largo_que_supera_los_cincuenta_caracteres_facilmente.txt"
    type: file
    content: "largo"
YAML

    asofs mount "$MOUNTPOINT" -c "$CONFIG" &
    sleep 1
}

teardown() {
    fusermount -u "$MOUNTPOINT" 2>/dev/null || true
    rmdir "$MOUNTPOINT" 2>/dev/null || true
    rm -f "$CONFIG"
}

@test "fichero con espacios existe" {
    [ -f "$MOUNTPOINT/fichero con espacios.txt" ]
}

@test "fichero con espacios es legible" {
    run cat "$MOUNTPOINT/fichero con espacios.txt"
    [ "$output" = "espacios" ]
}

@test "fichero que empieza con guion existe" {
    [ -f "$MOUNTPOINT/-inicio_guion.txt" ]
}

@test "fichero con acentos existe" {
    [ -f "$MOUNTPOINT/información.txt" ]
}

@test "fichero con japonés existe" {
    [ -f "$MOUNTPOINT/日本語.txt" ]
}

@test "fichero con emoji existe" {
    [ -f "$MOUNTPOINT/emoji_🎉.txt" ]
}

@test "fichero con Ñ existe" {
    [ -f "$MOUNTPOINT/Ñoño.txt" ]
}

@test "fichero oculto existe" {
    [ -f "$MOUNTPOINT/.oculto" ]
}

@test "fichero oculto no aparece en ls normal" {
    run ls "$MOUNTPOINT"
    [[ "$output" != *".oculto"* ]]
}

@test "fichero oculto aparece en ls -a" {
    run ls -a "$MOUNTPOINT"
    [[ "$output" == *".oculto"* ]]
}

@test "fichero con dolar existe" {
    [ -f "$MOUNTPOINT/precio\$50.txt" ]
}

@test "fichero con nombre largo existe" {
    [ -f "$MOUNTPOINT/nombre_muy_largo_que_supera_los_cincuenta_caracteres_facilmente.txt" ]
}

@test "find encuentra ficheros con espacios" {
    count=$(find "$MOUNTPOINT" -name "*espacios*" | wc -l)
    [ "$count" -eq 1 ]
}

@test "find encuentra ficheros unicode" {
    count=$(find "$MOUNTPOINT" -name "*.txt" | wc -l)
    [ "$count" -ge 8 ]
}
