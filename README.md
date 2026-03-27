# ASOFS

**Sistema de Ficheros Virtual para Administración de Sistemas Operativos**

Trabajo de Fin de Grado  
Escuela de Ingeniería Informática - ULPGC  
Autor: Raúl Trejo González  
Tutor: José Miguel Santos Espino

---

## Descripción

ASOFS es una herramienta que genera sistemas de ficheros virtuales con atributos configurables, diseñada para la docencia en la asignatura ASO. Permite crear escenarios de prueba con ficheros que incluyen permisos especiales, timestamps variados, nombres problemáticos y más.

## Requisitos

- Python >= 3.10
- Linux con FUSE3
- libfuse3-dev
```bash
sudo apt install fuse3 libfuse3-dev
```

## Instalación
```bash
git clone https://github.com/tu-usuario/asofs.git
cd asofs

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
pip install -e .
```

## Uso
```bash
# Crear punto de montaje
mkdir -p /tmp/asofs

# Montar
asofs mount /tmp/asofs -d

# En otra terminal
ls -la /tmp/asofs/
cat /tmp/asofs/hello.txt

# Desmontar
fusermount -u /tmp/asofs
```

## Licencia

MIT
