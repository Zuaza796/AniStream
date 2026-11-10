#!/usr/bin/env python3
"""Install an isolated copy and a launcher in the current user's XDG folders."""
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
APP_ID = 'io.github.Zuaza796.AniStream'

def desktop_quote(value):
    # Desktop Entry Exec quoting differs from shell quoting; escape field codes too.
    value = str(value).replace('%', '%%')
    for char in ('\\', '"', '`', '$'): value = value.replace(char, '\\' + char)
    return '"' + value + '"'

def install():
    data_home = Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share')
    bin_home = Path(os.environ.get('ANISTREAM_BIN_DIR') or Path.home() / '.local/bin')
    for path in (data_home, bin_home):
        if not path.is_absolute() or '\n' in str(path): raise ValueError('Las rutas de instalación deben ser absolutas y sin saltos de línea')
    base = data_home / 'anistream'
    base.mkdir(parents=True, exist_ok=True)
    target = base / 'application'
    staging = Path(tempfile.mkdtemp(prefix='.application-', dir=base))
    try:
        shutil.copytree(ROOT / 'anistream', staging / 'anistream', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        for name in ('LICENSE', 'README.md', 'THIRD_PARTY_NOTICES.md'):
            shutil.copy2(ROOT / name, staging / name)
        for name in ('docs', 'third_party'):
            shutil.copytree(ROOT / name, staging / name)
        shutil.copy2(ROOT / 'scripts/uninstall_user.py', staging / 'uninstall.py')
        previous = base / '.application-previous'
        if previous.exists(): shutil.rmtree(previous)
        if target.exists(): target.rename(previous)
        try: staging.rename(target)
        except OSError:
            if previous.exists(): previous.rename(target)
            raise
        if previous.exists(): shutil.rmtree(previous)
    finally:
        if staging.exists(): shutil.rmtree(staging)
    bin_home.mkdir(parents=True, exist_ok=True)
    log = base / 'app.log'
    launcher = '#!/bin/sh\n# Installed by AniStream\n'
    launcher += 'export PYTHONPATH=' + shlex.quote(str(target)) + '\n'
    launcher += 'exec ' + shlex.quote(sys.executable) + ' -m anistream "$@" >> ' + shlex.quote(str(log)) + ' 2>&1\n'
    command = bin_home / 'anistream'
    command.write_text(launcher); command.chmod(0o755)
    uninstaller = bin_home / 'anistream-uninstall'
    uninstaller.write_text('#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' ' + shlex.quote(str(target / 'uninstall.py')) + ' --data-home ' + shlex.quote(str(data_home)) + ' --bin-home ' + shlex.quote(str(bin_home)) + ' "$@"\n')
    uninstaller.chmod(0o755)
    desktop_dir = data_home / 'applications'; desktop_dir.mkdir(parents=True, exist_ok=True)
    desktop = desktop_dir / (APP_ID + '.desktop')
    desktop.write_text('[Desktop Entry]\nType=Application\nName=AniStream\nComment=Reproductor de anime para Linux\nExec=' + desktop_quote(command) + '\nIcon=video-x-generic\nTerminal=false\nCategories=AudioVideo;Video;Player;\nStartupNotify=true\nStartupWMClass=io.github.Zuaza796.AniStream\n')
    legacy = desktop_dir / 'anistream.desktop'
    if legacy.is_file():
        content = legacy.read_text()
        if 'Name=AniStream\n' in content and ('Exec=' + str(command) + '\n') in content:
            legacy.unlink()
    if shutil.which('update-desktop-database'):
        subprocess.run(['update-desktop-database', str(desktop_dir)], check=False)
    print('AniStream instalado. Ábrelo desde el menú de aplicaciones.')
    print('Comando:', command)
    print('Desinstalar:', uninstaller)

if __name__ == '__main__': install()
