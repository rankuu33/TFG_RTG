#!/usr/bin/env bats
# ASOFS - Tests de generación masiva

setup() {
    export MOUNTPOINT="/tmp/asofs_test_$$"
    export CONFIG="/tmp/asofs_config_$$.yaml"
    mkdir -p "$MOUNTPOINT"
    
    cat > "$CONFIG" << 'YAML'
seed: 123

root:
  - generate:
      type: file
      count: 10
      pattern: "file_{n:03d}.txt"
      size: [50, 100]
  
  - generate:
      type: symlink
      count: 5
      pattern: "link_{n:02d}"
      target: "/no/existe_{n}.txt"
  
  - generate:
      type: fifo
      count: 3
      pattern: "pipe_{n}"
YAML

    asofs mount "$MOUNTPOINT" -c "$CONFIG" &
    sleep 1
}

teardown() {
    fusermount -u "$MOUNTPOINT" 2>/dev/null || true
    rmdir "$MOUNTPOINT" 2>/dev/null || true
    rm -f "$CONFIG"
}

@test "genera 10 ficheros con patrón numérico" {
    run ls "$MOUNTPOINT"/file_*.txt
    [ "$status" -eq 0 ]
    count=$(ls "$MOUNTPOINT"/file_*.txt | wc -l)
    [ "$count" -eq 10 ]
}

@test "ficheros generados tienen tamaño en rango" {
    for f in "$MOUNTPOINT"/file_*.txt; do
        size=$(stat -c %s "$f")
        [ "$size" -ge 50 ]
        [ "$size" -le 100 ]
    done
}

@test "genera 5 symlinks" {
    count=$(find "$MOUNTPOINT" -maxdepth 1 -type l | wc -l)
    [ "$count" -eq 5 ]
}

@test "genera 3 FIFOs" {
    count=$(find "$MOUNTPOINT" -maxdepth 1 -type p | wc -l)
    [ "$count" -eq 3 ]
}

@test "semilla produce resultados reproducibles" {
    size1=$(stat -c %s "$MOUNTPOINT/file_000.txt")
    
    fusermount -u "$MOUNTPOINT"
    sleep 1
    
    asofs mount "$MOUNTPOINT" -c "$CONFIG" &
    sleep 1
    
    size2=$(stat -c %s "$MOUNTPOINT/file_000.txt")
    [ "$size1" -eq "$size2" ]
}
