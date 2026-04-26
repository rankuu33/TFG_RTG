#!/usr/bin/env bats
# ASOFS - Tests de usuarios y grupos ficticios

setup() {
    export MOUNTPOINT="/tmp/asofs_test_$$"
    export CONFIG="/tmp/asofs_config_$$.yaml"
    mkdir -p "$MOUNTPOINT"
    
    cat > "$CONFIG" << 'YAML'
users:
  alice: 1001
  bob: 1002
  admin: 9000

groups:
  students: 2001
  staff: 2002

root:
  - name: "alice_file.txt"
    type: file
    content: "Fichero de Alice"
    owner: alice
    group: students

  - name: "bob_file.txt"
    type: file
    content: "Fichero de Bob"
    owner: bob
    group: students

  - name: "admin_file.txt"
    type: file
    content: "Fichero de admin"
    owner: admin
    group: staff
    mode: "0600"

  - name: "proyecto"
    type: dir
    owner: admin
    group: staff
    mode: "0755"
    children:
      - name: "doc.txt"
        type: file
        owner: alice
        group: students
YAML

    asofs mount "$MOUNTPOINT" -c "$CONFIG" &
    sleep 1
}

teardown() {
    fusermount -u "$MOUNTPOINT" 2>/dev/null || true
    rmdir "$MOUNTPOINT" 2>/dev/null || true
    rm -f "$CONFIG"
}

@test "fichero tiene uid de alice (1001)" {
    uid=$(stat -c %u "$MOUNTPOINT/alice_file.txt")
    [ "$uid" -eq 1001 ]
}

@test "fichero tiene uid de bob (1002)" {
    uid=$(stat -c %u "$MOUNTPOINT/bob_file.txt")
    [ "$uid" -eq 1002 ]
}

@test "fichero tiene uid de admin (9000)" {
    uid=$(stat -c %u "$MOUNTPOINT/admin_file.txt")
    [ "$uid" -eq 9000 ]
}

@test "fichero tiene gid de students (2001)" {
    gid=$(stat -c %g "$MOUNTPOINT/alice_file.txt")
    [ "$gid" -eq 2001 ]
}

@test "fichero tiene gid de staff (2002)" {
    gid=$(stat -c %g "$MOUNTPOINT/admin_file.txt")
    [ "$gid" -eq 2002 ]
}

@test "directorio tiene owner correcto" {
    uid=$(stat -c %u "$MOUNTPOINT/proyecto")
    [ "$uid" -eq 9000 ]
}

@test "fichero dentro de directorio tiene su propio owner" {
    uid=$(stat -c %u "$MOUNTPOINT/proyecto/doc.txt")
    [ "$uid" -eq 1001 ]
}

@test "find -user encuentra ficheros por uid" {
    count=$(find "$MOUNTPOINT" -user 1001 | wc -l)
    [ "$count" -eq 2 ]
}

@test "find -group encuentra ficheros por gid" {
    count=$(find "$MOUNTPOINT" -group 2001 | wc -l)
    [ "$count" -eq 3 ]
}
