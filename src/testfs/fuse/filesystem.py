#!/usr/bin/env python3
"""
=============================================================================
ASOFS - Sistema de Ficheros Virtual para Administración de Sistemas Operativos
=============================================================================

Trabajo de Fin de Grado
Escuela de Ingeniería Informática - ULPGC
Autor: Raúl Trejo González
Tutor: José Miguel Santos Espino
"""

import os
import errno
import logging
from argparse import ArgumentParser

import pyfuse3
import trio

from testfs.model import (
    FileSystem, FileNode, DirNode, SymlinkNode, FifoNode, DeviceNode
)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)


class ASOFS(pyfuse3.Operations):
    """
    Sistema de ficheros FUSE para prácticas de ASO.
    
    Usa el modelo de datos definido en testfs.model.
    """
    
    def __init__(self, fs: FileSystem = None):
        super().__init__()
        
        # Usar filesystem proporcionado o crear uno de ejemplo
        if fs is not None:
            self._fs = fs
        else:
            self._fs = self._create_example_fs()
        
        log.info(f"ASOFS inicializado con {len(self._fs)} nodos")
    
    def _create_example_fs(self) -> FileSystem:
        """Crea un filesystem de ejemplo para pruebas."""
        fs = FileSystem()
        
        # Fichero de bienvenida
        hello = FileNode(
            name="hello.txt",
            content=b"Hola desde ASOFS!\n\nSistema de ficheros virtual para ASO.\n"
        )
        fs.add(hello)
        
        # Directorio de pruebas
        test_dir = DirNode(name="pruebas")
        fs.add(test_dir)
        
        # Fichero dentro del directorio
        readme = FileNode(
            name="README.md",
            content=b"# Directorio de pruebas\n\nAqui van los ficheros de prueba.\n"
        )
        fs.add(readme, parent_inode=test_dir.inode)
        
        # Fichero con permisos especiales (SUID)
        suid_file = FileNode(
            name="suid_example.sh",
            mode=0o4755,
            content=b"#!/bin/bash\necho 'Soy SUID'\n"
        )
        fs.add(suid_file, parent_inode=test_dir.inode)
        
        # Enlace simbólico
        link = SymlinkNode(
            name="link_to_hello.txt",
            target="hello.txt"
        )
        fs.add(link)
        
        # Enlace simbólico roto
        broken_link = SymlinkNode(
            name="broken_link.txt",
            target="/ruta/que/no/existe.txt"
        )
        fs.add(broken_link)
        
        # FIFO
        fifo = FifoNode(name="mi_pipe")
        fs.add(fifo)
        
        return fs
    
    async def getattr(self, inode, ctx=None):
        """Obtener atributos de un nodo."""
        log.debug(f"getattr(inode={inode})")
        
        node = self._fs.get(inode)
        if node is None:
            raise pyfuse3.FUSEError(errno.ENOENT)
        
        entry = pyfuse3.EntryAttributes()
        entry.st_ino = inode
        entry.st_mode = node.st_mode
        entry.st_uid = node.uid
        entry.st_gid = node.gid
        
        # Tamaño
        if isinstance(node, DirNode):
            entry.st_size = 4096
            entry.st_nlink = 2 + len(node.children)
        elif isinstance(node, (FileNode, SymlinkNode)):
            entry.st_size = node.size
            entry.st_nlink = 1
        else:
            entry.st_size = 0
            entry.st_nlink = 1
        
        # Timestamps (en nanosegundos)
        entry.st_atime_ns = int(node.atime * 1e9)
        entry.st_mtime_ns = int(node.mtime * 1e9)
        entry.st_ctime_ns = int(node.ctime * 1e9)
        
        # Device ID para dispositivos
        if isinstance(node, DeviceNode):
            entry.st_rdev = node.rdev
        
        entry.attr_timeout = 1
        entry.entry_timeout = 1
        
        return entry
    
    async def lookup(self, parent_inode, name, ctx=None):
        """Buscar un nodo por nombre."""
        name = name.decode('utf-8') if isinstance(name, bytes) else name
        log.debug(f"lookup(parent={parent_inode}, name='{name}')")
        
        parent = self._fs.get(parent_inode)
        if parent is None:
            raise pyfuse3.FUSEError(errno.ENOENT)
        
        if not isinstance(parent, DirNode):
            raise pyfuse3.FUSEError(errno.ENOTDIR)
        
        if name not in parent.children:
            raise pyfuse3.FUSEError(errno.ENOENT)
        
        child_inode = parent.children[name]
        return await self.getattr(child_inode, ctx)
    
    async def opendir(self, inode, ctx):
        """Abrir un directorio."""
        log.debug(f"opendir(inode={inode})")
        
        node = self._fs.get(inode)
        if node is None:
            raise pyfuse3.FUSEError(errno.ENOENT)
        
        if not isinstance(node, DirNode):
            raise pyfuse3.FUSEError(errno.ENOTDIR)
        
        return inode
    
    async def readdir(self, inode, start_id, token):
        """Listar contenido de un directorio."""
        log.debug(f"readdir(inode={inode}, start_id={start_id})")
        
        node = self._fs.get(inode)
        if node is None:
            raise pyfuse3.FUSEError(errno.ENOENT)
        
        if not isinstance(node, DirNode):
            raise pyfuse3.FUSEError(errno.ENOTDIR)
        
        # Construir lista de entradas
        entries = [
            ('.', inode),
            ('..', inode),
        ]
        entries.extend(node.children.items())
        
        for i, (name, entry_inode) in enumerate(entries):
            if i < start_id:
                continue
            
            name_bytes = name.encode('utf-8') if isinstance(name, str) else name
            entry_attrs = await self.getattr(entry_inode)
            
            if not pyfuse3.readdir_reply(token, name_bytes, entry_attrs, i + 1):
                break
    
    async def open(self, inode, flags, ctx):
        """Abrir un fichero."""
        log.debug(f"open(inode={inode}, flags={flags})")
        
        node = self._fs.get(inode)
        if node is None:
            raise pyfuse3.FUSEError(errno.ENOENT)
        
        if not isinstance(node, FileNode):
            raise pyfuse3.FUSEError(errno.EISDIR)
        
        return pyfuse3.FileInfo(fh=inode)
    
    async def read(self, fh, offset, size):
        """Leer contenido de un fichero."""
        log.debug(f"read(fh={fh}, offset={offset}, size={size})")
        
        node = self._fs.get(fh)
        if node is None:
            raise pyfuse3.FUSEError(errno.ENOENT)
        
        if not isinstance(node, FileNode):
            raise pyfuse3.FUSEError(errno.EISDIR)
        
        if node.content is None:
            return b''
        
        return node.content[offset:offset + size]
    
    async def readlink(self, inode, ctx):
        """Leer el destino de un enlace simbólico."""
        log.debug(f"readlink(inode={inode})")
        
        node = self._fs.get(inode)
        if node is None:
            raise pyfuse3.FUSEError(errno.ENOENT)
        
        if not isinstance(node, SymlinkNode):
            raise pyfuse3.FUSEError(errno.EINVAL)
        
        return node.target.encode('utf-8')


def main():
    parser = ArgumentParser(description='ASOFS - Sistema de ficheros para ASO')
    parser.add_argument('mountpoint', help='Directorio donde montar')
    parser.add_argument('-d', '--debug', action='store_true', help='Modo debug')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.mountpoint):
        os.makedirs(args.mountpoint)
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)
    
    asofs = ASOFS()
    
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


if __name__ == '__main__':
    main()
