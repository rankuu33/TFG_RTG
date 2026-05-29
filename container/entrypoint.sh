#!/bin/bash
set -e

CONFIG_FILE="${1:-}"
MOUNTPOINT="${ASOFS_MOUNTPOINT:-/mnt/asofs}"

if [ -z "$CONFIG_FILE" ]; then
    echo "ASOFS - Contenedor con usuarios ficticios"
    echo ""
    echo "Uso: podman run ... asofs-container <fichero.yaml>"
    echo ""
    echo "Ejemplos disponibles en /opt/asofs/examples/"
    exec /bin/bash
fi

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: no se encuentra el fichero '$CONFIG_FILE'"
    exit 1
fi

echo "=== ASOFS - Contenedor con usuarios ficticios ==="
echo ""

# Paso 1: Registrar usuarios y grupos del YAML
echo "[1/3] Registrando usuarios y grupos del YAML..."

python3 - "$CONFIG_FILE" << 'PYTHON_SCRIPT'
import sys
import yaml
import pwd
import grp

config_path = sys.argv[1]

with open(config_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

users = config.get('users', {})
groups = config.get('groups', {})

existing_users = {p.pw_name for p in pwd.getpwall()}
existing_uids = {p.pw_uid for p in pwd.getpwall()}
existing_groups = {g.gr_name for g in grp.getgrall()}
existing_gids = {g.gr_gid for g in grp.getgrall()}

passwd_lines = []
group_lines = []

for name, gid in sorted(groups.items(), key=lambda x: x[1]):
    gid = int(gid)
    name = str(name)
    if name not in existing_groups and gid not in existing_gids:
        group_lines.append(f"{name}:x:{gid}:")

for name, uid in sorted(users.items(), key=lambda x: x[1]):
    uid = int(uid)
    name = str(name)
    if name not in existing_users and uid not in existing_uids:
        gid = uid
        if name in groups:
            gid = int(groups[name])
        passwd_lines.append(f"{name}:x:{uid}:{gid}:{name} (ASOFS):/nonexistent:/usr/sbin/nologin")

with open('/etc/passwd', 'a') as f:
    for line in passwd_lines:
        f.write(line + '\n')

with open('/etc/group', 'a') as f:
    for line in group_lines:
        f.write(line + '\n')

n_users = len(passwd_lines)
n_groups = len(group_lines)

if n_users > 0 or n_groups > 0:
    print(f"    Registrados {n_users} usuario(s) y {n_groups} grupo(s)")
    for line in passwd_lines:
        parts = line.split(':')
        print(f"      - {parts[0]} (UID {parts[2]})")
    for line in group_lines:
        parts = line.split(':')
        print(f"      - {parts[0]} (GID {parts[2]})")
else:
    print("    No hay usuarios/grupos nuevos que registrar")
PYTHON_SCRIPT

# Paso 2: Montar ASOFS
echo "[2/3] Montando ASOFS en $MOUNTPOINT..."

mkdir -p "$MOUNTPOINT"
asofs mount "$MOUNTPOINT" -c "$CONFIG_FILE" > /tmp/asofs.log 2>&1 &
ASOFS_PID=$!
sleep 1

if ls "$MOUNTPOINT" >/dev/null 2>&1; then
    echo "    ASOFS montado correctamente"
else
    echo "    Advertencia: el montaje puede no estar listo aún"
fi

# Paso 3: Shell interactiva
echo "[3/3] Abriendo shell..."
echo ""
echo "============================================"
echo "  ASOFS listo en: $MOUNTPOINT"
echo "  Config:         $CONFIG_FILE"
echo ""
echo "  Prueba:"
echo "    ls -la $MOUNTPOINT/"
echo "    find $MOUNTPOINT -user alice"
echo ""
echo "  Escribe 'exit' para salir."
echo "============================================"
echo ""

cleanup() {
    echo ""
    echo "Desmontando ASOFS..."
    fusermount3 -u "$MOUNTPOINT" 2>/dev/null || true
    kill $ASOFS_PID 2>/dev/null || true
    wait $ASOFS_PID 2>/dev/null || true
    echo "Contenedor finalizado."
}

trap cleanup EXIT

cd "$MOUNTPOINT"
exec /bin/bash --norc --noprofile -i
