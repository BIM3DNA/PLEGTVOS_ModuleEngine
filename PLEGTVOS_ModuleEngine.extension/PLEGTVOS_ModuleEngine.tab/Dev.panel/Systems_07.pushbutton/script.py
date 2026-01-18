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
    ElementId,
    FailureProcessingResult,
    FailureSeverity,
    FilteredElementCollector,
    IFailuresPreprocessor,
    Line,
    LocationCurve,
    Transaction,
    TransactionGroup,
    XYZ,
)
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
from Autodesk.Revit.Exceptions import OperationCanceledException
from System.Collections.Generic import List as ClrList

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
PIPE_TYPE_TOKEN = "nlrs_52_pi_pvc u3 grijs od_dyka"

# Match by substring (case-insensitive) within MEPSystem.Name
SYS_SLOPE_RULES = [
    ("51 - VWA 2", 0.0075),  # 5%
    ("50 - HWA 4", 0.005),  # 7.5%
]

# Validation tolerance (ratio units, e.g. 0.05 == 5%)
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
        sbb = sb.get_BoundingBox(None)
        if not ebb or not sbb or not sbb.Transform:
            return False

        Tinv = sbb.Transform.Inverse

        pts = [
            _to_local_xyz(Tinv, XYZ(ebb.Min.X, ebb.Min.Y, ebb.Min.Z)),
            _to_local_xyz(Tinv, XYZ(ebb.Min.X, ebb.Min.Y, ebb.Max.Z)),
            _to_local_xyz(Tinv, XYZ(ebb.Min.X, ebb.Max.Y, ebb.Min.Z)),
            _to_local_xyz(Tinv, XYZ(ebb.Min.X, ebb.Max.Y, ebb.Max.Z)),
            _to_local_xyz(Tinv, XYZ(ebb.Max.X, ebb.Min.Y, ebb.Min.Z)),
            _to_local_xyz(Tinv, XYZ(ebb.Max.X, ebb.Min.Y, ebb.Max.Z)),
            _to_local_xyz(Tinv, XYZ(ebb.Max.X, ebb.Max.Y, ebb.Min.Z)),
            _to_local_xyz(Tinv, XYZ(ebb.Max.X, ebb.Max.Y, ebb.Max.Z)),
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


def set_curve_slope_keep_high_end(elem, slope_ratio):
    """
    LAST RESORT: Rewrites LocationCurve to enforce slope magnitude.
    Keeps higher endpoint fixed and lowers the other.
    """
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


# ==================================================
# Parameter helpers + slope application
# ==================================================
def _param(elem, bip):
    try:
        p = elem.get_Parameter(bip)
        return p if p and not p.IsReadOnly else None
    except Exception:
        return None


def _try_set_offsets_for_slope(elem, slope_ratio):
    """
    Apply slope by editing Start/End Offset parameters (often stable for Pipe).
    Keeps the higher endpoint offset and lowers the other.
    Returns True if something was set, else False.
    """
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
        p_start.Set(start_off)  # keep
        p_end.Set(start_off - drop)  # enforce
    else:
        p_end.Set(end_off)  # keep
        p_start.Set(end_off - drop)  # enforce

    return True


def _try_set_slope_param(elem, slope_ratio):
    """
    Best-effort set of a slope parameter if present/writable.
    Returns True if set.
    """
    bip_names = [
        "RBS_PIPE_SLOPE",
        "RBS_PIPE_SLOPE_PARAM",
        "RBS_DUCT_SLOPE",
        "RBS_DUCT_SLOPE_PARAM",
    ]

    for name in bip_names:
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


def apply_slope_mep_safe(elem, slope_ratio):
    """
    Preferred slope application (pragmatic):
    1) Slope parameter (if available)
    2) Offsets
    3) Last resort: curve rewrite
    """
    if _try_set_slope_param(elem, slope_ratio):
        return True
    if _try_set_offsets_for_slope(elem, slope_ratio):
        return True
    set_curve_slope_keep_high_end(elem, slope_ratio)
    return True


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
                sev = m.GetSeverity()
                if sev == FailureSeverity.Warning:
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
    """Attach failure preprocessor to a Transaction."""
    opts = tx.GetFailureHandlingOptions()
    opts.SetFailuresPreprocessor(RollbackOnMEPFailures(err_log))
    opts.SetClearAfterRollback(True)
    tx.SetFailureHandlingOptions(opts)


# ==================================================
# Classification by Pipe Type + MEPSystem.Name
# ==================================================
def get_pipe_type_name(p):
    try:
        t = doc.GetElement(p.GetTypeId())
        if not t:
            return ""

        pn = t.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM)
        if pn:
            s = pn.AsString()
            if s:
                return s

        n = getattr(t, "Name", None)
        if n:
            return n

        for key in ["Type Name", "Naam", "Type", "Naam Type"]:
            pp = t.LookupParameter(key)
            if pp:
                s2 = pp.AsString()
                if s2:
                    return s2
    except Exception:
        pass
    return ""


