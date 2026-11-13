"""Persistence of favorites, history and playback positions (no media URLs)."""
import json
import logging
import os
from pathlib import Path
import tempfile
import uuid

KEYS = ('favorites', 'history', 'positions', 'durations')

class Library:
    def __init__(self, path):
        self.path = Path(path)

    def load(self):
        state = {}
        try:
            state = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(state, dict): raise ValueError('Library must be an object')
            if any(k in state and not isinstance(state[k], dict) for k in KEYS):
                raise ValueError('Library sections must be objects')
        except FileNotFoundError:
            pass
        except (ValueError, UnicodeError):
            logging.exception('Invalid library; preserving original as library.json.invalid')
            backup = self.path.with_suffix('.json.invalid')
            if backup.exists(): backup = backup.with_name(backup.name + '.' + uuid.uuid4().hex)
            self.path.replace(backup)
            state = {}
        for key in KEYS: state.setdefault(key, {})
        return state

    def save(self, state):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Unique temporary file on the same filesystem, then atomic replacement.
        name = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.path.parent, prefix='.library-', delete=False) as f:
                name = f.name
                json.dump(state, f, ensure_ascii=False, allow_nan=False)
                f.flush(); os.fsync(f.fileno())
            os.replace(name, self.path)
        finally:
            if name and os.path.exists(name): os.unlink(name)


def series_metadata(item):
    """Keep presentation metadata separate from transient resume/card fields."""
    return {key: item[key] for key in ('path', 'title', 'image', 'description') if key in item}


def record_progress(state, item, episode, position, duration=0, watched_at=None):
    """Record actual playback, keeping series ordered by most recent progress."""
    import math
    import time
    if not math.isfinite(position) or position <= 0: return False
    path = item['path']; key = str(episode)
    state.setdefault('positions', {}).setdefault(path, {})[key] = position
    if math.isfinite(duration) and duration > 0:
        state.setdefault('durations', {}).setdefault(path, {})[key] = duration
    history = state.setdefault('history', {})
    history.pop(path, None)
    history[path] = dict(series_metadata(item), episode=episode,
        watched_at=time.time() if watched_at is None else watched_at)
    return True


def progress_item(state, item):
    """Return a copy suitable for display, without changing stored metadata."""
    result = dict(item)
    path = item['path']; episode = str(item.get('episode', ''))
    result['_resume_position'] = state.get('positions', {}).get(path, {}).get(episode, 0)
    result['_resume_duration'] = state.get('durations', {}).get(path, {}).get(episode, 0)
    return result


def unfinished(item):
    import math
    position = item.get('_resume_position', 0)
    duration = item.get('_resume_duration', 0)
    if not isinstance(position, (int, float)) or not math.isfinite(position) or position <= 0:
        return False
    if not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
        return True
    return position < duration * .95 and duration - position > 3


def history_items(state):
    # Dictionary order also supports existing libraries without timestamps.
    return [progress_item(state, item) for item in reversed(list(state.get('history', {}).values()))
        if isinstance(item, dict) and item.get('path') and item.get('title')]


def continue_items(state):
    return [item for item in history_items(state) if unfinished(item)]
