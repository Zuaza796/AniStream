# Instalación en Linux

## Instalación para el usuario

```bash
git clone https://github.com/Zuaza796/AniStream.git
cd AniStream
./install.sh
```

También puedes descargar el ZIP de GitHub y ejecutar el mismo comando tras extraerlo. Ejecuta el instalador como usuario normal, **sin `sudo ./install.sh`**. Si faltan dependencias, el script invoca sudo solo para el gestor de paquetes.

El instalador verifica las dependencias antes de modificar la instalación. Copia el código a un directorio propio, crea el comando `~/.local/bin/anistream` y añade el acceso al menú. Puedes mover o eliminar después la carpeta descargada. No requiere entorno virtual ni pip.

Si el comando `anistream` no está en tu PATH, ábrelo desde el menú o ejecuta `~/.local/bin/anistream`.

## Dependencias y compatibilidad

Python 3.10+, GTK 4.8+, PyGObject, BeautifulSoup 4, libmpv con ABI 2 (`libmpv.so.2`), libEGL y libGL. Se requiere una sesión gráfica y soporte OpenGL 3.2.

| Familia | Paquetes utilizados por el instalador |
| --- | --- |
| Arch y derivadas | `python python-gobject gtk4 python-beautifulsoup4 mpv libglvnd` |
| Debian / Ubuntu | `python3 python3-gi gir1.2-gtk-4.0 python3-bs4 libmpv2 libegl1 libgl1` |
| Fedora | `python3 python3-gobject gtk4 python3-beautifulsoup4 mpv-libs libglvnd-egl libglvnd-glx` |

Las versiones antiguas que solo ofrecen `libmpv1` o GTK menor que 4.8 no cumplen los requisitos. No se agregan repositorios externos automáticamente. En Fedora la disponibilidad de códecs depende de los paquetes habilitados en el sistema.

Las recetas se basan en las [instrucciones de PyGObject](https://pygobject.gnome.org/getting_started.html), los paquetes de [Arch](https://archlinux.org/packages/extra/x86_64/mpv/), [Debian](https://packages.debian.org/trixie/libmpv2) y [Fedora](https://packages.fedoraproject.org/pkgs/mpv/). Solo Arch con Wayland ha tenido una prueba gráfica local en este proyecto; no se afirma validación gráfica de las demás distribuciones.

Para otras distribuciones, instala los equivalentes y ejecuta:

```bash
./install.sh --no-deps
```

Comprobar sin instalar:

```bash
./install.sh --check
```

`anicli-esp` y un terminal compatible son opcionales. Solo se utilizan al pulsar el botón que abre la interfaz original.

## Actualización

Cierra AniStream, actualiza la carpeta del repositorio y ejecuta el instalador otra vez:

```bash
git pull --ff-only
./install.sh
```

La actualización reemplaza la copia instalada de la aplicación. Conserva `library.json`, la caché y los registros. La copia instalada no sigue automáticamente los cambios de Git.

## Desinstalación

Cierra la app y ejecuta:

```bash
~/.local/bin/anistream-uninstall
```

Se eliminan la copia instalada y los accesos creados por el instalador. Los favoritos, el historial y las posiciones se conservan en `${XDG_DATA_HOME:-~/.local/share}/anistream/`. Las dependencias del sistema tampoco se desinstalan.

## Ubicaciones alternativas

El instalador respeta `XDG_DATA_HOME`. Para empaquetado o pruebas se admite `ANISTREAM_BIN_DIR`:

```bash
XDG_DATA_HOME=/tmp/anistream-install/share \
ANISTREAM_BIN_DIR=/tmp/anistream-install/bin \
./install.sh --no-deps
```

Las rutas deben ser absolutas. Para iniciar esa instalación con los mismos datos, conserva el valor de `XDG_DATA_HOME` al ejecutarla. El desinstalador recuerda las ubicaciones usadas al instalar.
