"""
ASOFS - Modelo de datos
=======================

Define las estructuras para representar nodos del sistema de ficheros.
"""

import os
import stat
import time
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union
from enum import Enum


# Multiplicadores de tamaño
SIZE_UNITS = {
    'B': 1,
    'K': 1024,
    'KB': 1024,
    'M': 1024**2,
    'MB': 1024**2,
    'G': 1024**3,
    'GB': 1024**3,
    'T': 1024**4,
    'TB': 1024**4,
    'P': 1024**5,
    'PB': 1024**5,
}


def parse_size(value) -> int:
    """
    Parsea un tamaño a bytes.
    
    Soporta:
        100       -> 100 bytes
        "100"     -> 100 bytes
        "10KB"    -> 10240 bytes
        "5MB"     -> 5242880 bytes
        "1GB"     -> 1073741824 bytes
        "1.5GB"   -> 1610612736 bytes
    """
    if value is None:
        return 0
    
    if isinstance(value, int):
        return value
    
    if isinstance(value, float):
        return int(value)
    
    if isinstance(value, str):
        value = value.strip().upper()
        
        # Intentar como número simple
        try:
            return int(value)
        except ValueError:
            pass
        
        # Buscar número + unidad
        match = re.match(r'^([\d.]+)\s*([A-Z]+)$', value)
        if match:
            num = float(match.group(1))
            unit = match.group(2)
            
            if unit in SIZE_UNITS:
                return int(num * SIZE_UNITS[unit])
        
        raise ValueError(f"Tamaño inválido: {value}")
    
    raise ValueError(f"Tamaño inválido: {value}")


