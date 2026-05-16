# ASOFS - Administración de Sistemas Operativos File System

ASOFS es una herramienta para la creación y simulación de sistemas de ficheros orientada a la docencia en Administración de Sistemas Operativos.

El proyecto permite definir sistemas de ficheros virtuales mediante ficheros YAML y montarlos en Linux usando FUSE3. Su objetivo principal es facilitar la creación de escenarios de práctica reproducibles para trabajar con permisos, propietarios, grupos, enlaces, fechas, tamaños virtuales y distintos tipos de nodos sin tener que preparar manualmente una estructura real en disco.

Este repositorio forma parte del Trabajo de Fin de Grado:

**Diseño y desarrollo de una herramienta para la creación y simulación de sistemas de ficheros orientada a la docencia en Administración de Sistemas Operativos**

Autor: **Raúl Trejo González**  
Tutor: **José Miguel Santos Espino**  
Titulación: **Grado en Ingeniería Informática**  
Fecha: **Mayo de 2026**

---

## Características principales

- Definición declarativa de sistemas de ficheros mediante YAML.
- Montaje de sistemas de ficheros virtuales mediante FUSE3.
- Soporte para ficheros regulares, directorios, enlaces simbólicos, enlaces duros, FIFOs y nodos de dispositivo.
- Configuración de permisos POSIX, incluyendo bits especiales como SUID, SGID y sticky bit.
- Configuración de propietarios y grupos mediante nombres o UID/GID.
- Configuración de fechas de acceso, modificación y cambio.
- Soporte para tamaños virtuales sin materializar todo el contenido en disco.
- Generación masiva de nodos mediante patrones.
- Generación de árboles de directorios configurables.
- Generación de scripts para crear y eliminar usuarios/grupos ficticios de prácticas.
- Conjunto de ejemplos YAML orientados a escenarios docentes.
- Suite de pruebas funcionales basada en BATS.

---

## Estado del proyecto

ASOFS es un proyecto académico desarrollado como parte de un Trabajo de Fin de Grado.

La herramienta está pensada para entornos docentes, pruebas controladas y generación de escenarios de práctica. No debe considerarse un sistema de ficheros persistente ni una herramienta de administración de sistemas en producción.

---

## Requisitos

ASOFS requiere un sistema Linux con soporte para FUSE3.

### Requisitos principales

- Linux.
- Python 3.10 o superior.
- pip.
- FUSE3.
- libfuse3-dev.
- pkg-config.

### Instalación de dependencias del sistema

En distribuciones basadas en Debian o Ubuntu:

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv pkg-config libfuse3-dev fuse3
```

Comprobación básica:

```bash
python3 --version
fusermount3 -V
```

---

## Instalación

Clonar el repositorio:

```bash
git clone https://github.com/rankuu33/TFG_RTG.git
cd TFG_RTG
```

Crear y activar un entorno virtual:

```bash
python3 -m venv venv
source venv/bin/activate
```

Instalar dependencias e instalar el proyecto en modo desarrollo:

```bash
pip install -r requirements.txt
pip install -e .
```

Comprobar que el comando está disponible:

```bash
asofs --help
```

---

## Uso rápido

Crear un punto de montaje:

```bash
mkdir -p /tmp/asofs
```

Montar un sistema de ficheros usando un ejemplo YAML:

```bash
asofs mount /tmp/asofs -c examples/basic.yaml
```

Explorar el sistema de ficheros desde otra terminal:

```bash
ls -la /tmp/asofs
find /tmp/asofs -type f
stat /tmp/asofs/hello.txt
```

Desmontar:

```bash
fusermount3 -u /tmp/asofs
```

También se puede detener el proceso de montaje con `Ctrl+C` en la terminal donde se ejecutó `asofs mount`.

---

## Comandos disponibles

La interfaz de línea de comandos se organiza mediante subcomandos.

```bash
asofs <comando> [opciones]
```

### `mount`

Monta un sistema de ficheros virtual en un punto de montaje.

```bash
asofs mount <punto_de_montaje> [opciones]
```

Opciones:

```bash
-c, --config FILE    Fichero de configuración YAML
-d, --debug          Activa el modo debug
```

Ejemplo:

```bash
asofs mount /tmp/asofs -c examples/basic.yaml
```

Ejemplo con modo debug:

```bash
asofs mount /tmp/asofs -c examples/basic.yaml -d
```

---

### `setup-users`

Genera un script de shell para crear los usuarios y grupos definidos en una configuración YAML.

```bash
asofs setup-users -c config.yaml -o setup.sh
```

Revisar el script generado antes de ejecutarlo:

```bash
cat setup.sh
```

Ejecutar el script con privilegios de administración:

```bash
sudo bash setup.sh
```

---

### `cleanup-users`

Genera un script de shell para eliminar los usuarios y grupos definidos en una configuración YAML.

```bash
asofs cleanup-users -c config.yaml -o cleanup.sh
```

Revisar el script generado antes de ejecutarlo:

```bash
cat cleanup.sh
```

Ejecutar el script con privilegios de administración:

```bash
sudo bash cleanup.sh
```

---

## Formato de configuración YAML

ASOFS utiliza ficheros YAML para describir el sistema de ficheros virtual.

Estructura general:

```yaml
seed: 42

