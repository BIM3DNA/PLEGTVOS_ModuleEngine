# -*- coding: utf-8 -*-
import json
import os
import tempfile
from preview_models import BANNER

def encode(report):
    # Avoid IronPython 2.7/.NET 8 ensure_ascii encoder Unicode failure.
    value = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
    pieces = []
    for char in value:
        number = ord(char)
        if number < 128: pieces.append(char)
        elif number <= 65535: pieces.append('\\u%04x' % number)
        else:
            number -= 65536
            pieces.append('\\u%04x\\u%04x' % (55296 + (number >> 10), 56320 + (number & 1023)))
    return ''.join(pieces)

def summary(report):
    lines = [BANNER, 'Transfer: NOT IMPLEMENTED', 'Inventory: ' + report['inventory_status']]
    for sheet in report['sheets']:
        lines.append(u'{0} | {1} | viewports={2} schedules={3} not implemented in M1={4} number conflicts={5}'.format(
            sheet['number'], sheet['name'] if sheet['name'] is not None else '[UNKNOWN: name read failed]', len(sheet['viewports']), len(sheet['schedules']),
            len(sheet['unsupported']), len(sheet['number_conflicts'])))
    lines.append('Unimplemented content counts are not an API impossibility verdict.')
    for group in error_breakdown(report['errors']):
        lines.append('Read error: {0} | {1} | {2} | count={3}'.format(group['field'], group['api_call'], group['exception_type'], group['count']))
    lines.extend(report['limitations'])
    lines.append('Read errors: ' + str(len(report['errors'])))
    return u'\n'.join(lines)

def error_breakdown(errors):
    groups = {}
    for error in errors:
        field = error.get('context', 'UNKNOWN').rsplit(':', 1)[-1]
        trace = error.get('traceback', '')
        api = error.get('api_call') or ('Element.Name.GetValue' if 'Element.Name.GetValue' in trace else 'UNKNOWN_SEE_TRACEBACK')
        message = trace.splitlines()[-1] if trace else 'UNKNOWN'
        key = (field, api, error.get('exception_type', 'UNKNOWN'), message)
        groups[key] = groups.get(key, 0) + 1
    return [{'field': k[0], 'api_call': k[1], 'exception_type': k[2],
             'message': k[3], 'count': groups[k]} for k in sorted(groups)]


def write_report(report, report_root=None):
    report = dict(report)
    report['reader_version'] = 'M1.1'
    report['error_breakdown'] = error_breakdown(report['errors'])
    data = encode(report)
    if len(data) > 8 * 1024 * 1024:
        raise ValueError('Report exceeds 8 MiB; no complete report published')
    if report_root is None:
        local = os.environ.get('LOCALAPPDATA')
        if not local:
            raise ValueError('LOCALAPPDATA is unavailable; persistent report location unresolved')
        report_root = os.path.join(local, 'PLEGTVOS', 'SheetTransfer', 'reports')
    if not os.path.isdir(report_root):
        os.makedirs(report_root)
    directory = tempfile.mkdtemp(prefix='preview-', dir=report_root)
    with open(os.path.join(directory, 'preview.json'), 'wb') as stream:
        stream.write(data.encode('ascii'))
    with open(os.path.join(directory, 'preview.txt'), 'wb') as stream:
        stream.write((summary(report) + u'\n\nFull dependency inventory (JSON):\n' + data).encode('utf-8'))
    return directory
