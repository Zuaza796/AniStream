#!/usr/bin/env python3
"""Remove only installed app files; playback data are retained."""
import argparse
from pathlib import Path
import shutil

def main():
    p = argparse.ArgumentParser(description='Desinstala AniStream y conserva favoritos e historial.')
    p.add_argument('--data-home', required=True, type=Path)
    p.add_argument('--bin-home', required=True, type=Path)
    args = p.parse_args()
    target = args.data_home / 'anistream/application'
    if (target / 'anistream/__init__.py').is_file(): shutil.rmtree(target)
    for path in (args.bin_home / 'anistream', args.bin_home / 'anistream-uninstall', args.data_home / 'applications/io.github.Zuaza796.AniStream.desktop'):
        path.unlink(missing_ok=True)
    print('AniStream desinstalado. Tus datos se conservan en', args.data_home / 'anistream')

if __name__ == '__main__': main()