users:
  alice: 1001
  bob: 1002

groups:
  users: 100
  staff: 200

defaults:
  owner: alice
  group: users
  file_mode: "0644"
  dir_mode: "0755"

root:
  - name: "hello.txt"
    type: file
    content: "Hola mundo\n"
    mode: "0644"
    owner: alice
    group: users

  - name: "docs"
    type: dir
    mode: "0755"
    children:
      - name: "readme.txt"
        type: file
        content: "Documento dentro de un directorio\n"
```

---

## Tipos de nodos soportados

### Fichero regular

```yaml
- name: "documento.txt"
  type: file
  content: "Contenido del fichero\n"
  mode: "0644"
  owner: alice
  group: users
```

También puede definirse un fichero con tamaño virtual:

```yaml
- name: "grande.bin"
  type: file
  size: "1GB"
  content_type: pattern
  mode: "0644"
```

Tipos de contenido soportados:

```yaml
content_type: static
content_type: zeros
content_type: pattern
content_type: random
content_type: text
```

---

### Directorio

```yaml
- name: "carpeta"
  type: dir
  mode: "0755"
  children:
    - name: "archivo.txt"
      type: file
      content: "Contenido interno\n"
```

---

### Enlace simbólico

```yaml
- name: "documento.txt"
  type: file
  content: "Contenido original\n"

- name: "enlace_simbolico"
  type: symlink
  target: "/documento.txt"
```

---

### Enlace duro

```yaml
- name: "documento.txt"
  type: file
  content: "Contenido compartido\n"

- name: "enlace_duro"
  type: hardlink
  target: "/documento.txt"
```

El destino de un enlace duro debe existir en el mismo fichero YAML y no puede ser un directorio.

---

### FIFO

```yaml
- name: "tuberia"
  type: fifo
  mode: "0644"
```

---

### Dispositivo de carácter

```yaml
- name: "null"
  type: char
  major: 1
  minor: 3
  mode: "0666"
```

---

### Dispositivo de bloque

```yaml
- name: "sda"
  type: block
  major: 8
  minor: 0
  mode: "0660"
```

---

## Permisos

Los permisos se indican en formato octal como cadena de texto.

```yaml
mode: "0644"    # rw-r--r--
mode: "0755"    # rwxr-xr-x
mode: "0600"    # rw-------
```

También pueden usarse bits especiales:

```yaml
mode: "4755"    # SUID
mode: "2755"    # SGID
mode: "1755"    # sticky bit
```

Ejemplo de búsqueda sobre un escenario montado:

```bash
find /tmp/asofs -perm -4000
find /tmp/asofs -perm -2000
find /tmp/asofs -perm -1000
```

---

## Propietarios y grupos

Los usuarios y grupos pueden definirse en el YAML:

```yaml
users:
  alice: 1001
  bob: 1002

groups:
  users: 100
  staff: 200
```

Después pueden usarse en los nodos:

```yaml
- name: "privado.txt"
  type: file
  content: "Contenido privado\n"
  owner: alice
  group: staff
  mode: "0640"
```

También pueden utilizarse valores numéricos directamente:

```yaml
- name: "uid_gid_directo.txt"
  type: file
  content: "Ejemplo\n"
  owner: 1001
  group: 100
