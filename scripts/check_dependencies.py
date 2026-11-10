#!/usr/bin/env python3
"""Check native dependencies without requiring a running display server."""
import ctypes
import sys


def check():
    errors = []
    if sys.version_info < (3, 10): errors.append('Python >= 3.10')
    try:
        import gi
        gi.require_version('Gtk', '4.0')
        from gi.repository import Gtk
        if (Gtk.get_major_version(), Gtk.get_minor_version()) < (4, 8): errors.append('GTK >= 4.8')
    except (ImportError, ValueError): errors.append('PyGObject y GTK 4')
    try: import bs4
    except ImportError: errors.append('BeautifulSoup 4')
    for library in ('libmpv.so.2', 'libEGL.so.1', 'libGL.so.1'):
        try: ctypes.CDLL(library)
        except OSError: errors.append(library)
    if errors:
        print('Faltan dependencias: ' + ', '.join(errors), file=sys.stderr)
        return 1
    print('Dependencias disponibles: Python, GTK 4, PyGObject, BeautifulSoup, libmpv, OpenGL y EGL.')
    return 0

if __name__ == '__main__': raise SystemExit(check())
