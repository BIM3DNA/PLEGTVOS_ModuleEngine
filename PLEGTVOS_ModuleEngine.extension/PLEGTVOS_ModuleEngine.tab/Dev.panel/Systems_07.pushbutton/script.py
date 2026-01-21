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
  - MEPSystem contains "51 - VWA 2"  -> 5.0%  (0.05)
  - MEPSystem contains "50 - HWA 4"  -> 7.5%  (0.075)

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

# ==================================================
# Revit Document Setup
# ==================================================
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

# ==================================================
# Config
# ==================================================
PIPE_TYPE_ID = 926396

# Match by substring (case-insensitive) within MEPSystem.Name
# SYS_SLOPE_RULES = [
#     ("51 - VWA 2", 0.0075),  # 5%
#     ("50 - HWA 4", 0.005),  # 7.5%
# ]
SLOPE_VWA = 0.0075  # 7.5%
SLOPE_HWA = 0.005  # 5%

# Validation tolerance (ratio units, p.g. 0.05 == 5%)
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
    for name in ["RBS_PIPE_SLOPE_PARAM", "RBS_PIPE_SLOPE"]:
        bip = getattr(BuiltInParameter, name, None)
        if bip is None:
            continue
        try:
            p = _param(elem, bip)
            if p:
                p.Set(slope_ratio)
                return True
        except Exception:
            pass

    # Fallback by parameter name (template/locale-dependent)
    try:
        p = elem.LookupParameter("Slope")
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
        # Revit tolerance in feer
        tol = doc.Application.ShortCurveTolerance
        if crv.Length < tol * 1.5:
            return True
        p0 = crv.GetEndPoint(0)
        p1 = crv.GetEndPoint(1)
        if horiz_length(p0, p1) < tol * 0.5:
            return True
        return False
    except Exception:
        return True


def apply_slope_mep_safe(elem, slope_ratio):
    if _try_set_slope_param(elem, slope_ratio):
        return True
    if _try_set_offsets_for_slope(elem, slope_ratio):
        return True
    # set_curve_slope_keep_high_end(elem, slope_ratio)
    return False


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
                    fa.DeleteWarning(m)
                else:
                    try:
                        self.err_log.append(m.GetDescriptionText())
                    except Exception:
                        self.err_log.append("Non-warning failure (no description).")
                    return FailureProcessingResult.ProceedWithRollBack
            return FailureProcessingResult.Continue
        except Exception:
            return FailureProcessingResult.ProceedWithRollBack


def set_failure_opts(tx, err_log):
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

    bb_filter = BoundingBoxIntersectsFilter(outline)

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

    # Build connected components (runs
    comps = build_components(candidates)

    # Stats
    total = len(candidates)
    changed = 0
    failed = 0
    skipped = 0
    failures = []

    # --- Execution (single undo) ---
    tg = TransactionGroup(doc, "slope_solver: Apply Slopes (component-based)")
    tg.Start()

    try:
        for i, comp in enumerate(comps):
            tx = Transaction(doc, "slope_solver: component {}".format(i + 1))
            tx.Start()
            set_failure_opts(tx, failures)

            try:
                any_touched = False
                for p in comp:
                    target, sysname = classify_target_slope(p)
                    if target is None:
                        skipped += 1
                        continue
                    apply_slope(p, target)
                    any_touched = True

                if any_touched:
                    doc.Regenerate()

                st = tx.Commit()
                if st.ToString() != "Committed":
                    failed += len(comp)
                    continue

                # Validate after commit (per pipe)
                for p in comp:
                    target, sysname = classify_target_slope(p)
                    if target is None:
                        continue
                    actual = achieved_slope_ratio(p)
                    if actual is None or abs(actual - target) > SLOPE_TOL:
                        failed += 1
                        if len(failures) < 30:
                            failures.append(
                                "Slope mismatch pipe {}: target {:.6f}, actual {} (sys='{}')".format(
                                    p.Id.IntegerValue, target, actual, sysname
                                )
                            )
                    else:
                        changed += 1

            except Exception as ex:
                try:
                    tx.RollBack()
                except Exception:
                    pass
                failed += len(comp)
                if len(failures) < 30:
                    failures.append("Component {} failed: {}".format(i + 1, ex))

        tg.Assimilate()

    except Exception:
        try:
            tg.RollBack()
        except Exception:
            pass
        raise

    msg = (
        "Candidates: {0}\n"
        "Components: {1}\n\n"
        "Changed (validated): {2}\n"
        "Failed (validated/tx): {3}\n"
        "Skipped (no system match): {4}\n\n"
        "Failure samples:\n- {5}"
    ).format(
        total,
        len(comps),
        changed,
        failed,
        skipped,
        "\n- ".join(failures) if failures else "None",
    )

    TaskDialog.Show("slope_solver", msg)


if __name__ == "__main__":
    main()
