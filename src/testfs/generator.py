"""
ASOFS - Generador de ficheros
=============================

Genera ficheros automáticamente según patrones y distribuciones.

Ejemplo YAML:
    
    root:
      - generate:
          type: file
          count: 100
          pattern: "fichero_{n:03d}.txt"
          size: [100, 1000]  # rango aleatorio
          mode: "0644"
"""

import os
import random
import string
import time
from typing import Dict, Any, List, Optional, Tuple

from testfs.model import (
    FileSystem, FileNode, DirNode, SymlinkNode, FifoNode, DeviceNode
)


class Generator:
    """Generador de nodos para ASOFS."""
    
    def __init__(self, seed: int = None):
        """
        Args:
            seed: Semilla para reproducibilidad
        """
        if seed is not None:
            random.seed(seed)
        
        self._counter = 0
    
    def generate(self, fs: FileSystem, config: Dict[str, Any], parent_inode: int) -> List[int]:
        """
        Genera nodos según configuración.
        
        Args:
            fs: FileSystem donde añadir
            config: Configuración de generación
            parent_inode: Inode del directorio padre
        
        Returns:
            Lista de inodes creados
        """
        gen_type = config.get('type', 'file')
        count = config.get('count', 1)
        
        inodes = []
        for i in range(count):
            self._counter += 1
            
            if gen_type == 'file':
                inode = self._generate_file(fs, config, parent_inode, i)
            elif gen_type == 'dir':
                inode = self._generate_dir(fs, config, parent_inode, i)
            elif gen_type == 'symlink':
                inode = self._generate_symlink(fs, config, parent_inode, i)
            elif gen_type == 'fifo':
                inode = self._generate_fifo(fs, config, parent_inode, i)
            elif gen_type == 'mixed':
                inode = self._generate_mixed(fs, config, parent_inode, i)
            else:
                continue
            
            if inode:
                inodes.append(inode)
        
        return inodes
    
    def _generate_file(self, fs: FileSystem, config: Dict, parent: int, index: int) -> int:
        """Genera un fichero."""
        name = self._expand_pattern(config.get('pattern', 'file_{n}.txt'), index)
        mode = self._parse_mode(config.get('mode', '0644'))
        size = self._resolve_range(config.get('size', 0))
        
        # Generar contenido
        content = self._generate_content(size, config.get('content_type', 'random'))
        
        # Timestamps
        atime, mtime, ctime = self._resolve_timestamps(config)
        
        node = FileNode(
            name=name,
            mode=mode,
            size=size,
            content=content,
            atime=atime,
            mtime=mtime,
            ctime=ctime
        )
        
        return fs.add(node, parent)
    
    def _generate_dir(self, fs: FileSystem, config: Dict, parent: int, index: int) -> int:
        """Genera un directorio."""
        name = self._expand_pattern(config.get('pattern', 'dir_{n}'), index)
        mode = self._parse_mode(config.get('mode', '0755'))
        
        atime, mtime, ctime = self._resolve_timestamps(config)
        
        node = DirNode(
            name=name,
            mode=mode,
            atime=atime,
            mtime=mtime,
            ctime=ctime
        )
        
        inode = fs.add(node, parent)
        
        # Generar hijos si se especifica
        if 'children' in config:
            self.generate(fs, config['children'], inode)
        
        return inode
    
    def _generate_symlink(self, fs: FileSystem, config: Dict, parent: int, index: int) -> int:
        """Genera un symlink."""
        name = self._expand_pattern(config.get('pattern', 'link_{n}'), index)
        target = self._expand_pattern(config.get('target', '/tmp/target_{n}'), index)
        
        atime, mtime, ctime = self._resolve_timestamps(config)
        
        node = SymlinkNode(
            name=name,
            target=target,
            atime=atime,
            mtime=mtime,
            ctime=ctime
        )
        
        return fs.add(node, parent)
    
    def _generate_fifo(self, fs: FileSystem, config: Dict, parent: int, index: int) -> int:
        """Genera un FIFO."""
        name = self._expand_pattern(config.get('pattern', 'pipe_{n}'), index)
        mode = self._parse_mode(config.get('mode', '0644'))
        
        atime, mtime, ctime = self._resolve_timestamps(config)
        
        node = FifoNode(
            name=name,
            mode=mode,
            atime=atime,
            mtime=mtime,
            ctime=ctime
        )
        
        return fs.add(node, parent)
    
    def _generate_mixed(self, fs: FileSystem, config: Dict, parent: int, index: int) -> int:
        """Genera un tipo aleatorio."""
        node_type = random.choice(['file', 'symlink', 'fifo'])
        config_copy = config.copy()
        config_copy['type'] = node_type
        
        if node_type == 'file':
            return self._generate_file(fs, config_copy, parent, index)
        elif node_type == 'symlink':
            return self._generate_symlink(fs, config_copy, parent, index)
        else:
            return self._generate_fifo(fs, config_copy, parent, index)
    
    def _expand_pattern(self, pattern: str, index: int) -> str:
        """Expande un patrón con variables."""
        return pattern.format(
            n=index,
            N=self._counter,
            random=self._random_string(8),
            uuid=self._random_string(32),
            alpha=self._random_string(6, string.ascii_lowercase),
            num=self._random_string(4, string.digits)
        )
    
    def _resolve_range(self, value: Any) -> int:
        """Resuelve un valor o rango a un entero."""
        if isinstance(value, int):
            return value
        if isinstance(value, list) and len(value) == 2:
            return random.randint(value[0], value[1])
        return 0
    
    def _resolve_timestamps(self, config: Dict) -> Tuple[float, float, float]:
        """Resuelve timestamps según configuración."""
        now = time.time()
        
        # Si hay rango de tiempo
        time_range = config.get('time_range')
        if time_range:
            min_offset = self._parse_time_offset(time_range[0])
            max_offset = self._parse_time_offset(time_range[1])
            offset = random.uniform(min_offset, max_offset)
            t = now + offset
            return t, t, t
        
        return now, now, now
    
    def _parse_time_offset(self, value: str) -> float:
        """Parsea offset de tiempo como '-30d', '+1y', etc."""
        if isinstance(value, (int, float)):
            return float(value)
        
        import re
        match = re.match(r'^([+-]?\d+)([smhdwy])$', str(value).lower())
        if not match:
            return 0
        
        amount = int(match.group(1))
        unit = match.group(2)
        
        multipliers = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400,
            'w': 604800,
            'y': 31536000,
        }
        
        return amount * multipliers[unit]
    
    def _parse_mode(self, mode_value: Any) -> int:
        """Parsea permisos."""
        if isinstance(mode_value, int):
            return mode_value
        
        if isinstance(mode_value, str):
            mode_str = mode_value.lower().replace('0o', '')
            try:
                return int(mode_str, 8)
            except ValueError:
                return 0o644
        
        return 0o644
    
    def _generate_content(self, size: int, content_type: str = 'random') -> bytes:
        """Genera contenido de fichero."""
        if size == 0:
            return b''
        
        if content_type == 'zero':
            return b'\x00' * size
        elif content_type == 'text':
            return self._random_text(size).encode('utf-8')
        else:  # random
            return self._random_bytes(size)
    
    def _random_string(self, length: int, chars: str = None) -> str:
        """Genera string aleatorio."""
        if chars is None:
            chars = string.ascii_lowercase + string.digits
        return ''.join(random.choice(chars) for _ in range(length))
    
    def _random_bytes(self, size: int) -> bytes:
        """Genera bytes aleatorios."""
        return bytes(random.randint(0, 255) for _ in range(size))
    
    def _random_text(self, size: int) -> str:
        """Genera texto aleatorio legible."""
        words = ['lorem', 'ipsum', 'dolor', 'sit', 'amet', 'consectetur',
                 'adipiscing', 'elit', 'sed', 'do', 'eiusmod', 'tempor']
        
        result = []
        current_size = 0
        
        while current_size < size:
            word = random.choice(words)
            if current_size + len(word) + 1 > size:
                break
            result.append(word)
            current_size += len(word) + 1
        
        return ' '.join(result)


