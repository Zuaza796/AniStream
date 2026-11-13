# Componentes distribuidos con AniStream Fresa

AniStream Fresa y sus fresas dibujadas en código son originales del proyecto (MIT, Zuaza796). El proveedor AnimeAv1 adapta anicli-esp 1.3.1, Copyright 2026 Alejandro Sempere, bajo su opción MIT. El paquete incluye ambas licencias.

- AngleSharp 1.10.2: MIT, Copyright 2013-2026 AngleSharp. Fuente: https://github.com/AngleSharp/AngleSharp/tree/b01d947aacf42044d5daf6065be83871ec09b8f4
- LibVLCSharp y LibVLCSharp.WinForms 3.10.2: VideoLAN, LGPL-2.1-or-later. Fuentes: https://code.videolan.org/videolan/LibVLCSharp y https://github.com/videolan/libvlcsharp
- VideoLAN.LibVLC.Windows 3.0.24: distribución oficial de bibliotecas de VideoLAN, LGPL-2.1-or-later; los plugins conservan sus licencias respectivas. El paquete binario original está en https://www.nuget.org/packages/VideoLAN.LibVLC.Windows/3.0.24
- Fuentes de VLC 3.0.24: https://download.videolan.org/pub/videolan/vlc/3.0.24/vlc-3.0.24.tar.xz ; compilación del paquete NuGet: https://code.videolan.org/videolan/libvlc-nuget ; fuentes y contribuciones: https://code.videolan.org/videolan/vlc/-/tree/3.0.x/contrib
- .NET / Windows Forms: Microsoft y contribuidores, MIT y avisos de terceros incluidos. Fuentes: https://github.com/dotnet/runtime y https://github.com/dotnet/winforms

Las bibliotecas nativas de VLC permanecen como archivos separados en libvlc/win-x64 para conservar su estructura de plugins y permitir su sustitución por una versión compatible. El reproductor no se enlaza estáticamente a ellas. El código fuente de AniStream y las instrucciones de reconstrucción están en https://github.com/Zuaza796/AniStream/tree/main/windows

Los catálogos, portadas, pistas de audio y vídeos no se incluyen en el instalador; se obtienen del proveedor cuando el usuario abre contenido. La disponibilidad de idioma y subtítulos depende de cada título.
