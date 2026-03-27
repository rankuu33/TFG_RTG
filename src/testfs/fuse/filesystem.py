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
import stat
import errno
import logging
from argparse import ArgumentParser

import pyfuse3
import trio

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)


class ASOFS(pyfuse3.Operations):
    """
    Sistema de ficheros FUSE para prácticas de ASO.
    
    Estructura actual (hardcodeada):
        /
        └── hello.txt
    """
    
    def __init__(self):
        super().__init__()
        
        self._hello_content = b"Hola desde ASOFS!\n\nSistema de ficheros virtual para ASO.\n"
        
        self._files = {
            pyfuse3.ROOT_INODE: {
                'name': '/',
                'type': 'dir',
                'children': {'hello.txt': 2}
            },
            2: {
                'name': 'hello.txt',
                'type': 'file',
                'content': self._hello_content,
                'size': len(self._hello_content)
            }
        }
        
        log.info("ASOFS inicializado")
    
    async def getattr(self, inode, ctx=None):
        """Obtener atributos de un fichero (stat)."""
        log.debug(f"getattr(inode={inode})")
        
        if inode not in self._files:
            raise pyfuse3.FUSEError(errno.ENOENT)
        
        entry = pyfuse3.EntryAttributes()
        node = self._files[inode]
        
        entry.st_ino = inode
        
        if node['type'] == 'dir':
            entry.st_mode = stat.S_IFDIR | 0o755
            entry.st_size = 4096
            entry.st_nlink = 2
        else:
            entry.st_mode = stat.S_IFREG | 0o644
            entry.st_size = node['size']
            entry.st_nlink = 1
        
        entry.st_uid = os.getuid()
        entry.st_gid = os.getgid()
        
        now_ns = int(1e9 * os.stat('.').st_mtime)
        entry.st_atime_ns = now_ns
        entry.st_mtime_ns = now_ns
        entry.st_ctime_ns = now_ns
        
        entry.attr_timeout = 1
        entry.entry_timeout = 1
        
        return entry
    
    async def lookup(self, parent_inode, name, ctx=None):
        """Buscar fichero por nombre en un directorio."""
        name = name.decode('utf-8') if isinstance(name, bytes) else name
        log.debug(f"lookup(parent={parent_inode}, name='{name}')")
        
        if parent_inode not in self._files:
            raise pyfuse3.FUSEError(errno.ENOENT)
        
        parent = self._files[parent_inode]
        if parent['type'] != 'dir':
            raise pyfuse3.FUSEError(errno.ENOTDIR)
        
        if name not in parent['children']:
            raise pyfuse3.FUSEError(errno.ENOENT)
        
        child_inode = parent['children'][name]
        return await self.getattr(child_inode, ctx)
    
    async def opendir(self, inode, ctx):
        """Abrir un directorio."""
        log.debug(f"opendir(inode={inode})")
        
        if inode not in self._files:
            raise pyfuse3.FUSEError(errno.ENOENT)
        
        if self._files[inode]['type'] != 'dir':
            raise pyfuse3.FUSEError(errno.ENOTDIR)
        
        return inode
    
    async def readdir(self, inode, start_id, token):
        """Listar contenido de un directorio."""
        log.debug(f"readdir(inode={inode}, start_id={start_id})")
        
        if inode not in self._files:
            raise pyfuse3.FUSEError(errno.ENOENT)
        
        node = self._files[inode]
        if node['type'] != 'dir':
            raise pyfuse3.FUSEError(errno.ENOTDIR)
        
        entries = [
            ('.', inode),
            ('..', inode),
        ]
        
        for name, child_inode in node['children'].items():
            entries.append((name, child_inode))
        
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
        
        if inode not in self._files:
            raise pyfuse3.FUSEError(errno.ENOENT)
        
        if self._files[inode]['type'] != 'file':
            raise pyfuse3.FUSEError(errno.EISDIR)
        
        return pyfuse3.FileInfo(fh=inode)
    
    async def read(self, fh, offset, size):
        """Leer contenido de un fichero."""
        log.debug(f"read(fh={fh}, offset={offset}, size={size})")
        
        inode = fh
        
        if inode not in self._files:
            raise pyfuse3.FUSEError(errno.ENOENT)
        
        node = self._files[inode]
        if node['type'] != 'file':
            raise pyfuse3.FUSEError(errno.EISDIR)
        
        content = node['content']
        return content[offset:offset + size]


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
