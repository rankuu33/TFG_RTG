"""
ASOFS - Modelo de datos
=======================

Define las estructuras para representar nodos del sistema de ficheros.
"""

import os
import stat
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union
from enum import Enum


class NodeType(Enum):
    """Tipos de nodos soportados."""
    FILE = "file"
    DIR = "dir"
    SYMLINK = "symlink"
    FIFO = "fifo"
    DEVICE_CHAR = "char"
    DEVICE_BLOCK = "block"


@dataclass
class BaseNode:
    """
    Nodo base del sistema de ficheros.
    """
    name: str
    mode: int = 0o644
    uid: int = field(default_factory=os.getuid)
    gid: int = field(default_factory=os.getgid)
    atime: float = field(default_factory=time.time)
    mtime: float = field(default_factory=time.time)
    ctime: float = field(default_factory=time.time)
    
    inode: int = 0
    nlink: int = 1  # Contador de enlaces (hardlinks)
    
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
    
    def __post_init__(self):
        if self.content is not None and self.size == 0:
            self.size = len(self.content)
    
    @property
    def node_type(self) -> NodeType:
        return NodeType.FILE
    
    @property
    def st_mode(self) -> int:
        return stat.S_IFREG | self.mode


@dataclass
class DirNode(BaseNode):
    """Directorio."""
    mode: int = 0o755
    children: Dict[str, int] = field(default_factory=dict)
    
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
    """
    Contenedor del sistema de ficheros virtual.
    """
    
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
        
        self._nodes[node.inode] = node
        parent.add_child(node.name, node.inode)
        
        # Incrementar nlink del padre si es directorio
        if isinstance(node, DirNode):
            parent.nlink += 1
        
        return node.inode
    
    def add_hardlink(self, name: str, target_inode: int, parent_inode: int = ROOT_INODE) -> int:
        """
        Crea un hardlink a un nodo existente.
        
        Args:
            name: Nombre del nuevo enlace
            target_inode: Inode del fichero destino
            parent_inode: Directorio donde crear el enlace
        
        Returns:
            Inode del fichero (el mismo que target_inode)
        """
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
        
        # Añadir entrada en el directorio padre
        parent.add_child(name, target_inode)
        
        # Incrementar contador de enlaces
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
