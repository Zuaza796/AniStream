import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from anistream.pip_window import PIP_TITLE, configure_floating
from anistream.player import Video


class TransferTests(unittest.TestCase):
    def test_transfer_keeps_snapshot_and_does_not_destroy_core(self):
        player = SimpleNamespace(reparenting=False, playing_media=True,
            last_media=('https://video.example/clip.mp4', 'https://example/'),
            values={'time-pos':123.5, 'pause':1, 'mute':1, 'volume':35}, command=Mock())
        Video.prepare_reparent(player)
        self.assertTrue(player.reparenting)
        player.values['time-pos'] = 0
        self.assertEqual(player.resume_after_reparent[1]['time-pos'],123.5)
        self.assertEqual(player.resume_after_reparent[1]['pause'],1)

    def test_transfer_while_loading_keeps_requested_position(self):
        player = SimpleNamespace(reparenting=True, playing_media=True,
            last_media=('media', 'referer'), load_position=90,
            values={'time-pos':0, 'duration':0, 'pause':1}, command=Mock())
        Video.prepare_reparent(player)
        self.assertEqual(player.resume_after_reparent[1]['time-pos'],90)

    def test_unrealize_during_transfer_only_releases_renderer(self):
        player = SimpleNamespace(reparenting=True, closed=False, release_render=Mock(), close=Mock())
        Video.unrealize_video(player)
        player.release_render.assert_called_once()
        player.close.assert_not_called()

    def test_stopping_cancels_restore(self):
        player = SimpleNamespace(playing_media=True, resume_after_reparent=('media', {}), pending=('media', 0), command=Mock())
        Video.stop(player)
        self.assertFalse(player.playing_media)
        self.assertIsNone(player.resume_after_reparent)
        player.command.assert_called_once_with('stop')


class CompositorTests(unittest.TestCase):
    @patch.dict(os.environ, {'HYPRLAND_INSTANCE_SIGNATURE':'test'})
    @patch('anistream.pip_window.shutil.which', return_value='/usr/bin/hyprctl')
    @patch('anistream.pip_window.subprocess.run')
    @patch('anistream.pip_window.subprocess.check_output')
    def test_lua_fallback_only_targets_own_pip(self, output, run, which):
        output.side_effect = [json.dumps([
            {'pid':os.getpid()+1,'title':PIP_TITLE,'address':'0xBAD'},
            {'pid':os.getpid(),'title':PIP_TITLE,'address':'0x123','monitor':0,'pinned':False},
        ]).encode(), json.dumps([{'id':0,'x':0,'y':0,'width':1920,'height':1080,'scale':1}]).encode()]
        run.side_effect = [SimpleNamespace(returncode=7)] + [SimpleNamespace(returncode=0)]*5
        self.assertTrue(configure_floating())
        calls = [c.args[0] for c in run.call_args_list]
        self.assertEqual(calls[0],['hyprctl','dispatch','setfloating','address:0x123'])
        self.assertTrue(any('window.pin' in c[-1] and 'enable' in c[-1] for c in calls))
        self.assertTrue(all('0xBAD' not in ' '.join(c) for c in calls))

if __name__ == '__main__': unittest.main()
