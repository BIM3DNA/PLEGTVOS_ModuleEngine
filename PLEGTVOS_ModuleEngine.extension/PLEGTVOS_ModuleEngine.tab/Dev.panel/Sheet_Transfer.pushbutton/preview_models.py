# -*- coding: utf-8 -*-
"""Plain data only. Identity is document-session scoped, never a cross-doc ID."""
try:
    text_type = unicode
except NameError:
    text_type = str
BANNER = u"READ-ONLY PREVIEW \u2014 NO ELEMENTS WILL BE TRANSFERRED"

def text(value):
    if isinstance(value, bytes) and not isinstance(value, text_type):
        return value.decode('utf-8')
    return text_type(value)

def ordered(rows):
    result = {}
    for row in rows:
        key = row['key']
        if key in result and result[key] != row:
            raise ValueError('Conflicting duplicate identity: ' + key)
        result[key] = row
    return sorted(result.values(), key=lambda r: (r.get('number', ''), r.get('name', ''), r['key']))

def validate_pair(source, destination):
    if destination is None:
        raise ValueError('No supported open destination document')
    if source['key'] == destination['key']:
        raise ValueError('Source and destination must be different documents')

def view_support(kind):
    if kind in ('FloorPlan', 'CeilingPlan', 'EngineeringPlan'):
        return 'FUTURE_CANDIDATE_NOT_VALIDATED'
    return 'UNSUPPORTED_TRANSFER_KIND'


def content_classification(runtime_type):
    """Inventory interpretation, not an implemented or verified transfer route."""
    kind = runtime_type.rsplit('.', 1)[-1]
    routes = {'TextNote': 'TextNote.Create', 'DetailLine': 'NewDetailCurve',
              'DetailEllipse': 'NewDetailCurve', 'ImageInstance': 'ImageInstance.Create'}
    if kind in routes:
        return {'inventory_class': 'ANNOTATION_API_CANDIDATE',
                'api_route_for_future_review': routes[kind],
                'transfer_support': 'NOT_IMPLEMENTED_NOT_HOST_VERIFIED'}
    if kind in ('SketchPlane', 'GraphicsStyle'):
        return {'inventory_class': 'DEPENDENCY_REQUIRES_REVIEW',
                'transfer_support': 'UNRESOLVED_NOT_IMPLEMENTED'}
    return {'inventory_class': 'UNCLASSIFIED_REQUIRES_REVIEW',
            'transfer_support': 'UNRESOLVED_NOT_IMPLEMENTED'}
