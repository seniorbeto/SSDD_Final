# Práctica Final SSDD

* **logger**   – Servicio RPC en C que persiste eventos
* **server**   – Servidor C que ofrece operaciones de claves/valores y delega el log al *logger*
* **web_server** – Mini API *REST* en Python que llama al *server*
* **client**   – Cliente de línea de comandos en Python

El script `app.sh` simplifica las tareas de compilación y limpieza, pero este README describe **paso a paso** cómo compilar y ejecutar cada componente, tal y como exige el enunciado.

---

## Tabla de contenido

1. [Requisitos previos](#requisitos-previos)
2. [Estructura del repositorio](#estructura-del-repositorio)
3. [Compilación rápida con `app.sh`](#compilación-rápida-con-appsh)
4. [Compilación manual](#compilación-manual)
    1. [`logger`](#logger)
    2. [`server`](#server)
5. [Ejecución de los servicios](#ejecución-de-los-servicios)
    1. [Lanzar **logger**](#lanzar-logger)
    2. [Lanzar **server**](#lanzar-server)
    3. [Lanzar **web_server**](#lanzar-web_server)
    4. [Lanzar **client**](#lanzar-client)
6. [Limpieza de artefactos](#limpieza-de-artefactos)
7. [Autores](#autores)

---

## Requisitos previos

| Herramienta | Versión mínima | Notas |
|-------------|----------------|-------|
| **GCC / Clang** | 11 | Para compilar código C con CMake |
| **CMake**  | 3.20 | Generación de *build* |
| **rpcgen** | SunRPC | Generación de *stubs* RPC de `logger.x` |
| **Python** | 3.10 | Ejecutar Web API y cliente CLI |

> **Entorno de desarrollo:** Ubuntu 22.04 LTS.

> **Entorno de producción:** Guernika.


---

## Estructura del repositorio

```text
├── app.sh                # Constructor del proyecto
├── autores.txt            # Autores
├── client/               # Cliente CLI Python
│   ├── client.py
│   ├── netools/
│   │   ├── netools.py
│   │   └── ...
│   └── server_svc.py
├── logger/               # Servicio RPC en C
│   ├── logger.c
│   ├── logger.x          # Interfaz RPC
│   └── compile.sh        # Build individual
├── server/               # Servidor de claves/valores en C
│   ├── server.c
│   ├── claves.c|h        # Lógica de claves
│   └── compile.sh        # Build individual
└── web_server/
    └── web_server.py     # API HTTP (Web Service)
```

> Las carpetas `cmake-build-release/` y los ficheros `*.log` **no** se incluyen en el control de versiones; se crean al compilar.

---

## Compilación rápida con `app.sh`

El script raíz `app.sh` centraliza el proceso de compilación y limpieza.

| Acción | Comando       |
|--------|---------------|
| **Build completo** | `./app.sh -b` |
| **Clean completo** | `./app.sh -c` |
| **Ayuda** | `./app.sh -h` |

Internamente, el *build* realiza:

1. Generación de *stubs* RPC del logger (`rpcgen logger.x`).
2. Compilación del **logger** (`logger/compile.sh`).
3. Compilación del **server** (`server/compile.sh`).
4. Mostrar instrucciones de ejecución al terminar.

Los *logs* temporales (`*.log`) se eliminan si la compilación es exitosa.

---

## Compilación manual

Si necesitas compilar cada componente por separado (por ejemplo, en CI), sigue estos pasos.

### `logger`

```bash
cd logger
./compile.sh          # genera build en logger/cmake-build-release/
```

El script invoca `rpcgen` y CMake en modo *Release*.

### `server`

```bash
cd server
./compile.sh          # genera build en server/cmake-build-release/
```

---

## Ejecución de los servicios

### Lanzar **logger**

```bash
./logger/cmake-build-release/logger
```

El logger expone un servicio RPC en el puerto asignado por *portmapper* (`rpcbind`).

### Lanzar **server**

```bash
export LOG_RPC_IP=<ip_del_logger>
./server/cmake-build-release/server -p <PUERTO_SERVIDOR>
```

* El servidor abre un puerto TCP.
* Todas las operaciones se registran mediante RPC en el **logger**.
* El servidor es totalmente funcional sin el logger, pero no registrará las operaciones.

### Lanzar **web_server**

```bash
python3 web_server/web_server.py   # por defecto en http://127.0.0.1:8000
```

Es muy importante tener instaladas todas las dependencias de Python para este servicio.
Todas ellas están disponibles en Guernika, pero sería necesario instalarlas en caso de ejecutar
este servicio en local.

### Lanzar **client**

```bash
python3 client/client.py -s <ip_servidor> -p <puerto>
```

### Comprobación end-to-end rápida

```bash
# 1. Construye todo
a./app.sh -b
# 2. Terminal A – logger
./logger/cmake-build-release/logger
# 3. Terminal B – server
export LOG_RPC_IP=localhost
./server/cmake-build-release/server -p 4444
# 4. Terminal C – client
python3 client/client.py -s localhost -p 4444
```

---

## Limpieza de artefactos

Para eliminar **todos** los directorios de compilación, directorios __pycache__ y ficheros generados:

```bash
./app.sh -c
```

Esto elimina:

* `logger/cmake-build-release/`
* `server/cmake-build-release/`
* Ficheros `*.log` y *stubs* RPC (`logger_*.c`, `logger.h`).
* Todos los directorios `__pycache__` de Python.

---

## Autores

Consulta el fichero [`autores.txt`](./autores.txt).

---

