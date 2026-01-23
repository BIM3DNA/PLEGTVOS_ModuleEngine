# -*- coding: utf-8 -*-
__title__ = "slope_solver.py"
__doc__ = """Version = 2.0
Date    = 17.01.2026
________________________________________________________________
Description:
Apply configured slopes to PIPE CURVES inside a picked scope box,
based on Pipe Type + MEPSystem.Name rules.

Rules (current):
- Pipe Type: NLRS_52_PI_PVC U3 Grijs OD_Dyka
  - MEPSystem contains "51 - VWA"  -> 7.5/1000  (0.0075)
  - MEPSystem contains "50 - HWA"  -> 5.0/1000  (0.0050)

Notes:
- Uses per-element transactions for MEP robustness.
- Uses FailurePreprocessor to rollback on non-warning failures.
- Calls doc.Regenerate() after applying slope and before Commit().
________________________________________________________________
Author: Emin Avdovic
"""

# ==================================================
# Imports (keep minimal, but compatible with your environment)
# ==================================================
from Autodesk.Revit.DB import (
    BuiltInCategory,
    BuiltInParameter,
    BoundingBoxIntersectsFilter,
    ElementId,
    FailureProcessingResult,
    FailureSeverity,
    FilteredElementCollector,
    IFailuresPreprocessor,
    Line,
    LocationCurve,
    Outline,
    Transaction,
    TransactionGroup,
    XYZ,
)
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
from Autodesk.Revit.Exceptions import OperationCanceledException
from collections import defaultdict

# from System.Collections.Generic import List as ClrList

import math
import re

# one-time diagnostics
_SLOPE_DUMPED = False
_SLOPE_GEOM_DEBUG_DONE = False

# ==================================================
# Revit Document Setup
# ==================================================
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

# ==================================================
# Config
# ==================================================
PIPE_TYPE_ID = 926396
DEBUG_NO_ROLLBACK = False
USE_SCOPEBOX_Z = False  # False = XY-only, True = strict 3D (Z extents)
HORIZ_MIN_FT = 10.0 / 304.8  # 10 mm

# Match by substring (case-insensitive) within MEPSystem.Name
# SYS_SLOPE_RULES = [
#     ("51 - VWA 2", 0.0075),  # 5%
#     ("50 - HWA 4", 0.005),  # 7.5%
# ]
SLOPE_VWA = 0.0075  # 7.5/1000
SLOPE_HWA = 0.0050  # 5.0/1000

# Validation tolerance (ratio units, e.g. 0.0075 == 7.5/1000)
SLOPE_TOL = 1e-4


# ==================================================
# Selection
# ==================================================
class ScopeBoxSelectionFilter(ISelectionFilter):
    def AllowElement(self, elem):
        try:
            return elem.Category and elem.Category.Id.IntegerValue == int(
                BuiltInCategory.OST_VolumeOfInterest
            )
        except Exception:
            return False

    def AllowReference(self, ref, point):
        return False


def pick_scopebox(prompt):
    try:
        ref = uidoc.Selection.PickObject(
            ObjectType.Element, ScopeBoxSelectionFilter(), prompt
        )
        return doc.GetElement(ref.ElementId)
    except OperationCanceledException:
        return None


# ==================================================
# Geometry helpers (scope box intersection)
# ==================================================
def _to_local_xyz(Tinv, p):
    return Tinv.OfPoint(p)


def _bbox_intersects_scopebox(elem, sb):
    """AABB overlap in scope-box local coord (fast + robust)."""
    try:
        ebb = elem.get_BoundingBox(None)
        if not ebb:
            ebb = elem.get_BoundingBox(doc.ActiveView)

        sbb = sb.get_BoundingBox(None)
        if not ebb or not sbb or not sbb.Transform:
            return False

        Tinv = sbb.Transform.Inverse

        pts = [
            Tinv.OfPoint,
            (XYZ(ebb.Min.X, ebb.Min.Y, ebb.Min.Z)),
            Tinv.OfPoint,
            (XYZ(ebb.Min.X, ebb.Min.Y, ebb.Max.Z)),
            Tinv.OfPoint,
            (XYZ(ebb.Min.X, ebb.Max.Y, ebb.Min.Z)),
            Tinv.OfPoint,
            (XYZ(ebb.Min.X, ebb.Max.Y, ebb.Max.Z)),
            Tinv.OfPoint,
            (XYZ(ebb.Max.X, ebb.Min.Y, ebb.Min.Z)),
            Tinv.OfPoint,
            (XYZ(ebb.Max.X, ebb.Min.Y, ebb.Max.Z)),
            Tinv.OfPoint,
            (XYZ(ebb.Max.X, ebb.Max.Y, ebb.Min.Z)),
            Tinv.OfPoint,
            (XYZ(ebb.Max.X, ebb.Max.Y, ebb.Max.Z)),
        ]

        mn = XYZ(min(p.X for p in pts), min(p.Y for p in pts), min(p.Z for p in pts))
        mx = XYZ(max(p.X for p in pts), max(p.Y for p in pts), max(p.Z for p in pts))

        sb_mn = sbb.Min
        sb_mx = sbb.Max

        if mx.X < sb_mn.X or mn.X > sb_mx.X:
            return False
        if mx.Y < sb_mn.Y or mn.Y > sb_mx.Y:
            return False
        if mx.Z < sb_mn.Z or mn.Z > sb_mx.Z:
            return False
        return True
    except Exception:
        return False


