"""
ASOFS - Parser de configuración YAML
====================================

Lee ficheros YAML y genera un FileSystem con los nodos especificados.
"""

import os
import time
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from testfs.model import (
    FileSystem, FileNode, DirNode, SymlinkNode, FifoNode, DeviceNode,
    parse_size
)
from testfs.generator import Generator, pick_from_distribution


class ConfigError(Exception):
    """Error en la configuración."""
    pass


class ConfigParser:
    """Parser de configuración YAML para ASOFS."""
    
    def __init__(self):
        self._defaults = {
            'uid': os.getuid(),
            'gid': os.getgid(),
            'file_mode': 0o644,
            'dir_mode': 0o755,
        }
        self._pending_hardlinks: List[Tuple[str, str, int]] = []
        self._path_to_inode: Dict[str, int] = {}
        self._generator: Generator = None
        self._seed: int = None  # FIX: guardar seed para content_seed
        
        self._users: Dict[str, int] = {}
        self._groups: Dict[str, int] = {}
    
    def parse_file(self, path: str) -> FileSystem:
        """Lee un fichero YAML y devuelve un FileSystem."""
        with open(path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return self.parse(config)
    
    def parse(self, config: Dict[str, Any]) -> FileSystem:
        """Parsea un diccionario de configuración."""
        if config is None:
            config = {}
        
        self._pending_hardlinks = []
        self._path_to_inode = {'/': FileSystem.ROOT_INODE}
        self._users = {}
        self._groups = {}
        
        if 'users' in config:
            self._users = {str(k): int(v) for k, v in config['users'].items()}
        
        if 'groups' in config:
            self._groups = {str(k): int(v) for k, v in config['groups'].items()}
        
        if 'defaults' in config:
            defaults = config['defaults']
            
            if 'owner' in defaults:
                defaults['uid'] = self._resolve_uid(defaults.pop('owner'))
            if 'group' in defaults:
                defaults['gid'] = self._resolve_gid(defaults.pop('group'))
            
            self._defaults.update(defaults)
        
        seed = config.get('seed')
        self._seed = seed  # FIX: guardar seed
        self._generator = Generator(seed=seed)
        
        fs = FileSystem()
        
        if 'root' in config:
            for node_config in config['root']:
                self._parse_node(fs, node_config, fs.ROOT_INODE, '/')
        
        self._process_hardlinks(fs)
        
        return fs
    
    def _resolve_uid(self, value: Any) -> int:
        """Resuelve un uid desde nombre o número."""
        if value is None:
            return self._defaults['uid']
        
        if isinstance(value, int):
            return value
        
        value_str = str(value)
        
        if value_str in self._users:
            return self._users[value_str]
        
        try:
            return int(value_str)
        except ValueError:
            raise ConfigError(f"Usuario desconocido: {value}")
    
    def _resolve_gid(self, value: Any) -> int:
        """Resuelve un gid desde nombre o número."""
        if value is None:
            return self._defaults['gid']
        
        if isinstance(value, int):
            return value
        
        value_str = str(value)
        
        if value_str in self._groups:
            return self._groups[value_str]
        
        try:
            return int(value_str)
        except ValueError:
            raise ConfigError(f"Grupo desconocido: {value}")
    
    def _parse_node(self, fs: FileSystem, config: Dict[str, Any], parent_inode: int, parent_path: str):
        """Parsea un nodo y lo añade al filesystem."""
        
        if 'generate' in config:
            self._generator.generate(fs, config['generate'], parent_inode)
            return
        
        node_type = config.get('type', 'file')
        name = config.get('name')
        
        if not name:
            raise ConfigError("Cada nodo debe tener un 'name'")
        
        current_path = f"{parent_path.rstrip('/')}/{name}"
        
        if node_type == 'hardlink':
            target = config.get('target')
            if not target:
                raise ConfigError(f"Hardlink '{name}' necesita 'target'")
            self._pending_hardlinks.append((name, target, parent_inode))
            return
        
        mode = self._parse_mode(config.get('mode'), node_type)
        
        uid = self._resolve_uid(config.get('owner', config.get('uid')))
        gid = self._resolve_gid(config.get('group', config.get('gid')))
        
        now = time.time()
        atime = self._parse_timestamp(config.get('atime'), now)
        mtime = self._parse_timestamp(config.get('mtime'), now)
        ctime = self._parse_timestamp(config.get('ctime'), now)
        
        if node_type == 'file':
            node = self._create_file(config, name, mode, uid, gid, atime, mtime, ctime)
        elif node_type == 'dir':
            node = self._create_dir(config, name, mode, uid, gid, atime, mtime, ctime)
        elif node_type == 'symlink':
            node = self._create_symlink(config, name, uid, gid, atime, mtime, ctime)
        elif node_type == 'fifo':
            node = self._create_fifo(config, name, mode, uid, gid, atime, mtime, ctime)
        elif node_type in ('char', 'block'):
            node = self._create_device(config, name, mode, uid, gid, atime, mtime, ctime, node_type)
        else:
            raise ConfigError(f"Tipo de nodo desconocido: {node_type}")
        
        inode = fs.add(node, parent_inode)
        
        self._path_to_inode[current_path] = inode
        
        if node_type == 'dir' and 'children' in config:
            for child_config in config['children']:
                self._parse_node(fs, child_config, node.inode, current_path)
    
    def _process_hardlinks(self, fs: FileSystem):
        """Procesa los hardlinks pendientes."""
        for name, target, parent_inode in self._pending_hardlinks:
            target_path = target if target.startswith('/') else f"/{target}"
            target_inode = self._path_to_inode.get(target_path)
            
            if target_inode is None:
                raise ConfigError(f"Hardlink '{name}' apunta a '{target}' que no existe")
            
            fs.add_hardlink(name, target_inode, parent_inode)
    
    def _parse_mode(self, mode_value: Any, node_type: str) -> int:
        """Parsea el modo/permisos."""
        if mode_value is None:
            if node_type == 'dir':
                return self._defaults['dir_mode']
            return self._defaults['file_mode']
        
        if isinstance(mode_value, str) and mode_value.startswith('dist:'):
            dist_name = mode_value[5:]
            return pick_from_distribution(dist_name)
        
        if isinstance(mode_value, int):
            # FIX: Si es entero <= 7777, asumir que es octal mal escrito
            # (el usuario puso mode: 644 en lugar de mode: "0644")
            if mode_value <= 7777:
                octal_str = str(mode_value)
                try:
                    return int(octal_str, 8)
                except ValueError:
                    return mode_value
            return mode_value
        
        if isinstance(mode_value, str):
            mode_str = mode_value.lower().replace('0o', '')
            try:
                return int(mode_str, 8)
            except ValueError:
                raise ConfigError(f"Modo inválido: {mode_value}")
        
        raise ConfigError(f"Modo inválido: {mode_value}")
    
    def _parse_timestamp(self, ts_value: Any, default: float) -> float:
        """Parsea un timestamp."""
        if ts_value is None:
            return default
        
        if isinstance(ts_value, (int, float)):
            return float(ts_value)
        
        if isinstance(ts_value, str):
            ts_lower = ts_value.lower()
            
            if ts_lower == 'now':
                return time.time()
            
            if ts_lower.startswith(('+', '-')):
                return self._parse_relative_time(ts_lower)
            
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(ts_value)
                return dt.timestamp()
            except ValueError:
                pass
        
        raise ConfigError(f"Timestamp inválido: {ts_value}")
    
    def _parse_relative_time(self, value: str) -> float:
        """Parsea tiempo relativo como '+1d', '-30d', etc."""
        import re
        
        match = re.match(r'^([+-]?\d+)([smhdwy])$', value.lower())
        if not match:
            raise ConfigError(f"Formato de tiempo relativo inválido: {value}")
        
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
        
        return time.time() + (amount * multipliers[unit])
    
    def _create_file(self, config, name, mode, uid, gid, atime, mtime, ctime) -> FileNode:
        """Crea un FileNode."""
        content = config.get('content')
        content_type = config.get('content_type', 'static')
        size_value = config.get('size')
        
        # Si hay contenido estático
        if content is not None:
            if isinstance(content, str):
                content = content.encode('utf-8')
            size = len(content)
            content_type = 'static'
        else:
            content = None
            size = parse_size(size_value) if size_value else 0
        
        # FIX: usar seed global + nombre para reproducibilidad
        if self._seed is not None:
            content_seed = hash((self._seed, name)) & 0xFFFFFFFF
        else:
            content_seed = hash(name) & 0xFFFFFFFF
        
        return FileNode(
            name=name,
            mode=mode,
            uid=uid,
            gid=gid,
            atime=atime,
            mtime=mtime,
            ctime=ctime,
            size=size,
            content=content,
            content_type=content_type,
            content_seed=content_seed
        )
    
    def _create_dir(self, config, name, mode, uid, gid, atime, mtime, ctime) -> DirNode:
        """Crea un DirNode."""
        return DirNode(
            name=name,
            mode=mode,
            uid=uid,
            gid=gid,
            atime=atime,
            mtime=mtime,
            ctime=ctime
        )
    
    def _create_symlink(self, config, name, uid, gid, atime, mtime, ctime) -> SymlinkNode:
        """Crea un SymlinkNode."""
        target = config.get('target', '')
        if not target:
            raise ConfigError(f"Symlink '{name}' necesita 'target'")
        
        return SymlinkNode(
            name=name,
            target=target,
            uid=uid,
            gid=gid,
            atime=atime,
            mtime=mtime,
            ctime=ctime
        )
    
    def _create_fifo(self, config, name, mode, uid, gid, atime, mtime, ctime) -> FifoNode:
        """Crea un FifoNode."""
        return FifoNode(
            name=name,
            mode=mode,
            uid=uid,
            gid=gid,
            atime=atime,
            mtime=mtime,
            ctime=ctime
        )
    
    def _create_device(self, config, name, mode, uid, gid, atime, mtime, ctime, dev_type) -> DeviceNode:
        """Crea un DeviceNode."""
        major = config.get('major', 0)
        minor = config.get('minor', 0)
        
        return DeviceNode(
            name=name,
            mode=mode,
            uid=uid,
            gid=gid,
            atime=atime,
            mtime=mtime,
            ctime=ctime,
            major=major,
            minor=minor,
            block=(dev_type == 'block')
        )


def load_config(path: str) -> FileSystem:
    """Función de conveniencia para cargar configuración."""
    parser = ConfigParser()
    return parser.parse_file(path)
