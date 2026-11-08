import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
S = ROOT / 'scripts' / 'banner_fusion.py'
spec = importlib.util.spec_from_file_location('banner_fusion', S)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class BannerFusionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import subprocess, sys
        subprocess.run([sys.executable, str(ROOT / 'scripts/make_demo_banner.py'),
                        '--out', str(ROOT / 'output/demo_banner.png')], check=True,
                        stdout=subprocess.DEVNULL)
    def setUp(self):
        self.cfg = mod.load_config(str(ROOT / 'references' / 'example_layout.json'))

    def test_golden_reference_is_exactly_three_to_one(self):
        with Image.open(ROOT / 'output' / 'demo_banner.png') as img:
            self.assertEqual(img.size, (1536, 512))

    def test_default_avatar_intersects_only_bottom_strip(self):
        report = mod.geometry_report(self.cfg)
        self.assertGreater(report['overlap']['height_px'], 20)
        self.assertLess(report['overlap']['height_px'], 100)
        self.assertGreater(report['avatar']['cy'], 512)
        self.assertLess(report['avatar']['top_y'], 512)
        self.assertIsNotNone(report['overlap']['chord_at_banner_bottom'])

    def test_geometry_cover_no_crop(self):
        out = mod.calculate_from_screenshot((0, 0, 768, 256), (105, 309, 79), (1536, 512))
        self.assertAlmostEqual(out['avatar']['cx'], 210, places=3)
        self.assertAlmostEqual(out['avatar']['cy'], 618, places=3)
        self.assertAlmostEqual(out['avatar']['radius'], 158, places=3)

    def test_geometry_cover_vertical_crop(self):
        out = mod.calculate_from_screenshot((10, 20, 768, 240), (115, 329, 79), (1536, 512))
        # cover scale = 0.5, center crop offset y=8px, thus avatar center in original=634
        self.assertAlmostEqual(out['avatar']['cx'], 210, places=3)
        self.assertAlmostEqual(out['avatar']['cy'], 634, places=3)
        self.assertAlmostEqual(out['avatar']['radius'], 158, places=3)

    def test_report_safeguard_non_3to1(self):
        bad = dict(self.cfg)
        bad['banner'] = dict(self.cfg['banner'], width=1600)
        with self.assertRaises(ValueError):
            mod.geometry_report(bad)

    def test_preview_output_and_border_in_black_profile_region(self):
        with tempfile.TemporaryDirectory() as td:
            outfile = str(Path(td) / 'preview.png')
            result = mod.preview(str(ROOT / 'output' / 'demo_banner.png'),
                                 self.cfg, outfile, guide=True)
            self.assertEqual(result['size'][0], 1536)
            with Image.open(outfile) as img:
                self.assertGreater(img.height, 512)
                # The avatar is BELOW the bottom boundary and visible in the simulation.
                self.assertNotEqual(img.getpixel((210, 617)), (0, 0, 0))
                self.assertEqual(img.getpixel((1100, 800)), (0, 0, 0))

    def test_shift_down_crops_content_without_rescaling(self):
        with tempfile.TemporaryDirectory() as td:
            inp = ROOT / 'output' / 'demo_banner.png'
            outfile = str(Path(td) / 'shift.png')
            mod.shift_image(str(inp), outfile, dx=0, dy=20)
            with Image.open(inp) as before, Image.open(outfile) as after:
                self.assertEqual(before.size, after.size)
                self.assertEqual(after.getpixel((500, 200)), before.getpixel((500, 180)))

    def test_screenshot_preview_keeps_avatar_from_screen(self):
        with tempfile.TemporaryDirectory() as td:
            screen = Image.new('RGB', (300, 300), (10, 50, 60))
            screen.save(Path(td) / 'screen.png')
            banner = Image.new('RGB', (300, 100), (200, 100, 50))
            banner.save(Path(td) / 'b.png')
            output = str(Path(td) / 'out.png')
            mod.screenshot_preview(str(Path(td) / 'b.png'), str(Path(td) / 'screen.png'),
                                   (0, 0, 300, 100), (60, 135, 65), output)
            with Image.open(output) as img:
                self.assertEqual(img.getpixel((250, 20)), (200, 100, 50))
                # Old screenshot is preserved in overlapping avatar circle.
                self.assertEqual(img.getpixel((60, 90)), (10, 50, 60))
                self.assertEqual(img.getpixel((250, 200)), (10, 50, 60))

    def test_grid_dimensions(self):
        with tempfile.TemporaryDirectory() as td:
            inp = Path(td) / 'input.png'
            Image.new('RGB', (200, 150), (0, 0, 0)).save(inp)
            result = mod.grid(str(inp), str(Path(td) / 'grid.png'), 50)
            self.assertEqual(result['size'], (200, 150))


if __name__ == '__main__':
    unittest.main()