# Distribuciones de permisos para casos de práctica
PERMISSION_DISTRIBUTIONS = {
    'standard': [
        (0o644, 0.5),   # -rw-r--r-- (50%)
        (0o755, 0.2),   # -rwxr-xr-x (20%)
        (0o600, 0.15),  # -rw------- (15%)
        (0o777, 0.1),   # -rwxrwxrwx (10%)
        (0o000, 0.05),  # ---------- (5%)
    ],
    'special': [
        (0o4755, 0.3),  # SUID
        (0o2755, 0.3),  # SGID
        (0o1755, 0.2),  # Sticky
        (0o4000, 0.1),  # Solo SUID
        (0o2000, 0.1),  # Solo SGID
    ],
    'restrictive': [
        (0o600, 0.4),
        (0o400, 0.3),
        (0o000, 0.2),
        (0o100, 0.1),
    ],
}


def pick_from_distribution(dist_name: str) -> int:
    """Elige un permiso según distribución."""
    dist = PERMISSION_DISTRIBUTIONS.get(dist_name, PERMISSION_DISTRIBUTIONS['standard'])
    
    r = random.random()
    cumulative = 0
    
    for mode, prob in dist:
        cumulative += prob
        if r <= cumulative:
            return mode
    
    return dist[-1][0]
