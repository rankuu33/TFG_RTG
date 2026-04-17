#!/usr/bin/env python3
"""
ASOFS - Interfaz de línea de comandos
=====================================

Trabajo de Fin de Grado
Escuela de Ingeniería Informática - ULPGC
Autor: Raúl Trejo González
"""

import sys
import os
from argparse import ArgumentParser


def cmd_mount(args):
    """Comando: montar sistema de ficheros FUSE."""
    from testfs.fuse.filesystem import ASOFS
    from testfs.config import load_config
    import logging
    import pyfuse3
    import trio
    
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    log = logging.getLogger(__name__)
    
    if not os.path.exists(args.mountpoint):
        os.makedirs(args.mountpoint)
    
    if args.config:
        log.info(f"Cargando configuración desde {args.config}")
        fs = load_config(args.config)
    else:
        log.info("Usando filesystem de ejemplo")
        fs = None
    
    asofs = ASOFS(fs)
    
    fuse_options = set(pyfuse3.default_options)
    fuse_options.add('fsname=asofs')
    
    if args.debug:
        fuse_options.add('debug')
    
    pyfuse3.init(asofs, args.mountpoint, fuse_options)
    
    log.info(f"ASOFS montado en {args.mountpoint}")
    log.info("Ctrl+C para desmontar")
    
    try:
        trio.run(pyfuse3.main)
    except KeyboardInterrupt:
        log.info("Desmontando...")
    finally:
        pyfuse3.close()
        log.info("ASOFS desmontado")


def cmd_setup_users(args):
    """Comando: generar script para crear usuarios/grupos."""
    import yaml
    
    with open(args.config, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    users = config.get('users', {})
    groups = config.get('groups', {})
    
    # Filtrar usuarios/grupos del sistema (uid/gid < 1000)
    users = {k: v for k, v in users.items() if v >= 1000}
    groups = {k: v for k, v in groups.items() if v >= 1000}
    
    if not users and not groups:
        print("No hay usuarios ni grupos ficticios (uid/gid >= 1000) en la configuración.")
        sys.exit(0)
    
    script_lines = [
        "#!/bin/bash",
        "# ASOFS - Script para crear usuarios y grupos ficticios",
        f"# Generado desde: {args.config}",
        "#",
        "# Estos usuarios no tienen home ni shell (solo para propiedad de ficheros)",
        "# Ejecutar con: sudo bash script.sh",
        "",
        "set -e",
        "",
    ]
    
    # Primero grupos
    if groups:
        script_lines.append("# Crear grupos")
        for name, gid in sorted(groups.items(), key=lambda x: x[1]):
            script_lines.append(f'groupadd -g {gid} {name} 2>/dev/null || echo "Grupo {name} ya existe"')
        script_lines.append("")
    
    # Luego usuarios
    if users:
        script_lines.append("# Crear usuarios")
        for name, uid in sorted(users.items(), key=lambda x: x[1]):
            # -M: sin home, -N: sin grupo privado, -s /usr/sbin/nologin: sin login
            script_lines.append(
                f'useradd -M -N -u {uid} -s /usr/sbin/nologin {name} 2>/dev/null || echo "Usuario {name} ya existe"'
            )
        script_lines.append("")
    
    script_lines.append('echo "Usuarios y grupos creados correctamente"')
    
    script = '\n'.join(script_lines)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(script)
        os.chmod(args.output, 0o755)
        print(f"Script generado: {args.output}")
        print(f"Ejecutar con: sudo bash {args.output}")
    else:
        print(script)


def cmd_cleanup_users(args):
    """Comando: generar script para eliminar usuarios/grupos."""
    import yaml
    
    with open(args.config, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    users = config.get('users', {})
    groups = config.get('groups', {})
    
    # Filtrar usuarios/grupos del sistema
    users = {k: v for k, v in users.items() if v >= 1000}
    groups = {k: v for k, v in groups.items() if v >= 1000}
    
    if not users and not groups:
        print("No hay usuarios ni grupos ficticios en la configuración.")
        sys.exit(0)
    
    script_lines = [
        "#!/bin/bash",
        "# ASOFS - Script para eliminar usuarios y grupos ficticios",
        f"# Generado desde: {args.config}",
        "",
        "set -e",
        "",
    ]
    
    # Primero usuarios
    if users:
        script_lines.append("# Eliminar usuarios")
        for name in sorted(users.keys()):
            script_lines.append(f'userdel {name} 2>/dev/null || echo "Usuario {name} no existe"')
        script_lines.append("")
    
    # Luego grupos
    if groups:
        script_lines.append("# Eliminar grupos")
        for name in sorted(groups.keys()):
            script_lines.append(f'groupdel {name} 2>/dev/null || echo "Grupo {name} no existe"')
        script_lines.append("")
    
    script_lines.append('echo "Usuarios y grupos eliminados"')
    
    script = '\n'.join(script_lines)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(script)
        os.chmod(args.output, 0o755)
        print(f"Script generado: {args.output}")
        print(f"Ejecutar con: sudo bash {args.output}")
    else:
        print(script)


def main():
    parser = ArgumentParser(
        prog='asofs',
        description='ASOFS - Sistema de Ficheros Virtual para ASO'
    )
    parser.add_argument(
        '-v', '--version',
        action='version',
        version='%(prog)s 0.1.0'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Comandos disponibles')
    
    # Comando: mount
    mount_parser = subparsers.add_parser(
        'mount',
        help='Montar sistema de ficheros virtual FUSE'
    )
    mount_parser.add_argument(
        'mountpoint',
        help='Directorio donde montar'
    )
    mount_parser.add_argument(
        '-c', '--config',
        default=None,
        help='Fichero de configuración YAML'
    )
    mount_parser.add_argument(
        '-d', '--debug',
        action='store_true',
        help='Modo debug'
    )
    mount_parser.set_defaults(func=cmd_mount)
    
    # Comando: setup-users
    setup_parser = subparsers.add_parser(
        'setup-users',
        help='Generar script para crear usuarios/grupos ficticios'
    )
    setup_parser.add_argument(
        '-c', '--config',
        required=True,
        help='Fichero de configuración YAML'
    )
    setup_parser.add_argument(
        '-o', '--output',
        default=None,
        help='Fichero de salida (por defecto: stdout)'
    )
    setup_parser.set_defaults(func=cmd_setup_users)
    
    # Comando: cleanup-users
    cleanup_parser = subparsers.add_parser(
        'cleanup-users',
        help='Generar script para eliminar usuarios/grupos ficticios'
    )
    cleanup_parser.add_argument(
        '-c', '--config',
        required=True,
        help='Fichero de configuración YAML'
    )
    cleanup_parser.add_argument(
        '-o', '--output',
        default=None,
        help='Fichero de salida (por defecto: stdout)'
    )
    cleanup_parser.set_defaults(func=cmd_cleanup_users)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == '__main__':
    main()