def _scopebox_outline_model(sb):
    sbb = sb.get_BoundingBox(None)
    if not sbb:
        sbb = sb.get_BoundingBox(doc.ActiveView)
    if not sbb:
        return None

    T = sbb.Transform
    mn = sbb.Min
    mx = sbb.Max

    # If transform exists, map 8 corners to model coords and rebuild AABB
    if T:
        pts = [
            T.OfPoint(XYZ(mn.X, mn.Y, mn.Z)),
            T.OfPoint(XYZ(mn.X, mn.Y, mx.Z)),
            T.OfPoint(XYZ(mn.X, mx.Y, mn.Z)),
            T.OfPoint(XYZ(mn.X, mx.Y, mx.Z)),
            T.OfPoint(XYZ(mx.X, mn.Y, mn.Z)),
            T.OfPoint(XYZ(mx.X, mn.Y, mx.Z)),
            T.OfPoint(XYZ(mx.X, mx.Y, mn.Z)),
            T.OfPoint(XYZ(mx.X, mx.Y, mx.Z)),
        ]
        mn_m = XYZ(min(p.X for p in pts), min(p.Y for p in pts), min(p.Z for p in pts))
        mx_m = XYZ(max(p.X for p in pts), max(p.Y for p in pts), max(p.Z for p in pts))
        return Outline(mn_m, mx_m)

    return Outline(mn, mx)


# ==================================================
# Classification by Pipe Type + MEPSystem.Name
# ==================================================
def get_pipe_type_name(p):
    try:
        t = doc.GetElement(p.GetTypeId())
        if not t:
            return ""

        n = getattr(t, "Name", None)
        if n:
            return n

        pn = t.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM)
        if pn:
            s = pnAsString()
            if s:
                return s
    except Exception:
        pass
    return ""


def get_system_name(pipe):
    try:
        p = pipe.get_Parameter(BuiltInParameter.RBS_SYSTEM_NAME_PARAM)
        if p:
            return (p.AsString() or "").strip()
    except Exception:
        pass
    return ""


def classify_target_slope(pipe):
    sysname = get_system_name(pipe)
    low = re.sub(r"\s+", " ", (sysname or "").strip().lower())
    if "51 - vwa" in low:
        return (SLOPE_VWA, sysname)
    if "50 - hwa" in low:
        return (SLOPE_HWA, sysname)
    return (None, sysname)


# ==================================================
# Slope math + measurement
# ==================================================
def horiz_length(p0, p1):
    dx = p1.X - p0.X
    dy = p1.Y - p0.Y
    return math.sqrt(dx * dx + dy * dy)


def achieved_slope_ratio(elem):
    """Return abs(dZ)/horizontal_length, or None if not measurable"""
    try:
        loc = getattr(elem, "Location", None)
        if not isinstance(loc, LocationCurve):
            return None
        crv = loc.Curve
        p0 = crv.GetEndPoint(0)
        p1 = crv.GetEndPoint(1)
        hl = horiz_length(p0, p1)
        if hl < 1e-6:
            return None
        return abs(p1.Z - p0.Z) / hl
    except Exception:
        return None


def _param(elem, bip):
    try:
        p = elem.get_Parameter(bip)
        return p if p and not p.IsReadOnly else None
    except Exception:
        return None


def _try_set_slope_param(elem, slope_ratio):
    # Built-in candidates (guarded)
    for name in ["RBS_PIPE_SLOPE"]:
        if hasattr(BuiltInParameter, name):
            bip = getattr(BuiltInParameter, name, None)
            try:
                p = _param(elem, bip)
                if p:
                    p.Set(slope_ratio)
                    return True
            except Exception:
                pass

    # Fallback by parameter name (template/locale-dependent)
    for pname in ["Slope"]:
        try:
            p = elem.LookupParameter(pname)
            if p and not p.IsReadOnly:
                p.Set(slope_ratio)
                return True
        except Exception:
            pass
    return False


def _try_set_offsets_for_slope(elem, slope_ratio):
    loc = getattr(elem, "Location", None)
    if not isinstance(loc, LocationCurve):
        return False

    crv = loc.Curve
    p0 = crv.GetEndPoint(0)
    p1 = crv.GetEndPoint(1)

    hl = horiz_length(p0, p1)
    if hl < 1e-6:
        return False

    drop = slope_ratio * hl  # feet

    high_idx = 0 if p0.Z >= p1.Z else 1

    p_start = _param(elem, BuiltInParameter.RBS_START_OFFSET_PARAM)
    p_end = _param(elem, BuiltInParameter.RBS_END_OFFSET_PARAM)
    if not p_start or not p_end:
        return False

    start_off = p_start.AsDouble()
    end_off = p_end.AsDouble()

    if high_idx == 0:
        p_end.Set(start_off - drop)  # enforce
    else:
        p_start.Set(end_off - drop)  # enforce

    return True


