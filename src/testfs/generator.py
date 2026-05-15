"""
ASOFS - Generador de ficheros
=============================

Genera ficheros automáticamente según patrones y distribuciones.
"""

import os
import random
import string
import time
from typing import Dict, Any, List, Optional, Tuple

from testfs.model import (
    FileSystem, FileNode, DirNode, SymlinkNode, FifoNode, DeviceNode,
    parse_size
)


# Distribuciones de permisos
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
    'open': [
        (0o777, 0.4),
        (0o775, 0.3),
        (0o766, 0.2),
        (0o755, 0.1),
    ],
}

# Distribuciones de tamaños
SIZE_DISTRIBUTIONS = {
    'small': [
        (0, 0.1),
        (100, 0.3),
        (500, 0.3),
        (1024, 0.2),
        (4096, 0.1),
    ],
    'medium': [
        (1024, 0.2),
        (10*1024, 0.3),
        (100*1024, 0.3),
        (500*1024, 0.15),
        (1024*1024, 0.05),
    ],
    'large': [
        (1024*1024, 0.3),
        (10*1024*1024, 0.3),
        (100*1024*1024, 0.2),
        (500*1024*1024, 0.15),
        (1024*1024*1024, 0.05),
    ],
    'mixed': [
        (0, 0.1),
        (1024, 0.2),
        (100*1024, 0.3),
        (1024*1024, 0.2),
        (10*1024*1024, 0.15),
        (100*1024*1024, 0.05),
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


def pick_size_from_distribution(dist_name: str) -> int:
    """Elige un tamaño según distribución."""
    dist = SIZE_DISTRIBUTIONS.get(dist_name, SIZE_DISTRIBUTIONS['small'])
    
    r = random.random()
    cumulative = 0
    
    for size, prob in dist:
        cumulative += prob
        if r <= cumulative:
            # Añadir variación aleatoria ±50%
            variation = random.uniform(0.5, 1.5)
            return int(size * variation)
    
    return dist[-1][0]


class Generator:
    """Generador de nodos para ASOFS."""
    
    def __init__(self, seed: int = None):
        self.seed = seed  # FIX: guardar seed para reproducibilidad
        if seed is not None:
            random.seed(seed)
        
        self._counter = 0
    
    def generate(self, fs: FileSystem, config: Dict[str, Any], parent_inode: int) -> List[int]:
        """Genera nodos según configuración."""
        gen_type = config.get('type', 'file')
        count = config.get('count', 1)
        
        inodes = []
        for i in range(count):
            self._counter += 1
            
            if gen_type == 'file':
                inode = self._generate_file(fs, config, parent_inode, i)
            elif gen_type == 'dir':
                inode = self._generate_dir(fs, config, parent_inode, i)
            elif gen_type == 'tree':
                inode = self._generate_tree(fs, config, parent_inode, i)
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
        mode = self._resolve_mode(config.get('mode', '0644'))
        size = self._resolve_size(config.get('size', 0))
        content_type = config.get('content_type', 'zeros')
        
        atime, mtime, ctime = self._resolve_timestamps(config)
        
        # FIX: usar seed global + nombre para reproducibilidad
        if self.seed is not None:
            content_seed = hash((self.seed, name)) & 0xFFFFFFFF
        else:
            content_seed = hash(name) & 0xFFFFFFFF
        
        node = FileNode(
            name=name,
            mode=mode,
            size=size,
            content=None,
            content_type=content_type,
            content_seed=content_seed,
            atime=atime,
            mtime=mtime,
            ctime=ctime
        )
        
        return fs.add(node, parent)
    
    def _generate_dir(self, fs: FileSystem, config: Dict, parent: int, index: int) -> int:
        """Genera un directorio."""
        name = self._expand_pattern(config.get('pattern', 'dir_{n}'), index)
        mode = self._resolve_mode(config.get('mode', '0755'))
        
        atime, mtime, ctime = self._resolve_timestamps(config)
        
        node = DirNode(
            name=name,
            mode=mode,
            atime=atime,
            mtime=mtime,
            ctime=ctime
        )
        
        inode = fs.add(node, parent)
        
        # FIX: Manejar children correctamente
        if 'children' in config:
            children = config['children']
            if isinstance(children, list):
                # Lista de configs de generación
                for child_config in children:
                    if isinstance(child_config, dict) and 'generate' in child_config:
                        self.generate(fs, child_config['generate'], inode)
                    elif isinstance(child_config, dict):
                        # Config de generación directa
                        self.generate(fs, child_config, inode)
            elif isinstance(children, dict):
                # Config de generación único
                self.generate(fs, children, inode)
        
        return inode
    
    def _generate_tree(self, fs: FileSystem, config: Dict, parent: int, index: int) -> int:
        """
        Genera un árbol de directorios con profundidad configurable.
        
        Config:
            depth: 3              # Niveles de profundidad
            breadth: 2            # Subdirectorios por nivel
            files_per_dir: 5      # Ficheros por directorio
            dir_pattern: "dir_{n}"
            file_pattern: "file_{n}.txt"
        """
        depth = config.get('depth', 2)
        breadth = config.get('breadth', 2)
        files_per_dir = config.get('files_per_dir', 3)
        dir_pattern = config.get('dir_pattern', 'nivel{d}_dir{n}')
        file_pattern = config.get('file_pattern', 'file_{n}.txt')
        file_size = config.get('file_size', [100, 1000])
        file_mode = config.get('file_mode', '0644')
        dir_mode = config.get('dir_mode', '0755')
        
        # Crear directorio raíz del árbol
        root_name = self._expand_pattern(config.get('pattern', 'tree_{n}'), index)
        root_node = DirNode(
            name=root_name,
            mode=self._resolve_mode(dir_mode)
        )
        root_inode = fs.add(root_node, parent)
        
        # Generar árbol recursivamente
        self._generate_tree_level(
            fs, root_inode, 1, depth, breadth, files_per_dir,
            dir_pattern, file_pattern, file_size, file_mode, dir_mode
        )
        
        return root_inode
    
    def _generate_tree_level(
        self, fs: FileSystem, parent_inode: int, 
        current_depth: int, max_depth: int, breadth: int, files_per_dir: int,
        dir_pattern: str, file_pattern: str, file_size: Any, file_mode: str, dir_mode: str
    ):
        """Genera un nivel del árbol recursivamente."""
        
        # Generar ficheros en este nivel
        for i in range(files_per_dir):
            name = file_pattern.format(n=i, d=current_depth, N=self._counter)
            self._counter += 1
            
            # FIX: usar seed global para content_seed
            if self.seed is not None:
                content_seed = hash((self.seed, name)) & 0xFFFFFFFF
            else:
                content_seed = hash(name) & 0xFFFFFFFF
            
            node = FileNode(
                name=name,
                mode=self._resolve_mode(file_mode),
                size=self._resolve_size(file_size),
                content_type='random',
                content_seed=content_seed
            )
            fs.add(node, parent_inode)
        
        # Si no hemos llegado al fondo, crear subdirectorios
        if current_depth < max_depth:
            for i in range(breadth):
                dir_name = dir_pattern.format(n=i, d=current_depth, N=self._counter)
                self._counter += 1
                
                dir_node = DirNode(
                    name=dir_name,
                    mode=self._resolve_mode(dir_mode)
                )
                dir_inode = fs.add(dir_node, parent_inode)
                
                # Recursión
                self._generate_tree_level(
                    fs, dir_inode, current_depth + 1, max_depth, breadth, files_per_dir,
                    dir_pattern, file_pattern, file_size, file_mode, dir_mode
                )
    
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
        mode = self._resolve_mode(config.get('mode', '0644'))
        
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
    
    def _resolve_mode(self, mode_value: Any) -> int:
        """Resuelve permisos, soportando distribuciones."""
        if mode_value is None:
            return 0o644
        
        if isinstance(mode_value, int):
            return mode_value
        
        if isinstance(mode_value, str):
            # Distribución: "dist:standard", "dist:special"
            if mode_value.startswith('dist:'):
                dist_name = mode_value[5:]
                return pick_from_distribution(dist_name)
            
            # Octal: "0755", "4755"
            mode_str = mode_value.lower().replace('0o', '')
            try:
                return int(mode_str, 8)
            except ValueError:
                return 0o644
        
        return 0o644
    
    def _resolve_size(self, value: Any) -> int:
        """Resuelve tamaño, soportando rangos y distribuciones."""
        if value is None:
            return 0
        
        if isinstance(value, int):
            return value
        
        if isinstance(value, str):
            # Distribución: "dist:small", "dist:large"
            if value.startswith('dist:'):
                dist_name = value[5:]
                return pick_size_from_distribution(dist_name)
            
            # Tamaño con unidad: "10MB", "1GB"
            return parse_size(value)
        
        if isinstance(value, list) and len(value) == 2:
            # Rango: [100, 1000] o ["1KB", "10KB"]
            min_size = parse_size(value[0])
            max_size = parse_size(value[1])
            return random.randint(min_size, max_size)
        
        return 0
    
    def _resolve_timestamps(self, config: Dict) -> Tuple[float, float, float]:
        """Resuelve timestamps según configuración."""
        now = time.time()
        
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
    
    def _random_string(self, length: int, chars: str = None) -> str:
        """Genera string aleatorio."""
        if chars is None:
            chars = string.ascii_lowercase + string.digits
        return ''.join(random.choice(chars) for _ in range(length))
