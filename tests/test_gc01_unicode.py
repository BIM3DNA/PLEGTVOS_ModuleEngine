# -*- coding: utf-8 -*-
"""Unicode boundary regressions; no Revit imports or host-acceptance claims."""
import json
import os
import sys
import tempfile
import shutil
import unittest
from test_gc01_diagnostics import BUTTON
sys.path.insert(0, BUTTON)
import diagnostic_core as core
import report_store
import failure_diagnostics as failure

TEXT = u'\u010d\u0107\u0161\u017e\u0111 - ge\u00efsoleerde leiding - caf\u00e9'


class UnicodeTests(unittest.TestCase):
    def test_model_fields_roundtrip_and_determinism(self):
        payload = dict(document=dict(title=TEXT, path=u'C:/'+TEXT+u'/motor.rvt'),
                       scope_name=TEXT, category_name=TEXT, family_name=TEXT,
                       type_name=TEXT, parameter_name=TEXT, parameter_value=TEXT,
                       system_name=TEXT, connector_metadata=TEXT)
        encoded = core.canonical(payload)
        self.assertEqual(payload, json.loads(encoded))
        self.assertEqual(core.digest(payload), core.digest(dict(reversed(list(payload.items())))))
        encoded.encode('ascii')

    def test_unicode_report_directory_and_contents(self):
        root = tempfile.mkdtemp(prefix='gc01-unicode-')
        try:
            folder = os.path.join(root, TEXT)
            snapshot = dict(document=dict(key='unicode-fixture', title=TEXT))
            report = dict(snapshot=snapshot, content_sha256=core.digest(snapshot))
            path, warning = report_store.save(report, folder)
            self.assertIsNone(warning)
            with open(path, 'rb') as stream:
                self.assertEqual(report, json.loads(stream.read().decode('utf-8')))
        finally:
            shutil.rmtree(root)

    def test_display_valid_utf8_preserves_codepoints_as_escapes(self):
        self.assertEqual(failure.display(TEXT), failure.display(TEXT.encode('utf-8')))
        self.assertIn('\\u010d', failure.display(TEXT))

    def test_invalid_bytes_are_visible_not_replaced(self):
        rendered = failure.display(b'bad\xff\xfe')
        self.assertIn('INVALID_UTF8_BYTES', rendered)
        self.assertIn('\\xff', rendered)
        self.assertNotIn('\ufffd', rendered)
        # Invalid raw bytes are not silently normalized into model JSON.
        self.assertRaises((TypeError, UnicodeError), core.canonical, dict(value=b'\xff'))

    def test_complete_traceback_without_source_or_locals(self):
        def outer():
            def inner():
                b'\xff'.decode('utf-8')
            inner()
        try:
            outer()
        except UnicodeError:
            lines = failure.failure_lines(sys.exc_info(), dict(stage='inventory',element_id='1405931',field=TEXT))
        rendered = '\n'.join(lines)
        for expected in ('UnicodeDecodeError', 'outer', 'inner', '1405931', 'inventory', '\\u010d'):
            self.assertIn(expected, rendered)
        self.assertNotIn("b'\\xff'.decode", rendered)
        rendered.encode('ascii')

    def test_broken_exception_message_falls_back(self):
        class Broken(Exception):
            def __str__(self): return b'\xff'.decode('ascii')
            def __unicode__(self): return b'\xff'.decode('ascii')
        result = failure.display(Broken(b'\xff'))
        self.assertIn('UNPRINTABLE_MESSAGE', result)
        result.encode('ascii')


if __name__ == '__main__': unittest.main()
