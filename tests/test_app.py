import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'files/usr/lib/syslinuxos-conky-system/app.py'
spec = importlib.util.spec_from_file_location('app', SOURCE)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class LayoutTests(unittest.TestCase):
    def test_layout_fits_small_and_large_screens(self):
        for width, height in [(800, 600), (1280, 720), (1920, 1080), (3840, 2160)]:
            with self.subTest(resolution=(width, height)):
                layout = app.layout(width, height)
                self.assertLess(layout['width'] + layout['gap_x'], width)
                self.assertLess(layout['font'] * 1.8 * 48 + layout['gap_y'], height)
        self.assertGreater(app.layout(3840, 2160)['font'], app.layout(1920, 1080)['font'])
        self.assertGreater(app.layout(1920, 1080)['width'], app.layout(1280, 720)['width'])

    def test_position_uses_the_same_right_edge_as_conky_window(self):
        for width, height in [(800, 600), (1280, 720), (1920, 1080), (3840, 2160)]:
            self.assertEqual(app.layout(width, height)['gap_x'], 0)

    def test_invalid_scale_does_not_break_the_layout(self):
        expected = app.layout(1920, 1080)
        for value in ['nan', 'inf', '-1', '0', 'invalid']:
            with self.subTest(scale=value):
                self.assertEqual(app.layout(1920, 1080, value), expected)

    def test_active_primary_monitor_is_used(self):
        output = 'Screen 0: current 3840 x 1080\nHDMI-1 connected 1920x1080+1920+0\nDP-1 connected primary 1920x1080+0+0\n'
        with patch.object(app, 'output', return_value=output):
            self.assertEqual(app.resolution(), (1920, 1080))

    def test_resolution_falls_back_to_xdpyinfo(self):
        with patch.object(app, 'output', side_effect=['', '  dimensions:  1280x720 pixels (338x190 millimeters)']):
            self.assertEqual(app.resolution(), (1280, 720))


class NetworkTests(unittest.TestCase):
    def test_default_route_changes_are_followed(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(app, 'output', side_effect=['[{"dev":"enp3s0"}]', '[{"dev":"wlan0"}]']):
                first, second = app.network_text(), app.network_text()
        self.assertIn('${downspeed enp3s0}', first)
        self.assertIn('${downspeed wlan0}', second)
        self.assertNotIn('enp3s0', second)

    def test_offline_and_invalid_interfaces_produce_no_conky_injection(self):
        for data in ['[]', 'not json', '[{"dev":"${exec false}"}]', '[{"dev":"lo"}]']:
            with self.subTest(route=data), patch.dict(os.environ, {}, clear=True):
                with patch.object(app, 'output', return_value=data):
                    text = app.network_text()
                self.assertIn('Offline', text)
                self.assertNotIn('${exec', text)
                self.assertNotIn('${downspeed', text)


class ProcessTests(unittest.TestCase):
    def test_stop_recognizes_only_its_own_config_and_user(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            process = root / '123'
            process.mkdir()
            config = root / 'conkyrc-system.conf'
            with patch.object(app, 'PROC', root):
                (process / 'cmdline').write_bytes(b'conky\0-c\0conkyrc\0')
                self.assertFalse(app.owned_process(123, config))
                (process / 'cmdline').write_bytes(b'conky\0--config\0/tmp/conky-window-scaled.conf\0')
                self.assertFalse(app.owned_process(123, config))
                (process / 'cmdline').write_bytes(b'conky\0--config\0' + os.fsencode(config) + b'\0')
                self.assertTrue(app.owned_process(123, config))
                with patch.object(app.os, 'getuid', return_value=os.getuid() + 1):
                    self.assertFalse(app.owned_process(123, config))


class ConfigurationTests(unittest.TestCase):
    def test_every_layout_setting_is_rendered_and_background_is_transparent(self):
        template = SOURCE.parents[3] / 'etc/conky/conky-system.conf'
        with patch.object(app, 'TEMPLATE', template):
            small, large = app.render_config(1280, 720), app.render_config(3840, 2160)
        self.assertNotRegex(small, r'@[A-Z_]+@')
        self.assertIn('DejaVu Sans Mono:size=6.67', small)
        self.assertIn('DejaVu Sans Mono:size=20.0', large)
        self.assertIn('maximum_width = 240', small)
        self.assertIn('maximum_width = 720', large)
        self.assertIn('own_window_argb_value = 0', small)
        self.assertIn('own_window_transparent = true', small)
        self.assertIn('border_width = 0', small)

    def test_runtime_directory_is_private_and_symlinks_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.dict(os.environ, {'XDG_RUNTIME_DIR': temporary}):
                directory = app.runtime_dir()
                self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
                directory.rmdir()
                directory.symlink_to(Path(temporary), target_is_directory=True)
                with self.assertRaises(RuntimeError):
                    app.runtime_dir()

    def test_repeated_start_keeps_the_existing_instance(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.dict(os.environ, {'XDG_RUNTIME_DIR': temporary}):
                directory = app.runtime_dir()
                (directory / 'conky.pid').write_text('123')
                with patch.object(app, 'owned_process', return_value=True):
                    with patch.object(app.subprocess, 'Popen') as spawn:
                        self.assertEqual(app.control('start'), 0)
                        spawn.assert_not_called()


if __name__ == '__main__':
    unittest.main()
