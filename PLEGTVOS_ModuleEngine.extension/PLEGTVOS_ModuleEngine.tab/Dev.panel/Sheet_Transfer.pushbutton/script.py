# -*- coding: utf-8 -*-
__title__ = "Sheet\nTransfer"
__doc__ = "M1 read-only dependency preview. No transfer operation exists."
from Autodesk.Revit import DB
from preview_models import validate_pair, text
from revit_adapter import Adapter
from inventory import sheet_index, selected_inventory, target_inventory
from conflict_analysis import analyze
from reporting import write_report, summary
from preview_ui import choose_document, choose_sheets, notice
import traceback

def main():
    a = Adapter(DB)
    active = __revit__.ActiveUIDocument.Document if __revit__.ActiveUIDocument else None
    pairs = a.documents(__revit__.Application, active)
    if len(pairs) < 2:
        notice('Open two supported project documents. No destination is available.'); return
    source = choose_document(pairs, 'Select source project (active proposed)')
    if not source: return
    destinations = [(doc, row) for doc, row in pairs if not doc.Equals(source[0]) and not row['read_only']]
    if not destinations:
        notice('No supported writable destination project is open.'); return
    destination = choose_document(destinations, 'Select destination project - read-only preview')
    if not destination: return
    validate_pair(source[1], destination[1])
    # UI decision time is excluded from each bounded API phase.
    a = Adapter(DB)
    sheets = sheet_index(a, source[0], source[1]['key'])
    if not sheets:
        notice('Source has zero sheets.'); return
    chosen = choose_sheets(sheets)
    if not chosen: return
    if len(chosen) > 100:
        notice('Select at most 100 sheets per preview. Nothing was transferred.'); return
    initial_errors = a.errors
    a = Adapter(DB)
    a.errors.extend(initial_errors)
    selected = selected_inventory(a, source[0], source[1]['key'], chosen)
    target = target_inventory(a, destination[0], destination[1]['key'])
    report = analyze(source[1], destination[1], selected, target, a.errors)
    report['source']['modified_after'] = source[0].IsModified
    report['destination']['modified_after'] = destination[0].IsModified
    path = write_report(report)
    notice(summary(report)[:6000] + u'\n\nFull JSON and text report: ' + text(path))

if __name__ == '__main__':
    try:
        main()
    except Exception:
        # ASCII escape traceback rather than risk another Unicode console failure.
        failure = text(traceback.format_exc()).encode('ascii', 'backslashreplace').decode('ascii')
        notice(u'PREVIEW INCOMPLETE / UNKNOWN. No transfer was attempted.\n' + failure)
