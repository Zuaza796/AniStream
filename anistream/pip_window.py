"""Optional compositor integration for the app's own Picture-in-Picture window."""
import json
import logging
import os
import shutil
import subprocess
import time

PIP_TITLE = 'AniStream · Picture-in-Picture'


def configure_floating(title=PIP_TITLE):
    """Configure only our own mapped window; never change persistent WM rules."""
    if not os.environ.get('HYPRLAND_INSTANCE_SIGNATURE') or not shutil.which('hyprctl'):
        return False
    try:
        client = None
        for _ in range(12):
            clients = json.loads(subprocess.check_output(['hyprctl', '-j', 'clients'], timeout=2))
            client = next((c for c in clients if c.get('pid') == os.getpid() and c.get('title') == title), None)
            if client: break
            time.sleep(0.1)
        if not client: return False
        address = 'address:' + client['address']
        monitors = json.loads(subprocess.check_output(['hyprctl', '-j', 'monitors'], timeout=2))
        monitor = next((m for m in monitors if m['id'] == client.get('monitor')), None)
        commands = [
            ('setfloating', address, 'float', {'action': 'enable'}),
            ('resizewindowpixel', 'exact 480 300,' + address, 'resize', {'x':480, 'y':300, 'relative':False}),
        ]
        if monitor:
            scale = monitor.get('scale', 1)
            x = int(monitor['x'] + monitor['width'] / scale - 504)
            y = int(monitor['y'] + monitor['height'] / scale - 324)
            commands.append(('movewindowpixel', f'exact {x} {y},' + address, 'move', {'x':x, 'y':y, 'relative':False}))
        if not client.get('pinned'):
            commands.append(('pin', address, 'pin', {'action':'enable'}))
        commands.append(('alterzorder', 'top,' + address, 'alter_zorder', {'mode':'top'}))
        modern = False
        for command, arg, method, fields in commands:
            if not modern:
                result = subprocess.run(['hyprctl', 'dispatch', command, arg], capture_output=True, timeout=2)
                if result.returncode == 0: continue
                modern = True
            # Hyprland with Lua config uses typed dispatcher expressions.
            values = dict(window=address, **fields)
            table = ', '.join(k + '=' + json.dumps(v, ensure_ascii=False) for k,v in values.items())
            expression = 'hl.dsp.window.' + method + '({' + table + '})'
            subprocess.run(['hyprctl', 'dispatch', expression], check=True, capture_output=True, timeout=2)
        return True
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        logging.exception('Could not apply optional PiP compositor placement')
        return False
