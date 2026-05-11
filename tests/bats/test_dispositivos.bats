#!/usr/bin/env bats
# ASOFS - Tests de dispositivos char y block

setup() {
    export MOUNTPOINT="/tmp/asofs_test_$$"
    export CONFIG="/tmp/asofs_config_$$.yaml"
    mkdir -p "$MOUNTPOINT"
    
    cat > "$CONFIG" << 'YAML'
root:
  - name: "null"
    type: char
    major: 1
    minor: 3
    mode: "0666"

  - name: "zero"
    type: char
    major: 1
    minor: 5
    mode: "0666"

  - name: "sda"
    type: block
    major: 8
    minor: 0
    mode: "0660"

  - name: "sda1"
    type: block
    major: 8
    minor: 1
    mode: "0660"
YAML

    asofs mount "$MOUNTPOINT" -c "$CONFIG" &
    sleep 1
    
    # Esperar a que el mount esté listo
    for i in {1..10}; do
        if mountpoint -q "$MOUNTPOINT" 2>/dev/null; then
            break
        fi
        sleep 0.2
    done
}

teardown() {
    fusermount -u "$MOUNTPOINT" 2>/dev/null || true
    rmdir "$MOUNTPOINT" 2>/dev/null || true
    rm -f "$CONFIG"
}

@test "mount está listo" {
    mountpoint -q "$MOUNTPOINT"
}

@test "dispositivo char existe" {
    [ -c "$MOUNTPOINT/null" ]
}

@test "dispositivo block existe" {
    [ -b "$MOUNTPOINT/sda" ]
}

@test "find -type c encuentra dispositivos char" {
    count=$(find "$MOUNTPOINT" -type c | wc -l)
    [ "$count" -eq 2 ]
}

@test "find -type b encuentra dispositivos block" {
    count=$(find "$MOUNTPOINT" -type b | wc -l)
    [ "$count" -eq 2 ]
}

@test "dispositivo char tiene major:minor correctos" {
    run stat -c "%t:%T" "$MOUNTPOINT/null"
    [ "$output" = "1:3" ]
}

@test "dispositivo block tiene major:minor correctos" {
    run stat -c "%t:%T" "$MOUNTPOINT/sda"
    [ "$output" = "8:0" ]
}

@test "dispositivo char tiene permisos correctos" {
    run stat -c %a "$MOUNTPOINT/zero"
    [ "$output" = "666" ]
}

@test "dispositivo block tiene permisos correctos" {
    run stat -c %a "$MOUNTPOINT/sda1"
    [ "$output" = "660" ]
}