```

---

## Timestamps

ASOFS permite configurar fechas de acceso, modificación y cambio.

```yaml
- name: "antiguo.txt"
  type: file
  content: "Fichero antiguo\n"
  mtime: "-30d"
  atime: "-10d"
  ctime: "-5d"
```

Formatos soportados:

```yaml
mtime: "now"
mtime: "-30d"
mtime: "+7d"
mtime: "-1w"
mtime: "-1y"
mtime: "2024-06-15T10:00:00"
mtime: 1700000000
```

Unidades relativas:

- `s`: segundos.
- `m`: minutos.
- `h`: horas.
- `d`: días.
- `w`: semanas.
- `y`: años.

---

## Tamaños virtuales

Los ficheros pueden declarar tamaños sin almacenar todo el contenido físicamente en disco.

```yaml
- name: "pequeno.txt"
  type: file
  size: "1KB"
  content_type: pattern

- name: "imagen.img"
  type: file
  size: "1GB"
  content_type: zeros

- name: "enorme.raw"
  type: file
  size: "1TB"
  content_type: random
```

Formatos admitidos:

```yaml
size: 1024
size: "1KB"
size: "100MB"
size: "1GB"
size: "1TB"
size: "1PB"
```

---

## Generación masiva

ASOFS permite generar nodos de forma automática a partir de patrones.

### Generación de ficheros

```yaml
root:
  - generate:
      type: file
      count: 100
      pattern: "file_{n:04d}.txt"
      size: ["1KB", "100KB"]
      content_type: text
      mode: "dist:standard"
```

Variables disponibles en patrones:

```yaml
pattern: "file_{n}.txt"
pattern: "file_{n:04d}.txt"
pattern: "item_{random}.dat"
pattern: "item_{alpha}.dat"
pattern: "item_{uuid}.dat"
pattern: "item_{num}.dat"
```

---

### Generación de árboles

```yaml
root:
  - generate:
      type: tree
      count: 1
      pattern: "proyecto"
      depth: 4
      breadth: 3
      files_per_dir: 5
      dir_pattern: "modulo_{d}_{n}"
      file_pattern: "src_{n}.py"
      file_size: ["1KB", "50KB"]
      file_mode: "0644"
      dir_mode: "0755"
```

---

### Generación mixta

```yaml
root:
  - generate:
      type: mixed
      count: 50
      pattern: "item_{n:03d}"
      mode: "dist:standard"
      size: [100, 1000]
```

En la versión actual, la generación mixta se limita a ficheros, enlaces simbólicos y FIFOs.

---

## Distribuciones predefinidas

En generación masiva pueden usarse distribuciones para permisos:

```yaml
mode: "dist:standard"
mode: "dist:special"
mode: "dist:restrictive"
mode: "dist:open"
```

También pueden usarse distribuciones para tamaños:

```yaml
size: "dist:small"
size: "dist:medium"
size: "dist:large"
size: "dist:mixed"
```

---

## Ejemplo completo

Guardar el siguiente contenido como `config.yaml`:

```yaml
seed: 42

users:
  alice: 1001
  bob: 1002
  admin: 2000

groups:
  users: 100
  staff: 200

defaults:
  owner: alice
  group: users
  file_mode: "0644"
  dir_mode: "0755"

root:
  - name: "publico.txt"
    type: file
    content: "Fichero de acceso publico\n"
    mode: "0644"
    owner: alice
    group: users
    mtime: "-10d"

  - name: "privado.txt"
    type: file
    content: "Fichero privado\n"
    mode: "0600"
    owner: bob
    group: users
    mtime: "-30d"

  - name: "ejecutable_suid"
    type: file
    size: "1KB"
    content_type: pattern
    mode: "4755"
    owner: admin
    group: staff

  - name: "directorio"
    type: dir
    mode: "0755"
    children:
      - name: "interno.txt"
        type: file
        content: "Fichero interno\n"

  - name: "enlace_a_publico"
    type: symlink
    target: "/publico.txt"

  - generate:
      type: file
      count: 10
      pattern: "log_{n:03d}.txt"
      size: ["1KB", "10KB"]
      content_type: text
      mode: "0644"
      time_range: ["-365d", "-1d"]
