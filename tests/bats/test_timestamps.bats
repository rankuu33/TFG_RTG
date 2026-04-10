#!/usr/bin/env bats
# ASOFS - Tests de timestamps

setup() {
    export MOUNTPOINT="/tmp/asofs_test_$$"
    export CONFIG="/tmp/asofs_config_$$.yaml"
    mkdir -p "$MOUNTPOINT"
    
    cat > "$CONFIG" << 'YAML'
root:
  - name: "reciente.txt"
    type: file
    content: "hoy"
    mtime: "now"
  
  - name: "ayer.txt"
    type: file
    content: "ayer"
    mtime: "-1d"
  
  - name: "semana.txt"
    type: file
    content: "hace una semana"
    mtime: "-7d"
  
  - name: "mes.txt"
    type: file
    content: "hace un mes"
    mtime: "-30d"
  
  - name: "antiguo.txt"
    type: file
    content: "muy viejo"
    mtime: "-365d"
  
  - name: "futuro.txt"
    type: file
    content: "del futuro"
    mtime: "+30d"
YAML

    asofs mount "$MOUNTPOINT" -c "$CONFIG" &
    sleep 1
}

teardown() {
    fusermount -u "$MOUNTPOINT" 2>/dev/null || true
    rmdir "$MOUNTPOINT" 2>/dev/null || true
    rm -f "$CONFIG"
}

@test "find -mtime 0 encuentra ficheros de hoy" {
    run find "$MOUNTPOINT" -maxdepth 1 -mtime 0 -name "reciente.txt"
    [[ "$output" == *"reciente.txt"* ]]
}

@test "find -mtime +7 encuentra ficheros de hace más de una semana" {
    run find "$MOUNTPOINT" -maxdepth 1 -mtime +7 -type f
    [[ "$output" == *"mes.txt"* ]]
    [[ "$output" == *"antiguo.txt"* ]]
}

@test "find -mtime -7 encuentra ficheros recientes" {
    run find "$MOUNTPOINT" -maxdepth 1 -mtime -7 -type f
    [[ "$output" == *"reciente.txt"* ]]
    [[ "$output" == *"ayer.txt"* ]]
}

@test "fichero del futuro tiene fecha futura" {
    fecha_fichero=$(stat -c %Y "$MOUNTPOINT/futuro.txt")
    fecha_ahora=$(date +%s)
    [ "$fecha_fichero" -gt "$fecha_ahora" ]
}

@test "fichero antiguo tiene fecha pasada" {
    fecha_fichero=$(stat -c %Y "$MOUNTPOINT/antiguo.txt")
    fecha_limite=$(($(date +%s) - 300*86400))
    [ "$fecha_fichero" -lt "$fecha_limite" ]
}
