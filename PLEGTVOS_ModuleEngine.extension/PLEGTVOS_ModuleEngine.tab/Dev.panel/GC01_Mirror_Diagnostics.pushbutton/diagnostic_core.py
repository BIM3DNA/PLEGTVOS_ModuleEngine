# -*- coding: utf-8 -*-
"""Pure read-only diagnostic mathematics and serialization (Python 2.7+)."""
import hashlib
import json
import math

VERSION = "1.1.0"
SCHEMA = "plegtvos.gc01_mirror_diagnostic/1"
EPS = 1e-7


def sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def norm(v):
    return math.sqrt(dot(v, v))


def finite(v):
    return v is not None and len(v) == 3 and all(not math.isnan(x) and not math.isinf(x) for x in v)


def valid_selection(categories, scope_category):
    return len(categories) == 1 and categories[0] == scope_category


def scope_frame(segments):
    """Accept only a complete rectangular 12-edge wireframe; axes aren't L/R approval."""
    if len(segments) != 12 or any(len(s) != 2 for s in segments) or any(not finite(p) for s in segments for p in s):
        return None
    vertices = sorted(set(tuple(round(x, 7) for x in p) for s in segments for p in s))
    if len(vertices) != 8:
        return None
    origin = list(vertices[0])
    near = lambda a, b: norm(sub(a, b)) < 1e-6
    neighbors = []
    for a, b in segments:
        if near(a, origin): neighbors.append(b)
        elif near(b, origin): neighbors.append(a)
    if len(neighbors) != 3:
        return None
    vectors = sorted([sub(p, origin) for p in neighbors])
    lengths = [norm(v) for v in vectors]
    if min(lengths) < EPS:
        return None
    axes = [[x / length for x in v] for v, length in zip(vectors, lengths)]
    if any(abs(dot(axes[i], axes[j])) > 1e-6 for i, j in [(0, 1), (0, 2), (1, 2)]):
        return None
    expected = []
    for i in (0, 1):
        for j in (0, 1):
            for k in (0, 1):
                expected.append([origin[n] + i*vectors[0][n] + j*vectors[1][n] + k*vectors[2][n] for n in range(3)])
    if not all(any(near(p, q) for q in vertices) for p in expected):
        return None
    edges = set()
    for a, b in segments:
        ids = [next(i for i, p in enumerate(expected) if near(p, q)) for q in (a, b)]
        if bin(ids[0] ^ ids[1]).count('1') != 1:
            return None
        edges.add(tuple(sorted(ids)))
    if len(edges) != 12:
        return None
    return {"origin_ft": origin, "axes": axes, "lengths_ft": lengths,
            "derivation": "VALIDATED_RECTANGULAR_WIREFRAME", "approved": False}


def local(p, frame):
    return [dot(sub(p, frame["origin_ft"]), a) for a in frame["axes"]]


def point_inside(p, frame):
    return all(-EPS <= x <= length + EPS for x, length in zip(local(p, frame), frame["lengths_ft"]))


def classify(corners, frame, line=None):
    if frame is None or not corners or not all(finite(p) for p in corners):
        return "UNKNOWN"
    pts = [local(p, frame) for p in corners]
    if any(max(p[i] for p in pts) < -EPS or min(p[i] for p in pts) > frame["lengths_ft"][i] + EPS for i in range(3)):
        return "OUTSIDE"
    if all(point_inside(p, frame) for p in corners):
        return "INSIDE"
    # A bounded straight location curve crossing the box provides crossing evidence.
    if line and len(line) == 2 and all(finite(p) for p in line):
        a, b = [local(p, frame) for p in line]
        low, high = 0.0, 1.0
        for i in range(3):
            d = b[i] - a[i]
            if abs(d) < EPS:
                if a[i] < 0 or a[i] > frame["lengths_ft"][i]: return "UNKNOWN"
            else:
                t0, t1 = sorted([-a[i]/d, (frame["lengths_ft"][i]-a[i])/d])
                low, high = max(low, t0), min(high, t1)
        if low < high and (not point_inside(line[0], frame) or not point_inside(line[1], frame)):
            return "CROSSING"
    return "UNKNOWN"  # Intersecting AABBs alone cannot prove physical crossing.


