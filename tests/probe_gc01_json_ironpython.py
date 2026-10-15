# -*- coding: utf-8 -*-
"""Standalone IronPython/.NET8 JSON regression; no Revit imports or file writes.

Launcher must supply the matching IronPython standard library and button path.
"""
import json
import System
import diagnostic_core as core
import execution_control

text = u'90\u00b0 - \u010d\u0107\u0161\u017e\u0111 - ge\u00efsoleerde leiding'
# b literals are real IronPython bytes. Its str.encode result is an aliased
# System.String and cannot be distinguished from intended Unicode by its value.
utf8 = b'90\xc2\xb0'
net_text = System.String.Concat(u'90', u'\u00b0')
data = {'elements':[{'name':text,'id':'1405931','uid':'stable-id'}],
        'bytes':utf8,'net':net_text,'point':[1.123456789012345,-0.0],
        'slope':0.00751234567890123,'integer':9223372036854775807,
        'flag':True,'null':None,'tuple':(u'\U0001f642',r'\u00b0')}
copy = core.json_text(data)
assert copy['bytes']==u'90\u00b0' and copy['net']==u'90\u00b0'
assert copy['elements'][0]['name']==text
assert copy['point']==data['point'] and copy['slope']==data['slope']
assert copy['integer']==data['integer'] and isinstance(copy['integer'],long)
assert type(copy['flag']) is bool and copy['null'] is None
assert type(data['tuple']) is tuple and type(copy['tuple']) is list
encoded=core.canonical(data)
assert encoded==core.canonical(data)
assert all(ord(c)<128 for c in encoded)
assert json.loads(encoded)['elements'][0]['name']==text
assert json.loads(encoded)['tuple']==[u'\U0001f642',r'\u00b0']
snapshot={'elements':[{'name':text},{'name':u'90\u00b0'}]}
finalized=core.finalize(snapshot)
assert len(snapshot)==1 and len(finalized['elements'])==2
assert json.loads(core.canonical(finalized))['elements']==finalized['elements']
assert core.json_text(b'\xc4\x8d\xc4\x87\xc5\xa1\xc5\xbe\xc4\x91')==u'\u010d\u0107\u0161\u017e\u0111'
control=execution_control.Control(clock=lambda:0,sink=lambda lines:None)
assert json.loads(control.canonical(data))==copy
# Confirm the original encoder ambiguity independently of a Revit fixture.
try:json.dumps({'name':u'90\u00b0'},ensure_ascii=True)
except UnicodeError:print('ORIGINAL_UNICODE_ASCII_ENCODER_FAILURE_REPRODUCED')
else:raise AssertionError('Expected matching-runtime encoder failure')
for raw in (b'x'*41+b'\xb0',b'\xff\xfe'):
    try:core.finalize({'elements':[{'name':raw}]})
    except core.JsonTextError as error:
        message=unicode(error)
        assert '$["elements"][0]["name"]' in message
        assert 'outcome=rejected' in message and 'hex=' in message
        assert all(ord(c)<128 for c in message)
        print(message)
    else:raise AssertionError('Unknown encoding must be rejected')
print('M1_1E_NET8_JSON_PROBE_PASS; no live Revit acceptance')
