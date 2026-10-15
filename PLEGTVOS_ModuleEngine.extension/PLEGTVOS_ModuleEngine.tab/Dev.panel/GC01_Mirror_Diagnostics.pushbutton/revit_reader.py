# -*- coding: utf-8 -*-
"""Revit 2025 read adapter. No button imports and no model-writing operations."""
from Autodesk.Revit import DB
import diagnostic_core as core
import failure_diagnostics
import sys
import execution_control

CATEGORIES = ('OST_PipeCurves', 'OST_FlexPipeCurves', 'OST_PipeFitting',
              'OST_PipeAccessory', 'OST_DuctCurves', 'OST_FlexDuctCurves',
              'OST_DuctFitting', 'OST_DuctAccessory', 'OST_MechanicalEquipment',
              'OST_PlumbingFixtures', 'OST_Sprinklers', 'OST_Conduit',
              'OST_ConduitFitting', 'OST_CableTray', 'OST_CableTrayFitting',
              'OST_PipeInsulations', 'OST_DuctInsulations', 'OST_DuctLinings')
PARAMETERS = ('RBS_PIPE_SLOPE', 'RBS_PIPE_DIAMETER_PARAM', 'RBS_CURVE_WIDTH_PARAM',
              'RBS_CURVE_HEIGHT_PARAM', 'RBS_SYSTEM_CLASSIFICATION_PARAM',
              'RBS_SYSTEM_NAME_PARAM', 'RBS_PIPING_SYSTEM_TYPE_PARAM',
              'RBS_DUCT_SYSTEM_TYPE_PARAM', 'RBS_START_LEVEL_PARAM',
              'RBS_OFFSET_PARAM', 'RBS_START_OFFSET_PARAM', 'RBS_END_OFFSET_PARAM')


def eid(value):
    return str(value.Value)


def xyz(value):
    return [float(value.X), float(value.Y), float(value.Z)]


def transform(t):
    return dict(origin_ft=xyz(t.Origin), basis_x=xyz(t.BasisX),
                basis_y=xyz(t.BasisY), basis_z=xyz(t.BasisZ))


def builtin_category_list():
    # Explicit typed ICollection selects the Revit BuiltInCategory overload.
    from System.Collections.Generic import List
    return List[DB.BuiltInCategory]()


