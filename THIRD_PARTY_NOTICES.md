# Atribuciones de terceros

## anicli-esp 1.3.1

Autor: Alejandro Sempere. Repositorio: https://github.com/Asempere123123/anicli-esp

El proveedor AnimeAv1 de `anistream/backend.py` adapta el comportamiento de `src/animeav1.rs` de la distribución 1.3.1, obtenida de https://crates.io/api/v1/crates/anicli-esp/1.3.1/download. Se amplió con comprobaciones de enlaces, reintentos y resolución de Voe.

El paquete original declara `MIT OR Apache-2.0`. Esta adaptación utiliza la opción MIT y conserva su texto en [third_party/anicli-esp/LICENSE](third_party/anicli-esp/LICENSE). No se distribuye el binario Rust ni es necesario ejecutarlo para reproducir en la interfaz gráfica.

## Dependencias del sistema

GTK/PyGObject, libmpv, las implementaciones OpenGL/EGL y BeautifulSoup son proyectos independientes con sus propias licencias. Se instalan mediante la distribución Linux; este repositorio no incluye sus bibliotecas ni sus binarios. La licencia MIT de AniStream no reemplaza las licencias de esas dependencias.

Los catálogos, portadas y vídeos pertenecen a sus respectivos proveedores y titulares; no están incluidos en el código del proyecto.
