# -*- coding: utf-8 -*-
"""Dedicated diagnostic storage; no project latest.json or acceptance writes."""
import os
import uuid
from datetime import datetime
import diagnostic_core as core


def suggested_root(document):
    path = document.get('path') or ''
    parent = os.path.dirname(path)
    if parent and os.path.isdir(parent) and not document.get('is_cloud'):
        return os.path.join(parent, '_PLEGTVOS_ModuleEngine', 'state')
    return os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')),
                        'pyRevit', 'PLEGTVOS_ModuleEngine', 'state')


def exclusive_write(path, value):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0), 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write((core.canonical(value) + '\n').encode('utf-8'))
        stream.flush()
        os.fsync(stream.fileno())


def save(report, root):
    folder = os.path.join(root, 'gc01_mirror_diagnostics', report['snapshot']['document']['key'])
    if not os.path.isdir(folder): os.makedirs(folder)
    name = 'gc01_' + datetime.utcnow().strftime('%Y%m%dT%H%M%S%fZ') + '_' + uuid.uuid4().hex + '.json'
    path = os.path.join(folder, name)
    exclusive_write(path, report)
    pointer = dict(schema=core.SCHEMA, feature_id='GC01_MIRROR_DIAGNOSTICS',
                   report=name, content_sha256=report['content_sha256'])
    temporary = os.path.join(folder, 'latest_' + uuid.uuid4().hex + '.tmp')
    latest = os.path.join(folder, 'latest-report.json')
    try:
        exclusive_write(temporary, pointer)
        if hasattr(os, 'replace'):
            os.replace(temporary, latest)
        else:
            from System.IO import File
            if File.Exists(latest): File.Replace(temporary, latest, None)
            else: File.Move(temporary, latest)
    except Exception as error:
        # The immutable report remains usable even if pointer publication fails.
        return path, 'LATEST_POINTER_FAILED: ' + type(error).__name__
    return path, None