class Reader(object):
    def __init__(self, doc, control=None):
        self.doc = doc
        self.control = control or execution_control.Control()
        self.element_cache = {}
        self.issues = []
        self.systems = {}
        self.expected_absences = {}
        self.doc_key = 'UNRESOLVED_DOCUMENT'
        self.context = dict(stage='initialization', element_id=None, field=None)
        self.unicode_failures = []

    def issue(self, subject, field, reason='UNAVAILABLE', code=None):
        self.issues.append(dict(code=code or reason, severity='UNRESOLVED',
                                subject_key=subject, field=field, reason=reason,
                                evidence_kind='OBSERVED_READ', message=reason))

    def read(self, subject, field, getter, optional=False):
        previous_field = self.context['field']
        self.context['field'] = field
        try:
            self.control.check()
            value = self.control.text(getter())
            self.control.check()
            if value is None:
                if optional:
                    self.expected_absences[field] = self.expected_absences.get(field, 0) + 1
                else:
                    self.issue(subject, field)
            return value
        except execution_control.Stopped:
            raise
        except Exception as error:
            if isinstance(error, UnicodeError):
                if len(self.unicode_failures) >= self.control.limits['unicode_failures']:
                    raise execution_control.Stopped('UNICODE_FAILURE_LIMIT; see earlier failures')
                self.unicode_failures.append(failure_diagnostics.failure_lines(sys.exc_info(), dict(self.context)))
            self.issue(subject, field, 'READ_ERROR')
            self.issues[-1]['exception_type'] = type(error).__name__
            self.issues[-1]['context'] = dict(self.context)
            self.issues[-1]['traceback'] = failure_diagnostics.failure_lines(sys.exc_info(), dict(self.context))
            return None
        finally:
            self.context['field'] = previous_field

    def ref(self, element):
        if element is None: return None
        ident = self.read('element', 'id', lambda: eid(element.Id))
        uid = self.read(ident, 'unique_id', lambda: element.UniqueId)
        return dict(document_key=self.doc_key, id=ident, unique_id=uid,
                    key=self.doc_key + '/' + (uid or ('unresolved-id-' + str(ident))),
                    name=self.read(uid or ident, 'name', lambda: element.Name))

    def lookup(self, ident):
        key = eid(ident)
        if key not in self.element_cache:
            self.control.check()
            self.element_cache[key] = self.doc.GetElement(ident)
        return self.element_cache[key]

    def related(self, owner, field, ident):
        if ident is None or eid(ident) == '-1': return None
        element = self.read(owner, field, lambda: self.lookup(ident))
        return self.ref(element)

    def bbox(self, element):
        box = element.get_BoundingBox(None)
        if box is None: return None
        corners = []
        for x in (box.Min.X, box.Max.X):
            for y in (box.Min.Y, box.Max.Y):
                for z in (box.Min.Z, box.Max.Z):
                    corners.append(xyz(box.Transform.OfPoint(DB.XYZ(x, y, z))))
        return dict(min_ft=xyz(box.Min), max_ft=xyz(box.Max),
                    transform=transform(box.Transform), corners_ft=corners,
                    meaning='ELEMENT_BOUNDING_BOX_NOT_DESIGN_AXES')

    def geometry(self, scope):
        segments = []
        geometry = scope.get_Geometry(DB.Options())
        for obj in self.control.items(geometry, 'geometry_objects'):
            if isinstance(obj, DB.Line):
                segments.append([xyz(obj.GetEndPoint(0)), xyz(obj.GetEndPoint(1))])
            else:
                self.issue('scope', 'geometry', 'UNSUPPORTED')
        return sorted([sorted(s) for s in segments])

    def location(self, element):
        loc = element.Location
        if isinstance(loc, DB.LocationCurve):
            curve = loc.Curve
            ends = [xyz(curve.GetEndPoint(i)) for i in (0, 1)] if curve.IsBound else None
            return dict(kind='CURVE', curve_type=curve.GetType().Name,
                        endpoints_ft=ends, length_ft=float(curve.Length),
                        is_line=isinstance(curve, DB.Line), endpoint_order='REVIT_CURVE_0_TO_1')
        if isinstance(loc, DB.LocationPoint):
            return dict(kind='POINT', point_ft=xyz(loc.Point),
                        rotation_rad=self.read(eid(element.Id), 'rotation_rad', lambda: float(loc.Rotation)))
        self.issue(eid(element.Id), 'location', 'UNSUPPORTED')
        return dict(kind='NONE')

    def params(self, element, key):
        result = {}
        for name in PARAMETERS[:self.control.limits['parameters']]:
            if self.control.limits['parameters'] < len(PARAMETERS): self.control.limit('parameters')
            def get(name=name):
                param = element.get_Parameter(getattr(DB.BuiltInParameter, name))
                if param is None: return dict(status='NOT_APPLICABLE', value=None)
                storage = str(param.StorageType)
                if not param.HasValue: return dict(status='UNAVAILABLE', value=None)
                getters = {'Double': param.AsDouble, 'Integer': param.AsInteger,
                           'String': param.AsString, 'ElementId': lambda: eid(param.AsElementId())}
                return dict(status='READ', storage_type=storage,
                            value=self.control.text(getters[storage]()), units='REVIT_INTERNAL')
            result[name] = self.read(key, name, get)
        return result

    def system(self, system):
        if system is None: return None
        ref = self.ref(system); key = ref['key']
        if key not in self.systems:
            ref['type_ref'] = self.read(key, 'system_type', lambda: self.ref(self.lookup(system.GetTypeId())))
            ref['classification'] = self.read(key, 'classification', lambda: str(system.SystemType))
            ref['member_keys'] = []
            ref['coverage'] = 'OBSERVED_CONNECTOR_AND_ELEMENT_REFERENCES_ONLY'
            self.systems[key] = ref
        return key

    def descriptor(self, connector, owner_key):
        row = dict(owner_key=owner_key)
        for field, getter in (
            ('api_id', lambda: str(connector.Id)),
            ('connector_type', lambda: str(connector.ConnectorType)),
            ('domain', lambda: str(connector.Domain)),
            ('origin_ft', lambda: xyz(connector.Origin)),
            ('coordinate_system', lambda: transform(connector.CoordinateSystem)),
            ('shape', lambda: str(connector.Shape)),
            ('direction', lambda: str(connector.Direction)),
            ('is_connected', lambda: bool(connector.IsConnected))):
            row[field] = self.read(owner_key, 'connector.' + field, getter)
        row['dimensions'] = {}
        shape = row['shape']
        attrs = ('Radius',) if shape == 'Round' else ('Width', 'Height') if shape in ('Rectangular', 'Oval') else ()
        for attr in attrs:
            row['dimensions'][attr.lower() + '_ft'] = self.read(owner_key, attr, lambda attr=attr: float(getattr(connector, attr)))
        row['key_method'] = 'API_ID' if row['api_id'] is not None else 'GEOMETRIC_FINGERPRINT'
        row['key'] = core.connector_key(owner_key, row)
        row['system_key'] = self.read(row['key'], 'system', lambda: self.system(connector.MEPSystem))
        if row['system_key']:
            members = self.systems[row['system_key']]['member_keys']
            if owner_key not in members: members.append(owner_key)
        return row

    def connectors(self, element, row):
        key = row['key']
        if isinstance(element, DB.MEPCurve):
            manager = self.read(key, 'connector_manager', lambda: element.ConnectorManager)
        elif isinstance(element, DB.FamilyInstance):
            model = self.read(key, 'mep_model', lambda: element.MEPModel)
            manager = self.read(key, 'connector_manager', lambda: model.ConnectorManager) if model else None
        else:
            self.issue(key, 'connector_manager', 'UNSUPPORTED')
            manager = None
        if manager is None: return None, []
        connectors = self.read(key, 'connectors', lambda: manager.Connectors)
        if connectors is None: return None, []
        result, edges = [], []
        for connector in self.control.items(connectors, 'connectors_per_element', 'connectors'):
            current = self.descriptor(connector, key)
            refs = None
            if self.control.counts.get('references', 0) >= self.control.limits['references']:
                self.control.limit('references')
            else:
                refs = self.read(current['key'], 'all_refs', lambda: connector.AllRefs)
            current['references'] = []
            current['open_port_assessment'] = 'UNKNOWN_ENGINEERING_INTENT'
            seen_refs = set()
            for other in self.control.items(refs or [], 'references_per_connector', 'references'):
                owner = self.read(current['key'], 'reference_owner', lambda: self.ref(other.Owner))
                if owner is None: continue
                other_row = self.descriptor(other, owner['key'])
                if other_row['key'] in seen_refs: continue
                seen_refs.add(other_row['key'])
                logical = current['connector_type'] == 'Logical' or other_row['connector_type'] == 'Logical'
                physical_types = ('End', 'Curve', 'Physical')
                physical_candidate = current['connector_type'] in physical_types and other_row['connector_type'] in physical_types
                connected = self.read(current['key'], 'is_connected_to', lambda: bool(connector.IsConnectedTo(other))) if physical_candidate and not logical else None
                reciprocal = self.read(current['key'], 'reciprocal', lambda: bool(other.IsConnectedTo(connector))) if connected else None
                kind = 'LOGICAL' if logical else 'PHYSICAL' if connected else 'UNKNOWN'
                current['references'].append(dict(owner=owner, connector_key=other_row['key'], kind=kind))
                a, b = sorted([current['key'], other_row['key']]) if kind == 'PHYSICAL' else (current['key'], other_row['key'])
                edges.append(dict(from_key=a, to_key=b, observed_from=current['key'],
                                  from_owner=key, to_owner=owner['key'], kind=kind,
                                  is_connected_to=connected, reciprocal=reciprocal, boundary=None))
            current['references'] = sorted(current['references'], key=core.canonical)
            result.append(current)
        return result, edges

    def element(self, element, frame):
        row = self.ref(element); key = row['key']
        row['class'] = element.GetType().Name
        row['category_id'] = self.read(key, 'category_id', lambda: eid(element.Category.Id))
        row['category'] = self.read(key, 'category', lambda: element.Category.Name)
        row['bbox'] = self.read(key, 'bbox', lambda: self.bbox(element))
        row['location'] = self.read(key, 'location', lambda: self.location(element))
        loc = row['location'] or {}
        line = loc.get('endpoints_ft') if loc.get('is_line') else None
        row['membership'] = core.classify((row['bbox'] or {}).get('corners_ft'), frame, line)
        if row['membership'] == 'UNKNOWN': self.issue(key, 'membership', 'UNAVAILABLE', 'SCOPE_MEMBERSHIP_UNKNOWN')
        if self.control.mode == 'FAST' or row['membership'] == 'OUTSIDE':
            row.update(family_type={}, parameters={}, system_key=None, dependencies=[],
                       detail_status='NOT_INSPECTED_FAST' if self.control.mode == 'FAST' else 'OUTSIDE_SCOPE')
            return row
        typ = self.read(key, 'type', lambda: self.lookup(element.GetTypeId()))
        row['family_type'] = dict(type_ref=self.ref(typ), family=None)
        if typ:
            row['family_type']['family'] = self.read(key, 'family', lambda: typ.FamilyName)
        row['parameters'] = self.params(element, key)
        row['system_key'] = self.read(key, 'system', lambda: self.system(element.MEPSystem)) if isinstance(element, DB.MEPCurve) else None
        row['pinned'] = self.read(key, 'pinned', lambda: bool(element.Pinned))
        row['level'] = self.read(key, 'level', lambda: self.related(key, 'level', element.LevelId))
        row['workset'] = self.read(key, 'workset', lambda: str(element.WorksetId.IntegerValue))
        row['design_option'] = self.read(key, 'design_option', lambda: self.ref(element.DesignOption))
        row['group'] = self.read(key, 'group', lambda: self.related(key, 'group', element.GroupId))
        row['assembly'] = self.read(key, 'assembly', lambda: self.related(key, 'assembly', element.AssemblyInstanceId))
        row['orientation'] = None
        row['dependencies'] = []
        if isinstance(element, DB.FamilyInstance):
            row['orientation'] = {}
            for name in ('Mirrored', 'HandFlipped', 'FacingFlipped'):
                row['orientation'][name] = self.read(key, name, lambda name=name: bool(getattr(element, name)))
            for name in ('HandOrientation', 'FacingOrientation'):
                row['orientation'][name] = self.read(key, name, lambda name=name: xyz(getattr(element, name)))
            row['orientation']['transform'] = self.read(key, 'transform', lambda: transform(element.GetTransform()))
            host = self.read(key, 'host', lambda: self.ref(element.Host))
            if host: row['dependencies'].append(dict(relation='HOST', element=host))
            subids = self.read(key, 'subcomponents', lambda: element.GetSubComponentIds())
            for ident in self.control.items(subids or [], 'dependencies'):
                row['dependencies'].append(dict(relation='SHARED_SUBCOMPONENT', element=self.related(key, 'subcomponent', ident)))
            self.issue(key, 'non_shared_nested_content', 'UNSUPPORTED', 'OPAQUE_FAMILY_CONTENT')
        for field in ('group', 'assembly'):
            if row[field]: row['dependencies'].append(dict(relation=field.upper(), element=row[field]))
        dependent_ids = self.read(key, 'dependents', lambda: element.GetDependentElements(None))
        for ident in self.control.items(dependent_ids or [], 'dependencies'):
            if eid(ident) != row['id']:
                row['dependencies'].append(dict(relation='OTHER', element=self.related(key, 'dependent', ident)))
        row['dependencies'] = sorted(row['dependencies'], key=core.canonical)
        return row

    def prepare_categories(self, enum_values=None):
        # Preserve the original conversion and supported-name order; isolate for tests.
        if enum_values is None: enum_values = DB.BuiltInCategory
        self.context.update(stage='category_setup', element_id=None, field=None)
        self.control.progress('Category setup / enum conversion before', total=len(CATEGORIES))
        categories = {}
        for name in CATEGORIES:
            self.context['field'] = name
            value = self.read('inventory', name, lambda name=name: str(int(getattr(enum_values, name))))
            if value: categories[value] = name
        self.context['field'] = None
        self.control.progress('Category setup / enum conversion after', len(CATEGORIES), len(CATEGORIES))
        return categories

    def category_filter(self, categories):
        if len(categories) != len(CATEGORIES) or set(categories.values()) != set(CATEGORIES):
            raise execution_control.Stopped('CATEGORY_FILTER_INCOMPLETE; no partial supported set allowed')
        self.candidate_checkpoint('native_category_list_before')
        values = builtin_category_list()
        for name in CATEGORIES:
            self.context['field'] = name
            value = getattr(DB.BuiltInCategory, name)
            if categories.get(str(int(value))) != name:
                raise execution_control.Stopped('CATEGORY_FILTER_IDENTITY_MISMATCH')
            values.Add(value)
        self.candidate_checkpoint('native_category_list_after; multicategory_filter_before')
        result = DB.ElementMulticategoryFilter(values)
        try:
            self.candidate_checkpoint('multicategory_filter_after')
            return result
        except Exception:
            result.Dispose()
            raise

    def candidate_checkpoint(self, operation):
        self.context.update(stage='candidate_collection_setup', element_id=None, field=operation)
        self.control.progress('Collect candidate elements / ' + operation, force=True)

    def collect(self, scope):
        self.control.progress('Resolve scope box', element_id=eid(scope.Id))
        self.context.update(stage='document_identity', element_id=eid(scope.Id), field=None)
        doc = self.doc
        identity = {}
        for field, getter in (
            ('title', lambda: doc.Title), ('path', lambda: doc.PathName),
            ('project_info_unique_id', lambda: doc.ProjectInformation.UniqueId),
            ('is_workshared', lambda: bool(doc.IsWorkshared)),
            ('is_modified', lambda: bool(doc.IsModified)),
            ('active_view_unique_id', lambda: doc.ActiveView.UniqueId),
            ('is_cloud', lambda: bool(doc.IsModelInCloud))):
            identity[field] = self.read('document', field, getter)
        identity['central_guid'] = None
        identity['central_guid_status'] = 'NOT_APPLICABLE_NOT_WORKSHARED'
        if identity['is_workshared']:
            identity['central_guid_status'] = 'UNAVAILABLE'
            central_path = self.read('document', 'central_model_path', lambda: doc.GetWorksharingCentralModelPath())
            if central_path is not None:
                server = self.read('document', 'central_path_server', lambda: bool(central_path.ServerPath))
                empty = self.read('document', 'central_path_empty', lambda: bool(central_path.Empty))
                if server is False and empty is False:
                    # The documented GUID contract only applies to Revit Server.
                    identity['central_guid_status'] = 'NOT_APPLICABLE_NON_SERVER_CENTRAL'
                elif server is True:
                    identity['central_guid'] = self.read('document', 'central_guid', lambda: str(doc.WorksharingCentralGUID))
                    if identity['central_guid']: identity['central_guid_status'] = 'AVAILABLE'
        identity['cloud_project_guid'] = None; identity['cloud_model_guid'] = None
        if identity['is_cloud']:
            modelpath = self.read('document', 'cloud_path', lambda: doc.GetCloudModelPath())
            if modelpath:
                identity['cloud_project_guid'] = self.read('document', 'cloud_project_guid', lambda: str(modelpath.GetProjectGUID()))
                identity['cloud_model_guid'] = self.read('document', 'cloud_model_guid', lambda: str(modelpath.GetModelGUID()))
        self.context.update(stage='document_identity_hash', field='document identity')
        self.doc_key = core.digest(dict((k, identity[k]) for k in ('path', 'project_info_unique_id', 'central_guid', 'cloud_project_guid', 'cloud_model_guid')))
        identity['key'] = self.doc_key
        identity['durable_comparison'] = 'UNRESOLVED'  # No external fixture/revision qualification supplied.
        if not identity['path']: self.issue(self.doc_key, 'path', 'AMBIGUOUS', 'UNSAVED_DOCUMENT')
        self.context.update(stage='scope_geometry', field=None)
        source = dict(scope_box=self.ref(scope), bbox=self.read('scope', 'bbox', lambda: self.bbox(scope)),
                      geometry=self.read('scope', 'geometry', lambda: self.geometry(scope)),
                      membership_method='VALIDATED_WIREFRAME_CONSERVATIVE_BBOX_AND_LINEAR_CURVE', element_keys=[])
        frame = core.scope_frame(source['geometry'] or [])
        source['frame'] = frame
        if frame is None: self.issue('scope', 'frame', 'UNSUPPORTED', 'SCOPE_FRAME_UNAVAILABLE')
        self.issue('prediction', 'frame', 'UNAVAILABLE', 'MIRROR_FRAME_UNCONFIRMED')
        categories = self.prepare_categories()
        rows, connectors, edges, pipes, excluded = [], [], [], [], {}
        self.control.progress('Collect candidate elements')
        candidates = []
        seen_ids, seen_keys = set(), set()
        duplicate_count = 0
        identity_missing = False
        collector = None
        native_filter = None
        bounded = None
        try:
            native_filter = self.category_filter(categories)
            self.candidate_checkpoint('collector_constructor_before')
            collector = DB.FilteredElementCollector(doc)
            self.candidate_checkpoint('collector_constructor_after; instance_filter_before')
            collector = collector.WhereElementIsNotElementType()
            self.candidate_checkpoint('instance_filter_after; category_filter_apply_before')
            collector = collector.WherePasses(native_filter)
            self.candidate_checkpoint('category_filter_apply_after; bounded_iterator_create_before')
            bounded = self.control.element_items(collector, 'scanned_elements', checkpoint=self.candidate_checkpoint)
            self.candidate_checkpoint('bounded_iterator_created; first_iteration_before')
            for element in bounded:
                self.context.update(stage='candidate_collection', element_id=eid(element.Id), field=None)
                self.control.progress('Collect supported-category instances', self.control.counts['scanned_elements'], element_id=eid(element.Id))
                ident = eid(element.Id)
                if ident in seen_ids:
                    duplicate_count += 1
                    self.issue(ident, 'identity', 'AMBIGUOUS', 'DUPLICATE_ELEMENT_ID')
                    continue
                seen_ids.add(ident)
                cat = self.read(eid(element.Id), 'category', lambda: element.Category, optional=True)
                category_id = self.read(eid(element.Id), 'category_id', lambda: eid(cat.Id)) if cat is not None else None
                if category_id not in categories:
                    self.issue(ident, 'category', 'UNAVAILABLE', 'FILTERED_CATEGORY_UNVERIFIED')
                    excluded_key = category_id or 'NO_CATEGORY_OR_READ_ERROR'
                    entry = excluded.setdefault(excluded_key, dict(category_id=category_id, count=0,
                        status='NOT_IN_SUPPORTED_CATEGORY_SET' if category_id else 'NO_CATEGORY_OR_READ_ERROR'))
                    entry['count'] += 1
                    continue
                self.context.update(stage='scope_classification', element_id=eid(element.Id), field=None)
                row = self.read(eid(element.Id), 'element_record', lambda: self.element(element, frame))
                if row is None:
                    row = self.ref(element)
                    row.update(membership='UNKNOWN', collection_status='READ_ERROR', location=None,
                               parameters={}, system_key=None)
                row.update(inclusion_reason='SCOPE_FIRST_BOUNDED_DOCUMENT_MEP_INVENTORY', connector_count=None,
                    connector_scan='NOT_INSPECTED_FAST' if self.control.mode == 'FAST' else 'OUTSIDE_SCOPE_NOT_SCANNED')
                if not row.get('unique_id') or not row.get('id'):
                    identity_missing = True
                if row['key'] in seen_keys:
                    duplicate_count += 1
                    self.issue(row['key'], 'identity', 'AMBIGUOUS', 'DUPLICATE_ELEMENT_KEY')
                    continue
                seen_keys.add(row['key'])
                candidates.append((element, row))
        finally:
            try:
                if bounded is not None: bounded.close()
            finally:
                try:
                    if collector is not None: collector.Dispose()
                finally:
                    if native_filter is not None: native_filter.Dispose()
        # Classification is bounded by scanned_elements. Stable identity decides which
        # details survive a cap, independently of collector enumeration order.
        self.control.progress('Classify candidates / apply scope budgets', len(candidates), len(candidates))
        candidates.sort(key=lambda pair: pair[1]['key'])
        ledger = []
        memberships = dict(INSIDE=0, CROSSING=0, OUTSIDE=0, UNKNOWN=0)
        selected = []
        used = dict(candidates=0, unknown_candidates=0)
        for element, row in candidates:
            self.control.check()
            membership = row['membership']
            memberships[membership] += 1
            detail = False
            if membership != 'OUTSIDE':
                budget = 'unknown_candidates' if membership == 'UNKNOWN' else 'candidates'
                if (self.control.mode == 'FAST' and budget == 'candidates') or used[budget] < self.control.limits[budget]:
                    used[budget] += 1
                    detail = True
                    rows.append(row)
                    source['element_keys'].append(row['key'])
                    selected.append((element, row))
                else:
                    self.control.limit(budget)
            ledger.append(dict(key=row['key'], id=row['id'], category_id=row.get('category_id'),
                               membership=membership, detail_retained=detail))
        self.control.counts.update(used)
        del candidates
        self.control.progress('Inspect connector topology' + (' (skipped FAST)' if self.control.mode == 'FAST' else ''), total=len(selected))
        if self.control.mode == 'FULL':
            for index, (element, row) in enumerate(selected):
                self.context.update(stage='connectors', element_id=eid(element.Id), field=None)
                self.control.progress('Inspect connector topology', index, len(selected), eid(element.Id))
                if self.control.counts.get('connectors', 0) >= self.control.limits['connectors']:
                    self.control.limit('connectors'); break
                cs, es = self.connectors(element, row)
                row['connector_count'] = len(cs) if cs is not None else None
                row['connector_scan'] = 'BOUNDED' if cs is not None else 'UNAVAILABLE'
                row['connector_keys'] = sorted(c['key'] for c in cs or [])
                connectors.extend(cs or []); edges.extend(es)
        self.control.progress('Inspect pipe slopes', total=len(selected))
        for index, (element, row) in enumerate(selected):
            if index % min(500, self.control.limits['candidates']) == 0:
                self.control.progress('FAST detail batch boundary' if self.control.mode == 'FAST' else 'Detail boundary', index, len(selected), eid(element.Id), force=True)
            self.control.progress('Inspect pipe slopes', index, len(selected), eid(element.Id))
            self.context.update(stage='pipe_slopes', element_id=eid(element.Id), field=None)
            if categories.get(row.get('category_id')) in ('OST_PipeCurves', 'OST_FlexPipeCurves'):
                loc = row['location'] or {}
                measurement = core.slope(loc.get('endpoints_ft'), loc.get('is_line', False))
                measurement.update(element_key=row['key'], length_ft=loc.get('length_ft'),
                    revit_slope_parameter=row['parameters'].get('RBS_PIPE_SLOPE'), system_key=row['system_key'])
                pipes.append(measurement)
        self.context.update(stage='connector_summary', element_id=None, field=None)
        membership = dict((r['key'], r['membership']) for r in rows)
        seen = set()
        for c in connectors:
            if c['key'] in seen: self.issue(c['key'], 'key', 'AMBIGUOUS', 'AMBIGUOUS_CONNECTOR_KEY')
            seen.add(c['key'])
            c['boundary_proximity'] = 'UNKNOWN'
            if frame and c['origin_ft']:
                local = core.local(c['origin_ft'], frame)
                c['boundary_proximity'] = 'NEAR_SCOPE_FACE' if any(abs(x) < 1e-4 or abs(x-l) < 1e-4 for x, l in zip(local, frame['lengths_ft'])) else 'NOT_NEAR_SCOPE_FACE'
        for edge in edges:
            values = [membership.get(edge[k]) for k in ('from_owner', 'to_owner')]
            edge['boundary'] = True if 'OUTSIDE' in values or 'CROSSING' in values else False if values == ['INSIDE', 'INSIDE'] else None
        # Preserve directional observations while deduplicating physical adjacency.
        grouped = {}
        for e in edges:
            key = (e['kind'], e['from_key'], e['to_key'])
            grouped.setdefault(key, []).append(e)
        edges = [dict(kind=k[0], from_key=k[1], to_key=k[2], observations=sorted(v, key=core.canonical)) for k, v in grouped.items()]
        for system in self.systems.values(): system['member_keys'].sort()
        counts = {}
        for row in rows:
            key = row.get('category_id', 'UNKNOWN'); counts[key] = counts.get(key, 0) + 1
        candidates = [r for r in rows if r['membership'] != 'OUTSIDE']
        summary = dict(physical_candidates=len(candidates), inventoried_elements=len(rows),
                       connector_bearing_elements=sum(bool(r.get('connector_count')) for r in candidates),
                       connectors=len(connectors), connected=sum(c['is_connected'] is True for c in connectors),
                       unconnected=sum(c['is_connected'] is False for c in connectors),
                       connection_unknown=sum(c['is_connected'] is None for c in connectors),
                       boundary_connectors=sum(c['boundary_proximity']=='NEAR_SCOPE_FACE' for c in connectors),
                       physical_boundary_edges=sum(e['kind']=='PHYSICAL' and any(o['boundary'] is True for o in e['observations']) for e in edges),
                       pipes=len(pipes), measured_slopes=sum(p['status']=='MEASURED' for p in pipes),
                       vertical_pipes=sum(p['status']=='VERTICAL' for p in pipes),
                       unsupported_categories=None,
                       missing_family_type=sum(not (r.get('family_type') or {}).get('type_ref') or not (r.get('family_type') or {}).get('family') for r in candidates))
        if self.control.mode == 'FAST':
            for name in ('connector_bearing_elements', 'connectors', 'connected', 'unconnected',
                         'connection_unknown', 'boundary_connectors', 'physical_boundary_edges', 'missing_family_type'):
                summary[name] = None
        self.context.update(stage='coordinates', element_id=None, field=None)
        coordinates = dict(space='REVIT_INTERNAL', length_unit='ft', angle_unit='rad',
                           project_location=self.read('coordinates', 'project_location', lambda: self.ref(doc.ActiveProjectLocation)),
                           shared_transform=self.read('coordinates', 'shared_transform', lambda: transform(doc.ActiveProjectLocation.GetTotalTransform())),
                           architectural_links=[], reference_points=[])
        link_collector = DB.FilteredElementCollector(doc).OfClass(DB.RevitLinkInstance) if self.control.mode == 'FULL' else None
        try:
            for link in self.control.items(link_collector or [], 'links'):
                self.context.update(stage='link_coordinates', element_id=eid(link.Id), field=None)
                coordinates['architectural_links'].append(dict(instance=self.ref(link), transform=self.read(eid(link.Id), 'link_transform', lambda: transform(link.GetTotalTransform()))))
        finally:
            if link_collector is not None: link_collector.Dispose()
        self.context.update(stage='coordinate_sort', element_id=None, field='architectural_links')
        coordinates['architectural_links'].sort(key=core.canonical)
        self.issue('coverage', 'dependencies', 'UNSUPPORTED', 'DEPENDENCY_CLOSURE_UNRESOLVED')
        risks = [dict(code='MIRROR_FRAME_UNCONFIRMED', confidence='UNCONFIRMED', blocking=True),
                 dict(code='SLOPE_RULES_UNCONFIRMED', confidence='UNCONFIRMED', blocking=True),
                 dict(code='OPEN_PORT_INTENT_UNCONFIRMED', confidence='UNCONFIRMED', blocking=True),
                 dict(code='DEPENDENCY_CLOSURE_UNRESOLVED', confidence='STATIC_RISK', blocking=True)]
        for connector in connectors:
            if connector['is_connected'] is False:
                risks.append(dict(code='OPEN_CONNECTOR_REQUIRES_ENGINEERING_REVIEW',
                    subject_keys=[connector['key']], confidence='OBSERVED_SOURCE_CONDITION',
                    blocking=False, confirmed_defect=False))
        summary['classifications'] = memberships
        summary['unresolved_issues'] = len(self.issues)
        summary['api_extraction_errors'] = sum(i['reason']=='READ_ERROR' for i in self.issues)
        summary['predicted_mirror_risks'] = len(risks)
        summary['issue_counts_by_reason'] = {}
        for issue in self.issues:
            reason = issue['reason']
            summary['issue_counts_by_reason'][reason] = summary['issue_counts_by_reason'].get(reason, 0) + 1
        source['element_keys'].sort()
        self.control.progress('Calculate mirror preview (unapproved; no transform applied)')
        preview = core.prediction()
        preview['source_frame'] = frame
        self.context.update(stage='snapshot_finalize', element_id=None, field='snapshot')
        self.control.check()
        snapshot = core.finalize(dict(document=identity, coordinates=coordinates, source=source,
            target=dict(status='NOT_SELECTED', scope_box=None, element_keys=[], matches=[]),
            prediction=preview, confirmed_defects=[], policy=dict(approval_reference=None, allowed_open_ports=[], slope_rules=[],
                position_tolerance_ft=None, angle_tolerance_rad=None, slope_tolerance_ratio=None,
                inclusion_rules=list(CATEGORIES)),
            coverage=dict(complete=False, candidate_count=len(candidates), element_count=len(rows),
                counts_by_category=sorted([dict(category_id=k, count=v) for k, v in counts.items()], key=core.canonical),
                excluded=None, filtered_category_anomalies=sorted(excluded.values(), key=core.canonical), limits_reached=[],
                opaque_dependencies=['NON_SHARED_FAMILY_CONTENT', 'DEPENDENCY_CLOSURE_NOT_PROVEN']),
            elements=rows, connectors=connectors, edges=edges, systems=list(self.systems.values()),
            pipes=pipes, issues=self.issues, predicted_risks=risks, summary=summary))

        snapshot['coverage'].update(self.control.coverage())
        snapshot['coverage']['excluded_category_inventory'] = 'NOT_INSPECTED_BY_FILTERED_COLLECTION'
        snapshot['coverage']['scanned_elements_basis'] = 'SUPPORTED_CATEGORY_INSTANCES_INSPECTED'
        snapshot['coverage']['collector_filter'] = dict(kind='ElementMulticategoryFilter',
            element_types=False, supported_categories=list(CATEGORIES), category_ids=categories)
        snapshot['coverage']['duplicate_observations'] = duplicate_count
        snapshot['coverage']['classification_ledger'] = ledger
        snapshot['coverage']['classification_counts'] = memberships
        snapshot['coverage']['scan_exhausted'] = bool(bounded is not None and bounded.exhausted)
        blockers = list(self.control.truncated)
        if not snapshot['coverage']['scan_exhausted']: blockers.append('COLLECTOR_EXHAUSTION_UNPROVEN')
        if frame is None: blockers.append('SCOPE_FRAME_UNAVAILABLE')
        if memberships['UNKNOWN']: blockers.append('UNKNOWN_MEMBERSHIP')
        if summary['api_extraction_errors']: blockers.append('API_READ_ERRORS')
        if excluded: blockers.append('FILTERED_CATEGORY_UNVERIFIED')
        if duplicate_count: blockers.append('DUPLICATE_IDENTITIES')
        if (identity_missing or not identity['path'] or not identity['project_info_unique_id']
                or not source['scope_box'].get('unique_id')):
            blockers.append('IDENTITY_UNAVAILABLE')
        snapshot['coverage']['inventory_blockers'] = sorted(set(blockers))
        snapshot['coverage']['classification_inventory_complete'] = not [
            value for value in blockers if value not in ('candidates', 'unknown_candidates')]
        snapshot['coverage']['scope_inventory_complete'] = not blockers
        snapshot['coverage']['detail_coverage_complete'] = not blockers
        snapshot['coverage']['pipe_slope_detail_coverage_complete'] = not blockers
        snapshot['coverage']['detail_batch_size'] = min(500, self.control.limits['candidates'])
        snapshot['coverage']['candidates_limit_basis'] = 'PER_FAST_DETAIL_BATCH' if self.control.mode == 'FAST' else 'TOTAL_RETAINED'
        snapshot['coverage']['snapshot_identity'] = 'REQUIRES_SAVED_SOURCE_QUALIFICATION'
        snapshot['coverage']['mirror_readiness'] = 'UNRESOLVED'
        snapshot['coverage']['expected_absences'] = dict(self.expected_absences)
        snapshot['coverage']['fast_omissions'] = (dict(
            connector_topology=dict(status='NOT_INSPECTED_FAST', elements=len(selected)),
            detailed_parameters_family_system_dependencies=dict(status='NOT_INSPECTED_FAST', elements=len(selected)),
            architectural_links=dict(status='NOT_INSPECTED_FAST')) if self.control.mode == 'FAST' else {})
        snapshot['coverage']['scope_inventory_basis'] = 'SUPPORTED_18_CATEGORIES_ONLY; conservative bbox/linear-curve classification'
        snapshot['coverage']['detail_and_slope_basis'] = 'RETAINED_NON_OUTSIDE_RECORDS_ONLY; see classification ledger and limits'
        snapshot['coverage']['baseline_comparison'] = 'PENDING_EXACT_DOCUMENT_AND_SNAPSHOT_EVIDENCE'
        snapshot['elements'].sort(key=lambda row: row['key'])
        snapshot['coverage']['architectural_links'] = 'NOT_INSPECTED_FAST' if self.control.mode == 'FAST' else 'BOUNDED'
        self.control.check()
        return snapshot
