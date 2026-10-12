# -*- coding: utf-8 -*-
"""Revit 2025 read adapter. No button imports and no model-writing operations."""
from Autodesk.Revit import DB
import diagnostic_core as core
import failure_diagnostics
import sys

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


class Reader(object):
    def __init__(self, doc):
        self.doc = doc
        self.issues = []
        self.systems = {}
        self.doc_key = 'UNRESOLVED_DOCUMENT'
        self.context = dict(stage='initialization', element_id=None, field=None)
        self.unicode_failures = []

    def issue(self, subject, field, reason='UNAVAILABLE', code=None):
        self.issues.append(dict(code=code or reason, severity='UNRESOLVED',
                                subject_key=subject, field=field, reason=reason,
                                evidence_kind='OBSERVED_READ', message=reason))

    def read(self, subject, field, getter):
        previous_field = self.context['field']
        self.context['field'] = field
        try:
            value = getter()
            if value is None:
                self.issue(subject, field)
            return value
        except Exception as error:
            if isinstance(error, UnicodeError):
                self.unicode_failures.extend(failure_diagnostics.failure_lines(sys.exc_info(), dict(self.context)))
            self.issue(subject, field, 'READ_ERROR')
            self.issues[-1]['exception_type'] = type(error).__name__
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

    def related(self, owner, field, ident):
        if ident is None or eid(ident) == '-1': return None
        element = self.read(owner, field, lambda: self.doc.GetElement(ident))
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
        for obj in geometry:
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
        for name in PARAMETERS:
            def get(name=name):
                param = element.get_Parameter(getattr(DB.BuiltInParameter, name))
                if param is None: return dict(status='NOT_APPLICABLE', value=None)
                storage = str(param.StorageType)
                if not param.HasValue: return dict(status='UNAVAILABLE', value=None)
                getters = {'Double': param.AsDouble, 'Integer': param.AsInteger,
                           'String': param.AsString, 'ElementId': lambda: eid(param.AsElementId())}
                return dict(status='READ', storage_type=storage,
                            value=getters[storage](), units='REVIT_INTERNAL')
            result[name] = self.read(key, name, get)
        return result

    def system(self, system):
        if system is None: return None
        ref = self.ref(system); key = ref['key']
        if key not in self.systems:
            ref['type_ref'] = self.read(key, 'system_type', lambda: self.ref(self.doc.GetElement(system.GetTypeId())))
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
        connectors = self.read(key, 'connectors', lambda: list(manager.Connectors))
        if connectors is None: return None, []
        result, edges = [], []
        for connector in connectors:
            current = self.descriptor(connector, key)
            refs = self.read(current['key'], 'all_refs', lambda: list(connector.AllRefs))
            current['references'] = []
            current['open_port_assessment'] = 'UNKNOWN_ENGINEERING_INTENT'
            for other in refs or []:
                owner = self.read(current['key'], 'reference_owner', lambda: self.ref(other.Owner))
                if owner is None: continue
                other_row = self.descriptor(other, owner['key'])
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
        typ = self.read(key, 'type', lambda: self.doc.GetElement(element.GetTypeId()))
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
            subids = self.read(key, 'subcomponents', lambda: list(element.GetSubComponentIds()))
            for ident in subids or []:
                row['dependencies'].append(dict(relation='SHARED_SUBCOMPONENT', element=self.related(key, 'subcomponent', ident)))
            self.issue(key, 'non_shared_nested_content', 'UNSUPPORTED', 'OPAQUE_FAMILY_CONTENT')
        for field in ('group', 'assembly'):
            if row[field]: row['dependencies'].append(dict(relation=field.upper(), element=row[field]))
        dependent_ids = self.read(key, 'dependents', lambda: list(element.GetDependentElements(None)))
        for ident in dependent_ids or []:
            if eid(ident) != row['id']:
                row['dependencies'].append(dict(relation='OTHER', element=self.related(key, 'dependent', ident)))
        row['dependencies'] = sorted(row['dependencies'], key=core.canonical)
        return row

    def collect(self, scope):
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
        identity['central_guid'] = self.read('document', 'central_guid', lambda: str(doc.WorksharingCentralGUID)) if identity['is_workshared'] else None
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
        self.context.update(stage='category_setup', element_id=None, field=None)
        categories = {}
        for name in CATEGORIES:
            value = self.read('inventory', name, lambda name=name: str(int(getattr(DB.BuiltInCategory, name))))
            if value: categories[value] = name
        rows, connectors, edges, pipes, excluded = [], [], [], [], {}
        # Document-wide model collector; never active-view restricted.
        for element in DB.FilteredElementCollector(doc).WhereElementIsNotElementType():
            self.context.update(stage='element_inventory', element_id=eid(element.Id), field=None)
            cat = self.read('inventory', 'category', lambda: element.Category)
            if cat is None: continue
            category_id = eid(cat.Id)
            if category_id not in categories:
                # Unsupported model categories retained in a count ledger, not represented as scanned MEP.
                if cat.CategoryType == DB.CategoryType.Model:
                    entry = excluded.setdefault(category_id, dict(category_id=category_id, name=cat.Name, count=0, reason='OUTSIDE_SUPPORTED_MEP_CATEGORY_SET'))
                    entry['count'] += 1
                continue
            row = self.read(eid(element.Id), 'element_record', lambda: self.element(element, frame))
            if row is None:
                row = self.ref(element); row.update(membership='UNKNOWN', collection_status='READ_ERROR')
                source['element_keys'].append(row['key'])
                rows.append(row); continue
            row['inclusion_reason'] = 'DOCUMENT_WIDE_PHYSICAL_MEP_CATEGORY'
            rows.append(row)
            if row['membership'] == 'OUTSIDE':
                row['connector_count'] = None; row['connector_scan'] = 'OUTSIDE_SCOPE_NOT_SCANNED'
                continue
            source['element_keys'].append(row['key'])
            self.context.update(stage='connectors', field=None)
            cs, es = self.connectors(element, row)
            row['connector_count'] = len(cs) if cs is not None else None
            row['connector_scan'] = 'COLLECTED' if cs is not None else 'UNAVAILABLE'
            row['connector_keys'] = sorted(c['key'] for c in cs or [])
            connectors.extend(cs or []); edges.extend(es)
            if categories[category_id] in ('OST_PipeCurves', 'OST_FlexPipeCurves'):
                self.context.update(stage='pipe_slopes', field=None)
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
                       unsupported_categories=len(excluded),
                       missing_family_type=sum(not (r.get('family_type') or {}).get('type_ref') or not (r.get('family_type') or {}).get('family') for r in candidates))
        self.context.update(stage='coordinates', element_id=None, field=None)
        coordinates = dict(space='REVIT_INTERNAL', length_unit='ft', angle_unit='rad',
                           project_location=self.read('coordinates', 'project_location', lambda: self.ref(doc.ActiveProjectLocation)),
                           shared_transform=self.read('coordinates', 'shared_transform', lambda: transform(doc.ActiveProjectLocation.GetTotalTransform())),
                           architectural_links=[], reference_points=[])
        for link in DB.FilteredElementCollector(doc).OfClass(DB.RevitLinkInstance):
            self.context.update(stage='link_coordinates', element_id=eid(link.Id), field=None)
            coordinates['architectural_links'].append(dict(instance=self.ref(link), transform=self.read(eid(link.Id), 'link_transform', lambda: transform(link.GetTotalTransform()))))
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
        summary['unresolved_issues'] = len(self.issues)
        summary['api_extraction_errors'] = sum(i['reason']=='READ_ERROR' for i in self.issues)
        summary['predicted_mirror_risks'] = len(risks)
        source['element_keys'].sort()
        preview = core.prediction()
        preview['source_frame'] = frame
        self.context.update(stage='snapshot_finalize', element_id=None, field='snapshot')
        return core.finalize(dict(document=identity, coordinates=coordinates, source=source,
            target=dict(status='NOT_SELECTED', scope_box=None, element_keys=[], matches=[]),
            prediction=preview, confirmed_defects=[], policy=dict(approval_reference=None, allowed_open_ports=[], slope_rules=[],
                position_tolerance_ft=None, angle_tolerance_rad=None, slope_tolerance_ratio=None,
                inclusion_rules=list(CATEGORIES)),
            coverage=dict(complete=False, candidate_count=len(candidates), element_count=len(rows),
                counts_by_category=sorted([dict(category_id=k, count=v) for k, v in counts.items()], key=core.canonical),
                excluded=sorted(excluded.values(), key=core.canonical), limits_reached=[],
                opaque_dependencies=['NON_SHARED_FAMILY_CONTENT', 'DEPENDENCY_CLOSURE_NOT_PROVEN']),
            elements=rows, connectors=connectors, edges=edges, systems=list(self.systems.values()),
            pipes=pipes, issues=self.issues, predicted_risks=risks, summary=summary))
