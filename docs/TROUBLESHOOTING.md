# Solución de problemas

## Se queda cargando

Usa el icono de reintento. La aplicación obtiene enlaces nuevos, comprueba el acceso y prueba los servidores compatibles. Un enlace comprobado puede fallar después; la disponibilidad depende del proveedor y del servidor.

Comprueba primero las dependencias:

```bash
./install.sh --check
```

Los registros están en `${ANISTREAM_DATA_DIR:-${XDG_DATA_HOME:-~/.local/share}/anistream}/`:

- `errors.log`: resolución de fuentes, peticiones de reproducción y errores de la app.
- `mpv-embedded.log`: diagnóstico nativo de vídeo/audio; se reemplaza al iniciar un reproductor.
- `app.log`: salida del lanzador instalado y excepciones de GTK.

Los logs pueden incluir títulos, rutas de reproducción y enlaces firmados. Comparte únicamente el fragmento necesario, sin datos privados ni tokens.

## «No se pudo iniciar libmpv» con español de México

`player.py` establece `LC_NUMERIC=C` inmediatamente antes de crear libmpv. Este ajuste se necesita incluso si el separador decimal del locale es un punto. Si utilizas una copia antigua, actualiza y reinstala. No hace falta cambiar el idioma del escritorio ni exportar `LC_ALL=C`.

## Pantalla negra o error OpenGL

Comprueba los drivers de tu GPU y que la sesión disponga de OpenGL 3.2 y EGL. Ejecutar en un contenedor sin pantalla no valida la reproducción gráfica. El vídeo debe dibujarse en `Gtk.GLArea`; la app no abre una ventana externa para reproducir.

## Audio o vídeo no disponibles en una serie

Prueba otro episodio y revisa los errores del servidor. La disponibilidad de pistas y los códecs depende de la fuente y de la compilación de libmpv del sistema. La aplicación no genera doblajes ni subtítulos.

## Cambié el código, pero el menú abre la versión anterior

El acceso del menú ejecuta una copia instalada. Cierra la app y ejecuta `./install.sh` de nuevo, o usa `python3 -m anistream` para desarrollar directamente.

## Restaurar biblioteca dañada

Cuando la biblioteca no es JSON válido, se conserva como `library.json.invalid`. Cierra la app antes de restaurar una copia. No borres toda la carpeta de datos para resolver un fallo de reproducción: contiene tus favoritos y posiciones.
