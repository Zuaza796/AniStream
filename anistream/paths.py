"""User data paths. Application code is stored separately by the installer."""
import os
from pathlib import Path

DATA = Path(os.environ.get('ANISTREAM_DATA_DIR') or (
    Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share') / 'anistream'
)).expanduser()
