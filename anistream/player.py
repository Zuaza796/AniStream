"""Embedded libmpv renderer for GTK4, using the installed mpv C/render API."""
import ctypes as C
import logging
import locale
import re
from .paths import DATA
from pathlib import Path
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib

P = C.c_void_p
class Param(C.Structure):
    _fields_ = [('type', C.c_int), ('data', P)]
class FBO(C.Structure):
    _fields_ = [('fbo', C.c_int), ('w', C.c_int), ('h', C.c_int), ('format', C.c_int)]
GETPROC = C.CFUNCTYPE(P, P, C.c_char_p)
UPDATE = C.CFUNCTYPE(None, P)
class Init(C.Structure):
    _fields_ = [('get_proc_address', GETPROC), ('ctx', P)]
class Event(C.Structure):
    _fields_ = [('id', C.c_int), ('error', C.c_int), ('userdata', C.c_uint64), ('data', P)]
class Property(C.Structure):
    _fields_ = [('name', C.c_char_p), ('format', C.c_int), ('data', P)]
class EndFile(C.Structure):
    _fields_ = [('reason', C.c_int), ('error', C.c_int)]

def api(lib, name, result, args):
    f = getattr(lib, name); f.restype = result; f.argtypes = args; return f

class Video(Gtk.GLArea):
    def __init__(self, changed, failed):
        super().__init__(hexpand=True, vexpand=True)
        self.changed, self.failed = changed, failed
        self.context = P(); self.handle = None; self.pending = None
        self.closed = False; self.redraw_pending = False
        self.initialization_error = None
        self.reparenting = False
        self.resume_after_reparent = None
        self.last_media = None
        self.playing_media = False
        self.values = {'time-pos': 0., 'duration': 0., 'pause': False}
        self.lib = C.CDLL('libmpv.so.2')
        self.create = api(self.lib, 'mpv_create', P, [])
        self.initialize = api(self.lib, 'mpv_initialize', C.c_int, [P])
        self.option = api(self.lib, 'mpv_set_option_string', C.c_int, [P, C.c_char_p, C.c_char_p])
        self.command_async = api(self.lib, 'mpv_command_async', C.c_int, [P, C.c_uint64, C.POINTER(C.c_char_p)])
        self.property_string = api(self.lib, 'mpv_get_property_string', P, [P, C.c_char_p])
        self.free = api(self.lib, 'mpv_free', None, [P])
        self.modern_loadfile = True
        self.observe = api(self.lib, 'mpv_observe_property', C.c_int, [P, C.c_uint64, C.c_char_p, C.c_int])
        self.wait = api(self.lib, 'mpv_wait_event', C.POINTER(Event), [P, C.c_double])
        self.destroy = api(self.lib, 'mpv_terminate_destroy', None, [P])
        self.error_string = api(self.lib, 'mpv_error_string', C.c_char_p, [C.c_int])
        self.render_create = api(self.lib, 'mpv_render_context_create', C.c_int, [C.POINTER(P), P, C.POINTER(Param)])
        self.render_frame = api(self.lib, 'mpv_render_context_render', C.c_int, [P, C.POINTER(Param)])
        self.render_free = api(self.lib, 'mpv_render_context_free', None, [P])
        self.set_update = api(self.lib, 'mpv_render_context_set_update_callback', None, [P, UPDATE, P])
        egl = C.CDLL('libEGL.so.1')
        self.getproc = api(egl, 'eglGetProcAddress', P, [C.c_char_p])
        self.gl = C.CDLL('libGL.so.1')
        self.gl_get = api(self.gl, 'glGetIntegerv', None, [C.c_uint, C.POINTER(C.c_int)])
        self.resolve_cb = GETPROC(lambda _, name: self.getproc(name))
        self.update_cb = UPDATE(self.updated)
        self.set_required_version(3, 2)
        if hasattr(self, 'set_allowed_apis'): self.set_allowed_apis(Gdk.GLAPI.GL)
        else: self.set_use_es(False)
        self.set_auto_render(False)
        self.set_focusable(True)
        self.connect('realize', self.realize_video)
        self.connect('render', self.render_video)
        self.connect('unrealize', self.unrealize_video)
        self.timer = GLib.timeout_add(150, self.poll)

    def check(self, result):
        if result < 0: raise RuntimeError(self.error_string(result).decode())

    def realize_video(self, *_):
        self.closed = False
        self.initialization_error = None
        if not self.timer: self.timer = GLib.timeout_add(150, self.poll)
        self.make_current()
        if self.get_error():
            self.initialization_error = 'No se pudo iniciar OpenGL: ' + str(self.get_error())
            self.failed(self.initialization_error); return
        try:
            if not self.handle:
                # GTK applies the desktop locale during startup. libmpv refuses
                # non-C LC_NUMERIC, including es_MX even with a dot decimal separator.
                # Reset only numeric formatting, keeping the interface language.
                locale.setlocale(locale.LC_NUMERIC, 'C')
                self.handle = self.create()
                if not self.handle: raise RuntimeError('No se pudo iniciar libmpv')
                for key, value in {'vo':'libmpv', 'terminal':'no', 'config':'no', 'idle':'yes', 'keep-open':'yes', 'hwdec':'no', 'network-timeout':'12', 'ytdl':'no', 'user-agent':'Mozilla/5.0', 'log-file':str(DATA / 'mpv-embedded.log'), 'http-header-fields':'Referer: https://www.mp4upload.com/', 'input-default-bindings':'no', 'osc':'no'}.items():
                    self.check(self.option(self.handle, key.encode(), value.encode()))
                self.check(self.initialize(self.handle))
                version = self.property_string(self.handle, b'mpv-version')
                if version:
                    try:
                        match = re.search(r'(\d+)\.(\d+)', C.string_at(version).decode())
                        if match: self.modern_loadfile = tuple(map(int, match.groups())) >= (0, 38)
                    finally: self.free(version)
            init = Init(self.resolve_cb, None)
            params = (Param * 3)(Param(1, C.cast(C.c_char_p(b'opengl'), P)), Param(2, C.cast(C.pointer(init), P)), Param())
            self.check(self.render_create(C.byref(self.context), self.handle, params))
            self.set_update(self.context, self.update_cb, None)
            for name, fmt in [('time-pos',5), ('duration',5), ('pause',3), ('paused-for-cache',3), ('mute',3), ('volume',5)]:
                self.check(self.observe(self.handle, 0, name.encode(), fmt))
            if self.resume_after_reparent:
                media, values = self.resume_after_reparent
                self.resume_after_reparent = None
                # Discard teardown events before starting on the new GL context.
                while self.wait(self.handle, 0).contents.id: pass
                self.load(media[0], values.get('time-pos', 0), media[1])
                self.command('set', 'pause', 'yes' if values.get('pause') else 'no')
                self.command('set', 'mute', 'yes' if values.get('mute') else 'no')
                self.command('set', 'volume', str(values.get('volume', 100)))
            else:
                self.reparenting = False
                if self.pending:
                    args = self.pending; self.pending = None; self.load(*args)
        except Exception as e:
            logging.exception('Player initialization failed')
            self.reparenting = False
            self.initialization_error = 'No se pudo iniciar el reproductor: ' + str(e)
            self.failed(self.initialization_error)

    def updated(self, _):
        # libmpv invokes this on its rendering thread. GTK runs on the main loop.
        if not self.closed and not self.redraw_pending:
            self.redraw_pending = True
            GLib.idle_add(self.redraw)

    def redraw(self):
        self.redraw_pending = False
        if not self.closed and self.context: self.queue_render()
        return False

    def render_video(self, *_):
        if not self.context or self.closed: return True
        fbo = C.c_int(); self.gl_get(0x8CA6, C.byref(fbo))
        scale = self.get_scale_factor()
        target = FBO(fbo.value, max(1,self.get_width()*scale), max(1,self.get_height()*scale), 0)
        flip = C.c_int(1)
        params = (Param * 3)(Param(3, C.cast(C.pointer(target), P)), Param(4, C.cast(C.pointer(flip), P)), Param())
        result = self.render_frame(self.context, params)
        if result < 0: self.failed('Error al dibujar el vídeo: ' + self.error_string(result).decode())
        return True

    def command(self, *args):
        if not self.handle or self.closed: return
        argv = (C.c_char_p * (len(args)+1))(*(str(a).encode() for a in args), None)
        self.check(self.command_async(self.handle, 0, argv))

    def load(self, url, position=0, referer='https://www.mp4upload.com/'):
        if self.closed: raise RuntimeError('El reproductor se cerró; vuelve a abrir el episodio.')
        if self.initialization_error: raise RuntimeError(self.initialization_error)
        if not self.context:
            self.pending = (url, position, referer); return
        self.last_media = (url, referer)
        self.load_position = max(0, position)
        self.playing_media = True
        self.values.update({'time-pos': 0., 'duration': 0.})
        self.command('set', 'http-header-fields', 'Referer: ' + referer)
        options = f'start={max(0,position):.2f}'
        if self.modern_loadfile: self.command('loadfile', url, 'replace', '-1', options)
        else: self.command('loadfile', url, 'replace', options)
        self.command('set', 'pause', 'no')

    def stop(self):
        self.playing_media = False
        self.resume_after_reparent = None
        self.pending = None
        self.command('stop')

    def poll(self):
        if self.closed: return False
        if not self.handle: return True
        for _ in range(100):
            event = self.wait(self.handle, 0).contents
            if event.id == 0: break
            if event.id == 22 and event.data:
                prop = C.cast(event.data, C.POINTER(Property)).contents
                if prop.data and prop.format in (3,5):
                    value = C.cast(prop.data, C.POINTER(C.c_double if prop.format==5 else C.c_int)).contents.value
                    self.values[prop.name.decode()] = value
            elif event.id == 8:
                self.reparenting = False
            elif event.id == 7 and event.data:
                end = C.cast(event.data, C.POINTER(EndFile)).contents
                if end.error < 0 and not self.reparenting:
                    logging.error('libmpv end-file error=%s', self.error_string(end.error).decode())
                    self.failed('No se pudo reproducir: ' + self.error_string(end.error).decode())
            elif event.error < 0 and not self.reparenting:
                self.failed('Reproductor: ' + self.error_string(event.error).decode())
        self.changed(self.values)
        return True

    def prepare_reparent(self):
        """Retain the mpv core while GTK recreates the GL area in another window."""
        self.reparenting = True
        if self.playing_media and self.last_media:
            values = dict(self.values)
            if not values.get('duration'):
                values['time-pos'] = max(values.get('time-pos', 0), getattr(self, 'load_position', 0))
            self.resume_after_reparent = (self.last_media, values)
        self.command('set', 'pause', 'yes')

    def release_render(self):
        if self.context:
            self.make_current()
            self.render_free(self.context); self.context = P()

    def unrealize_video(self, *_):
        if self.reparenting and not self.closed: self.release_render()
        else: self.close()

    def close(self):
        if self.closed: return
        self.closed = True
        if self.timer: GLib.source_remove(self.timer); self.timer = None
        self.release_render()
        if self.handle:
            self.destroy(self.handle); self.handle = None
