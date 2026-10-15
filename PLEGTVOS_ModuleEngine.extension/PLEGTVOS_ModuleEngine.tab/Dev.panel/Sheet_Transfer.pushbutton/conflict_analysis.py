# -*- coding: utf-8 -*-
from preview_models import ordered, validate_pair

def matches(rows, field, value):
    if value is None:
        return []
    return ordered([r for r in rows if r.get(field) == value])

def analyze(source, destination, sheets, target, errors):
    validate_pair(source, destination)
    sheets = ordered(sheets)
    numbers = {}
    for sheet in sheets:
        numbers[sheet.get('number')] = numbers.get(sheet.get('number'), 0) + 1
    for sheet in sheets:
        sheet['number_conflicts'] = matches(target['sheets'], 'number', sheet.get('number'))
        sheet['duplicate_source_number'] = numbers[sheet.get('number')] > 1
        sheet['titleblock_status'] = 'OBSERVED' if sheet['titleblocks'] else 'UNKNOWN_MISSING_TITLEBLOCK'
        for block in sheet['titleblocks']:
            candidates = []
            if block.get('family') is not None and block.get('type_name') is not None:
                candidates = [r for r in target['titleblocks'] if r.get('family') == block['family'] and r.get('type_name') == block['type_name']]
            block['destination_candidates'] = ordered(candidates)
            block['match_status'] = 'NAME_CANDIDATE_NOT_EQUIVALENCE' if candidates else 'UNKNOWN_NO_MATCH'
        for vp in sheet['viewports']:
            view = vp.get('view')
            if view:
                view['destination_name_conflicts'] = matches(target['views'], 'name', view.get('name'))
                for field, pool in [('template', target['templates']), ('scope', target['scopes'])]:
                    ref = view.get(field)
                    if ref and ref.get('key'):
                        ref['destination_name_candidates'] = matches(pool, 'name', ref.get('name'))
                        ref['mapping_status'] = 'UNRESOLVED_NAME_ONLY'
    return {'schema': 'plegtvos.sheet_transfer_preview/1', 'mode': 'READ_ONLY',
            'transfer_enabled': False, 'transfer_status': 'NOT_IMPLEMENTED',
            'source': source, 'destination': destination, 'sheets': sheets,
            'errors': errors, 'inventory_status': 'UNKNOWN_READ_ERRORS' if errors else 'OBSERVED_WITH_DECLARED_LIMITATIONS',
            'limitations': ['No transfer capability is accepted in M1.',
                'View-owned annotations, host references, revisions and parameter parity are NOT_INSPECTED.',
                'Template/type/scope name candidates are not verified equivalence.',
                'Crop geometry fidelity and target model correspondence remain UNRESOLVED.']}
