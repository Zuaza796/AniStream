# Desarrollo y pruebas

## Ejecutar desde el código

Instala las dependencias de [instalación](INSTALLATION.md) y utiliza el Python del sistema, que es el que tiene los bindings de GTK:

```bash
./install.sh --check
ANISTREAM_DATA_DIR=/tmp/anistream-dev python3 -m anistream
```

`app.py` en la raíz conserva la compatibilidad con lanzadores antiguos. El punto de entrada del paquete es `python3 -m anistream`. `pyproject.toml` describe el paquete, pero pip por sí solo no instala GTK, libmpv ni los bindings nativos.

## Pruebas sin red ni pantalla

```bash
python3 -m unittest discover -s tests -v
bash -n install.sh
python3 scripts/check_dependencies.py
```

Las pruebas cubren selección de fuentes, rechazo de enlaces de publicidad, fallback, persistencia y ciclo de instalación/desinstalación con rutas aisladas. No llaman a sudo ni modifican la instalación real. La plantilla [github-actions.yml.example](github-actions.yml.example) ejecuta estas comprobaciones en Ubuntu sin descargar episodios. Para activarla, cópiala a `.github/workflows/ci.yml` usando una credencial con permiso para workflows o desde el editor de GitHub. La autenticación utilizada para la publicación inicial no permite crear workflows.

## Prueba gráfica opcional

Requiere una sesión gráfica, conexión a Internet y un episodio disponible:

```bash
env -u LC_ALL LANG=es_MX.UTF-8 LC_NUMERIC=es_MX.UTF-8 \
  python3 tests/smoke_player.py /tmp/anistream-smoke
```

Ejecuta el mismo comando dos veces. La primera ejecución reproduce un episodio en el área integrada, salta al segundo 30 y guarda el estado. La segunda verifica que un proceso nuevo recupera esa posición. La prueba silencia el audio y usa una biblioteca aislada. El locale debe existir en tu sistema.

Un cambio de controles debe comprobar también: ocultación por inactividad, retorno con movimiento, arrastre de la barra sin ocultarse, teclado, silencio y pantalla completa. Un cambio de fuentes requiere comprobar fallos de red y agotamiento de reintentos, además del caso exitoso.

## Antes de publicar

- Ejecuta las pruebas y revisa `git diff --check`.
- No incluyas `library.json`, imágenes de caché, logs, enlaces firmados ni capturas del escritorio personal.
- Actualiza los documentos cuando cambien los contratos de los módulos o los requisitos.
- Mantén las atribuciones del código adaptado de anicli-esp.

El repositorio remoto es `https://github.com/Zuaza796/AniStream.git`. El historial de uso pertenece al directorio XDG del usuario y no forma parte de Git.

## Prueba de Picture-in-Picture

La prueba utiliza un vídeo local, sin depender de servidores externos ni modificar la biblioteca personal. Con ffmpeg disponible:

```bash
ffmpeg -f lavfi -i testsrc2=size=640x360:rate=24 -t 60 -c:v mpeg4 -q:v 8 -an /tmp/anistream-pip.mp4
python3 tests/smoke_pip.py /tmp/anistream-pip.mp4
```

Comprueba cambios repetidos de ventana, mismo núcleo mpv, posición y pausa conservadas, cierre de PiP y navegación del catálogo. En Hyprland verifica también flotación y fijación. Es una prueba gráfica opcional; las pruebas unitarias de `test_pip.py` no requieren pantalla ni cambios reales en el compositor.

## Biblioteca y Continuar viendo

`test_continue_watching.py` comprueba compatibilidad con bibliotecas antiguas, orden de reproducción, filtros de episodios terminados y conservación de metadatos. La prueba gráfica, con un clip local de al menos 60 segundos, recorre los botones reales de navegación, una respuesta de catálogo tardía, la continuación del episodio correcto y la persistencia de favoritos:

```bash
python3 tests/smoke_library.py /tmp/anistream-pip.mp4
```

La red se sustituye por datos de prueba dentro de ese proceso; la biblioteca se guarda en un directorio temporal independiente.
