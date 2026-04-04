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
    from testfs.fuse.filesystem import ASOFS, main as fuse_main
    from testfs.config import load_config
    from testfs.model import FileSystem
    import logging
    import pyfuse3
    import trio
    
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    log = logging.getLogger(__name__)
    
    # Crear punto de montaje si no existe
    if not os.path.exists(args.mountpoint):
        os.makedirs(args.mountpoint)
    
    # Cargar configuración o usar ejemplo
    if args.config:
        log.info(f"Cargando configuración desde {args.config}")
        fs = load_config(args.config)
    else:
        log.info("Usando filesystem de ejemplo")
        fs = None  # ASOFS creará uno de ejemplo
    
    # Crear ASOFS
    asofs = ASOFS(fs)
    
    # Configurar FUSE
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
