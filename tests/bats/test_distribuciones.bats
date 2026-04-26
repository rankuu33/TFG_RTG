#!/usr/bin/env bats
# ASOFS - Tests de distribuciones y árboles

setup() {
    export MOUNTPOINT="/tmp/asofs_test_$$"
    export CONFIG="/tmp/asofs_config_$$.yaml"
    mkdir -p "$MOUNTPOINT"
    
    cat > "$CONFIG" << 'YAML'
seed: 123

root:
  # Distribución de permisos
  - name: "permisos"
    type: dir
    children:
      - generate:
          type: file
          count: 10
          pattern: "std_{n:02d}.txt"
          mode: "dist:standard"
          size: 100

      - generate:
          type: file
          count: 5
          pattern: "special_{n:02d}.bin"
          mode: "dist:special"
          size: 100

  # Distribución de tamaños
  - name: "tamanos"
    type: dir
    children:
      - generate:
          type: file
          count: 10
          pattern: "small_{n:02d}.dat"
          size: "dist:small"

      - generate:
          type: file
          count: 5
          pattern: "large_{n:02d}.dat"
          size: "dist:large"

  # Árbol de directorios
  - generate:
      type: tree
      count: 1
      pattern: "arbol"
      depth: 3
      breadth: 2
      files_per_dir: 2
      file_size: [100, 200]
YAML

    asofs mount "$MOUNTPOINT" -c "$CONFIG" &
    sleep 1
}

teardown() {
    fusermount -u "$MOUNTPOINT" 2>/dev/null || true
    rmdir "$MOUNTPOINT" 2>/dev/null || true
    rm -f "$CONFIG"
}

@test "genera ficheros con distribución de permisos standard" {
    count=$(ls "$MOUNTPOINT/permisos"/std_*.txt | wc -l)
    [ "$count" -eq 10 ]
}

@test "distribución standard produce permisos variados" {
    permisos=$(stat -c %a "$MOUNTPOINT/permisos"/std_*.txt | sort -u | wc -l)
    [ "$permisos" -gt 1 ]
}

@test "distribución special produce SUID/SGID" {
    suid_count=$(find "$MOUNTPOINT/permisos" -name "special_*" -perm -4000 | wc -l)
    sgid_count=$(find "$MOUNTPOINT/permisos" -name "special_*" -perm -2000 | wc -l)
    total=$((suid_count + sgid_count))
    [ "$total" -gt 0 ]
}

@test "genera ficheros con distribución de tamaños small" {
    count=$(ls "$MOUNTPOINT/tamanos"/small_*.dat | wc -l)
    [ "$count" -eq 10 ]
}

@test "distribución small produce ficheros pequeños" {
    for f in "$MOUNTPOINT/tamanos"/small_*.dat; do
        size=$(stat -c %s "$f")
        [ "$size" -lt 10000 ]
    done
}

@test "distribución large produce ficheros grandes" {
    large_count=0
    for f in "$MOUNTPOINT/tamanos"/large_*.dat; do
        size=$(stat -c %s "$f")
        if [ "$size" -gt 100000 ]; then
            large_count=$((large_count + 1))
        fi
    done
    [ "$large_count" -gt 0 ]
}

@test "árbol tiene estructura correcta" {
    [ -d "$MOUNTPOINT/arbol" ]
}

@test "árbol tiene profundidad correcta" {
    max_depth=$(find "$MOUNTPOINT/arbol" -type d -printf '%d\n' | sort -rn | head -1)
    [ "$max_depth" -ge 2 ]
}

@test "árbol tiene ficheros en cada nivel" {
    file_count=$(find "$MOUNTPOINT/arbol" -type f | wc -l)
    [ "$file_count" -gt 10 ]
}

@test "árbol tiene subdirectorios" {
    dir_count=$(find "$MOUNTPOINT/arbol" -type d | wc -l)
    [ "$dir_count" -gt 5 ]
}
