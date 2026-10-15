# -*- coding: utf-8 -*-
"""The only Revit mutation boundary for the development-only F1 experiment."""
import os
import time
import sys
import uuid
from Autodesk.Revit import DB
from f1_core import validate_destination
from f1_reporting import text_type, write

_UNRESOLVED = []


def name(element):
    return text_type(DB.Element.Name.__get__(element))


def identity(element):
    return {'id': text_type(element.Id.Value), 'unique_id': text_type(element.UniqueId)}


def same_document(source, destination):
    # Native object equality, never a path or ProjectInformation element UID test.
    if not source.IsValidObject or not destination.IsValidObject:
        raise ValueError('Document identity unavailable: invalid object')
    forward = source.Equals(destination)
    reverse = destination.Equals(source)
    if forward not in (True, False) or reverse not in (True, False) or forward != reverse:
        raise ValueError('Document identity unavailable: inconsistent native equality')
    return bool(forward)


def document_state(doc):
    path = text_type(doc.PathName)
    return {'valid': bool(doc.IsValidObject), 'project': not doc.IsFamilyDocument,
            'saved_local': bool(path and os.path.isabs(path) and not path.startswith('\\\\')
                                and path.lower().endswith('.rvt') and os.path.isfile(path)),
            'path': path, 'title': text_type(doc.Title),
            'project_information_unique_id': text_type(doc.ProjectInformation.UniqueId),
            'stable_file_model_identity': {'status': 'UNAVAILABLE',
                                           'reason': 'No independent file/model identity established by F1'},
            'read_only': bool(doc.IsReadOnly), 'linked': bool(doc.IsLinked),
            'modifiable': bool(doc.IsModifiable), 'workshared': bool(doc.IsWorkshared),
            'cloud': bool(doc.IsModelInCloud), 'modified': bool(doc.IsModified)}


def collect(doc, cls=None, category=None, owner=None, cap=20000, instances=False):
    if cls is None and category is None:
        raise ValueError('F1 inventory requires an explicit class or category filter')
    deadline = time.time() + 60
    collector = DB.FilteredElementCollector(doc)
    iterator = None
    try:
        if cls is not None: collector = collector.OfClass(cls)
        if category is not None: collector = collector.OfCategory(category)
        if owner is not None: collector = collector.OwnedByView(owner)
        if instances: collector = collector.WhereElementIsNotElementType()
        iterator = collector.GetElementIterator()
        iterator.Reset()
        values = []
        while iterator.MoveNext():
            if time.time() > deadline or len(values) >= cap:
                raise RuntimeError('Bounded F1 inventory incomplete')
            values.append(iterator.Current)
        return values
    finally:
        if iterator is not None: iterator.Dispose()
        collector.Dispose()


def symbol_info(doc, symbol):
    if symbol is None or not symbol.IsValidObject or not symbol.Document.Equals(doc):
        raise ValueError('Title-block symbol missing or from another document')
    if not isinstance(symbol, DB.FamilySymbol) or symbol.Id == DB.ElementId.InvalidElementId:
        raise ValueError('Expected destination FamilySymbol')
    if symbol.Category is None or symbol.Category.Id != DB.ElementId(DB.BuiltInCategory.OST_TitleBlocks):
        raise ValueError('Expected OST_TitleBlocks')
    if symbol.Family.FamilyPlacementType != DB.FamilyPlacementType.ViewBased:
        raise ValueError('Expected ViewBased title-block family')
    current = doc.GetElement(symbol.Id)
    if current is None or current.UniqueId != symbol.UniqueId:
        raise ValueError('Stale title-block selection')
    row = identity(symbol)
    row.update({'family': text_type(symbol.FamilyName), 'name': name(symbol),
                'active': bool(symbol.IsActive)})
    return row


class NativeTransaction(object):
    def __init__(self, native): self.native = native
    def Start(self): return text_type(self.native.Start())
    def GetStatus(self): return text_type(self.native.GetStatus())
    def Commit(self): return text_type(self.native.Commit())
    def RollBack(self): return text_type(self.native.RollBack())
    def Dispose(self): self.native.Dispose()


class AbortFailures(DB.IFailuresPreprocessor):
    __namespace__ = 'PlegtvosF1_' + uuid.uuid4().hex

    def __init__(self, evidence): self.evidence = evidence

    def PreprocessFailures(self, accessor):
        try:
            messages = accessor.GetFailureMessages()
            if messages.Count == 0:
                return DB.FailureProcessingResult.Continue
            for message in messages:
                if len(self.evidence) >= 100:
                    break
                self.evidence.append({'severity': text_type(message.GetSeverity()),
                                      'description': text_type(message.GetDescriptionText())[:1000]})
        except Exception:
            self.evidence.append({'status': 'FAILURE_DETAILS_UNAVAILABLE'})
        # All warnings/errors reject the experiment. Nothing is deleted or resolved.
        return DB.FailureProcessingResult.ProceedWithRollBack