def slope(endpoints, linear=True):
    result = {"endpoints_ft": endpoints, "endpoint_order": "REVIT_CURVE_0_TO_1",
              "flow_status": "UNKNOWN", "compliance": "UNKNOWN", "upstream_endpoint": None,
              "horizontal_run_ft": None, "delta_z_ft": None, "slope_signed_ratio": None,
              "slope_abs_ratio": None, "start_elevation_ft": None, "end_elevation_ft": None,
              "chord_length_ft": None, "status": "UNAVAILABLE"}
    if not endpoints or len(endpoints) != 2 or not all(finite(p) for p in endpoints): return result
    a, b = endpoints
    d = sub(b, a); horizontal = math.sqrt(d[0]**2 + d[1]**2)
    result.update(start_elevation_ft=a[2], end_elevation_ft=b[2], delta_z_ft=d[2],
                  chord_length_ft=norm(d), horizontal_run_ft=horizontal)
    if not linear:
        result["status"] = "UNSUPPORTED_CURVE"
    elif horizontal < EPS:
        result["status"] = "DEGENERATE" if norm(d) < EPS else "VERTICAL"
    else:
        result.update(status="MEASURED", slope_signed_ratio=d[2]/horizontal,
                      slope_abs_ratio=abs(d[2])/horizontal)
    return result


def reflect(vector, normal, origin=None):
    if not finite(vector) or not finite(normal) or abs(norm(normal)-1) > 1e-9:
        raise ValueError("Finite vector and unit normal required")
    if origin is not None and not finite(origin):
        raise ValueError('Finite plane origin required')
    distance = dot(sub(vector, origin) if origin is not None else vector, normal)
    return [vector[i]-2*distance*normal[i] for i in range(3)]



def map_frame(value, source, target, direction=False):
    """Pure rigid map Ttarget * inverse(Tsource); accepts orthonormal frames only."""
    for frame in (source, target):
        axes = frame['axes']
        if len(axes) != 3 or not finite(frame['origin_ft']):
            raise ValueError('Invalid frame')
        if any(not finite(a) or abs(norm(a)-1) > 1e-9 for a in axes):
            raise ValueError('Invalid frame axes')
        if any(abs(dot(axes[i],axes[j])) > 1e-9 for i,j in ((0,1),(0,2),(1,2))):
            raise ValueError('Nonorthogonal frame')
    if not finite(value): raise ValueError('Invalid value')
    relative = value if direction else sub(value, source['origin_ft'])
    coordinates = [dot(relative, axis) for axis in source['axes']]
    return [sum(coordinates[j]*target['axes'][j][i] for j in range(3)) +
            (0 if direction else target['origin_ft'][i]) for i in range(3)]


def prediction():
    return {"status": "MIRROR_FRAME_UNCONFIRMED", "plane": None, "source_frame": None,
            "target_frame": None, "matrix4x4_row_major": None, "determinant": None,
            "expected_points": [], "expected_connectors": [],
            "unsupported_transformations": ["UNAPPROVED_FRAME", "TARGET_NOT_SELECTED"]}


def normalized(value):
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value): raise ValueError("Non-finite JSON value")
        return round(value, 12) if value else 0.0
    if isinstance(value, dict): return dict((k, normalized(v)) for k, v in value.items())
    if isinstance(value, (list, tuple)): return [normalized(v) for v in value]
    return value


def canonical(value):
    return json.dumps(normalized(value), sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def connector_key(owner, descriptor):
    if descriptor.get("api_id") is not None:
        return owner + '/connector/' + str(descriptor["api_id"])
    fields = dict((k, descriptor.get(k)) for k in ('connector_type', 'domain', 'origin_ft', 'coordinate_system'))
    return owner + '/fingerprint/' + digest(fields)


def finalize(snapshot):
    for field in ('elements', 'connectors', 'edges', 'systems', 'issues', 'predicted_risks', 'pipes'):
        snapshot[field] = sorted(snapshot.get(field, []), key=canonical)
    return normalized(snapshot)
