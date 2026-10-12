# -*- coding: utf-8 -*-
"""Failure-only ASCII-safe rendering. Never normalize or replace model data."""
import sys
try:
    text_type = unicode
except NameError:
    text_type = str


def display(value):
    """Lossless escape display; invalid external bytes are explicitly labelled."""
    try:
        if isinstance(value, bytes) and not isinstance(value, text_type):
            try:
                value = value.decode('utf-8', 'strict')
            except UnicodeError:
                return 'INVALID_UTF8_BYTES: ' + repr(value)
        elif not isinstance(value, text_type):
            value = text_type(value)
        return value.encode('ascii', 'backslashreplace').decode('ascii')
    except Exception:
        try:
            return 'UNPRINTABLE_MESSAGE: ' + display(repr(value))
        except Exception:
            return 'UNPRINTABLE_MESSAGE'


def failure_lines(exc_info, context):
    """Every traceback frame, without reading source lines, locals or model values."""
    kind, error, tb = exc_info
    lines = ['Collection context:']
    for key in ('stage', 'element_id', 'field'):
        lines.append('  ' + key + ': ' + display(context.get(key)))
    lines.append('Traceback (most recent call last; source lines omitted):')
    while tb is not None:
        code = tb.tb_frame.f_code
        lines.append('  File "' + display(code.co_filename) + '", line ' +
                     display(tb.tb_lineno) + ', in ' + display(code.co_name))
        tb = tb.tb_next
    lines.append(display(kind.__name__) + ': ' + display(error))
    return lines


def emit(lines):
    for line in lines:
        # Render again at the actual console boundary; only ASCII reaches stdout.
        sys.stdout.write(display(line) + '\n')
