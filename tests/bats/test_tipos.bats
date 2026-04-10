#!/usr/bin/env bats
# ASOFS - Tests de tipos de ficheros

setup() {
    export MOUNTPOINT="/tmp/asofs_test_$$"
    export CONFIG="/tmp/asofs_config_$$.yaml"
    mkdir -p "$MOUNTPOINT"
    
    cat > "$CONFIG" << 'YAML'
root:
  - name: "regular.txt"
    type: file
    content: "fichero regular"
  
  - name: "directorio"
    type: dir
    children:
      - name: "dentro.txt"
        type: file
        content: "estoy dentro"
  
  - name: "enlace_valido"
    type: symlink
    target: "regular.txt"
  
  - name: "enlace_roto"
    type: symlink
    target: "/no/existe"
  
  - name: "tuberia"
    type: fifo
    mode: "0644"
YAML

    asofs mount "$MOUNTPOINT" -c "$CONFIG" &
    sleep 1
}

teardown() {
    fusermount -u "$MOUNTPOINT" 2>/dev/null || true
    rmdir "$MOUNTPOINT" 2>/dev/null || true
    rm -f "$CONFIG"
}

@test "fichero regular existe y es legible" {
    [ -f "$MOUNTPOINT/regular.txt" ]
    run cat "$MOUNTPOINT/regular.txt"
    [ "$status" -eq 0 ]
    [ "$output" = "fichero regular" ]
}

@test "directorio existe y contiene fichero" {
    [ -d "$MOUNTPOINT/directorio" ]
    [ -f "$MOUNTPOINT/directorio/dentro.txt" ]
}

@test "symlink válido apunta correctamente" {
    [ -L "$MOUNTPOINT/enlace_valido" ]
    run readlink "$MOUNTPOINT/enlace_valido"
    [ "$output" = "regular.txt" ]
}

@test "symlink válido es accesible" {
    run cat "$MOUNTPOINT/enlace_valido"
    [ "$status" -eq 0 ]
    [ "$output" = "fichero regular" ]
}

@test "symlink roto es detectado por find" {
    [ -L "$MOUNTPOINT/enlace_roto" ]
    run find "$MOUNTPOINT" -xtype l -name "enlace_roto"
    [[ "$output" == *"enlace_roto"* ]]
}

@test "FIFO existe y tiene tipo correcto" {
    [ -p "$MOUNTPOINT/tuberia" ]
}
