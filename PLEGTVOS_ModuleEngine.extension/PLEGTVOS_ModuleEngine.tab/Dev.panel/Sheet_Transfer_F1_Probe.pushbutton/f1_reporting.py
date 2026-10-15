# -*- coding: utf-8 -*-
import json
import os
import tempfile
try:
    text_type = unicode
except NameError:
    text_type = str


def encoded(report):
    value = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
    pieces = []
    for char in value:
        number = ord(char)
        if number < 128:
            pieces.append(char)
        elif number <= 65535:
            pieces.append('\\u%04x' % number)
        else:
            number -= 65536
            pieces.append('\\u%04x\\u%04x' % (55296 + (number >> 10), 56320 + (number & 1023)))
    result = ''.join(pieces).encode('ascii')
    if len(result) > 8 * 1024 * 1024:
        raise ValueError('F1 report exceeds 8 MiB; no complete report published')
    return result


def reserve_directory():
    base = os.environ.get('LOCALAPPDATA')
    if not base:
        raise ValueError('Persistent LOCALAPPDATA unavailable')
    root = os.path.join(base, 'PLEGTVOS', 'SheetTransfer', 'experiments', 'F1')
    if not os.path.isdir(root):
        os.makedirs(root)
    return tempfile.mkdtemp(prefix='run-', dir=root)


def write(directory, report, phase):
    data = encoded(report)
    path = os.path.join(directory, phase + '.json')
    if os.path.exists(path):
        raise ValueError('Refusing to overwrite experiment evidence')
    with open(path, 'wb') as stream:
        stream.write(data)
    with open(path, 'rb') as stream:
        if stream.read() != data:
            raise IOError('Report read-back mismatch')
    with open(os.path.join(directory, phase + '.txt'), 'wb') as stream:
        stream.write(('F1 status: ' + report.get('status', 'UNKNOWN') + '\n').encode('ascii') + data)
    return path
