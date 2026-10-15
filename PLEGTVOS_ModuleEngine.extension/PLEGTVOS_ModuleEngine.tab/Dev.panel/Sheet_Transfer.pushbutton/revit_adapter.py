# -*- coding: utf-8 -*-
"""Read-only Revit boundary. Collectors use explicit native iterators."""
import time
import traceback
from preview_models import text

class Adapter(object):
    def __init__(self, db, limit=10000, seconds=60):
        self.db = db
        self.limit = limit
        self.deadline = time.time() + seconds
        self.errors = []
        self.scanned = 0

    def check(self):
        if time.time() > self.deadline:
            raise RuntimeError('Preview budget reached; inventory is incomplete')

    def read(self, context, action, api_call=None):
        self.check()
        try:
            return action()
        except Exception as exc:
            self.errors.append({'context': context, 'status': 'UNKNOWN',
                                'api_call': api_call,
                                'exception_type': type(exc).__name__,
                                'traceback': text(traceback.format_exc())})
            return None

    def collect(self, doc, cls=None, category=None, owner=None, types=False):
        self.check()
        collector = self.db.FilteredElementCollector(doc)
        iterator = None
        try:
            if cls is not None:
                collector = collector.OfClass(cls)
            if category is not None:
                collector = collector.OfCategory(category)
            if owner is not None:
                collector = collector.OwnedByView(owner)
            collector = collector.WhereElementIsElementType() if types else collector.WhereElementIsNotElementType()
            iterator = collector.GetElementIterator()
            iterator.Reset()
            result = []
            while True:
                self.check()
                if not iterator.MoveNext():
                    return result
                self.scanned += 1
                if self.scanned > self.limit:
                    raise RuntimeError('Preview scan limit reached; inventory is incomplete')
                result.append(iterator.Current)
        finally:
            if iterator is not None:
                iterator.Dispose()
            collector.Dispose()

    def identity(self, element, doc_key):
        uid = text(element.UniqueId)
        if not uid:
            raise ValueError('Missing UniqueId')
        return {'key': doc_key + ':' + uid, 'unique_id': uid,
                'element_id': text(element.Id.Value)}

    def named(self, element, doc_key):
        row = self.identity(element, doc_key)
        row['name'] = self.read(row['key'] + ':name', lambda: text(self.db.Element.Name.__get__(element)),
                                api_call='Element.Name.__get__')
        row['name_status'] = 'UNKNOWN_READ_ERROR' if row['name'] is None else 'READ_OK'
        return row

    def reference(self, doc, eid, doc_key):
        if eid == self.db.ElementId.InvalidElementId:
            return {'status': 'NONE_ASSIGNED'}
        element = doc.GetElement(eid)
        if element is None:
            raise ValueError('Unresolved reference ' + text(eid.Value))
        row = self.named(element, doc_key)
        row['status'] = 'RESOLVED_SOURCE_ONLY'
        return row

    def scope(self, doc, view, key):
        parameter = view.get_Parameter(self.db.BuiltInParameter.VIEWER_VOLUME_OF_INTEREST_CROP)
        if parameter is None:
            return {'status': 'NOT_APPLICABLE_NO_PARAMETER'}
        return self.reference(doc, parameter.AsElementId(), key)

    def crop(self, view):
        result = {'active': view.CropBoxActive, 'visible': view.CropBoxVisible,
                  'geometry': 'NOT_INSPECTED', 'annotation_crop': 'NOT_INSPECTED'}
        manager = view.GetCropRegionShapeManager()
        if manager is not None:
            try:
                result['can_have_shape'] = manager.CanHaveShape
                result['split_regions'] = manager.NumberOfSplitRegions
            finally:
                manager.Dispose()
        return result

    def documents(self, application, active):
        result = []
        iterator = application.Documents.ForwardIterator()
        iterator.Reset()
        try:
            while iterator.MoveNext():
                doc = iterator.Current
                if doc.IsValidObject and not doc.IsFamilyDocument and not doc.IsLinked:
                    number = len(result) + 1
                    row = {'key': 'open-session-doc-' + text(number), 'title': text(doc.Title),
                           'path': text(doc.PathName), 'read_only': doc.IsReadOnly,
                           'workshared': doc.IsWorkshared, 'modified_before': doc.IsModified,
                           'identity_scope': 'CURRENT_INVOCATION_ONLY', 'proposed_source': doc.Equals(active) if active else False}
                    result.append((doc, row))
                if len(result) > 100:
                    raise RuntimeError('Open document limit reached')
        finally:
            if hasattr(iterator, 'Dispose'):
                iterator.Dispose()
        return result
