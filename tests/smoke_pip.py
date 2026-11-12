"""Optional graphical PiP regression using a local clip (at least 30 seconds)."""
import os
import tempfile
os.environ['ANISTREAM_DATA_DIR'] = tempfile.mkdtemp(prefix='anistream-pip-test-')
import sys,time,json,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
if len(sys.argv)!=2:
 print('Uso: python3 tests/smoke_pip.py /ruta/a/video-de-prueba.mp4');sys.exit(2)
clip=str(Path(sys.argv[1]).resolve())
from anistream.app import AniStream,GLib
app=AniStream();app.set_application_id('io.github.Zuaza796.AniStream.PipTest')
app.search=lambda *_:None
started=time.monotonic();phase=0;original_handle=None;deadline=0;passed=False
item={'path':'/media/test','title':'Prueba Picture-in-Picture','image':''}
def activate(*_):
 def load():
  app.current_video=(item,1);app.requested_video=(item,1);app.current_episodes=[1]
  app.source_queue=[];app.playback_error=False
  app.pages.set_visible_child_name('player');app.header.set_visible(False)
  app.video.load(clip)
  return False
 GLib.timeout_add(500,load)
def done(ok):
 global passed
 passed=ok
 print('RESULT',ok,'phase',phase,'status',app.player_status.get_text(),flush=True)
 app.leave_player();app.win.close()
def tick():
 global phase,original_handle,deadline
 if time.monotonic()-started>55:
  done(False);return False
 pos=app.video.values.get('time-pos',0);paused=app.video.values.get('pause')
 if phase==0 and pos>1:
  original_handle=app.video.handle
  app.video.command('set','pause','yes');app.video.command('seek','20','absolute');phase=1
 elif phase==1 and paused and pos>=20 and app.pip_button.get_sensitive():
  app.toggle_pip();phase=2;deadline=time.monotonic()+2
 elif phase==2 and app.pip_window and app.video.context and not app.waiting_for_video and time.monotonic()>deadline:
  assert app.video.handle==original_handle
  assert app.video.get_root() is app.pip_window
  assert paused and 19<=pos<=21,(pos,paused)
  if os.environ.get('HYPRLAND_INSTANCE_SIGNATURE'):
   clients=json.loads(subprocess.check_output(['hyprctl','-j','clients']))
   c=next(c for c in clients if c['pid']==os.getpid() and c['title']=='AniStream · Picture-in-Picture')
   if not(c['floating'] and c['pinned']): return True
  print('PASS PiP; same mpv core; preserved pause/position',flush=True)
  app.restore_pip();phase=3
 elif phase==3 and not app.waiting_for_video and app.video.context and app.pip_window is None:
  assert app.video.handle==original_handle and app.video.get_root() is app.win
  assert paused and 19<=pos<=21,(pos,paused)
  print('PASS restore preserves playback position + pause',flush=True)
  app.toggle_pip();phase=4
 elif phase==4 and app.pip_window and not app.waiting_for_video:
  app.pip_window.close();phase=5
 elif phase==5 and app.pip_window is None and not app.waiting_for_video:
  print('PASS close PiP returns to main window',flush=True)
  app.video.command('set','pause','no');phase=6
 elif phase==6 and pos>21 and not paused:
  app.toggle_pip();phase=7
 elif phase==7 and app.pip_window and not app.waiting_for_video and not paused:
  app.browse_during_pip()
  assert app.pages.get_visible_child_name()=='browser'
  assert app.video.get_root() is app.pip_window
  print('PASS PiP while browsing catalog',flush=True)
  done(True);return False
 return True
app.connect('activate',activate);GLib.timeout_add(150,tick);app.run(None)
sys.exit(0 if passed else 1)
