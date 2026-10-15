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
import execution_control
import snapshot_guard
import detail_batches


def observations(uidoc):
    doc = uidoc.Document
    return dict(is_modified=bool(doc.IsModified), active_view_id=revit_reader.eid(doc.ActiveView.Id),
                selection=sorted(revit_reader.eid(i) for i in uidoc.Selection.GetElementIds()))


def run(control):
    control.progress('Validate selection')
    uidoc = __revit__.ActiveUIDocument
    if uidoc is None:
        print('Open a project and preselect exactly one scope box. No report written.')
        return
    doc = uidoc.Document
    ids = uidoc.Selection.GetElementIds()
    if ids.Count != 1:
        print('Preselect exactly one scope box. No report written.')
        return
    ids = list(ids)
    selected = [doc.GetElement(i) for i in ids]
    categories = [revit_reader.eid(e.Category.Id) if e is not None and e.Category else None for e in selected]
    if doc.IsFamilyDocument or not core.valid_selection(categories, str(int(DB.BuiltInCategory.OST_VolumeOfInterest))):
        print('Preselect exactly one scope box in a project. No report written.')
        return
    print(u'READ-ONLY DIAGNOSTIC \u2014 NO MODEL CHANGES')
    before = observations(uidoc)
    freshness = snapshot_guard.capture(doc, DB, control)
    reader = revit_reader.Reader(doc, control)
    try:
        snapshot = reader.collect(selected[0])
    except Exception as error:
        failure_diagnostics.emit(['Collection failed; no report written and no model edits attempted.'])
        failure_diagnostics.emit(failure_diagnostics.failure_lines(sys.exc_info(), reader.context))
        if reader.unicode_failures:
            failure_diagnostics.emit(['Earlier caught Unicode read failures:'])

            for lines in reader.unicode_failures: failure_diagnostics.emit(lines)
        return
    if reader.unicode_failures:
        failure_diagnostics.emit(['Caught Unicode read failures (fields remain unresolved):'])
        for lines in reader.unicode_failures: failure_diagnostics.emit(lines)
    if snapshot_guard.capture(doc, DB, control) != freshness:
        raise snapshot_guard.UnqualifiedSnapshot('Source changed during collection; start a fresh diagnostic')
    snapshot['coverage']['snapshot_identity'] = freshness['status']
    control.progress('Serialize JSON', len(snapshot['elements']), len(snapshot['elements']))
    after = observations(uidoc)
    hasher = hashlib.sha256()
    for name in ('script.py', 'diagnostic_core.py', 'revit_reader.py', 'report_store.py', 'failure_diagnostics.py', 'execution_control.py', 'snapshot_guard.py', 'detail_batches.py'):
        with open(os.path.join(HERE, name), 'rb') as stream: hasher.update(stream.read())
    report = dict(schema=core.SCHEMA, feature_id='GC01_MIRROR_DIAGNOSTICS',
                  status='TRUNCATED_UNRESOLVED' if control.truncated else 'OBSERVATION_ONLY_UNRESOLVED', snapshot=snapshot,
                  content_sha256=None,  # Per-part and manifest hashes replace a monolithic report hash.
                  run=dict(captured_utc=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
                           collector_version='1.1h', diagnostic_mode=control.mode, code_sha=None, source_sha256=hasher.hexdigest(),
                           loaded_path=HERE, revit_build=doc.Application.VersionBuild,
                           revit_version=doc.Application.VersionNumber, python_engine=sys.version),
                  safety=dict(model_write_apis_invoked=False, transactions_started=False,
                              observation_before=before, observation_after=after,
                              observed_fields_unchanged=before==after, host_acceptance='NOT_RUN',
                              limitation='These fields do not prove full model invariance or Undo state.'))
    summary = snapshot['summary']
    failure_diagnostics.emit(['Module: ' + failure_diagnostics.display(snapshot['source']['scope_box']['name']),
        'Mode: ' + control.mode + '; status: ' + report['status'],
        'Limits reached: ' + ', '.join(control.truncated),
        'Scanned elements = supported-category instances inspected; unsupported categories NOT INSPECTED.'])
    if control.mode == 'FAST':
        failure_diagnostics.emit(['FAST connector counts are NOT INSPECTED, not evidence of zero connectors.'])
    print('Candidates: {physical_candidates}; connector-bearing elements: {connector_bearing_elements}'.format(**summary))
    print('Connectors: {connectors}; connected: {connected}; unconnected: {unconnected}; unknown: {connection_unknown}'.format(**summary))
    print('Pipes: {pipes}; measured slopes: {measured_slopes}; vertical: {vertical_pipes}'.format(**summary))
    print('Near-boundary connectors: {boundary_connectors}; physical boundary edges: {physical_boundary_edges}; unresolved issues: {unresolved_issues}'.format(**summary))
    print('Mirror: MIRROR_FRAME_UNCONFIRMED. Open-port intent and slope compliance: UNKNOWN.')
    if before != after:
        print('Observed document/view/selection state changed during collection; export stopped. Investigate in host.')
        return
    # Each plan/part/manifest is bounded independently before its exclusive write.
    default = report_store.suggested_root(snapshot['document'])
    choice = forms.CommandSwitchWindow.show(['Use diagnostic folder', 'Choose external folder', 'Continue incomplete bundle'],
        message='Export immutable FAST detail parts and manifest?\n' + default)
    if not choice:
        print('Export cancelled; no files written.')
        return
    resume = forms.pick_file(file_ext='json', title='Select incomplete FAST bundle plan.json') if choice == 'Continue incomplete bundle' else None
    if choice == 'Continue incomplete bundle' and not resume: return
    root = os.path.dirname(resume) if resume else default if choice == 'Use diagnostic folder' else forms.pick_folder(title='Choose diagnostic report root')
    if not root:
        print('Export cancelled; no files written.')
        return
    try:
        control.progress('Write report', len(snapshot['elements']), len(snapshot['elements']))
        path = detail_batches.save(report, root, freshness, control, resume=resume)
        failure_diagnostics.emit(['JSON: ' + failure_diagnostics.display(path)])
        control.progress('Write report complete', len(snapshot['elements']), len(snapshot['elements']), force=True)

    except execution_control.Stopped:
        raise
    except Exception as error:
        failure_diagnostics.emit(failure_diagnostics.failure_lines(sys.exc_info(), dict(stage='Write report', element_id=None, field='path/JSON')))
        print('Export failed ({0}); no model changes attempted. Check the diagnostic folder for a partial file.'.format(type(error).__name__))


def main():
    mode = 'FAST'
    if execution_control.FULL_HOST_ENABLED:
        mode = forms.CommandSwitchWindow.show(['FAST', 'FULL'], message='Diagnostic mode (FAST is the default recommendation)')
        if not mode: return
    control = execution_control.Control(mode)
    failure_diagnostics.emit(['GC01 diagnostic mode: ' + mode, 'Loaded path: ' + failure_diagnostics.display(HERE),
        'Engine: ' + failure_diagnostics.display(sys.version),
        'Cooperative stop only: an active Revit API call cannot be interrupted.'])
    try:
        run(control)
    except Exception:
        failure_diagnostics.emit(['Diagnostic stopped; no model edits attempted. Do not treat a partial export as accepted.'])
        failure_diagnostics.emit(failure_diagnostics.failure_lines(sys.exc_info(),
            dict(stage=control.stage, element_id=None, field='stage boundary')))


if __name__ == '__main__':
    main()
