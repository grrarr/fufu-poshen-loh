"""Tests for psl_io.save_data (sweep AW19). Never touches the real data file.
Run: python -u test_psl_io.py
"""
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

import psl_io

SAMPLE = {"version": 1, "updated": "2026-01-01",
          "examProblems": [{"id": i, "text": "xé" * 50} for i in range(200)]}


def old_write(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class SaveDataTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.path = os.path.join(self.d, 'christopher-psl-data.json')
        old_write({"version": 1, "keep": "me"}, self.path)
        with open(self.path, 'rb') as f:
            self.before = f.read()

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_crash_mid_write_keeps_old_file(self):
        real_dump = json.dump

        def half_dump(obj, fp, **kw):
            fp.write('{"version": 1, "examPro')   # half the payload, then die
            raise RuntimeError('crash mid-write')

        with mock.patch.object(psl_io.json, 'dump', side_effect=half_dump):
            with self.assertRaises(RuntimeError):
                psl_io.save_data(SAMPLE, self.path)
        with open(self.path, 'rb') as f:
            self.assertEqual(f.read(), self.before)
        self.assertEqual(os.listdir(self.d), ['christopher-psl-data.json'])  # no tmp left
        self.assertIs(json.dump, real_dump)

    def test_bytes_match_old_write(self):
        other = os.path.join(self.d, 'old.json')
        old_write(SAMPLE, other)
        psl_io.save_data(SAMPLE, self.path)
        with open(other, 'rb') as a, open(self.path, 'rb') as b:
            self.assertEqual(a.read(), b.read())

    def test_replace_locked_falls_back_in_place(self):
        with mock.patch.object(psl_io.os, 'replace', side_effect=PermissionError(5, 'denied')), \
             mock.patch.object(psl_io.time, 'sleep'):
            psl_io.save_data(SAMPLE, self.path)
        with open(self.path, encoding='utf-8') as f:
            self.assertEqual(json.load(f), SAMPLE)
        self.assertEqual(os.listdir(self.d), ['christopher-psl-data.json'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