def get_system_name_and_typeid(pipe):
    sysname = ""
    stid = None

    try:
        p = pipe.get_Parameter(BuiltInParameter.RBS_SYSTEM_NAME_PARAM)
        if p:
            sysname = (p.AsString() or "").strip()
    except Exception:
        pass
    try:
        p = pipe.get_Parameter(BuiltInParameter.RBS_PIPING_SYSTEM_TYPE_PARAM)
        if p:
            eid = p.AsElementId()
            if eid and eid != ElementId.InvalidElementId:
                stid = eid.IntegerValue
    except Exception:
        pass

    return (sysname, stid)


def classify_slope_by_system(pipe):
    """Return (slope_ratio, reason) or (None, reason)."""
    sysname, stid = get_system_name_and_typeid(pipe)
    low = (sysname or "").strip().lower()
    low = re.sub(r"\s+", " ", low)  # normalize spaces

    # Match "51 - VWA ..." > 5%
    if "51 - vwa" in low:
        return (0.0075, "systemNameToken:'51 - VWA' ({})".format(sysname))
    # Match "50 - HWA ..." > 7.5%
    if "50 - hwa" in low:
        return (0.005, "systemNameToken:'50 - HWA' ({})".format(sysname))

    if not low and stid is None:
        return (None, "no system params")

    return (None, "system not matched (name='{}', typeId={})".format(sysname, stid))


# ==================================================
# Candidate collection
# ==================================================
def collect_target_pipes_in_scopebox(sb):
    """Collect PipeCurves in scope box, filtered by Pipe Type name."""
    pipes = (
        FilteredElementCollector(doc)
        .OfCategory(BuiltInCategory.OST_PipeCurves)
        .WhereElementIsNotElementType()
        .ToElements()
    )

    inside = []
    debug_printed = 0

    for p in pipes:
        try:
            if not _bbox_intersects_scopebox(p, sb):
                continue

            tname = (get_pipe_type_name(p) or "").strip().lower()
            if debug_printed < 10:
                print("IN-SCOPE TYPE RAW:", repr(tname))
                debug_printed += 1

            if PIPE_TYPE_TOKEN not in tname:
                continue

            inside.append(p)
        except Exception:
            pass

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
    for p in candidates[:10]:
        sysname, stid = get_system_name_and_typeid(p)
        print("PIPE", p.Id.IntegerValue, "SYSNAME:", repr(sysname), "SYSTYPEID:", stid)

    if not candidates:
        TaskDialog.Show(
            "slope_solver",
            "No target PipeCurves found in scope box.\nType filter: {}".format(
                PIPE_TYPE_TOKEN
            ),
        )
        return

    # Diagnostics
    classified_75 = 0
    classified_50 = 0
    unclassified = 0

    for e in candidates:
        slope, _ = classify_slope_by_system(e)
        if slope is None:
            unclassified += 1
        elif abs(slope - 0.005) < 1e-9:
            classified_75 += 1
        elif abs(slope - 0.0075) < 1e-9:
            classified_50 += 1

    # --- Execution (single undo) ---
    tg = TransactionGroup(doc, "slope_solver: Apply Slopes (System-based)")
    tg.Start()

    changed = 0
    failed = 0
    failures = []  # sample lines

    try:
        for e in candidates:
            txe = Transaction(doc, "slope_solver: elem {}".format(e.Id.IntegerValue))
            started = False
            try:
                txe.Start()
                started = True
                set_failure_opts(txe, failures)

                target, reason = classify_slope_by_system(e)
                if target is None:
                    txe.RollBack()
                    continue

                apply_slope_mep_safe(e, target)

                # IMPORTANT: let Revit solve connectivity while txn is open
                doc.Regenerate()

                st = txe.Commit()
                if st != TransactionStatus.Committed:
                    failed += 1
                    if len(failures) < 30:
                        failures.append(
                            "TX not committed (elem {}): {}".format(
                                e.Id.IntegerValue, reason
                            )
                        )
                    continue

                actual = achieved_slope_ratio(e)
                if actual is None or abs(actual - target) > SLOPE_TOL:
                    failed += 1
                    if len(failures) < 30:
                        failures.append(
                            "Slope mismatch (elem {}): target {:.6f}, actual {} ({})".format(
                                e.Id.IntegerValue, target, actual, reason
                            )
                        )
                else:
                    changed += 1

            except Exception as ex:
                failed += 1
                if len(failures) < 30:
                    failures.append("Elem {} failed: {}".format(e.Id.IntegerValue, ex))
                try:
                    if started:
                        txe.RollBack()
                except Exception:
                    pass

        tg.Assimilate()

    except Exception:
        try:
            tg.RollBack()
        except Exception:
            pass
        raise

    msg = (
        "Scope candidates (type-filtered): {0}\n"
        "Classified 7.5%: {1}\n"
        "Classified 5.0%: {2}\n"
        "Unclassified (system not matched / no system): {3}\n\n"
        "Changed: {4}\n"
        "Failed: {5}\n\n"
        "Failure samples:\n- {6}"
    ).format(
        len(candidates),
        classified_75,
        classified_50,
        unclassified,
        changed,
        failed,
        "\n- ".join(failures) if failures else "None",
    )

    TaskDialog.Show("slope_solver", msg)


if __name__ == "__main__":
    main()
