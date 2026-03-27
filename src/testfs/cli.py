#!/usr/bin/env python3
"""
ASOFS - Interfaz de línea de comandos
=====================================

Trabajo de Fin de Grado
Escuela de Ingeniería Informática - ULPGC
Autor: Raúl Trejo González
"""

import sys
from argparse import ArgumentParser


def cmd_mount(args):
    """Comando: montar sistema de ficheros FUSE."""
    from testfs.fuse.filesystem import main as fuse_main
    
    sys.argv = ['asofs', args.mountpoint]
    if args.debug:
        sys.argv.append('-d')
    
    fuse_main()


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
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == '__main__':
    main()
