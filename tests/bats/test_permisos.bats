#!/usr/bin/env bats
# ASOFS - Tests de permisos

setup() {
    export MOUNTPOINT="/tmp/asofs_test_$$"
    export CONFIG="/tmp/asofs_config_$$.yaml"
    mkdir -p "$MOUNTPOINT"
    
    cat > "$CONFIG" << 'YAML'
root:
  - name: "normal.txt"
    type: file
    mode: "0644"
  
  - name: "ejecutable.sh"
    type: file
    mode: "0755"
  
  - name: "suid.sh"
    type: file
    mode: "4755"
  
  - name: "sgid.sh"
    type: file
    mode: "2755"
  
  - name: "sticky_dir"
    type: dir
    mode: "1755"
  
  - name: "secreto.txt"
    type: file
    mode: "0000"
  
  - name: "solo_lectura.txt"
    type: file
    mode: "0444"
YAML

    asofs mount "$MOUNTPOINT" -c "$CONFIG" &
    sleep 1
}

teardown() {
    fusermount -u "$MOUNTPOINT" 2>/dev/null || true
    rmdir "$MOUNTPOINT" 2>/dev/null || true
    rm -f "$CONFIG"
}

@test "permisos 644 correctos" {
    run stat -c %a "$MOUNTPOINT/normal.txt"
    [ "$output" = "644" ]
}

@test "permisos 755 correctos" {
    run stat -c %a "$MOUNTPOINT/ejecutable.sh"
    [ "$output" = "755" ]
}

@test "SUID detectado" {
    run stat -c %a "$MOUNTPOINT/suid.sh"
    [ "$output" = "4755" ]
}

@test "SUID encontrado con find" {
    run find "$MOUNTPOINT" -perm -4000
    [[ "$output" == *"suid.sh"* ]]
}

@test "SGID detectado" {
    run stat -c %a "$MOUNTPOINT/sgid.sh"
    [ "$output" = "2755" ]
}

@test "SGID encontrado con find" {
    run find "$MOUNTPOINT" -perm -2000
    [[ "$output" == *"sgid.sh"* ]]
}

@test "sticky bit en directorio" {
    run stat -c %a "$MOUNTPOINT/sticky_dir"
    [ "$output" = "1755" ]
}

@test "fichero sin permisos" {
    run stat -c %a "$MOUNTPOINT/secreto.txt"
    [ "$output" = "0" ]
}

@test "fichero solo lectura" {
    run stat -c %a "$MOUNTPOINT/solo_lectura.txt"
    [ "$output" = "444" ]
}
