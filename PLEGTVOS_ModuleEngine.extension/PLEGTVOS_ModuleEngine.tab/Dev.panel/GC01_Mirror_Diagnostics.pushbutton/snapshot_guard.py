# -*- coding: utf-8 -*-
"""Read-only qualification for cross-invocation saved-local snapshot identity."""
import hashlib
import os


class UnqualifiedSnapshot(ValueError): pass


def version(value):
    try:
        guid=str(value.VersionGUID); saves=int(value.NumberOfSaves)
        if not guid or guid=='00000000-0000-0000-0000-000000000000' or saves<0:
            raise UnqualifiedSnapshot('Document version unavailable')
        return dict(guid=guid, saves=saves)
    finally:
        dispose=getattr(value, 'Dispose', None)
        if dispose is not None: dispose()


def capture(doc, db, control):
    control.progress('Qualify saved source snapshot')
    if doc.IsModified or doc.IsModelInCloud or not doc.PathName:
        raise UnqualifiedSnapshot('Requires an already saved, unmodified local document; no save attempted')
    if not doc.ProjectInformation.UniqueId: raise UnqualifiedSnapshot('Project identity unavailable')
    path=doc.PathName
    if not os.path.isfile(path): raise UnqualifiedSnapshot('Source RVT file unavailable')
    memory=version(db.Document.GetDocumentVersion(doc))
    info=db.BasicFileInfo.Extract(path)
    try: disk=version(info.GetDocumentVersion())
    finally: info.Dispose()
    if memory != disk: raise UnqualifiedSnapshot('Memory/disk document versions differ')
    before=os.stat(path)
    hasher=hashlib.sha256()
    with open(path, 'rb') as stream:
        while True:
            control.check()
            chunk=stream.read(1024*1024)
            if not chunk: break
            hasher.update(chunk)
    after=os.stat(path)
    if (before.st_size, before.st_mtime) != (after.st_size, after.st_mtime):
        raise UnqualifiedSnapshot('Source file changed during fingerprinting')
    if doc.IsModified or memory != version(db.Document.GetDocumentVersion(doc)):
        raise UnqualifiedSnapshot('Source document changed during qualification')
    control.check()
    return dict(status='SAVED_LOCAL_MEMORY_DISK_MATCH', path=path,
                project_info_unique_id=doc.ProjectInformation.UniqueId,
                document_version=memory, rvt_sha256=hasher.hexdigest(), bytes=after.st_size)
