"""Optional GTK regression for library navigation and Continue Watching (local clip >=60s)."""
import os,tempfile,sys,time,threading
from pathlib import Path
os.environ['ANISTREAM_DATA_DIR']=tempfile.mkdtemp(prefix='anistream-library-ui-')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
if len(sys.argv)!=2:
 print('Uso: python3 tests/smoke_library.py /ruta/a/video-de-prueba.mp4');sys.exit(2)
clip=str(Path(sys.argv[1]).resolve())
from anistream.app import AniStream,GLib,Gtk,backend
item={'path':'/media/ongoing','title':'Prueba: continuar viendo','image':'','description':'Prueba local'}
finished=dict(item,path='/media/finished',title='Prueba: terminado')
release=threading.Event()
def catalog(query):
 release.wait(10)
 return [item,finished]
backend.catalog=catalog
backend.episodes=lambda _: [1,2,3]
backend.sources=lambda *_: [{'name':'Local','embed':'clip'}]
backend.resolve=lambda _: {'url':clip,'referer':'https://example/','server':'Prueba local'}
app=AniStream();app.set_application_id('io.github.Zuaza796.AniStream.LibraryTest')
app.state={'favorites':{item['path']:dict(item)},'history':{item['path']:dict(item,episode=2),finished['path']:dict(finished,episode=3)},'positions':{item['path']:{'2':12},finished['path']:{'3':59}},'durations':{item['path']:{'2':60},finished['path']:{'3':60}}}
app.save()
started=time.monotonic();phase=0;deadline=0;passed=False

def activated(*_):
 global phase,deadline
 app.nav_buttons['favorites'].emit('clicked')
 assert app.current_view=='favorites' and app.hero.get_text()=='Mi lista'
 assert app.content.get_first_child().get_first_child() is not None
 app.nav_buttons['history'].emit('clicked')
 assert app.current_view=='history' and '2 animes' in app.status.get_text()
 release.set();deadline=time.monotonic()+.5
 print('PASS actual Mi lista and Historial button clicks',flush=True)

def tick():
 global phase,deadline,passed
 if time.monotonic()-started>35:
  print('FAIL timeout',phase,app.status.get_text(),flush=True);app.win.close();return False
 if phase==0 and time.monotonic()>deadline:
  assert app.current_view=='history' and app.hero.get_text()=='Historial'
  print('PASS old catalog request cannot overwrite library view',flush=True)
  app.nav_buttons['home'].emit('clicked');phase=1;deadline=time.monotonic()+.5
 elif phase==1 and time.monotonic()>deadline:
  row=app.continue_section.get_first_child().get_child()
  if isinstance(row,Gtk.Viewport):row=row.get_child()
  assert len(list(row))==1
  card=row.get_first_child()
  assert card.get_first_child().get_child().get_first_child() is not None
  card.get_first_child().emit('clicked')
  phase=2
 elif phase==2 and app.current_video and app.video.values.get('time-pos',0)>=12 and not app.waiting_for_video:
  assert app.current_video[1]==2
  assert app.current_episodes==[1,2,3]
  app.video.command('set','pause','yes')
  app.save_position();app.leave_player()
  assert app.current_view=='home'
  assert app.library_store.load()['positions'][item['path']]['2']>=12
  print('PASS Continue card resumes correct episode and saves progress',flush=True)
  app.nav_buttons['favorites'].emit('clicked')
  grid=app.content.get_first_child()
  outer=grid.get_first_child().get_child()
  outer.get_last_child().emit('clicked')
  assert app.state['favorites']=={} and 'Aún no tienes' in app.status.get_text()
  app.detail(item)
  fav=next(w for w in app.content if isinstance(w,Gtk.Button) and w.get_label()=='♡  Añadir a mi lista')
  fav.emit('clicked')
  assert item['path'] in app.library_store.load()['favorites']
  assert fav.get_label()=='♥  Quitar de mi lista'
  print('PASS remove and re-add favorite persists',flush=True)
  passed=True;app.win.close();return False
 return True
app.connect('activate',activated);GLib.timeout_add(100,tick);app.run(None)
release.set()
sys.exit(0 if passed else 1)