def _connector_closest_to_point(pipe, pt):
    try:
        conns = pipe.ConnectorManager.Connectors
    except Exception:
        return None
    best = None
    best_d = None
    for c in conns:
        try:
            d = c.Origin.DistanceTo(pt)
            if best is None or d < best_d:
                best = c
                best_d = d
        except Exception:
            pass
    return best


def _conn_ref_count(conn):
    try:
        return len(list(conn.AllRefs))
    except Exception:
        return 0


def _select_end_to_move(pipe, p0, p1):
    c0 = _connector_closest_to_point(pipe, p0)
    c1 = _connector_closest_to_point(pipe, p1)
    r0 = _conn_ref_count(c0) if c0 else 0
    r1 = _conn_ref_count(c1) if c1 else 0
    if r0 < r1:
        return 0
    if r1 < r0:
        return 1
    # tie: move the lower end to keep high end
    return 0 if p0.Z <= p1.Z else 1


def _apply_slope_by_geometry(elem, slope_ratio):
    global _SLOPE_GEOM_DEBUG_DONE
    loc = getattr(elem, "Location", None)
    if not isinstance(loc, LocationCurve):
        return False
    crv = loc.Curve
    if crv is None:
        return False
    p0 = crv.GetEndPoint(0)
    p1 = crv.GetEndPoint(1)
    hl = horiz_length(p0, p1)
    if hl < HORIZ_MIN_FT:
        return False
    dz = slope_ratio * hl
    idx = _select_end_to_move(elem, p0, p1)
    if idx == 0:
        new_p0 = XYZ(p0.X, p0.Y, p1.Z - dz)
        loc.Curve = Line.CreateBound(new_p0, p1)
    else:
        new_p1 = XYZ(p1.X, p1.Y, p0.Z - dz)
        loc.Curve = Line.CreateBound(p0, new_p1)

    if not _SLOPE_GEOM_DEBUG_DONE:
        _SLOPE_GEOM_DEBUG_DONE = True
        label = "{:.1f}/1000".format(slope_ratio * 1000.0)
        print("DEBUG: geom slope sample pipe {}".format(elem.Id.IntegerValue))
        print("  before p0={}, p1={}".format(p0, p1))
        print("  horiz_run_ft={:.6f}, dz_ft={:.6f}".format(hl, dz))
        print(
            "  after p0={}, p1={}".format(
                loc.Curve.GetEndPoint(0), loc.Curve.GetEndPoint(1)
            )
        )
        print("  target label={}".format(label))

    return True


def _get_slope_param_value(elem):
    for name in ["RBS_PIPE_SLOPE"]:
        if hasattr(BuiltInParameter, name):
            bip = getattr(BuiltInParameter, name, None)
            try:
                p = elem.get_Parameter(bip)
                if p:
                    return p.AsDouble()
            except Exception:
                pass
    for pname in ["Slope"]:
        try:
            p = elem.LookupParameter(pname)
            if p:
                return p.AsDouble()
        except Exception:
            pass
    return None


def _offset_slope_ratio(elem):
    try:
        loc = getattr(elem, "Location", None)
        if not isinstance(loc, LocationCurve):
            return None
        crv = loc.Curve
        if crv is None:
            return None
        p0 = crv.GetEndPoint(0)
        p1 = crv.GetEndPoint(1)
        hl = horiz_length(p0, p1)
        if hl < 1e-6:
            return None
        p_start = _param(elem, BuiltInParameter.RBS_START_OFFSET_PARAM)
        p_end = _param(elem, BuiltInParameter.RBS_END_OFFSET_PARAM)
        if not p_start or not p_end:
            return None
        start_off = p_start.AsDouble()
        end_off = p_end.AsDouble()
        return abs(start_off - end_off) / hl
    except Exception:
        return None


def set_curve_slope_keep_high_end(elem, slope_ratio):
    loc = getattr(elem, "Location", None)
    if not isinstance(loc, LocationCurve):
        raise Exception("No LocationCurve")

    crv = loc.Curve
    p0 = crv.GetEndPoint(0)
    p1 = crv.GetEndPoint(1)

    hl = horiz_length(p0, p1)
    if hl < 1e-6:
        raise Exception("Too short (horiz length ~0)")

    drop = slope_ratio * hl  # feet

    if p0.Z >= p1.Z:
        high = p0
        low = p1
        high_idx = 0
    else:
        high = p1
        low = p0
        high_idx = 1

    new_low = XYZ(low.X, low.Y, high.Z - drop)

    if high_idx == 0:
        loc.Curve = Line.CreateBound(high, new_low)
    else:
        loc.Curve = Line.CreateBound(new_low, high)


def is_too_short(elem):
    try:
        loc = elem.Location
        if not isinstance(loc, LocationCurve):
            return True
        crv = loc.Curve
        if crv is None:
            return True
        # Revit tolerance in feet
        tol = doc.Application.ShortCurveTolerance
        if crv.Length < tol * 1.5:
            return True
        p0 = crv.GetEndPoint(0)
        p1 = crv.GetEndPoint(1)
        if horiz_length(p0, p1) < 1e-6:
            return True
        return False
    except Exception:
        return True


