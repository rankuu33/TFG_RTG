#!/usr/bin/env bats
# ASOFS - Tests de hardlinks

setup() {
    export MOUNTPOINT="/tmp/asofs_test_$$"
    export CONFIG="/tmp/asofs_config_$$.yaml"
    mkdir -p "$MOUNTPOINT"
    
    cat > "$CONFIG" << 'YAML'
root:
  - name: "original.txt"
    type: file
    content: "contenido compartido"
  
  - name: "hardlink1.txt"
    type: hardlink
    target: "/original.txt"
  
  - name: "hardlink2.txt"
    type: hardlink
    target: "/original.txt"
YAML

    asofs mount "$MOUNTPOINT" -c "$CONFIG" &
    sleep 1
}

teardown() {
    fusermount -u "$MOUNTPOINT" 2>/dev/null || true
    rmdir "$MOUNTPOINT" 2>/dev/null || true
    rm -f "$CONFIG"
}

@test "hardlinks tienen mismo inode" {
    inode1=$(stat -c %i "$MOUNTPOINT/original.txt")
    inode2=$(stat -c %i "$MOUNTPOINT/hardlink1.txt")
    inode3=$(stat -c %i "$MOUNTPOINT/hardlink2.txt")
    [ "$inode1" = "$inode2" ]
    [ "$inode1" = "$inode3" ]
}

@test "nlink es 3 para fichero con 2 hardlinks" {
    run stat -c %h "$MOUNTPOINT/original.txt"
    [ "$output" = "3" ]
}

@test "hardlinks tienen mismo contenido" {
    content1=$(cat "$MOUNTPOINT/original.txt")
    content2=$(cat "$MOUNTPOINT/hardlink1.txt")
    content3=$(cat "$MOUNTPOINT/hardlink2.txt")
    [ "$content1" = "$content2" ]
    [ "$content1" = "$content3" ]
}

@test "find -inum encuentra todos los hardlinks" {
    inode=$(stat -c %i "$MOUNTPOINT/original.txt")
    run find "$MOUNTPOINT" -inum "$inode"
    [[ "$output" == *"original.txt"* ]]
    [[ "$output" == *"hardlink1.txt"* ]]
    [[ "$output" == *"hardlink2.txt"* ]]
}
