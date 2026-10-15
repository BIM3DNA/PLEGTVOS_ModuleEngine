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

    def test_utf8_degree_bosnian_dutch_nested(self):
        text = u'90\u00b0 - \u010d\u0107\u0161\u017e\u0111 - ge\u00efsoleerde leiding'
        data = {'elements': [{'name': text.encode('utf-8'), 'id': '1405931'}],
                'document': {'title': text}, 'tuple': (b'ASCII', text)}
        value = core.json_text(data)
        self.assertEqual(text, value['elements'][0]['name'])
        self.assertEqual(['ASCII', text], value['tuple'])
        self.assertEqual(value, json.loads(core.canonical(data)))
        self.assertEqual(core.canonical(data), core.canonical(data))
        self.assertEqual(text.encode('utf-8'), data['elements'][0]['name'])
        self.assertIsInstance(data['tuple'], tuple)

    def test_unknown_degree_bytes_rejected_with_full_path(self):
        raw = b'x'*41 + b'\xb0' + b' secret-model-parameter'
        try:
            core.finalize({'elements': [{'family_type': {'name': raw}}]})
        except core.JsonTextError as error:
            message = str(error)
        else: self.fail('Must not guess legacy encoding')
        for token in ('$["elements"][0]["family_type"]["name"]', 'type=bytes',
                      'encoding=utf-8/strict', 'outcome=rejected', 'b0'):
            self.assertIn(token,message)
        self.assertNotIn('secret-model-parameter',message)
        message.encode('ascii')

    def test_numeric_types_and_identifiers_unchanged(self):
        data = dict(integer=9223372036854775807, flag=True, value=None,
                    slope=0.00751234567890123, point=[1.123456789012345, -0.0],
                    id='1405931', uid='stable-id-0000')
        result = core.json_text(data)
        self.assertEqual(data,result)
        for name in ('integer','flag','value','slope','id','uid'):
            self.assertIs(type(data[name]),type(result[name]))
        # Preserve the existing canonical numeric policy; no new rounding.
        self.assertEqual(core.canonical(data),core.canonical(result))

    def test_finalize_does_not_mutate_or_reorder_input(self):
        data={'elements':[{'name':b'z'},{'name':b'a'}]}
        result=core.finalize(data)
        self.assertEqual([{'name':b'z'},{'name':b'a'}],data['elements'])
        self.assertEqual(['a','z'],[r['name'] for r in result['elements']])

    def test_invalid_key_and_decoded_key_collision(self):
        self.assertRaises(core.JsonTextError,core.canonical,{b'\xff':1})
        # Distinct byte/unicode keys coexist on CPython3, not all Python2 engines.
        mixed={b'name':1,u'name':2}
        if len(mixed)==2:self.assertRaises(core.JsonTextError,core.canonical,mixed)

    def test_bounded_encoder_uses_same_text_boundary(self):
        import execution_control
        control=execution_control.Control(clock=lambda:0,sink=lambda lines:None)
        payload={'name':u'90\u00b0'.encode('utf-8')}
        self.assertEqual(core.canonical(payload),control.canonical(payload))
        self.assertRaises(core.JsonTextError,control.canonical,{'name':b'\xb0'})

    def test_invalid_bytes_do_not_create_report_file(self):
        root=tempfile.mkdtemp(prefix='gc01-invalid-json-')
        try:
            target=os.path.join(root,'report.json')
            self.assertRaises(core.JsonTextError,report_store.exclusive_write,target,{'value':b'\xb0'})
            self.assertFalse(os.path.exists(target))
        finally:shutil.rmtree(root)

    def test_ascii_json_matches_standard_unicode_escaping(self):
        try: make_char=unichr
        except NameError: make_char=chr
        text=''.join(make_char(n) for n in range(256))+u'\U0001f642\u2028\u010d'
        payload={'text':text,'literal':r'\u00b0', 'nested':[u'\"\\\n',None,True,1]}
        expected=json.dumps(payload,sort_keys=True,separators=(',', ':'),ensure_ascii=True,allow_nan=False)
        self.assertEqual(expected,core.canonical(payload))
        self.assertEqual(payload,json.loads(core.canonical(payload)))

    def test_ascii_safe_path_for_unicode_keys(self):
        try:core.canonical({u'\u010d': [b'\xff']})
        except core.JsonTextError as error:message=str(error)
        else:self.fail('Expected precise rejection')
        self.assertIn('\\u010d',message)
        self.assertIn('[0]',message)
        message.encode('ascii')

    def test_emit_to_ascii_only_console(self):
        class AsciiConsole(object):
            def __init__(self): self.lines = []
            def write(self, value):
                value.encode('ascii', 'strict')
                self.lines.append(value)
        console = AsciiConsole()
        original = sys.stdout
        try:
            sys.stdout = console
            failure.emit([TEXT, b'bad\xff'])
        finally:
            sys.stdout = original
        rendered = ''.join(console.lines)
        self.assertIn('\\u010d', rendered)
        self.assertIn('INVALID_UTF8_BYTES', rendered)
        self.assertIn('\\xff', rendered)


if __name__ == '__main__': unittest.main()