def apply_slope_mep_safe(elem, slope_ratio):
    if _try_set_slope_param(elem, slope_ratio):
        return (True, "slope_param")
    if _try_set_offsets_for_slope(elem, slope_ratio):
        return (True, "offsets")
    try:
        set_curve_slope_keep_high_end(elem, slope_ratio)
        return (True, "rewrite_curve")
    except Exception:
        pass
    if _apply_slope_by_geometry(elem, slope_ratio):
        return (True, "rewrite_curve")
    return (False, "rewrite_curve")


def apply_slope_disconnect_retry(elem, slope_ratio):
    # Prefer curve rewrite when disconnected
    try:
        set_curve_slope_keep_high_end(elem, slope_ratio)
        return (True, "disconnect_retry")
    except Exception:
        pass
    if _apply_slope_by_geometry(elem, slope_ratio):
        return (True, "disconnect_retry")
    if _try_set_offsets_for_slope(elem, slope_ratio):
        return (True, "disconnect_retry")
    if _try_set_slope_param(elem, slope_ratio):
        return (True, "disconnect_retry")
    return (False, "disconnect_retry")


# ==================================================
# Failure handling
# ==================================================


class RollbackOnMEPFailures(IFailuresPreprocessor):
    def __init__(self, err_log):
        self.err_log = err_log

    def PreprocessFailures(self, fa):
        try:
            msgs = fa.GetFailureMessages()
            for m in msgs:
                if m.GetSeverity() == FailureSeverity.Warning:
                    try:
                        self.err_log.append(
                            "Warning: {}".format(m.GetDescriptionText())
                        )
                    except Exception:
                        self.err_log.append("Warning (no description).")
                    fa.DeleteWarning(m)
                else:
                    try:
                        self.err_log.append("Error: {}".format(m.GetDescriptionText()))
                    except Exception:
                        self.err_log.append("Error (no description).")
                    return FailureProcessingResult.ProceedWithRollBack
            return FailureProcessingResult.Continue
        except Exception:
            return FailureProcessingResult.ProceedWithRollBack


class LogFailuresPreprocessor(IFailuresPreprocessor):
    def __init__(self, err_log):
        self.err_log = err_log

    def PreprocessFailures(self, fa):
        try:
            msgs = fa.GetFailureMessages()
            for m in msgs:
                try:
                    self.err_log.append(m.GetDescriptionText())
                except Exception:
                    self.err_log.append("Failure message (no description).")
            return FailureProcessingResult.Continue
        except Exception:
            return FailureProcessingResult.Continue


def set_failure_opts(tx, err_log):
    if DEBUG_NO_ROLLBACK:
        # Log only, do not delete warnings or force rollback
        opts = tx.GetFailureHandlingOptions()
        opts.SetFailuresPreprocessor(LogFailuresPreprocessor(err_log))
        tx.SetFailureHandlingOptions(opts)
        return
    opts = tx.GetFailureHandlingOptions()
    opts.SetFailuresPreprocessor(RollbackOnMEPFailures(err_log))
    opts.SetClearAfterRollback(True)
    tx.SetFailureHandlingOptions(opts)


# ==================================================
# CONNECTIVITY
# ===================================================


def _connector_ids_for_elem(elem):
    out = set()
    try:
        cm = elem.ConnectorManager
    except Exception:
        return out

    try:
        conns = cm.Connectors
    except Exception:
        return out

    for c in conns:
        try:
            refs = c.AllRefs
        except Exception:
            continue
        for r in refs:
            try:
                owner = r.Owner
                if owner and owner.Id and owner.Id != elem.Id:
                    out.add(owner.Id.IntegerValue)
            except Exception:
                pass
    return out


def _is_connectivity_failure(text):
    if not text:
        return False
    low = text.lower()
    keys = [
        "connect",
        "connection",
        "network",
        "constraint",
        "cannot",
        "can't",
        "route",
        "system",
        "mep",
    ]
    return any(k in low for k in keys)


def _get_end_connectors(pipe):
    ends = []
    try:
        conns = pipe.ConnectorManager.Connectors
    except Exception:
        return ends
    for c in conns:
        try:
            if c.ConnectorType.ToString().lower() == "end":
                ends.append(c)
        except Exception:
            pass
    if not ends:
        try:
            return list(conns)
        except Exception:
            return []
    return ends


def _disconnect_all(pipe):
    pairs = []
    try:
        conns = _get_end_connectors(pipe)
    except Exception:
        return pairs

    for c in conns:
        try:
            refs = list(c.AllRefs)
        except Exception:
            continue
        for r in refs:
            try:
                if r and r.Owner and r.Owner.Id != pipe.Id:
                    try:
                        c.DisconnectFrom(r)
                        pairs.append((c, r))
                    except Exception:
                        pass
            except Exception:
                pass
    return pairs


def _reconnect_pairs(pairs):
    failed = 0
    for c, r in pairs:
        try:
            c.ConnectTo(r)
        except Exception:
            failed += 1
    return failed


def _try_disconnect_apply_reconnect(pipe, slope_ratio):
    pairs = _disconnect_all(pipe)
    ok, method = apply_slope_disconnect_retry(pipe, slope_ratio)
    try:
        doc.Regenerate()
    except Exception:
        pass
    failed_reconnects = _reconnect_pairs(pairs) if pairs else 0
    if not ok:
        return (False, method, "disconnect_required")
    if failed_reconnects > 0:
        return (True, method, "reconnect_failed")
    return (True, method, None)


