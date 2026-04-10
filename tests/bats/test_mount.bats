#!/usr/bin/env bats
# ASOFS - Tests de montaje básico

setup() {
    export MOUNTPOINT="/tmp/asofs_test_$$"
    mkdir -p "$MOUNTPOINT"
}

teardown() {
    fusermount -u "$MOUNTPOINT" 2>/dev/null || true
    rmdir "$MOUNTPOINT" 2>/dev/null || true
}

@test "asofs se monta correctamente" {
    asofs mount "$MOUNTPOINT" &
    sleep 1
    mountpoint -q "$MOUNTPOINT"
}

@test "asofs se desmonta con fusermount" {
    asofs mount "$MOUNTPOINT" &
    sleep 1
    fusermount -u "$MOUNTPOINT"
    ! mountpoint -q "$MOUNTPOINT"
}

@test "punto de montaje vacío sin config muestra ejemplo" {
    asofs mount "$MOUNTPOINT" &
    sleep 1
    [ -f "$MOUNTPOINT/hello.txt" ]
}

@test "hello.txt tiene contenido correcto" {
    asofs mount "$MOUNTPOINT" &
    sleep 1
    run cat "$MOUNTPOINT/hello.txt"
    [ "$status" -eq 0 ]
    [[ "$output" == *"ASOFS"* ]]
}
