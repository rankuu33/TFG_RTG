"""
ASOFS - Modelo de datos
=======================

Define las estructuras para representar nodos del sistema de ficheros:
- FileNode: ficheros regulares
- DirNode: directorios
- SymlinkNode: enlaces simbólicos
- FifoNode: named pipes
- DeviceNode: dispositivos

Cada nodo tiene atributos configurables:
- Permisos (mode)
- Propietario (uid/gid)
- Timestamps (atime, mtime, ctime)
- Tamaño (para ficheros)
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
    HARDLINK = "hardlink"


@dataclass
class BaseNode:
    """
    Nodo base del sistema de ficheros.
    
    Attributes:
        name: Nombre del fichero/directorio
        mode: Permisos (ej: 0o755, 0o644)
        uid: ID de usuario propietario
        gid: ID de grupo propietario
        atime: Tiempo de último acceso (timestamp)
        mtime: Tiempo de última modificación (timestamp)
        ctime: Tiempo de último cambio de metadatos (timestamp)
    """
    name: str
    mode: int = 0o644
    uid: int = field(default_factory=os.getuid)
    gid: int = field(default_factory=os.getgid)
    atime: float = field(default_factory=time.time)
    mtime: float = field(default_factory=time.time)
    ctime: float = field(default_factory=time.time)
    
    # Se asigna al añadir al filesystem
    inode: int = 0
    
    @property
    def node_type(self) -> NodeType:
        """Tipo de nodo (a implementar en subclases)."""
        raise NotImplementedError
    
    @property
    def st_mode(self) -> int:
        """Modo completo para stat (tipo + permisos)."""
        raise NotImplementedError


@dataclass
class FileNode(BaseNode):
    """
    Fichero regular.
    
    Attributes:
        size: Tamaño del fichero en bytes
        content: Contenido (opcional, puede generarse on-demand)
    """
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
    """
    Directorio.
    
    Attributes:
        children: Diccionario nombre -> inode de los hijos
    """
    mode: int = 0o755
    children: Dict[str, int] = field(default_factory=dict)
    
    @property
    def node_type(self) -> NodeType:
        return NodeType.DIR
    
    @property
    def st_mode(self) -> int:
        return stat.S_IFDIR | self.mode
    
    def add_child(self, name: str, inode: int):
        """Añade un hijo al directorio."""
        self.children[name] = inode
    
    def remove_child(self, name: str):
        """Elimina un hijo del directorio."""
        if name in self.children:
            del self.children[name]


@dataclass
class SymlinkNode(BaseNode):
    """
    Enlace simbólico.
    
    Attributes:
        target: Ruta a la que apunta el enlace
    """
    target: str = ""
    mode: int = 0o777  # Los symlinks siempre tienen 777
    
    @property
    def node_type(self) -> NodeType:
        return NodeType.SYMLINK
    
    @property
    def st_mode(self) -> int:
        return stat.S_IFLNK | self.mode
    
    @property
    def size(self) -> int:
        """El tamaño de un symlink es la longitud del target."""
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
    """
    Dispositivo (bloque o carácter).
    
    Attributes:
        major: Número major del dispositivo
        minor: Número minor del dispositivo
        block: True si es dispositivo de bloque, False si es de carácter
    """
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
        """Genera el device ID para st_rdev."""
        return os.makedev(self.major, self.minor)


# Tipo union para cualquier nodo
Node = Union[FileNode, DirNode, SymlinkNode, FifoNode, DeviceNode]


class FileSystem:
    """
    Contenedor del sistema de ficheros virtual.
    
    Gestiona la colección de nodos y la asignación de inodes.
    """
    
    # El inode 1 siempre es la raíz en FUSE
    ROOT_INODE = 1
    
    def __init__(self):
        self._nodes: Dict[int, Node] = {}
        self._next_inode = 2  # El 1 es la raíz
        
        # Crear directorio raíz
        root = DirNode(name="/")
        root.inode = self.ROOT_INODE
        self._nodes[self.ROOT_INODE] = root
    
    @property
    def root(self) -> DirNode:
        """Devuelve el nodo raíz."""
        return self._nodes[self.ROOT_INODE]
    
    def get(self, inode: int) -> Optional[Node]:
        """Obtiene un nodo por su inode."""
        return self._nodes.get(inode)
    
    def add(self, node: Node, parent_inode: int = ROOT_INODE) -> int:
        """
        Añade un nodo al sistema de ficheros.
        
        Args:
            node: Nodo a añadir
            parent_inode: Inode del directorio padre
        
        Returns:
            Inode asignado al nodo
        """
        parent = self._nodes.get(parent_inode)
        if parent is None:
            raise ValueError(f"Parent inode {parent_inode} no existe")
        if not isinstance(parent, DirNode):
            raise ValueError(f"Parent inode {parent_inode} no es un directorio")
        
        # Asignar inode
        node.inode = self._next_inode
        self._next_inode += 1
        
        # Añadir al diccionario
        self._nodes[node.inode] = node
        
        # Añadir como hijo del padre
        parent.add_child(node.name, node.inode)
        
        return node.inode
    
    def list_dir(self, inode: int) -> List[tuple]:
        """
        Lista el contenido de un directorio.
        
        Returns:
            Lista de tuplas (nombre, inode)
        """
        node = self._nodes.get(inode)
        if node is None or not isinstance(node, DirNode):
            return []
        
        return list(node.children.items())
    
    def __len__(self) -> int:
        """Número total de nodos."""
        return len(self._nodes)
    
    def __repr__(self) -> str:
        return f"FileSystem({len(self)} nodos)"