def build_components(pipes):
    by_id = {p.Id.IntegerValue: p for p in pipes}

    adj = {}
    for pid, p in by_id.items():
        nbrs = _connector_ids_for_elem(p)
        adj[pid] = [nid for nid in nbrs if nid in by_id]

    seen = set()
    comps = []

    for pid in by_id:
        if pid in seen:
            continue
        stack = [pid]
        seen.add(pid)
        comp_ids = []
        while stack:
            cur = stack.pop()
            comp_ids.append(cur)
            for nb in adj.get(cur, []):
                if nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        comps.append([by_id[i] for i in comp_ids])

    return comps


# ==================================================
# COLLECTION
# ==================================================


def collect_target_pipes_in_scopebox(sb):
    outline = _scopebox_outline_model(sb)
    if not outline:
        print("DEBUG: scope box has no bounding box; cannot build outline.")
        return []

    # XY-only outline unless strict Z is requested
    if USE_SCOPEBOX_Z:
        bb_filter = BoundingBoxIntersectsFilter(outline)
    else:
        INF = 1e9
        xy_outline = Outline(
            XYZ(outline.MinimumPoint.X, outline.MinimumPoint.Y, -INF),
            XYZ(outline.MaximumPoint.X, outline.MaximumPoint.Y, INF),
        )
        bb_filter = BoundingBoxIntersectsFilter(xy_outline)

    pipes = (
        FilteredElementCollector(doc)
        .OfCategory(BuiltInCategory.OST_PipeCurves)
        .WhereElementIsNotElementType()
        .WherePasses(bb_filter)
        .ToElements()
    )

    inside = []
    for p in pipes:
        try:
            if p.GetTypeId().IntegerValue != PIPE_TYPE_ID:
                continue
            inside.append(p)
        except Exception:
            pass
    print(
        "DEBUG totals: pipes_bb_filter=",
        len(pipes),
        "type_match=",
        len(inside),
    )
    return inside