class Host(object):
    def __init__(self, source, destination, symbol, acknowledged, expected_state, directory):
        self.source = source
        self.destination = destination
        self.symbol_uid = text_type(symbol.UniqueId)
        self.expected_state = expected_state
        self.acknowledged = acknowledged
        self.directory = directory
        self.failures = []
        self.handler = None
        self.created_ids = []
        self.selected = symbol_info(destination, symbol)
        self.number = 'F1-' + uuid.uuid4().hex[:16]

    def validate(self):
        if _UNRESOLVED:
            raise RuntimeError('Prior unresolved experiment: restart only after operator recovery')
        if not self.source.IsValidObject or self.source.IsModifiable:
            raise ValueError('Source unavailable or in a transaction')
        state = document_state(self.destination)
        validate_destination(state, same_document(self.source, self.destination), self.acknowledged)
        if state != self.expected_state:
            raise ValueError('Destination state changed since confirmation')
        if symbol_info(self.destination, self.destination.GetElement(self.symbol_uid)) != self.selected:
            raise ValueError('Selected type changed since confirmation')
        return {'source': document_state(self.source), 'destination': state,
                'runtime_document_identity': {'method': 'Document.Equals in both directions', 'same_document': False},
                'titleblock_type': self.selected, 'disposable_acknowledged': self.acknowledged,
                'adapter_path': __file__, 'engine': sys.version,
                'revit_version': text_type(self.destination.Application.VersionNumber),
                'revit_build': text_type(self.destination.Application.VersionBuild)}

    def snapshot_one(self, doc):
        sheets = []
        for sheet in collect(doc, cls=DB.ViewSheet, cap=2000, instances=True):
            row = identity(sheet)
            row.update({'number': text_type(sheet.SheetNumber), 'name': name(sheet)})
            sheets.append(row)
        blocks = []
        for block in collect(doc, category=DB.BuiltInCategory.OST_TitleBlocks, cap=5000, instances=True):
            if not isinstance(block, DB.FamilyInstance): continue
            row = identity(block)
            row.update({'type_id': text_type(block.GetTypeId().Value),
                        'owner_view_id': text_type(block.OwnerViewId.Value)})
            blocks.append(row)
        result = {'state': document_state(doc), 'sheets': sorted(sheets, key=lambda x: x['unique_id']),
                  'sheet_count': len(sheets), 'titleblocks': sorted(blocks, key=lambda x: x['unique_id'])}
        return result

    def snapshot(self):
        return {'source': self.snapshot_one(self.source),
                'destination': self.snapshot_one(self.destination),
                'selected_type': symbol_info(self.destination, self.destination.GetElement(self.symbol_uid))}

    def preflight_report(self, report):
        for sheet in report['before']['destination']['sheets']:
            if sheet['number'] == self.number: raise ValueError('Temporary number conflict')
        write(self.directory, report, 'before')

    def group(self):
        return NativeTransaction(DB.TransactionGroup(self.destination, 'EXPERIMENTAL F1 - rollback only'))

    def transaction(self):
        return NativeTransaction(DB.Transaction(self.destination, 'F1 temporary sheet'))

    def configure_failures(self, transaction):
        self.handler = AbortFailures(self.failures)
        options = transaction.native.GetFailureHandlingOptions()
        options.SetFailuresPreprocessor(self.handler)
        options.SetForcedModalHandling(True)
        options.SetClearAfterRollback(False)
        transaction.native.SetFailureHandlingOptions(options)

    def create(self, report, force_invalid_type):
        symbol = self.destination.GetElement(self.symbol_uid)
        symbol_info(self.destination, symbol)
        type_id = DB.ElementId(-999999) if force_invalid_type else symbol.Id
        sheet = DB.ViewSheet.Create(self.destination, type_id)
        self.created_ids.append(sheet.Id)
        report['created'] = {'sheet': identity(sheet), 'titleblocks': []}
        if force_invalid_type:
            raise RuntimeError('Invalid-type fault unexpectedly created a sheet')
        sheet.SheetNumber = self.number
        sheet.Name = 'EXPERIMENTAL F1 - MUST BE ROLLED BACK'
        report['created']['sheet']['temporary_number'] = text_type(sheet.SheetNumber)
        self.destination.Regenerate()
        for block in collect(self.destination, category=DB.BuiltInCategory.OST_TitleBlocks, owner=sheet.Id, cap=20, instances=True):
            self.created_ids.append(block.Id)
            report['created']['titleblocks'].append(identity(block))

    def verify_created(self, report):
        created = report['created']
        sheet = self.destination.GetElement(created['sheet']['unique_id'])
        if not isinstance(sheet, DB.ViewSheet) or not sheet.Document.Equals(self.destination):
            raise ValueError('Created destination sheet not verified')
        if text_type(sheet.SheetNumber) != self.number or sheet.GetAllViewports().Count != 0:
            raise ValueError('Expected numbered blank sheet')
        blocks = collect(self.destination, category=DB.BuiltInCategory.OST_TitleBlocks, owner=sheet.Id, cap=20, instances=True)
        if len(blocks) != 1:
            raise ValueError('Expected exactly one title-block instance')
        block = blocks[0]
        symbol = self.destination.GetElement(self.symbol_uid)
        if not isinstance(block, DB.FamilyInstance) or block.GetTypeId() != symbol.Id:
            raise ValueError('Title-block instance/type mismatch')
        if not self.created_ids or block.Id not in self.created_ids:
            raise ValueError('Created title-block identity not recorded')
        created['validated'] = True

    def created_absent(self, report):
        for eid in self.created_ids:
            if self.destination.GetElement(eid) is not None: return False
        created = report.get('created')
        if created:
            rows = [created['sheet']] + created['titleblocks']
            for row in rows:
                if self.destination.GetElement(row['unique_id']) is not None: return False
        return True

    def hold_unresolved(self, transaction, group):
        _UNRESOLVED.append((self, transaction, group))
