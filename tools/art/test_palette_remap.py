"""Regression checks for import safety, not screenshots of one implementation."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from palette_remap import (GB_BACKGROUND_COLORS, image_stats, main,
                           remap_pixels, validation_failures)

COLORS = sorted(GB_BACKGROUND_COLORS)

class BackgroundChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'sample.png'

    def failures(self, image):
        image.save(self.path)
        return validation_failures(image_stats(self.path), COLORS, 192)

    def test_valid_single_shade_is_allowed(self):
        self.assertEqual([], self.failures(Image.new('RGB',(160,144),COLORS[0])))

    def test_partial_tiles_rejected(self):
        self.assertTrue(any('multiples' in x for x in self.failures(Image.new('RGB',(257,257),COLORS[0]))))

    def test_minimum_and_maximum_dimensions(self):
        for size, reason in [((152,144),'at least'),((2048,144),'axis'),((2040,520),'area')]:
            with self.subTest(size=size):
                self.assertTrue(any(reason in x for x in self.failures(Image.new('RGB',size,COLORS[0]))))

    def test_transparency_and_soft_alpha_rejected(self):
        for alpha in (0,128):
            im=Image.new('RGBA',(160,144),(*COLORS[0],255))
            im.putpixel((10,10),(*COLORS[0],alpha))
            self.assertTrue(any('opaque' in x for x in self.failures(im)))

    def test_display_palette_is_not_runtime_palette(self):
        self.assertTrue(any('noncanonical' in x for x in self.failures(Image.new('RGB',(160,144),'#E8DFC8'))))

    def test_over_budget_rejected(self):
        im=Image.new('RGB',(160,144),COLORS[0])
        for i in range(193):
            x,y=(i%20)*8,(i//20)*8
            for bit in range(8):
                if i & (1<<bit): im.putpixel((x+bit,y),COLORS[1])
        self.assertTrue(any('budget' in x for x in self.failures(im)))

    def test_index_mapping_preserves_shade_identity(self):
        source=[(0,0,0),(1,1,1),(2,2,2),(3,3,3)]
        im=Image.new('RGB',(4,1)); im.putdata(source)
        mapped,_=remap_pixels(im,COLORS,mode='index',source_palette=source)
        self.assertEqual([(*c,255) for c in COLORS],list(mapped.getdata()))
        with self.assertRaises(ValueError):
            remap_pixels(im,COLORS,mode='index',source_palette=[source[0]]*4)
        with self.assertRaises(ValueError):
            remap_pixels(Image.new('RGB',(1,1),'red'),COLORS,mode='index',source_palette=source)

    def test_overwrite_guard_and_cli_failure(self):
        Image.new('RGB',(160,144),'red').save(self.path)
        before=self.path.read_bytes()
        with contextlib.redirect_stderr(io.StringIO()),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(2,main(['remap','--input',str(self.path),'--output',str(self.path),'--palette','unused.hex']))
            self.assertEqual(1,main(['validate','--input',str(self.path)]))
        self.assertEqual(before,self.path.read_bytes())

if __name__ == '__main__':
    unittest.main()
