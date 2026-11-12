# AniStream

Reproductor de anime para **Linux**, con interfaz en español y vídeo integrado en la misma ventana. Construido con Python, GTK 4 y libmpv, a partir del proveedor AnimeAv1 de [anicli-esp](https://github.com/Asempere123123/anicli-esp).

- Búsqueda con portadas, sinopsis y selección de episodios.
- Favoritos, historial y continuación desde la posición guardada.
- Controles con iconos superpuestos al vídeo que se ocultan tras 2,5 segundos de inactividad.
- Pausa, avance, volumen, silencio, pantalla completa y cambio de episodio.
- Picture-in-Picture: vídeo en ventana flotante pequeña, con retorno a la app.
- Comprobación de enlaces, reintentos y alternativa entre MP4Upload y Voe.

La disponibilidad, el audio y los subtítulos dependen de cada título y del proveedor. AniStream no aloja ni distribuye vídeos. El binario original de anicli-esp es opcional.

## Instalación rápida

Descarga el [ZIP del proyecto](https://github.com/Zuaza796/AniStream/archive/refs/heads/main.zip), extráelo y ejecuta `./install.sh` desde su carpeta. También puedes usar Git:

```bash
git clone https://github.com/Zuaza796/AniStream.git
cd AniStream
./install.sh
```

El instalador comprueba las dependencias y, si faltan, utiliza el gestor de paquetes de la distribución. Solo ese paso necesita `sudo`. La app se instala para tu usuario y aparece en el menú como **AniStream**. No hace falta compilar Rust, instalar paquetes con pip ni tener anicli-esp instalado.

Recetas incluidas para Arch y derivadas, Debian/Ubuntu y Fedora. La instalación y reproducción se han probado en Arch Linux con Wayland; las demás recetas requieren validación en sus respectivas distribuciones. Requisitos: Python 3.10+, GTK 4.8+, PyGObject, BeautifulSoup 4, libmpv.so.2, OpenGL y EGL.

[Instalación, actualización y desinstalación](docs/INSTALLATION.md) · [Solución de problemas](docs/TROUBLESHOOTING.md)

## Uso

Abre AniStream desde el menú, busca una serie, entra en su ficha y selecciona un episodio. Los controles aparecen al mover el cursor. Al cerrar o regresar a la ficha se guarda la posición; durante la reproducción se actualiza cada cinco segundos.

| Atajo | Acción |
| --- | --- |
| Espacio | Pausar o continuar |
| ← / → | Retroceder o avanzar diez segundos |
| F | Alternar pantalla completa |
| P | Entrar o salir de Picture-in-Picture |
| Esc | Salir de pantalla completa; después volver a episodios |

El icono de una pantalla con un recuadro pequeño abre Picture-in-Picture. Conserva la posición, la pausa y el volumen; pulsa de nuevo el icono o cierra la ventana flotante para regresar. En Hyprland queda flotante y fijada entre espacios de trabajo. En otros escritorios el orden sobre otras aplicaciones depende del gestor de ventanas.

«Mi lista» guarda favoritos. «Historial» registra el último episodio abierto, no si se terminó de ver. Si falla una conexión, usa el icono de reintento. La ficha también permite abrir el episodio en el navegador.

## Arquitectura

```text
anistream/
├── app.py               # Interfaz GTK y coordinación de búsquedas/reproducción
├── backend.py           # Catálogo, episodios y resolución de servidores
├── player.py            # Puente ctypes de libmpv a Gtk.GLArea
├── library.py           # Persistencia JSON con escritura atómica
├── paths.py             # Directorios XDG y aislamiento de datos de prueba
└── resources/theme.css  # Estilos de la interfaz
scripts/                 # Instalación, desinstalación y comprobación de dependencias
tests/                   # Pruebas sin red y prueba gráfica opcional
docs/                    # Arquitectura, instalación, desarrollo y diagnóstico
third_party/             # Licencia y atribución del código adaptado
```

[Diseño y flujos de ejecución](docs/ARCHITECTURE.md) · [Desarrollo y pruebas](docs/DEVELOPMENT.md) · [Contribuir](CONTRIBUTING.md)

## Desarrollo

Con las dependencias nativas instaladas:

```bash
./install.sh --check
python3 -m anistream
python3 -m unittest discover -s tests -v
```

Los datos personales se guardan fuera del repositorio en `${XDG_DATA_HOME:-~/.local/share}/anistream/`. Para probar con una biblioteca independiente:

```bash
ANISTREAM_DATA_DIR=/tmp/anistream-dev python3 -m anistream
```

## Licencia y créditos

Código de AniStream bajo [MIT](LICENSE). La adaptación del proveedor de anicli-esp 1.3.1 conserva la atribución a Alejandro Sempere y su licencia MIT en [third_party](third_party/anicli-esp/LICENSE). Consulta [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) para las dependencias y la procedencia del código.
