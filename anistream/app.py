#!/usr/bin/python3
import concurrent.futures
import json
import os
import sys
import shutil
from importlib.resources import files
import time
import logging
from pathlib import Path
import subprocess
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib
from . import backend
from .player import Video
from .paths import DATA
from .library import Library, series_metadata, record_progress, unfinished, history_items, continue_items
from .pip_window import PIP_TITLE, configure_floating

DATA.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=DATA / 'errors.log', level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
POOL = concurrent.futures.ThreadPoolExecutor(max_workers=6)
CSS = files('anistream').joinpath('resources/theme.css').read_bytes()

def label(text, css=None):
    w = Gtk.Label(label=text, xalign=0)
    if css: w.add_css_class(css)
    return w

def button(text, action, css=None):
    b = Gtk.Button(label=text)
    b.connect('clicked', lambda *_: action())
    if css: b.add_css_class(css)
    return b

def icon_button(icon, title, action, css=None):
    b = Gtk.Button()
    b.set_child(Gtk.Image.new_from_file(str(files('anistream').joinpath('resources', icon))) if icon.endswith('.svg') else Gtk.Image.new_from_icon_name(icon))
    b.set_tooltip_text(title)
    b.update_property([Gtk.AccessibleProperty.LABEL], [title])
    b.connect('clicked', lambda *_: action())
    if css: b.add_css_class(css)
    return b


def update_icon(b, icon, title):
    if icon.endswith('.svg'): b.get_child().set_from_file(str(files('anistream').joinpath('resources', icon)))
    else: b.get_child().set_from_icon_name(icon)
    b.set_tooltip_text(title)
    b.update_property([Gtk.AccessibleProperty.LABEL], [title])


