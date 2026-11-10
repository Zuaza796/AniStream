"""Real GTK/libmpv playback smoke test; pass an isolated state directory.

Run twice with desktop locale, e.g.:
  env -u LC_ALL LANG=es_MX.UTF-8 python3 tests/smoke_player.py /tmp/anistream-smoke
"""
import locale
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from anistream import app as module
from anistream.app import AniStream, GLib
module.DATA = Path(sys.argv[1]); module.DATA.mkdir(parents=True, exist_ok=True)
app = AniStream(); app.set_application_id('mx.zuaza.AniStream.PlaybackSmoke')
item = {'title':'Dark Summoner', 'path':'/media/dark-summoner-to-dekiteiru', 'image':''}
expected = app.state.get('positions', {}).get(item['path'], {}).get('1', 0)
started = time.monotonic(); seeking = False; passed = False

def activated(*_):
    print('Desktop numeric locale:', locale.setlocale(locale.LC_NUMERIC), flush=True)
    app.current_episodes = [1, 2]
    def start():
        app.play(item, 1)
        return False
    GLib.timeout_add(500, start)

def tick():
    global seeking, passed
    if app.video.handle: app.video.command('set', 'mute', 'yes')
    if time.monotonic() - started > 65:
        print('FAIL:', app.player_status.get_text(), 'init=', app.video.initialization_error, flush=True)
        app.win.close(); return False
    pos = app.video.values.get('time-pos', 0)
    if pos > 1 and not app.waiting_for_video:
        assert app.video.context and app.video.get_realized()
        assert locale.setlocale(locale.LC_NUMERIC) == 'C'
        assert app.controls_event(None, None) is False
        if expected:
            assert pos >= expected - 1, (pos, expected)
            print('PASS fresh desktop-locale launch resumed video at', round(pos, 2), flush=True)
            passed = True; app.win.close(); return False
        if not seeking:
            seeking = True; app.video.command('seek', '30', 'absolute')
        elif pos >= 30:
            print('PASS embedded playback under desktop locale; position saved', flush=True)
            passed = True; app.win.close(); return False
    return True

app.connect('activate', activated)
GLib.timeout_add(300, tick)
app.run(None)
sys.exit(0 if passed else 1)
