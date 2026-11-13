# AniStream Fresa para Windows

Edición independiente de AniStream con frontend nativo **Windows Forms**, colores rosa pastel, detalles crema y verde menta, icono pixel art original y botones con silueta de fresa. No utiliza GTK ni modifica la edición de Linux.

## Instalar

Descarga `AniStreamFresa-Setup.exe` desde la [página de versiones](https://github.com/Zuaza796/AniStream/releases). Ábrelo y pulsa la fresa de instalación. Crea accesos en el escritorio y en Inicio; no requiere administrador, Python, VLC instalado ni .NET instalado previamente.

También hay un ZIP portable. Extrae **toda** la carpeta y abre `AniStreamFresa.exe`. No copies únicamente el ejecutable: el directorio `libvlc/win-x64` contiene los plugins y bibliotecas nativas del vídeo.

Destino: **Windows 10/11 de 64 bits**. La aplicación y el instalador se compilan en Linux para Windows x64. El proveedor y la persistencia se prueban de manera automatizada; **la ejecución y la interfaz gráfica en un equipo Windows están pendientes de validación**. Los primeros artefactos se publican como versión preliminar, sin firma digital.

## Funciones

- Catálogo, búsqueda, sinopsis y selección de episodios.
- Mi lista, historial y Continuar viendo con biblioteca propia.
- Vídeo dentro de la aplicación, pausa, avance, volumen y pantalla completa.
- Controles superpuestos que se ocultan tras 2,5 segundos sin movimiento.
- Picture-in-Picture con ventana pequeña que permanece encima de otras ventanas.
- Fallback entre MP4Upload y Voe, comprobación de enlaces y reintento.
- Todos los botones de acción de la aplicación y el instalador son fresas dibujadas en código, con región de clic de esa forma y descripción accesible.

Los textos son en español. El audio y los subtítulos dependen del proveedor; la app no crea doblajes. Los cuadros de diálogo del sistema conservan el estilo de Windows.

Atajos: Espacio pausa; flechas avanzan/retroceden diez segundos; F alterna pantalla completa; P entra/sale de PiP; Esc regresa al reproductor o al inicio.

## Datos y desinstalación

- Aplicación instalada: `%LOCALAPPDATA%\Programs\AniStreamFresa`
- Biblioteca y registro: `%LOCALAPPDATA%\AniStreamFresa`

Es una biblioteca distinta a la edición Linux. Para desinstalar, usa **Configuración → Aplicaciones → AniStream Fresa**. El historial y los favoritos se conservan.

## Arquitectura

```text
windows/
  AniStream.Core/          Proveedor HTTPS, modelos y biblioteca JSON atómica
  AniStream.Fresa/         Frontend WinForms, fresas y reproducción LibVLCSharp
  AniStream.Fresa.Setup/   Instalador por usuario con payload completo
  AniStream.Core.Tests/    Pruebas sin interfaz (se ejecutan también en Linux)
  build/                  Generador del icono, desinstalador y empaquetado
  licenses/               Licencias y procedencia de dependencias
```

La interfaz llama al proveedor mediante tareas asíncronas cancelables. Las respuestas de una sección anterior no sustituyen la vista actual. El vídeo usa LibVLC en un `VideoView` integrado; PiP mueve el mismo control a una ventana `TopMost`, sin crear otro reproductor. El guardado se hace cada cinco segundos, al navegar y al cerrar. Los capítulos al 95 % o más salen de Continuar viendo y permanecen en el historial.

Las fresas de la interfaz se dibujan mediante `GraphicsPath`; la región de clic coincide con el contorno. El icono de la app se genera con una matriz de píxeles original, sin fotografías ni assets de terceros.

## Compilar

Herramientas para desarrolladores: **SDK .NET 10**, Python 3 y conexión para restaurar los paquetes NuGet. No son requisitos para quien instala el ejecutable terminado.

```bash
python3 windows/build/create_icon.py
dotnet run --project windows/AniStream.Core.Tests -c Release
python3 windows/build/publish.py
```

El mismo script puede ejecutarse desde Windows con `python` en lugar de `python3`. Si el SDK no está en PATH:

```bash
python3 windows/build/publish.py --dotnet /ruta/al/dotnet
```

Para probar además el proveedor real, de forma opcional:

```bash
dotnet run --project windows/AniStream.Core.Tests -c Release -- --live
```

El empaquetado publica el programa autocontenido, comprueba las DLL de VLC, incluye los avisos, genera el ZIP portable, lo incrusta en el instalador y produce `SHA256SUMS.txt`. Los binarios quedan en `windows/artifacts/releases/` y no se guardan en Git.

## Verificar en Windows

Instala desde una cuenta normal, inicia desde el acceso directo y comprueba búsqueda, favoritos tras reiniciar, continuación, reproducción MP4/HLS, pausa, volumen, controles al mover el ratón, PiP y cierre. Para aislar la interfaz del proveedor puedes abrir un archivo local con `AniStreamFresa.exe "C:\ruta\video.mp4"`; ese modo de diagnóstico no guarda el vídeo local en el historial.

Si ocurre un error de inicio, conserva la carpeta portable completa y revisa `%LOCALAPPDATA%\AniStreamFresa\errors.log`. La disponibilidad de servidores externos puede variar.
