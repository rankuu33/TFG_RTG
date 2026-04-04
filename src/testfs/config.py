"""
ASOFS - Parser de configuración YAML
====================================

Lee ficheros YAML y genera un FileSystem con los nodos especificados.

Formato soportado:
    
    # Metadatos globales (opcional)
    defaults:
      uid: 1000
      gid: 1000
    
    # Estructura del sistema de ficheros
    root:
      - name: "fichero.txt"
        type: file
        content: "Contenido del fichero"
        mode: 0644
      
      - name: "directorio"
        type: dir
        children:
          - name: "otro.txt"
            type: file
      
      - name: "enlace"
        type: symlink
        target: "fichero.txt"
"""

import os
import time
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from testfs.model import (
    FileSystem, FileNode, DirNode, SymlinkNode, FifoNode, DeviceNode
)


class ConfigError(Exception):
    """Error en la configuración."""
    pass


class ConfigParser:
    """
    Parser de configuración YAML para ASOFS.
    """
    
    def __init__(self):
        self._defaults = {
            'uid': os.getuid(),
            'gid': os.getgid(),
            'file_mode': 0o644,
            'dir_mode': 0o755,
        }
    
    def parse_file(self, path: str) -> FileSystem:
        """
        Lee un fichero YAML y devuelve un FileSystem.
        
        Args:
            path: Ruta al fichero YAML
        
        Returns:
            FileSystem configurado
        """
        with open(path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        return self.parse(config)
    
    def parse(self, config: Dict[str, Any]) -> FileSystem:
        """
        Parsea un diccionario de configuración.
        
        Args:
            config: Diccionario con la configuración
        
        Returns:
            FileSystem configurado
        """
        if config is None:
            config = {}
        
        # Cargar defaults
        if 'defaults' in config:
            self._defaults.update(config['defaults'])
        
        # Crear filesystem
        fs = FileSystem()
        
        # Parsear nodos raíz
        if 'root' in config:
            for node_config in config['root']:
                self._parse_node(fs, node_config, fs.ROOT_INODE)
        
        return fs
    
    def _parse_node(self, fs: FileSystem, config: Dict[str, Any], parent_inode: int):
        """
        Parsea un nodo y lo añade al filesystem.
        
        Args:
            fs: FileSystem donde añadir
            config: Configuración del nodo
            parent_inode: Inode del directorio padre
        """
        node_type = config.get('type', 'file')
        name = config.get('name')
        
        if not name:
            raise ConfigError("Cada nodo debe tener un 'name'")
        
        # Atributos comunes
        mode = self._parse_mode(config.get('mode'), node_type)
        uid = config.get('uid', self._defaults['uid'])
        gid = config.get('gid', self._defaults['gid'])
        
        # Timestamps
        now = time.time()
        atime = self._parse_timestamp(config.get('atime'), now)
        mtime = self._parse_timestamp(config.get('mtime'), now)
        ctime = self._parse_timestamp(config.get('ctime'), now)
        
        # Crear nodo según tipo
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
        
        # Añadir al filesystem
        fs.add(node, parent_inode)
        
        # Si es directorio, parsear hijos
        if node_type == 'dir' and 'children' in config:
            for child_config in config['children']:
                self._parse_node(fs, child_config, node.inode)
    
    def _parse_mode(self, mode_value: Any, node_type: str) -> int:
        """Parsea el modo/permisos."""
        if mode_value is None:
            if node_type == 'dir':
                return self._defaults['dir_mode']
            return self._defaults['file_mode']
        
        if isinstance(mode_value, int):
            return mode_value
        
        if isinstance(mode_value, str):
            # Soportar formato octal: "0755", "755", "0o755"
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
            # Soportar formatos relativos
            ts_lower = ts_value.lower()
            
            if ts_lower == 'now':
                return time.time()
            
            # Formato: "+1d", "-30d", "+1h", etc.
            if ts_lower.startswith(('+', '-')):
                return self._parse_relative_time(ts_lower)
            
            # Intentar parsear como fecha ISO
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
        content = config.get('content', '')
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        size = config.get('size', len(content) if content else 0)
        
        return FileNode(
            name=name,
            mode=mode,
            uid=uid,
            gid=gid,
            atime=atime,
            mtime=mtime,
            ctime=ctime,
            size=size,
            content=content
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
    """
    Función de conveniencia para cargar configuración.
    
    Args:
        path: Ruta al fichero YAML
    
    Returns:
        FileSystem configurado
    """
    parser = ConfigParser()
    return parser.parse_file(path)