def format_size(size: int) -> str:
    """Formatea un tamaño en bytes a formato legible."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if size < 1024:
            if unit == 'B':
                return f"{size}{unit}"
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}PB"


class NodeType(Enum):
    """Tipos de nodos soportados."""
    FILE = "file"
    DIR = "dir"
    SYMLINK = "symlink"
    FIFO = "fifo"
    DEVICE_CHAR = "char"
    DEVICE_BLOCK = "block"


class ContentGenerator:
    """Genera contenido on-demand para ficheros grandes."""
    
    @staticmethod
    def zeros(offset: int, size: int) -> bytes:
        """Genera bytes nulos (como /dev/zero)."""
        return b'\x00' * size
    
    @staticmethod
    def pattern(offset: int, size: int, pattern: bytes = b'ASOFS') -> bytes:
        """Genera un patrón repetido."""
        pattern_len = len(pattern)
        start_in_pattern = offset % pattern_len
        
        result = bytearray(size)
        for i in range(size):
            result[i] = pattern[(start_in_pattern + i) % pattern_len]
        
        return bytes(result)
    
    @staticmethod
    def random(offset: int, size: int, seed: int = 0) -> bytes:
        """Genera bytes pseudo-aleatorios deterministas."""
        import hashlib
        
        result = bytearray()
        
        block_num = offset // 32
        block_offset = offset % 32
        
        while len(result) < size + block_offset:
            h = hashlib.sha256()
            h.update(f"{seed}:{block_num}".encode())
            result.extend(h.digest())
            block_num += 1
        
        return bytes(result[block_offset:block_offset + size])
    
    @staticmethod
    def text(offset: int, size: int) -> bytes:
        """Genera texto lorem ipsum repetido."""
        lorem = (
            b"Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
            b"Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
            b"Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris. "
        )
        return ContentGenerator.pattern(offset, size, lorem)


@dataclass
class BaseNode:
    """Nodo base del sistema de ficheros."""
    name: str
    mode: int = 0o644
    uid: int = field(default_factory=os.getuid)
    gid: int = field(default_factory=os.getgid)
    atime: float = field(default_factory=time.time)
    mtime: float = field(default_factory=time.time)
    ctime: float = field(default_factory=time.time)
    
    inode: int = 0
    nlink: int = 1
    
    @property
    def node_type(self) -> NodeType:
        raise NotImplementedError
    
    @property
    def st_mode(self) -> int:
        raise NotImplementedError


@dataclass
class FileNode(BaseNode):
    """Fichero regular."""
    size: int = 0
    content: Optional[bytes] = None
    
    # Para contenido generado on-demand
    content_type: str = "static"  # static, zeros, pattern, random, text
    content_seed: int = 0
    
    def __post_init__(self):
        if self.content is not None and self.size == 0:
            self.size = len(self.content)
    
    @property
    def node_type(self) -> NodeType:
        return NodeType.FILE
    
    @property
    def st_mode(self) -> int:
        return stat.S_IFREG | self.mode
    
    def read(self, offset: int, size: int) -> bytes:
        """Lee contenido del fichero."""
        if offset >= self.size:
            return b''
        
        size = min(size, self.size - offset)
        
        # Si tiene contenido estático
        if self.content is not None:
            return self.content[offset:offset + size]
        
        # Generar contenido on-demand
        if self.content_type == "zeros":
            return ContentGenerator.zeros(offset, size)
        elif self.content_type == "pattern":
            return ContentGenerator.pattern(offset, size)
        elif self.content_type == "random":
            return ContentGenerator.random(offset, size, self.content_seed)
        elif self.content_type == "text":
            return ContentGenerator.text(offset, size)
        else:
            return b'\x00' * size


@dataclass
class DirNode(BaseNode):
    """Directorio."""
    mode: int = 0o755
    children: Dict[str, int] = field(default_factory=dict)
    parent: int = 1  # inode del padre (root apunta a sí mismo)
    
    @property
    def node_type(self) -> NodeType:
        return NodeType.DIR
    
    @property
    def st_mode(self) -> int:
        return stat.S_IFDIR | self.mode
    
    def add_child(self, name: str, inode: int):
        self.children[name] = inode
    
    def remove_child(self, name: str):
        if name in self.children:
            del self.children[name]


@dataclass
class SymlinkNode(BaseNode):
    """Enlace simbólico."""
    target: str = ""
    mode: int = 0o777
    
    @property
    def node_type(self) -> NodeType:
        return NodeType.SYMLINK
    
    @property
    def st_mode(self) -> int:
        return stat.S_IFLNK | self.mode
    
    @property
    def size(self) -> int:
        return len(self.target)


@dataclass
class FifoNode(BaseNode):
    """Named pipe (FIFO)."""
    mode: int = 0o644
    
    @property
    def node_type(self) -> NodeType:
        return NodeType.FIFO
    
    @property
    def st_mode(self) -> int:
        return stat.S_IFIFO | self.mode
    
    @property
    def size(self) -> int:
        return 0


@dataclass
class DeviceNode(BaseNode):
    """Dispositivo (bloque o carácter)."""
    major: int = 0
    minor: int = 0
    block: bool = False
    mode: int = 0o660
    
    @property
    def node_type(self) -> NodeType:
        return NodeType.DEVICE_BLOCK if self.block else NodeType.DEVICE_CHAR
    
    @property
    def st_mode(self) -> int:
        if self.block:
            return stat.S_IFBLK | self.mode
        return stat.S_IFCHR | self.mode
    
    @property
    def size(self) -> int:
        return 0
    
    @property
    def rdev(self) -> int:
        return os.makedev(self.major, self.minor)


Node = Union[FileNode, DirNode, SymlinkNode, FifoNode, DeviceNode]


class FileSystem:
    """Contenedor del sistema de ficheros virtual."""
    
    ROOT_INODE = 1
    
    def __init__(self):
        self._nodes: Dict[int, Node] = {}
        self._next_inode = 2
        
        root = DirNode(name="/")
        root.inode = self.ROOT_INODE
        root.nlink = 2
        self._nodes[self.ROOT_INODE] = root
    
    @property
    def root(self) -> DirNode:
        return self._nodes[self.ROOT_INODE]
    
    def get(self, inode: int) -> Optional[Node]:
        return self._nodes.get(inode)
    
    def add(self, node: Node, parent_inode: int = ROOT_INODE) -> int:
        """Añade un nodo al filesystem."""
        parent = self._nodes.get(parent_inode)
        if parent is None:
            raise ValueError(f"Parent inode {parent_inode} no existe")
        if not isinstance(parent, DirNode):
            raise ValueError(f"Parent inode {parent_inode} no es un directorio")
        
        node.inode = self._next_inode
        self._next_inode += 1
        
        # Asignar parent a directorios
        if isinstance(node, DirNode):
            node.parent = parent_inode
        
        self._nodes[node.inode] = node
        parent.add_child(node.name, node.inode)
        
        if isinstance(node, DirNode):
            parent.nlink += 1
        
        return node.inode
    
    def add_hardlink(self, name: str, target_inode: int, parent_inode: int = ROOT_INODE) -> int:
        """Crea un hardlink a un nodo existente."""
        parent = self._nodes.get(parent_inode)
        if parent is None:
            raise ValueError(f"Parent inode {parent_inode} no existe")
        if not isinstance(parent, DirNode):
            raise ValueError(f"Parent inode {parent_inode} no es un directorio")
        
        target = self._nodes.get(target_inode)
        if target is None:
            raise ValueError(f"Target inode {target_inode} no existe")
        if isinstance(target, DirNode):
            raise ValueError("No se pueden crear hardlinks a directorios")
        
        parent.add_child(name, target_inode)
        target.nlink += 1
        
        return target_inode
    
    def find_by_name(self, name: str, parent_inode: int = ROOT_INODE) -> Optional[int]:
        """Busca un nodo por nombre en un directorio."""
        parent = self._nodes.get(parent_inode)
        if parent is None or not isinstance(parent, DirNode):
            return None
        return parent.children.get(name)
    
    def list_dir(self, inode: int) -> List[tuple]:
        node = self._nodes.get(inode)
        if node is None or not isinstance(node, DirNode):
            return []
        return list(node.children.items())
    
    def __len__(self) -> int:
        return len(self._nodes)
    
    def __repr__(self) -> str:
        return f"FileSystem({len(self)} nodos)"