```

Montar:

```bash
mkdir -p /tmp/asofs
asofs mount /tmp/asofs -c config.yaml
```

Probar comandos:

```bash
ls -la /tmp/asofs
find /tmp/asofs -type f
find /tmp/asofs -perm -4000
find /tmp/asofs -mtime +30
stat /tmp/asofs/ejecutable_suid
```

Desmontar:

```bash
fusermount3 -u /tmp/asofs
```

---

## Ejemplos incluidos

El repositorio incluye ficheros YAML de ejemplo en el directorio `examples/`.

Uso típico:

```bash
asofs mount /tmp/asofs -c examples/basic.yaml
```

Se recomienda revisar los ejemplos antes de crear configuraciones propias:

```bash
ls examples
```

---

## Tests

El repositorio incluye una suite de pruebas funcionales basada en BATS.

Ejecutar todos los tests:

```bash
tests/run_tests.sh
```

También puede ejecutarse directamente un fichero concreto de pruebas si BATS está instalado en el sistema:

```bash
bats tests/bats/test_mount.bats
```

---

## Estructura del proyecto

La estructura principal del repositorio es:

```text
TFG_RTG/
├── README.md
├── LICENSE
├── pyproject.toml
├── requirements.txt
├── examples/
│   └── *.yaml
├── src/
│   └── testfs/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── generator.py
│       ├── model.py
│       └── fuse/
│           ├── __init__.py
│           └── filesystem.py
└── tests/
    ├── run_tests.sh
    └── bats/
        └── test_*.bats
```

Nota: en la versión actual, el paquete Python interno conserva el nombre `testfs`, aunque el comando instalado para el usuario es `asofs`.

---

## Componentes principales

- `cli.py`: interfaz de línea de comandos.
- `config.py`: carga y validación de configuraciones YAML.
- `model.py`: modelo de nodos del sistema de ficheros.
- `generator.py`: generación masiva de estructuras.
- `filesystem.py`: integración con FUSE3.
- `examples/`: configuraciones de ejemplo.
- `tests/`: pruebas funcionales.

---

## Limitaciones actuales

- ASOFS depende de FUSE3, por lo que está orientado a Linux.
- No se ofrece compatibilidad oficial con Windows ni macOS.
- La herramienta está diseñada principalmente para escenarios docentes y de prueba.
- El sistema de ficheros virtual no está pensado como almacenamiento persistente.
- Los enlaces duros deben apuntar a rutas existentes dentro del mismo YAML.
- La generación mixta no genera todos los tipos de nodos disponibles.
- Algunas operaciones dependen del comportamiento del entorno FUSE y de los permisos del usuario que ejecuta el montaje.

---

## Solución de problemas

### El comando `asofs` no existe

Comprobar que el entorno virtual está activado:

```bash
source venv/bin/activate
```

Reinstalar el proyecto en modo desarrollo:

```bash
pip install -e .
```

---

### Error relacionado con FUSE3

Comprobar que FUSE3 está instalado:

```bash
fusermount3 -V
```

Instalar dependencias:

```bash
sudo apt install pkg-config libfuse3-dev fuse3
```

---

### No se puede montar en el punto indicado

Comprobar que el directorio existe:

```bash
mkdir -p /tmp/asofs
```

Comprobar permisos:

```bash
ls -ld /tmp/asofs
```

Probar con un punto de montaje dentro de `/tmp`:

```bash
asofs mount /tmp/asofs -c examples/basic.yaml
```

---

### El punto de montaje queda ocupado

Desmontar con:

```bash
fusermount3 -u /tmp/asofs
```

Si el desmontaje normal no funciona:

```bash
fusermount3 -uz /tmp/asofs
```

---

## Advertencia sobre usuarios ficticios

Los comandos `setup-users` y `cleanup-users` generan scripts que pueden crear o eliminar usuarios y grupos del sistema.

Antes de ejecutar estos scripts con `sudo`, se recomienda revisar siempre su contenido:

```bash
cat setup.sh
cat cleanup.sh
```

---

## Licencia

Este proyecto se publica bajo licencia MIT. Consultar el fichero `LICENSE` para más información.

---

## Autor

Raúl Trejo González  
Trabajo de Fin de Grado  
Grado en Ingeniería Informática  
Escuela de Ingeniería Informática  
Universidad de Las Palmas de Gran Canaria