class AniStream(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='io.github.Zuaza796.AniStream')
        self.library_store = Library(DATA / 'library.json')
        self.state = self.library_store.load()
        self.current_view = 'home'
        self.home_catalog = None
        self.generation = 0
        self.play_request = 0
        self.current_video = None
        self.last_saved_second = 0
        self.waiting_for_video = False
        self.attempt_id = 0
        self.connect('activate', self.activate)

    def save(self):
        self.library_store.save(self.state)

    def work(self, job, done, message='Cargando…', generation=None):
        self.status.set_text(message)
        future = POOL.submit(job)
        def finish(f):
            def update():
                if generation is not None and generation != self.generation: return False
                try:
                    result = f.result()
                    done(result)
                except Exception as e: self.status.set_text(str(e))
                return False
            GLib.idle_add(update)
        future.add_done_callback(finish)

    def activate(self, *_):
        if hasattr(self, 'win'):
            self.win.present(); return
        settings = Gtk.Settings.get_default()
        settings.set_property('gtk-application-prefer-dark-theme', True)
        css = Gtk.CssProvider(); css.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css, 600)
        self.win = Gtk.ApplicationWindow(application=self, title='AniStream')
        self.win.set_default_size(1160, 800)
        header = Gtk.HeaderBar(); header.set_title_widget(label('◉  AniStream', 'brand'))
        self.win.set_titlebar(header)
        self.header = header
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        for side in ('top','bottom','start','end'): getattr(root, 'set_margin_' + side)(24)
        self.pages = Gtk.Stack()
        self.pages.add_named(root, 'browser')
        self.win.set_child(self.pages)
        self.build_player()
        self.win.connect('close-request', self.close_player)
        nav = Gtk.Box(spacing=10)
        self.nav_buttons = {}
        for key, text, action in [('home', 'Inicio', self.home), ('favorites', '♡  Mi lista', lambda: self.show_library('favorites')), ('history', '↺  Historial', lambda: self.show_library('history'))]:
            self.nav_buttons[key] = button(text, action)
            nav.append(self.nav_buttons[key])
        nav.append(button('anicli-esp ↗', self.terminal))
        root.append(nav)
        self.hero = label('Tu próximo anime empieza aquí.', 'hero'); self.hero.set_wrap(True); root.append(self.hero)
        root.append(label('Explora, guarda tus series y disfruta aquí mismo.  •  AnimeAv1 / anicli-esp', 'subtitle'))
        row = Gtk.Box(spacing=10)
        self.entry = Gtk.Entry(placeholder_text='Buscar anime… Naruto, One Piece, Frieren', hexpand=True)
        self.entry.connect('activate', lambda *_: self.search(self.entry.get_text()))
        row.append(self.entry); row.append(button('Buscar', lambda: self.search(self.entry.get_text()), 'accent')); root.append(row)
        self.status = label('', 'status'); self.status.set_wrap(True); root.append(self.status)
        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        scroll = Gtk.ScrolledWindow(vexpand=True); scroll.set_child(self.content); root.append(scroll)
        self.win.present(); self.search('')

    def clear(self):
        while self.content.get_first_child(): self.content.remove(self.content.get_first_child())

    def grid(self, parent=None):
        grid = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, homogeneous=True, max_children_per_line=6, min_children_per_line=1)
        (parent or self.content).append(grid)
        return grid

    def set_view(self, name, title):
        self.current_view = name
        self.hero.set_text(title)
        for key, b in self.nav_buttons.items():
            if key == name: b.add_css_class('accent')
            else: b.remove_css_class('accent')

    def home(self, refresh_catalog=True):
        self.save_position()
        self.generation += 1; generation = self.generation
        self.set_view('home', 'Tu próximo anime empieza aquí.')
        self.clear()
        self.content.append(label('Continuar viendo', 'section-title'))
        self.continue_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.content.append(self.continue_section)
        self.render_continue()
        self.content.append(label('Explorar anime', 'section-title'))
        catalog_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.content.append(catalog_section)
        if self.home_catalog is not None:
            self.render_cards(self.home_catalog, catalog_section)
            self.status.set_text(f'{len(self.home_catalog)} series para explorar')
            if not refresh_catalog: return
        def done(items):
            self.home_catalog = items
            while catalog_section.get_first_child(): catalog_section.remove(catalog_section.get_first_child())
            self.render_cards(items, catalog_section)
            self.status.set_text(f'{len(items)} series para explorar' if items else 'El catálogo no devolvió resultados. Puedes usar tu biblioteca o buscar un título.')
        self.work(lambda: backend.catalog(''), done, 'Cargando catálogo…', generation=generation)

    def render_continue(self):
        while self.continue_section.get_first_child(): self.continue_section.remove(self.continue_section.get_first_child())
        items = continue_items(self.state)
        if not items:
            message = label('Aquí aparecerán los episodios que dejes a medias para retomarlos.', 'subtitle')
            message.set_wrap(True); self.continue_section.append(message)
            return
        row = Gtk.Box(spacing=12, valign=Gtk.Align.START)
        for item in items:
            card = self.make_card(item, self.resume_item, 'continue')
            card.set_size_request(190, -1); row.append(card)
        scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.AUTOMATIC, vscrollbar_policy=Gtk.PolicyType.NEVER)
        scroll.set_propagate_natural_height(True); scroll.set_child(row)
        self.continue_section.append(scroll)

    def search(self, query):
        query = query.strip()
        if not query:
            self.home()
            return
        self.generation += 1; generation = self.generation
        self.set_view('search', f'Resultados para «{query}»')
        self.clear()
        def done(items):
            self.cards(items)
        self.work(lambda: backend.catalog(query), done, 'Buscando en AnimeAv1…', generation=generation)

    def show_library(self, kind):
        self.save_position()
        self.generation += 1
        title = 'Mi lista' if kind == 'favorites' else 'Historial'
        self.set_view(kind, title)
        self.clear()
        items = list(reversed(list(self.state['favorites'].values()))) if kind == 'favorites' else history_items(self.state)
        if not items:
            self.status.set_text('Aún no tienes animes en tu lista.' if kind == 'favorites' else 'Aún no has reproducido episodios.')
            message = label('Añade favoritos con el corazón en la ficha de un anime.' if kind == 'favorites' else 'Los episodios aparecerán aquí cuando empieces a verlos.', 'subtitle')
            message.set_wrap(True); self.content.append(message)
            return
        self.status.set_text(f'{len(items)} animes · {title}')
        self.render_cards(items, self.content, kind=kind)

    def cards(self, items):
        self.clear()
        self.status.set_text(f'{len(items)} series' if items else 'No hay resultados para esta búsqueda.')
        self.render_cards(items, self.content)

    def render_cards(self, items, parent, kind='catalog'):
        grid = self.grid(parent)
        for item in items:
            grid.append(self.make_card(item, self.detail, kind))

    def make_card(self, item, selected, kind='catalog'):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, valign=Gtk.Align.START)
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        picture = Gtk.Picture(); picture.set_size_request(155, 220); picture.set_content_fit(Gtk.ContentFit.COVER)
        frame = Gtk.AspectFrame(ratio=300 / 425, obey_child=False)
        frame.set_child(picture); card.append(frame)
        title = label(item['title']); title.set_wrap(True); title.set_max_width_chars(23); card.append(title)
        if 'episode' in item:
            pos = item.get('_resume_position', 0); duration = item.get('_resume_duration', 0)
            caption = f"Episodio {item['episode']}"
            if pos > 0:
                caption += ' · ' + self.timestamp(pos)
                if duration > 0: caption += ' / ' + self.timestamp(duration)
            meta = label(caption, 'subtitle'); meta.set_wrap(True); card.append(meta)
            if duration > 0:
                progress = Gtk.ProgressBar(fraction=min(1, max(0, pos / duration)))
                card.append(progress)
        b = Gtk.Button(); b.add_css_class('card'); b.set_child(card)
        b.connect('clicked', lambda *_: selected(item)); outer.append(b)
        if kind == 'continue':
            outer.append(button(f"▶ Continuar ep. {item['episode']}", lambda: self.resume_item(item), 'accent'))
            outer.append(button('Ver episodios', lambda: self.detail(item)))
        elif kind == 'history' and unfinished(item):
            outer.append(button(f"▶ Continuar ep. {item['episode']}", lambda: self.resume_item(item), 'accent'))
        elif kind == 'favorites':
            def remove():
                self.state['favorites'].pop(item['path'], None)
                self.save(); self.show_library('favorites')
            outer.append(button('♡ Quitar de mi lista', remove))
        if item.get('image'):
            future = POOL.submit(self.image, item['image'])
            def loaded(f):
                def apply():
                    try: picture.set_paintable(Gdk.Texture.new_from_bytes(GLib.Bytes.new(f.result())))
                    except Exception: pass
                    return False
                GLib.idle_add(apply)
            future.add_done_callback(loaded)
        return outer

    def resume_item(self, item):
        self.generation += 1; generation = self.generation
        def done(nums):
            if item['episode'] not in nums:
                self.status.set_text('Ese episodio ya no está disponible. Abre la ficha para elegir otro.')
                return
            self.current_episodes = nums
            self.play(series_metadata(item), item['episode'])
        self.work(lambda: backend.episodes(item), done,
            f"Preparando {item['title']} · episodio {item['episode']}…", generation=generation)

    @staticmethod
    def image(url):
        import hashlib
        path = DATA / (hashlib.sha256(url.encode()).hexdigest() + '.img')
        if path.exists(): return path.read_bytes()
        data = backend.fetch(url); path.write_bytes(data); return data

    def detail(self, item):
        self.set_view('detail', item['title'])
        self.generation += 1; generation = self.generation
        self.clear(); self.content.append(button('← Volver', lambda: self.search(self.entry.get_text())))
        title = label(item['title'], 'hero'); title.set_wrap(True); self.content.append(title)
        desc = label(item.get('description', ''), 'subtitle'); desc.set_wrap(True); self.content.append(desc)
        fav = button('', lambda: None)
        def favorite(*_):
            key = item['path']
            if key in self.state['favorites']: del self.state['favorites'][key]
            else: self.state['favorites'][key] = series_metadata(item)
            self.save(); refresh()
        def refresh(): fav.set_label('♥  Quitar de mi lista' if item['path'] in self.state['favorites'] else '♡  Añadir a mi lista')
        fav.connect('clicked', favorite); refresh(); self.content.append(fav)
        def done(nums):
            if generation != self.generation: return
            self.current_episodes = nums
            self.status.set_text(f'{len(nums)} episodios · Selecciona un episodio para reproducirlo aquí')
            old = self.state['history'].get(item['path'], {}).get('episode')
            if old in nums: self.content.append(button(f'Continuar episodio {old}', lambda: self.play(item, old), 'accent'))
            grid = self.grid()
            for n in nums:
                grid.append(button(f'▶  {n:02}', lambda ep=n: self.play(item, ep)))
            self.episode = Gtk.SpinButton.new_with_range(min(nums), max(nums), 1)
            self.episode.set_value(old if old in nums else nums[0])
            row = Gtk.Box(spacing=10); row.append(self.episode)
            row.append(button('Abrir episodio en navegador ↗', lambda: Gtk.show_uri(self.win, backend.BASE + item['path'] + '/' + str(self.episode.get_value_as_int()), 0)))
            self.content.append(row)
        self.work(lambda: backend.episodes(item), done, 'Cargando episodios…', generation=generation)

    def build_player(self):
        self.pip_window = None
        self.controls_timer = None
        self.controls_dragging = False
        self.last_pointer_position = None
        self.player_overlay = Gtk.Overlay(hexpand=True, vexpand=True)
        self.player_overlay.add_css_class('video-surface')
        self.video = Video(self.video_changed, self.video_error)
        self.player_overlay.set_child(self.video)

        top = Gtk.Box(spacing=12)
        top.add_css_class('video-top'); top.add_css_class('video-controls')
        self.player_back = icon_button('go-previous-symbolic', 'Volver a episodios (Esc)', self.leave_player)
        top.append(self.player_back)
        self.video_title = label('Reproductor')
        self.video_title.set_hexpand(True); self.video_title.set_ellipsize(3)
        top.append(self.video_title)
        self.top_controls = Gtk.Revealer(transition_type=Gtk.RevealerTransitionType.CROSSFADE, transition_duration=200)
        self.top_controls.set_valign(Gtk.Align.START); self.top_controls.set_child(top)
        self.player_overlay.add_overlay(self.top_controls)

        bottom = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        bottom.add_css_class('video-bottom'); bottom.add_css_class('video-controls')
        self.player_status = label('Selecciona un episodio', 'status')
        self.player_status.set_wrap(True); bottom.append(self.player_status)
        self.progress = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 1)
        self.progress.set_draw_value(False); self.progress.set_hexpand(True)
        self.progress.set_tooltip_text('Posición de reproducción')
        self.progress.connect('change-value', self.seek_video)
        bottom.append(self.progress)
        controls = Gtk.Box(spacing=4)
        self.previous = icon_button('media-skip-backward-symbolic', 'Episodio anterior', lambda: self.step_episode(-1))
        self.next = icon_button('media-skip-forward-symbolic', 'Episodio siguiente', lambda: self.step_episode(1))
        controls.append(self.previous)
        controls.append(icon_button('media-seek-backward-symbolic', 'Retroceder 10 segundos (←)', lambda: self.video.command('seek', '-10', 'relative')))
        self.pause = icon_button('media-playback-pause-symbolic', 'Pausar (Espacio)', lambda: self.video.command('cycle', 'pause'), 'accent')
        controls.append(self.pause)
        controls.append(icon_button('media-seek-forward-symbolic', 'Avanzar 10 segundos (→)', lambda: self.video.command('seek', '10', 'relative')))
        controls.append(self.next)
        self.mute = icon_button('audio-volume-high-symbolic', 'Silenciar', lambda: self.video.command('cycle', 'mute'))
        controls.append(self.mute)
        self.volume = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.volume.set_draw_value(False); self.volume.set_value(100)
        self.volume.set_size_request(80, -1); self.volume.set_tooltip_text('Volumen')
        self.volume.connect('value-changed', lambda w: self.video.command('set', 'volume', str(w.get_value())))
        controls.append(self.volume)
        self.clock = label('00:00 / 00:00')
        self.clock.set_hexpand(True); controls.append(self.clock)
        controls.append(icon_button('view-refresh-symbolic', 'Reintentar conexión', self.retry_video))
        self.fullscreen_button = icon_button('view-fullscreen-symbolic', 'Pantalla completa (F)', self.fullscreen)
        controls.append(self.fullscreen_button)
        self.pip_button = icon_button('pip-enter.svg', 'Picture-in-Picture: abrir ventana flotante (P)', self.toggle_pip)
        self.pip_button.set_sensitive(False)
        controls.append(self.pip_button)
        bottom.append(controls)
        self.bottom_controls = Gtk.Revealer(transition_type=Gtk.RevealerTransitionType.CROSSFADE, transition_duration=200)
        self.bottom_controls.set_valign(Gtk.Align.END); self.bottom_controls.set_child(bottom)
        self.player_overlay.add_overlay(self.bottom_controls)
        self.player_host = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True)
        self.player_host.append(self.player_overlay)
        self.pip_placeholder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, vexpand=True)
        self.pip_placeholder.append(label('Reproduciendo en Picture-in-Picture', 'subtitle'))
        self.pip_placeholder.append(button('Volver al reproductor', self.restore_pip, 'accent'))
        self.pip_placeholder.append(button('Explorar catálogo', self.browse_during_pip))
        self.pip_placeholder.set_visible(False)
        self.player_host.append(self.pip_placeholder)
        self.pages.add_named(self.player_host, 'player')
        # Compact PiP keeps pause, mute, time and the return-to-app button.
        self.pip_hidden_controls = [w for w in list(controls) if w not in (self.pause, self.mute, self.clock, self.pip_button)]
        self.pip_hidden_controls.append(self.player_back)


        motion = Gtk.EventControllerMotion()
        motion.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        motion.connect('motion', self.controls_motion)
        motion.connect('enter', self.controls_motion)
        self.player_overlay.add_controller(motion)
        click = Gtk.EventControllerLegacy()
        click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        click.connect('event', self.controls_event)
        self.player_overlay.add_controller(click)
        keys = Gtk.EventControllerKey()
        keys.connect('key-pressed', self.player_key); self.win.add_controller(keys)
        self.win.connect('notify::fullscreened', self.fullscreen_changed)
        self.show_controls()

    def active_player_window(self):
        return self.pip_window or self.win

    def toggle_pip(self):
        if self.pip_window:
            self.restore_pip()
            return
        if not self.current_video or self.waiting_for_video or not self.video.context: return
        self.save_position()
        self.win.unfullscreen()
        pip = Gtk.ApplicationWindow(application=self, title=PIP_TITLE)
        pip.set_transient_for(self.win)
        pip.set_default_size(480, 300)
        pip.set_resizable(True)
        pip.connect('close-request', self.pip_closed)
        keys = Gtk.EventControllerKey()
        keys.connect('key-pressed', self.player_key); pip.add_controller(keys)
        self.pip_window = pip
        self.waiting_for_video = True; self.attempt_started = time.monotonic()
        self.video.prepare_reparent()
        self.player_host.remove(self.player_overlay)
        self.pip_placeholder.set_visible(True)
        for widget in self.pip_hidden_controls: widget.set_visible(False)
        update_icon(self.pip_button, 'pip-exit.svg', 'Volver a la ventana principal (P)')
        self.player_overlay.add_css_class('pip')
        pip.set_child(self.player_overlay)
        pip.present()
        self.controls_dragging = False
        self.show_controls(); self.video.grab_focus()
        POOL.submit(configure_floating)

    def restore_pip(self, present=True):
        if not self.pip_window: return
        pip = self.pip_window
        self.save_position()
        self.waiting_for_video = bool(self.video.playing_media)
        self.attempt_started = time.monotonic()
        self.video.prepare_reparent()
        pip.set_child(None)
        self.pip_window = None
        self.player_host.prepend(self.player_overlay)
        self.pip_placeholder.set_visible(False)
        for widget in self.pip_hidden_controls: widget.set_visible(True)
        self.player_overlay.remove_css_class('pip')
        update_icon(self.pip_button, 'pip-enter.svg', 'Picture-in-Picture: abrir ventana flotante (P)')
        self.pages.set_visible_child_name('player')
        self.header.set_visible(False)
        pip.destroy()
        if present: self.win.present()
        self.controls_dragging = False
        self.show_controls(); self.video.grab_focus()

    def pip_closed(self, *_):
        self.restore_pip()
        return True

    def browse_during_pip(self):
        self.pages.set_visible_child_name('browser')
        self.header.set_visible(True)
        self.search(self.entry.get_text())

    def controls_motion(self, controller, x, y):
        # Revealing/hiding overlays can re-pick the widget under a stationary
        # cursor. Only physical movement should restart the inactivity timer.
        old = self.last_pointer_position
        self.last_pointer_position = (x, y)
        if old is None or abs(x - old[0]) > 0.5 or abs(y - old[1]) > 0.5:
            self.show_controls()

    def controls_event(self, controller, event):
        if event is None: return False
        kind = event.get_event_type()
        if kind in (Gdk.EventType.BUTTON_PRESS, Gdk.EventType.TOUCH_BEGIN): self.controls_pressed()
        elif kind in (Gdk.EventType.BUTTON_RELEASE, Gdk.EventType.TOUCH_END, Gdk.EventType.TOUCH_CANCEL): self.controls_released()
        return False

    def controls_pressed(self, *_):
        self.controls_dragging = True
        self.show_controls()

    def controls_released(self, *_):
        self.controls_dragging = False
        self.show_controls()

    def show_controls(self):
        if self.controls_timer:
            GLib.source_remove(self.controls_timer)
            self.controls_timer = None
        for bar in (self.top_controls, self.bottom_controls):
            bar.set_reveal_child(True); bar.set_can_target(True)
        self.player_overlay.set_cursor_from_name('default')
        if self.pip_window or self.pages.get_visible_child_name() == 'player':
            self.controls_timer = GLib.timeout_add(2500, self.hide_controls)

    def hide_controls(self):
        self.controls_timer = None
        if not self.pip_window and self.pages.get_visible_child_name() != 'player': return False
        # Keep controls available while dragging, keyboard-focused, or showing an error.
        focus = self.active_player_window().get_focus()
        keyboard_focus = focus and focus.has_visible_focus() and any(focus.is_ancestor(bar) for bar in (self.top_controls, self.bottom_controls))
        if self.controls_dragging or keyboard_focus or getattr(self, 'playback_error', False):
            self.controls_timer = GLib.timeout_add(1000, self.hide_controls)
            return False
        for bar in (self.top_controls, self.bottom_controls):
            bar.set_reveal_child(False); bar.set_can_target(False)
        self.player_overlay.set_cursor_from_name('none')
        return False

    def fullscreen_changed(self, *_):
        active = self.win.is_fullscreen()
        update_icon(self.fullscreen_button, 'view-restore-symbolic' if active else 'view-fullscreen-symbolic', 'Salir de pantalla completa (Esc)' if active else 'Pantalla completa (F)')
        if self.pages.get_visible_child_name() == 'player': self.show_controls()

    def fullscreen(self):
        if self.pip_window: self.restore_pip()
        if self.win.is_fullscreen(): self.win.unfullscreen()
        else: self.win.fullscreen()

    def player_key(self, controller, key, code, modifiers):
        if controller.get_widget() is not self.pip_window and self.pages.get_visible_child_name() != 'player': return False
        self.show_controls()
        if key == Gdk.KEY_Escape:
            if self.pip_window: self.restore_pip()
            elif self.win.is_fullscreen(): self.win.unfullscreen()
            else: self.leave_player()
        elif key in (Gdk.KEY_p, Gdk.KEY_P): self.toggle_pip()
        elif key in (Gdk.KEY_f, Gdk.KEY_F): self.fullscreen()
        elif key == Gdk.KEY_space: self.video.command('cycle', 'pause')
        elif key == Gdk.KEY_Left: self.video.command('seek', '-10', 'relative')
        elif key == Gdk.KEY_Right: self.video.command('seek', '10', 'relative')
        else: return False
        return True

    def seek_video(self, scale, scroll, value):
        self.video.command('seek', str(value), 'absolute')
        return False

    @staticmethod
    def timestamp(seconds):
        n = max(0, int(seconds))
        return f'{n // 3600}:{n // 60 % 60:02}:{n % 60:02}' if n >= 3600 else f'{n // 60:02}:{n % 60:02}'

    def video_changed(self, values):
        if not self.current_video: return
        pos, duration = values.get('time-pos', 0), values.get('duration', 0)
        self.pip_button.set_sensitive(duration > 0 and not self.waiting_for_video)
        if self.waiting_for_video:
            if duration > 0 and pos > 0:
                self.waiting_for_video = False
            elif time.monotonic() - self.attempt_started > 22:
                self.video_error('El servidor tardó demasiado en iniciar el vídeo')
                return
        update_icon(self.pause, 'media-playback-start-symbolic' if values.get('pause') else 'media-playback-pause-symbolic', 'Reproducir (Espacio)' if values.get('pause') else 'Pausar (Espacio)')
        muted = values.get('mute') or values.get('volume', 100) == 0
        update_icon(self.mute, 'audio-volume-muted-symbolic' if muted else 'audio-volume-high-symbolic', 'Activar sonido' if muted else 'Silenciar')
        if not self.controls_dragging:
            self.progress.set_range(0, max(1, duration)); self.progress.set_value(pos)
        self.clock.set_text(self.timestamp(pos) + ' / ' + self.timestamp(duration))
        if duration and not getattr(self, 'playback_error', False):
            self.player_status.set_text('Cargando vídeo…' if values.get('paused-for-cache') else 'Reproducción en pausa' if values.get('pause') else 'Reproduciendo')
        if pos > 0 and abs(int(pos) - self.last_saved_second) >= 5:
            self.save_position()

    def retry_video(self):
        if getattr(self, 'requested_video', None):
            item, episode = self.requested_video
            self.play(item, episode)

    def video_error(self, message):
        logging.error('Playback error: %s', message)
        if self.waiting_for_video:
            self.waiting_for_video = False
            self.save_position()
            self.current_video = None
            self.video.stop()
            self.try_source(self.play_request, message)
            return
        self.playback_error = True
        self.show_controls()
        self.player_status.set_text(message + '. Pulsa Reintentar o vuelve a la ficha.')

    def save_position(self):
        if not self.current_video: return
        item, episode = self.current_video
        pos = self.video.values.get('time-pos', 0)
        duration = self.video.values.get('duration', 0)
        if record_progress(self.state, item, episode, pos, duration):
            self.last_saved_second = int(pos)
            self.save()

    def leave_player(self):
        if self.pip_window:
            self.save_position(); self.video.stop(); self.restore_pip(present=False)
        self.pip_button.set_sensitive(False)
        self.play_request += 1
        self.waiting_for_video = False
        self.save_position(); self.current_video = None
        self.video.stop(); self.win.unfullscreen()
        self.pages.set_visible_child_name('browser')
        self.header.set_visible(True)
        if self.controls_timer: GLib.source_remove(self.controls_timer); self.controls_timer = None
        self.player_overlay.set_cursor_from_name('default')
        self.video.values.update({'time-pos': 0., 'duration': 0.})
        if self.current_view == 'home': self.home(refresh_catalog=False)
        elif self.current_view in ('favorites', 'history'): self.show_library(self.current_view)

    def close_player(self, *_):
        self.play_request += 1
        self.waiting_for_video = False
        self.save_position()
        if self.controls_timer: GLib.source_remove(self.controls_timer); self.controls_timer = None
        self.video.close()
        if self.pip_window:
            self.pip_window.set_child(None)
            self.pip_window.destroy(); self.pip_window = None
        return False

    def step_episode(self, delta):
        if not self.current_video: return
        item, episode = self.current_video
        nums = self.current_episodes
        if episode in nums:
            idx = nums.index(episode) + delta
            if 0 <= idx < len(nums): self.play(item, nums[idx])

    def play(self, item, episode):
        if self.pip_window:
            self.save_position(); self.video.stop(); self.restore_pip()
        self.pip_button.set_sensitive(False)
        self.save_position()
        self.play_request += 1; request = self.play_request
        self.waiting_for_video = False
        self.video.stop()
        self.requested_video = (item, episode)
        self.current_video = None
        self.source_queue = []
        self.video.values.update({'time-pos': 0., 'duration': 0.})
        self.last_saved_second = 0
        self.playback_error = False
        self.video_title.set_text(f"{item['title']} · Episodio {episode}")
        self.player_status.set_text(f'Buscando servidores para el episodio {episode}…')
        self.clock.set_text('00:00 / 00:00'); self.progress.set_value(0)
        self.pages.set_visible_child_name('player'); self.header.set_visible(False)
        self.controls_dragging = False
        self.show_controls(); self.video.grab_focus()
        self.previous.set_sensitive(False); self.next.set_sensitive(False)
        logging.info('Play requested path=%s episode=%s request=%s', item['path'], episode, request)
        def done(sources):
            # Refresh MP4Upload once on failure, then try an independent server.
            self.source_queue = []
            for source in sources:
                self.source_queue.append(source)
                self.source_queue.append(source)
            self.try_source(request)
        self.player_job(lambda: backend.sources(item, episode), done, request)

    def player_job(self, job, done, request, failed=None):
        future = POOL.submit(job)
        def finished(f):
            def deliver():
                if request != self.play_request: return False
                try: done(f.result())
                except Exception as e:
                    logging.exception('Playback job failed request=%s', request)
                    if failed: failed(str(e))
                    else: self.video_error(str(e))
                return False
            GLib.idle_add(deliver)
        future.add_done_callback(finished)

    def try_source(self, request, last_error=''):
        if request != self.play_request: return
        if not self.source_queue:
            self.playback_error = True
            self.show_controls()
            self.player_status.set_text('No se pudo iniciar el vídeo. ' + last_error + ' · Pulsa Reintentar para volver a conectar.')
            return
        source = self.source_queue.pop(0)
        self.attempt_id += 1
        attempt = self.attempt_id
        self.current_video = None
        self.video.values.update({'time-pos': 0., 'duration': 0.})
        self.playback_error = False
        self.player_status.set_text('Conectando con ' + source['name'] + '…')
        item, episode = self.requested_video
        def ready(media):
            if attempt != self.attempt_id: return
            self.current_video = (item, episode)
            nums = getattr(self, 'current_episodes', [])
            if episode in nums:
                self.previous.set_sensitive(nums.index(episode) > 0)
                self.next.set_sensitive(nums.index(episode) < len(nums) - 1)
            pos = self.state.get('positions', {}).get(item['path'], {}).get(str(episode), 0)
            duration = self.state.get('durations', {}).get(item['path'], {}).get(str(episode), 0)
            if duration and pos >= duration - 3: pos = 0
            self.waiting_for_video = True
            self.attempt_started = time.monotonic()
            try: self.video.load(media['url'], pos, media['referer'])
            except Exception as e: self.video_error(str(e)); return
            self.player_status.set_text('Cargando vídeo · ' + media['server'])
        self.player_job(lambda: backend.resolve(source), ready, request, lambda error: self.try_source(request, error))

    def terminal(self):
        executable = shutil.which('anicli-esp')
        local = Path.home() / '.local/bin/anicli-esp'
        if not executable and local.is_file(): executable = str(local)
        if not executable:
            self.status.set_text('anicli-esp es opcional: instálalo para abrir su interfaz de terminal.')
            return
        for terminal, args in [('kitty', []), ('gnome-terminal', ['--']), ('konsole', ['-e']), ('x-terminal-emulator', ['-e']), ('xterm', ['-e'])]:
            path = shutil.which(terminal)
            if path:
                try: subprocess.Popen([path, *args, executable])
                except OSError as e: self.status.set_text(str(e))
                return
        self.status.set_text('No se encontró un emulador de terminal compatible.')


def main():
    if sys.argv[1:] == ['--version']:
        from . import __version__
        print('AniStream ' + __version__)
        return 0
    return AniStream().run(None)


if __name__ == '__main__':
    raise SystemExit(main())
