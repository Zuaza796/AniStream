import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class InstallationTests(unittest.TestCase):
    def test_install_upgrade_and_uninstall_keep_personal_data(self):
        with tempfile.TemporaryDirectory(prefix='anistream install ') as folder:
            root = Path(folder)
            data = root / 'data with spaces'
            binary = root / 'bin with spaces'
            env = dict(os.environ, XDG_DATA_HOME=str(data), ANISTREAM_BIN_DIR=str(binary))
            env.pop('ANISTREAM_DATA_DIR', None)
            for _ in range(2):
                subprocess.run([sys.executable, str(ROOT / 'scripts/install_user.py')], env=env, check=True, capture_output=True)
            desktop = data / 'applications/io.github.Zuaza796.AniStream.desktop'
            self.assertTrue(desktop.exists())
            if shutil.which('desktop-file-validate'):
                subprocess.run(['desktop-file-validate', str(desktop)], check=True, capture_output=True)
            self.assertNotIn('__pycache__', '\n'.join(str(p) for p in (data / 'anistream/application').rglob('*')))
            version = subprocess.run([str(binary / 'anistream'), '--version'], env=env, capture_output=True, text=True, check=True)
            # Launcher redirects to app.log, just like when launched by the desktop.
            self.assertIn('AniStream 0.1.0', (data / 'anistream/app.log').read_text())
            library = data / 'anistream/library.json'
            library.write_text('{"favorites":{}}')
            subprocess.run([str(binary / 'anistream-uninstall')], env=env, check=True, capture_output=True)
            self.assertEqual(library.read_text(), '{"favorites":{}}')
            self.assertFalse((data / 'anistream/application').exists())
            self.assertFalse((binary / 'anistream').exists())
            self.assertFalse(desktop.exists())
