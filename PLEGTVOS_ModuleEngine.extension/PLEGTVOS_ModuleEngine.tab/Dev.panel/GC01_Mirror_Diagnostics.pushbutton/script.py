# -*- coding: utf-8 -*-
__title__ = "GC01 Mirror\nDiagnostics"
__doc__ = "Read-only GC01 inventory, connector and slope evidence. No model changes."

import os
import sys
import hashlib
from datetime import datetime
from Autodesk.Revit import DB
from pyrevit import forms

HERE = os.path.dirname(__file__)
if HERE not in sys.path: sys.path.insert(0, HERE)
import diagnostic_core as core
import revit_reader
import report_store
import failure_diagnostics


def observations(uidoc):
    doc = uidoc.Document
    return dict(is_modified=bool(doc.IsModified), active_view_id=revit_reader.eid(doc.ActiveView.Id),
                selection=sorted(revit_reader.eid(i) for i in uidoc.Selection.GetElementIds()))


def main():
    uidoc = __revit__.ActiveUIDocument
    if uidoc is None:
        print('Open a project and preselect exactly one scope box. No report written.')
        return
    doc = uidoc.Document
    ids = list(uidoc.Selection.GetElementIds())
    selected = [doc.GetElement(i) for i in ids]
    categories = [revit_reader.eid(e.Category.Id) if e is not None and e.Category else None for e in selected]
    if doc.IsFamilyDocument or not core.valid_selection(categories, str(int(DB.BuiltInCategory.OST_VolumeOfInterest))):
        print('Preselect exactly one scope box in a project. No report written.')
        return
    print(u'READ-ONLY DIAGNOSTIC \u2014 NO MODEL CHANGES')
    before = observations(uidoc)
    reader = revit_reader.Reader(doc)
    try:
        snapshot = reader.collect(selected[0])
    except Exception as error:
        failure_diagnostics.emit(['Collection failed; no report written and no model edits attempted.'])
        failure_diagnostics.emit(failure_diagnostics.failure_lines(sys.exc_info(), reader.context))
        if reader.unicode_failures:
            failure_diagnostics.emit(['Earlier caught Unicode read failures:'])
            failure_diagnostics.emit(reader.unicode_failures)
        return
    if reader.unicode_failures:
        failure_diagnostics.emit(['Caught Unicode read failures (fields remain unresolved):'])
        failure_diagnostics.emit(reader.unicode_failures)
    after = observations(uidoc)
    hasher = hashlib.sha256()
    for name in ('script.py', 'diagnostic_core.py', 'revit_reader.py', 'report_store.py', 'failure_diagnostics.py'):
        with open(os.path.join(HERE, name), 'rb') as stream: hasher.update(stream.read())
    report = dict(schema=core.SCHEMA, feature_id='GC01_MIRROR_DIAGNOSTICS',
                  status='OBSERVATION_ONLY_UNRESOLVED', snapshot=snapshot,
                  content_sha256=core.digest(snapshot),
                  run=dict(captured_utc=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
                           collector_version=core.VERSION, code_sha=None, source_sha256=hasher.hexdigest(),
                           loaded_path=HERE, revit_build=doc.Application.VersionBuild,
                           revit_version=doc.Application.VersionNumber, python_engine=sys.version),
                  safety=dict(model_write_apis_invoked=False, transactions_started=False,
                              observation_before=before, observation_after=after,
                              observed_fields_unchanged=before==after, host_acceptance='NOT_RUN',
                              limitation='These fields do not prove full model invariance or Undo state.'))
    summary = snapshot['summary']
    print('Module: {0}'.format(snapshot['source']['scope_box']['name']))
    print('Candidates: {physical_candidates}; connector-bearing elements: {connector_bearing_elements}'.format(**summary))
    print('Connectors: {connectors}; connected: {connected}; unconnected: {unconnected}; unknown: {connection_unknown}'.format(**summary))
    print('Pipes: {pipes}; measured slopes: {measured_slopes}; vertical: {vertical_pipes}'.format(**summary))
    print('Near-boundary connectors: {boundary_connectors}; physical boundary edges: {physical_boundary_edges}; unresolved issues: {unresolved_issues}'.format(**summary))
    print('Mirror: MIRROR_FRAME_UNCONFIRMED. Open-port intent and slope compliance: UNKNOWN.')
    if before != after:
        print('Observed document/view/selection state changed during collection; export stopped. Investigate in host.')
        return
    default = report_store.suggested_root(snapshot['document'])
    choice = forms.CommandSwitchWindow.show(['Use diagnostic folder', 'Choose external folder'],
        message='Export immutable report and diagnostic-only latest pointer?\n' + default)
    if not choice:
        print('Export cancelled; no files written.')
        return
    root = default if choice == 'Use diagnostic folder' else forms.pick_folder(title='Choose diagnostic report root')
    if not root:
        print('Export cancelled; no files written.')
        return
    try:
        path, warning = report_store.save(report, root)
        print('JSON: ' + path)
        if warning: print(warning)
    except Exception as error:
        print('Export failed ({0}); no model changes attempted. Check the diagnostic folder for a partial file.'.format(type(error).__name__))


if __name__ == '__main__':
    main()
