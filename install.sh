#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
skip_deps=0
case "${1:-}" in
  --no-deps) skip_deps=1 ;;
  --check) exec /usr/bin/python3 "$repo_dir/scripts/check_dependencies.py" ;;
  --help|-h) echo 'Uso: ./install.sh [--no-deps | --check]'; exit 0 ;;
  '') ;;
  *) echo 'Opción desconocida. Usa --help.' >&2; exit 2 ;;
esac
if [[ "$EUID" -eq 0 ]]; then
  echo 'Ejecuta ./install.sh como usuario normal. Solo las dependencias usarán sudo.' >&2
  exit 1
fi
if ! /usr/bin/python3 "$repo_dir/scripts/check_dependencies.py"; then
  if [[ "$skip_deps" -eq 1 ]]; then exit 1; fi
  source /etc/os-release
  distro=" ${ID:-} ${ID_LIKE:-} "
  if [[ "$distro" == *' arch '* ]]; then
    sudo pacman -S --needed python python-gobject gtk4 python-beautifulsoup4 mpv libglvnd
  elif [[ "$distro" == *' debian '* || "$distro" == *' ubuntu '* ]]; then
    sudo apt-get update
    sudo apt-get install -y python3 python3-gi gir1.2-gtk-4.0 python3-bs4 libmpv2 libegl1 libgl1
  elif [[ "$distro" == *' fedora '* ]]; then
    sudo dnf install -y python3 python3-gobject gtk4 python3-beautifulsoup4 mpv-libs libglvnd-egl libglvnd-glx
  else
    echo 'Distribución sin receta automática. Consulta docs/INSTALLATION.md e instala las dependencias.' >&2
    exit 1
  fi
  /usr/bin/python3 "$repo_dir/scripts/check_dependencies.py"
fi
exec /usr/bin/python3 "$repo_dir/scripts/install_user.py"
