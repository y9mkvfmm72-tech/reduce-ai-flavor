# -*- coding: utf-8 -*-
"""Smoke tests for the regex / heuristic fixes in v1.3.

Run from the repo root:
    python -m unittest discover -s tests -v
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import consistency as cs          # noqa: E402
import flavor_audit as fa         # noqa: E402
import layout_audit as la         # noqa: E402


class CaptionTests(unittest.TestCase):
    def test_table_caption_en(self):
        self.assertEqual(fa.TAB_CAP.match("Table 2. Charge measured").group(1), "2")

    def test_table_caption_zh(self):
        self.assertEqual(fa.TAB_CAP.match("表 1　常数与参数").group(1), "1")
        self.assertEqual(fa.TAB_CAP.match("表 A1　按记录顺序的读数").group(1), "A1")

    def test_figure_caption_zh(self):
        self.assertEqual(fa.FIG_CAP.match("图 1　各液滴电荷量").group(1), "1")

    def test_caption_line(self):
        self.assertTrue(fa.CAPTION_LINE.match("Table 1. Constants"))
        self.assertTrue(fa.CAPTION_LINE.match("图 1　各液滴"))
        self.assertFalse(fa.CAPTION_LINE.match("The table shows"))


class FirstPersonTests(unittest.TestCase):
    def test_zh(self):
        self.assertEqual(fa.first_person_count("我先调平，然后我们记录。"), 2)

    def test_en(self):
        self.assertEqual(fa.first_person_count("I leveled the unit. We recorded it."), 2)


class MirrorTests(unittest.TestCase):
    def test_numbered_steps_are_skipped(self):
        prose = [
            "1. Adjustment. I leveled the unit. I set the field.",
            "2. Preparation. I filled the atomizer. I sprayed the mist.",
        ]
        self.assertEqual(fa.mirror_pairs(prose), [])

    def test_short_paragraphs_are_skipped(self):
        prose = [
            "The first value is small. The second value is large.",
            "The first result is clear. The second result is clear.",
        ]
        self.assertEqual(fa.mirror_pairs(prose), [])


class FontTests(unittest.TestCase):
    def test_times_variants_collapse(self):
        for name in ("TimesNewRomanPSMT", "TimesNewRomanPS-BoldMT",
                     "TimesNewRomanPS-ItalicMT"):
            self.assertEqual(la.family_of(name), "TimesNewRoman")

    def test_simsun(self):
        self.assertEqual(la.family_of("SimSun"), "SimSun")


class PageNumberTests(unittest.TestCase):
    def test_plain(self):
        self.assertTrue(la.is_page_number_line("1"))

    def test_footer_with_title(self):
        self.assertTrue(la.is_page_number_line("Millikan oil drop experiment 1"))
        self.assertTrue(la.is_page_number_line("密立根油滴实验 4"))

    def test_not_a_page_number(self):
        self.assertFalse(la.is_page_number_line("Table 2"))


class ConsistencyCaptionTests(unittest.TestCase):
    def test_zh(self):
        self.assertEqual(cs.caption_number("表 1　常数与参数"), "1")

    def test_en(self):
        self.assertEqual(cs.caption_number("Table A1. Readings"), "A1")

    def test_none(self):
        self.assertIsNone(cs.caption_number("The table shows"))


if __name__ == "__main__":
    unittest.main()