def _chunked(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def _level_info(pipe):
    # Try start level param first
    try:
        p = pipe.get_Parameter(BuiltInParameter.RBS_START_LEVEL_PARAM)
        if p:
            lvl_id = p.AsElementId()
            lvl = doc.GetElement(lvl_id)
            if lvl:
                return (lvl.Name, lvl.Id.IntegerValue)
    except Exception:
        pass
    # Fallback: Reference Level parameter
    try:
        p = pipe.LookupParameter("Reference Level")
        if p and p.AsElementId():
            lvl = doc.GetElement(p.AsElementId())
            if lvl:
                return (lvl.Name, lvl.Id.IntegerValue)
    except Exception:
        pass
    return ("<None>", None)


def _bbox_minmax_z(elem):
    try:
        bb = elem.get_BoundingBox(None)
        if bb:
            return (bb.Min.Z, bb.Max.Z)
    except Exception:
        pass
    return (None, None)


def _get_system_type_id(pipe):
    try:
        p = pipe.get_Parameter(BuiltInParameter.RBS_PIPING_SYSTEM_TYPE_PARAM)
        if p:
            return p.AsElementId()
    except Exception:
        pass
    return ElementId.InvalidElementId


def _param_state(elem, bip):
    if bip is None:
        return (False, False, None)
    try:
        p = elem.get_Parameter(bip)
        if not p:
            return (False, False, None)
        return (True, not p.IsReadOnly, p.AsDouble())
    except Exception:
        return (False, False, None)


def _param_state_by_name(elem, name):
    try:
        p = elem.LookupParameter(name)
        if not p:
            return (False, False, None)
        return (True, not p.IsReadOnly, p.AsDouble())
    except Exception:
        return (False, False, None)


def _pipe_diag(pipe):
    sysname = get_system_name(pipe)
    sys_type_id = _get_system_type_id(pipe)
    loc = getattr(pipe, "Location", None)
    has_loc = isinstance(loc, LocationCurve)
    horiz = None
    length = None
    below_tol = None
    if has_loc:
        crv = loc.Curve
        if crv:
            p0 = crv.GetEndPoint(0)
            p1 = crv.GetEndPoint(1)
            horiz = horiz_length(p0, p1)
            length = crv.Length
            try:
                below_tol = length < doc.Application.ShortCurveTolerance * 1.5
            except Exception:
                below_tol = None

    slope_param = _param_state(pipe, getattr(BuiltInParameter, "RBS_PIPE_SLOPE", None))
    start_off = _param_state(pipe, BuiltInParameter.RBS_START_OFFSET_PARAM)
    end_off = _param_state(pipe, BuiltInParameter.RBS_END_OFFSET_PARAM)
    slope_lookup = _param_state_by_name(pipe, "Slope")

    return {
        "id": pipe.Id.IntegerValue,
        "name": getattr(pipe, "Name", ""),
        "pinned": getattr(pipe, "Pinned", False),
        "workset": getattr(pipe, "WorksetId", ElementId.InvalidElementId).IntegerValue,
        "view_specific": getattr(pipe, "ViewSpecific", False),
        "system": sysname,
        "system_type_id": (
            sys_type_id.IntegerValue
            if sys_type_id and sys_type_id != ElementId.InvalidElementId
            else None
        ),
        "has_loc": has_loc,
        "horiz_ft": horiz,
        "horiz_mm": horiz * 304.8 if horiz is not None else None,
        "curve_len_ft": length,
        "below_tol": below_tol,
        "achieved": achieved_slope_ratio(pipe),
        "slope_param": slope_param,
        "start_off": start_off,
        "end_off": end_off,
        "slope_lookup": slope_lookup,
    }


def _slope_readonly(diag):
    # slope param present but read-only, and offsets read-only or missing
    sp = diag.get("slope_param", (False, False, None))
    so = diag.get("start_off", (False, False, None))
    eo = diag.get("end_off", (False, False, None))
    slope_ro = sp[0] and (not sp[1])
    offsets_ro = (so[0] and (not so[1])) and (eo[0] and (not eo[1]))
    return slope_ro and offsets_ro


def dump_slope_params_once(sample_pipe):
    global _SLOPE_DUMPED
    if _SLOPE_DUMPED or not sample_pipe:
        return
    _SLOPE_DUMPED = True
    try:
        print(
            "DEBUG: slope parameter candidates for pipe {}".format(
                sample_pipe.Id.IntegerValue
            )
        )
        for p in sample_pipe.Parameters:
            try:
                pname = p.Definition.Name
                if "slope" in pname.lower():
                    st = p.StorageType.ToString()
                    ro = p.IsReadOnly
                    val = None
                    try:
                        if p.StorageType.ToString() == "Double":
                            val = p.AsDouble()
                        else:
                            val = p.AsValueString()
                    except Exception:
                        val = None
                    print(
                        "  - {} | StorageType={} | ReadOnly={} | Value={}".format(
                            pname, st, ro, val
                        )
                    )
            except Exception:
                pass
    except Exception:
        pass


# ==================================================
# MAIN
# ==================================================
def main():
    sb = pick_scopebox("Pick scope box (slope solving region)")
    if not sb:
        TaskDialog.Show("slope_solver", "Cancelled by user (no scope box picked).")
        return

    candidates = collect_target_pipes_in_scopebox(sb)
    if not candidates:
        TaskDialog.Show(
            "slope_solver",
            "No target PipeCurves found in scope box.\nTypeId filter: {}".format(
                PIPE_TYPE_ID
            ),
        )
        return

    # One-time dump of slope-related parameters for a sample pipe
    dump_slope_params_once(candidates[0] if candidates else None)

    # Diagnostics (pre-execution)
    sys_counts = defaultdict(int)
    unmatched_rules = 0
    level_counts = defaultdict(lambda: {"candidates": 0, "changed": 0, "failed": 0, "skipped": 0})
    for p in candidates:
        sysname = get_system_name(p)
        sys_counts[sysname] += 1
        target, _ = classify_target_slope(p)
        if target is None:
            unmatched_rules += 1
        lvl_name, lvl_id = _level_info(p)
        level_counts[lvl_name]["candidates"] += 1

    print("DEBUG: total candidates =", len(candidates))
    print("DEBUG: system counts (incl. empty):")
    for k, v in sorted(sys_counts.items(), key=lambda x: x[0] or ""):
        print("  '{}' : {}".format(k, v))
    print("DEBUG: unmatched system rules =", unmatched_rules)
    print(
        "DEBUG: slopes VWA={:.6f} ({:.1f}/1000), HWA={:.6f} ({:.1f}/1000)".format(
            SLOPE_VWA,
            SLOPE_VWA * 1000.0,
            SLOPE_HWA,
            SLOPE_HWA * 1000.0,
        )
    )

    # Preflight skip logic
    skipped_too_short = 0
    skipped_pinned = 0
    skipped_no_location = 0
    skipped_no_rule = 0
    skipped_near_vertical = 0

    to_process = []
    failure_samples = []
    for p in candidates:
        lvl_name, lvl_id = _level_info(p)
        minz, maxz = _bbox_minmax_z(p)
        strict_pass = _bbox_intersects_scopebox(p, sb)
        xy_pass = True  # already passed XY filter to be in candidates
        print(
            "DEBUG: pipe {} sys='{}' level='{}' lvl_id={} bboxZ=({}, {}) xy_pass={} strict_pass={}".format(
                p.Id.IntegerValue,
                get_system_name(p),
                lvl_name,
                lvl_id,
                minz,
                maxz,
                xy_pass,
                strict_pass,
            )
        )

        if USE_SCOPEBOX_Z and not strict_pass:
            skipped_no_rule += 0
            skipped_near_vertical += 0
            skipped_no_location += 0
            skipped_too_short += 0
            skipped_pinned += 0
            level_counts[lvl_name]["skipped"] += 1
            if len(failure_samples) < 30:
                failure_samples.append(
                    "Pipe {} (sys='{}') method=skipped_outside_z reason=OUTSIDE_SCOPEBOX_Z".format(
                        p.Id.IntegerValue, get_system_name(p)
                    )
                )
            continue

        try:
            if getattr(p, "Pinned", False):
                skipped_pinned += 1
                level_counts[lvl_name]["skipped"] += 1
                if len(failure_samples) < 30:
                    failure_samples.append(
                        "Pipe {} (sys='{}') method=skipped_pinned reason=PINNED".format(
                            p.Id.IntegerValue, get_system_name(p)
                        )
                    )
                continue
        except Exception:
            pass

        loc = getattr(p, "Location", None)
        if not isinstance(loc, LocationCurve):
            skipped_no_location += 1
            level_counts[lvl_name]["skipped"] += 1
            if len(failure_samples) < 30:
                failure_samples.append(
                    "Pipe {} (sys='{}') method=skipped_no_location reason=NO_LOCATION".format(
                        p.Id.IntegerValue, get_system_name(p)
                    )
                )
            continue

        if is_too_short(p):
            skipped_too_short += 1
            level_counts[lvl_name]["skipped"] += 1
            if len(failure_samples) < 30:
                failure_samples.append(
                    "Pipe {} (sys='{}') method=skipped_too_short reason=TOO_SHORT".format(
                        p.Id.IntegerValue, get_system_name(p)
                    )
                )
            continue

        # Near-vertical guardrail
        try:
            crv = loc.Curve
            if crv:
                p0 = crv.GetEndPoint(0)
                p1 = crv.GetEndPoint(1)
                hl = horiz_length(p0, p1)
                if hl < HORIZ_MIN_FT:
                    skipped_near_vertical += 1
                    level_counts[lvl_name]["skipped"] += 1
                    if len(failure_samples) < 30:
                        failure_samples.append(
                            "Pipe {} (sys='{}') method=skipped_near_vertical reason=NEAR_VERTICAL".format(
                                p.Id.IntegerValue, get_system_name(p)
                            )
                        )
                    continue
        except Exception:
            pass

        target, sysname = classify_target_slope(p)
        if target is None:
            skipped_no_rule += 1
            level_counts[lvl_name]["skipped"] += 1
            if len(failure_samples) < 30:
                failure_samples.append(
                    "Pipe {} (sys='{}') method=skipped_no_rule reason=NO_RULE".format(
                        p.Id.IntegerValue, get_system_name(p)
                    )
                )
            continue

        to_process.append((p, target, sysname))

    if not to_process:
        TaskDialog.Show(
            "slope_solver",
            "No eligible PipeCurves after preflight skips.\n"
            "Skipped: pinned={}, no_location={}, too_short={}, no_rule={}".format(
                skipped_pinned,
                skipped_no_location,
                skipped_too_short,
                skipped_no_rule,
            ),
        )
        return

    # Stats
    total = len(candidates)
    changed = 0
    failed_tx = 0
    failed_no_delta = 0
    disconnect_retries = 0
    reconnect_failures = 0
    failures = []

    # --- Execution (single undo) ---
    tg = TransactionGroup(doc, "slope_solver: Apply Slopes")
    tg.Start()

    try:
        # debug readback per system (limit)
        debug_readback = defaultdict(int)
        for p, target, sysname in to_process:
            diag = _pipe_diag(p)
            method = "slope_param"
            tx = Transaction(doc, "slope_solver: pipe {}".format(p.Id.IntegerValue))
            tx.Start()
            err_log = []
            set_failure_opts(tx, err_log)

            try:
                ok, method = apply_slope_mep_safe(p, target)
                st = tx.Commit()
                tx_status = st.ToString()
                ex = None
            except Exception as ex:
                try:
                    tx.RollBack()
                except Exception:
                    pass
                tx_status = "RolledBack"

            actual = None
            if tx_status == "Committed":
                actual = achieved_slope_ratio(p)
            else:
                failed_tx += 1
                lvl_name, _ = _level_info(p)
                level_counts[lvl_name]["failed"] += 1
                if len(failure_samples) < 30:
                    failure_samples.append(
                        "Pipe {id} ({name}) sys='{sys}' method={m} reason=TX_ROLLBACK tx={tx} ex={ex} failures={f} diag={d}".format(
                            id=diag["id"],
                            name=diag["name"],
                            sys=diag["system"],
                            m=method,
                            tx=tx_status,
                            ex=repr(ex),
                            f="; ".join(err_log) if err_log else "None",
                            d=diag,
                        )
                    )
            if actual is not None and abs(actual - target) <= SLOPE_TOL:
                changed += 1
                lvl_name, _ = _level_info(p)
                level_counts[lvl_name]["changed"] += 1
                # debug readback samples per system
                if debug_readback[sysname] < 3:
                    try:
                        loc = p.Location
                        crv = loc.Curve
                        p0 = crv.GetEndPoint(0)
                        p1 = crv.GetEndPoint(1)
                        hl = horiz_length(p0, p1)
                        rise = abs(p1.Z - p0.Z)
                        print(
                            "DEBUG: sys='{}' pipe {} rise/run={:.6f}/{:.6f} ratio={:.6f}".format(
                                sysname, p.Id.IntegerValue, rise, hl, rise / hl if hl > 1e-9 else 0.0
                            )
                        )
                        debug_readback[sysname] += 1
                    except Exception:
                        pass
                continue

            orig_ex = repr(ex) if ex else "None"
            orig_fail = "; ".join(err_log) if err_log else "None"

            # Retry with disconnect if slope did not change or failed
            tx2 = Transaction(
                doc, "slope_solver: disconnect_retry {}".format(p.Id.IntegerValue)
            )
            tx2.Start()
            err_log2 = []
            set_failure_opts(tx2, err_log2)
            try:
                ok2, method2, reconnect_note = _try_disconnect_apply_reconnect(
                    p, target
                )
                st2 = tx2.Commit()
                tx2_status = st2.ToString()
            except Exception as ex2:
                try:
                    tx2.RollBack()
                except Exception:
                    pass
                failed_tx += 1
                if len(failure_samples) < 30:
                    failure_samples.append(
                        "Pipe {id} ({name}) sys='{sys}' method=disconnect_retry tx=RolledBack ex={ex} failures={f} diag={d}".format(
                            id=diag["id"],
                            name=diag["name"],
                            sys=diag["system"],
                            ex=repr(ex2),
                            f="; ".join(err_log2) if err_log2 else "None",
                            d=diag,
                        )
                    )
                continue

            disconnect_retries += 1
            if tx2_status != "Committed":
                failed_tx += 1
                lvl_name, _ = _level_info(p)
                level_counts[lvl_name]["failed"] += 1
                if len(failure_samples) < 30:
                    failure_samples.append(
                        "Pipe {id} ({name}) sys='{sys}' method=disconnect_retry reason=TX_ROLLBACK tx={tx} ex={ex} failures={f} orig_failures={of} diag={d}".format(
                            id=diag["id"],
                            name=diag["name"],
                            sys=diag["system"],
                            tx=tx2_status,
                            ex=repr(None),
                            f="; ".join(err_log2) if err_log2 else "None",
                            of=orig_fail,
                            d=diag,
                        )
                    )
                continue

            actual2 = achieved_slope_ratio(p)
            if actual2 is not None and abs(actual2 - target) <= SLOPE_TOL:
                changed += 1
                lvl_name, _ = _level_info(p)
                level_counts[lvl_name]["changed"] += 1
                if reconnect_note == "reconnect_failed":
                    reconnect_failures += 1
                    if len(failure_samples) < 30:
                        failure_samples.append(
                            "Pipe {id} ({name}) sys='{sys}' method=disconnect_retry reason=NETWORK_RECONNECT_FAILED tx=Committed ex=None failures={f} orig_failures={of} diag={d}".format(
                                id=diag["id"],
                                name=diag["name"],
                                sys=diag["system"],
                                f="; ".join(err_log2) if err_log2 else "None",
                                of=orig_fail,
                                d=diag,
                            )
                        )
                continue

            failed_no_delta += 1
            lvl_name, _ = _level_info(p)
            level_counts[lvl_name]["failed"] += 1
            if len(failure_samples) < 30:
                reason = "SLOPE_READONLY" if _slope_readonly(diag) else "NO_SLOPE_DELTA"
                failure_samples.append(
                    "Pipe {id} ({name}) sys='{sys}' method=disconnect_retry reason={r} target={t:.6f} actual={a} tx=Committed ex=None failures={f} orig_failures={of} diag={d}".format(
                        id=diag["id"],
                        name=diag["name"],
                        sys=diag["system"],
                        f="; ".join(err_log2) if err_log2 else "None",
                        of=orig_fail,
                        r=reason,
                        t=target,
                        a=actual2,
                        d=diag,
                    )
                )

        tg.Assimilate()

    except Exception:
        try:
            tg.RollBack()
        except Exception:
            pass
        raise

    if failure_samples:
        print("DEBUG: failure samples:")
        for s in failure_samples[:30]:
            print("  - {}".format(s))

    # Level summary lines
    lvl_lines = []
    for lvl, stats in level_counts.items():
        lvl_lines.append(
            "{}: c={} ch={} f={} sk={}".format(
                lvl,
                stats["candidates"],
                stats["changed"],
                stats["failed"],
                stats["skipped"],
            )
        )

    msg = (
        "Candidates: {0}\n"
        "Changed (validated): {1}\n"
        "Failed (tx rollback): {2}\n"
        "Failed (no slope delta): {3}\n"
        "Skipped (pinned): {4}\n"
        "Skipped (no location): {5}\n"
        "Skipped (too short): {6}\n"
        "Skipped (no rule): {7}\n"
        "Skipped (near vertical): {8}\n"
        "Disconnect retries: {9}\n"
        "Reconnect failures: {10}\n\n"
        "Level summary:\n- {11}\n\n"
        "Slope VWA: {12:.6f} ({13:.1f}/1000)\n"
        "Slope HWA: {14:.6f} ({15:.1f}/1000)\n\n"
        "Failure samples (first 30):\n- {16}"
    ).format(
        total,
        changed,
        failed_tx,
        failed_no_delta,
        skipped_pinned,
        skipped_no_location,
        skipped_too_short,
        skipped_no_rule,
        skipped_near_vertical,
        disconnect_retries,
        reconnect_failures,
        "\n- ".join(lvl_lines) if lvl_lines else "None",
        SLOPE_VWA,
        SLOPE_VWA * 1000.0,
        SLOPE_HWA,
        SLOPE_HWA * 1000.0,
        "\n- ".join(failure_samples[:30]) if failure_samples else "None",
    )

    TaskDialog.Show("slope_solver", msg)


if __name__ == "__main__":
    main()
