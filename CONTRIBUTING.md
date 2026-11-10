# Contribuir

Consulta [Desarrollo](docs/DEVELOPMENT.md) y [Arquitectura](docs/ARCHITECTURE.md). Abre una rama para cada cambio y describe el problema, el comportamiento resultante y las verificaciones realizadas.

Mantén GTK en el hilo principal y la red en los trabajadores. No hagas llamadas síncronas de control de libmpv desde el renderizador. Los proveedores no deben importar la interfaz ni guardar URLs temporales en la biblioteca.

Para reportar un fallo, incluye distribución, versión de Python/GTK/mpv, pasos para reproducirlo y un fragmento de log revisado. Evita adjuntar tu biblioteca o capturas completas del escritorio.

Las pruebas de unidad deben poder ejecutarse sin conexión. Las pruebas reales de reproducción son optativas y utilizan datos de usuario aislados.
