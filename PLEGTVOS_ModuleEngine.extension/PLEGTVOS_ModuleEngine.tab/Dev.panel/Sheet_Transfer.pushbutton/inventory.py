# -*- coding: utf-8 -*-
from preview_models import text, ordered, view_support, content_classification

def sheet_index(adapter, doc, key):
    result = []
    for sheet in adapter.collect(doc, cls=adapter.db.ViewSheet):
        row = adapter.named(sheet, key)
        row['number'] = text(sheet.SheetNumber)
        row['placeholder'] = sheet.IsPlaceholder
        result.append((sheet, row))
    return sorted(result, key=lambda pair: (pair[1]['number'], pair[1]['key']))

def titleblock(adapter, element, key, instance):
    symbol = element.Document.GetElement(element.GetTypeId()) if instance else element
    if symbol is None:
        raise ValueError('Missing title-block type')
    row = adapter.named(element, key)
    row['type_identity'] = adapter.identity(symbol, key)
    row['type_name'] = adapter.named(symbol, key)['name']
    row['family'] = text(symbol.FamilyName)
    return row

def target_inventory(a, doc, key):
    db = a.db
    views = []; templates = []
    for view in a.collect(doc, cls=db.View):
        row = a.named(view, key)
        row['view_type'] = text(view.ViewType)
        (templates if view.IsTemplate else views).append(row)
    blocks = []
    for block in a.collect(doc, category=db.BuiltInCategory.OST_TitleBlocks, types=True):
        row = a.read('destination titleblock', lambda: titleblock(a, block, key, False))
        if row: blocks.append(row)
    return {'sheets': [r for _, r in sheet_index(a, doc, key)],
            'views': ordered(views), 'templates': ordered(templates), 'titleblocks': ordered(blocks),
            'scopes': ordered([a.named(e, key) for e in a.collect(doc, category=db.BuiltInCategory.OST_VolumeOfInterest)])}

def view_record(a, doc, view, key):
    row = a.named(view, key); context = row['key']
    row['view_type'] = a.read(context + ':type', lambda: text(view.ViewType))
    row['transfer_support'] = view_support(row['view_type'])
    row['template'] = a.read(context + ':template', lambda: a.reference(doc, view.ViewTemplateId, key))
    row['scope'] = a.read(context + ':scope', lambda: a.scope(doc, view, key))
    row['primary'] = a.read(context + ':primary', lambda: a.reference(doc, view.GetPrimaryViewId(), key))
    row['crop'] = a.read(context + ':crop', lambda: a.crop(view))
    row['view_owned_contents'] = 'NOT_INSPECTED_UNRESOLVED'
    return row

def selected_inventory(a, doc, key, selected):
    result = []; seen = set(); cache = {}
    for sheet, basic in selected:
        if basic['key'] in seen: continue
        seen.add(basic['key'])
        row = dict(basic); row.update({'titleblocks': [], 'viewports': [], 'schedules': [], 'unsupported': []})
        for element in a.collect(doc, owner=sheet.Id):
            item = a.named(element, key); context = item['key']
            if isinstance(element, a.db.Viewport):
                item['placement'] = a.read(context + ':center', lambda: point(element.GetBoxCenter()))
                item['rotation'] = a.read(context + ':rotation', lambda: text(element.Rotation))
                view_key = text(element.ViewId.Value)
                if view_key not in cache:
                    cache[view_key] = a.read(context + ':view', lambda: view_record(a, doc, doc.GetElement(element.ViewId), key))
                item['view'] = cache[view_key]
                row['viewports'].append(item)
            elif isinstance(element, a.db.ScheduleSheetInstance):
                item['schedule'] = a.read(context + ':schedule', lambda: a.reference(doc, element.ScheduleId, key))
                item['placement'] = a.read(context + ':position', lambda: point(element.Point))
                item['transfer_support'] = 'UNSUPPORTED_TRANSFER_SCHEDULE'
                row['schedules'].append(item)
            elif element.Category and element.Category.Id == a.db.ElementId(a.db.BuiltInCategory.OST_TitleBlocks):
                block = a.read(context + ':titleblock', lambda: titleblock(a, element, key, True))
                if block: row['titleblocks'].append(block)
                else:
                    item['status'] = 'UNKNOWN_TITLEBLOCK'; row['unsupported'].append(item)
            else:
                item['runtime_type'] = text(element.GetType().FullName)
                item['status'] = 'UNSUPPORTED_BY_M1_NOT_API_VERDICT'
                item.update(content_classification(item['runtime_type']))
                row['unsupported'].append(item)
        for field in ['titleblocks', 'viewports', 'schedules', 'unsupported']:
            row[field] = ordered(row[field])
        result.append(row)
    return ordered(result)

def point(p):
    return [p.X, p.Y, p.Z]
