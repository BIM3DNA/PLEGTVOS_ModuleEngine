# -*- coding: utf-8 -*-
__title__ = "slope_solver.py"
__doc__ = """Version = 1.0
Date    = 16.01.2025
________________________________________________________________
Description:
Apply configure slopes to pipes/flex pipes/round ducts inside a picked scope box,
based on group type name / assembly name rules.

Default mode: Scope Box selection (safe).
________________________________________________________________
Author: Emin Avdovic"""

# ==================================================
# Imports
# ==================================================
from Autodesk.Revit.DB import *
from Autodesk.Revit.DB import (
    AssemblyInstance,
    BuiltInCategory,
    BuiltInParameter,
    Category,
    DWGExportOptions,
    ElementId,
    FamilySymbol,
    FamilyInstance,
    FailureProcessingResult,
    FailureSeverity,
    FBXExportOptions,
    FilteredElementCollector,
    FormatOptions,
    FilterStringRule,
    FilterStringRuleEvaluator,
    FilterStringBeginsWith,
    FilterStringContains,
    FilterStringEquals,
    Group,
    GroupType,
    TextNote,
    TextNoteType,
    TextNoteOptions,
    Transaction,
    TransactionGroup,
    IndependentTag,
    ImageExportOptions,
    ImageFileType,
    ImageResolution,
    IFailuresPreprocessor,
    LocationCurve,
    LocationPoint,
    Line,
    MEPCurve,
    UV,
    UnitTypeId,
    Reference,
    TagMode,
    TagOrientation,
    ViewSchedule,
    ViewSheet,
    ViewDuplicateOption,
    ViewDiscipline,
    Viewport,
    ParameterValueProvider,
    ParameterFilterElement,
    ScheduleSheetInstance,
    ScheduleFilter,
    ScheduleFilterType,
    ScheduleSortGroupField,
    ScheduleSortOrder,
    StorageType,
    SectionType,
    XYZ,
)
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
from Autodesk.Revit.UI import *
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.UI import UIDocument
from Autodesk.Revit.UI import UIApplication
from Autodesk.Revit.DB.Structure import *
from Autodesk.Revit.Exceptions import *
from Autodesk.Revit.Attributes import *
from Autodesk.Revit.Exceptions import ArgumentException
from Autodesk.Revit.Exceptions import OperationCanceledException
from System.Collections.Generic import List as ClrList

import clr
import System
import System.IO
import os
import subprocess
import datetime
import tempfile


clr.AddReference("System")
clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")
clr.AddReference("RevitServices")
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")
clr.AddReference("WindowsBase")
from RevitServices.Persistence import DocumentManager
from System.Windows.Forms import (
    FormBorderStyle,
    AnchorStyles,
    AutoScaleMode,
    Form,
    ComboBox,
    ListBox,
    PictureBox,
    PictureBoxSizeMode,
    DataGridView,
    DataGridViewTextBoxColumn,
    DataGridViewButtonColumn,
    DataGridViewAutoSizeColumnsMode,
    DataGridViewSelectionMode,
    DockStyle,
    TextBox,
    Button,
    MessageBox,
    DialogResult,
    Label,
    ScrollBars,
    Application,
)
from System.Drawing import Image, Point, Color, Rectangle, Size
from System.IO import MemoryStream
from System.Windows.Forms import DataGridViewButtonColumn
from pyrevit import script

from System import Array
import math, re, sys

# ==================================================
# Revit Document Setup
# ==================================================
app = __revit__.Application
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

# VERBOSE = False

# def debug(*args):
#     if VERBOSE:
#         print(" ".join([str(a) for a in args]))


# output = script.get_output()
# output.close_others()

try:
    from PIL import Image as PILImage

    PIL_OK = True
except ImportError:
    PIL_OK = False

# ==================================================
# Main Code
# ==================================================


# --- Selection ---
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


# --- Geometry helpers (scope box intersection) ---
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


# --- Classification rules ---
SLOPE_75 = 0.0075  # 7.5 mm / 1000 mm
SLOPE_50 = 0.0050  # 5.0 mm / 1000 mm


def _safe_name(e):
    try:
        return e.Name or ""
    except Exception:
        return ""


def _group_type_name(group_inst):
    try:
        gt = doc.GetElement(group_inst.GetTypeId())
        return _safe_name(gt)
    except Exception:
        return ""


def _assembly_name_for_member(elem):
    """Try to recover assembly instance name/type for a member element."""
    try:
        aid = getattr(elem, "AssemblyInstanceId", ElementId.InvalidElementId)
        if aid and aid != ElementId.InvalidElementId:
            asm = doc.GetElement(aid)
            if asm and asm.IsValidObject:
                # AssemblyInstance.Name often contains instance name; type name may be relevant too
                tname = ""
                try:
                    t = doc.GetElement(asm.GetTypeId())
                    tname = _safe_name(t)
                except Exception:
                    pass
                return (_safe_name(asm) + " " + tname).strip()
    except Exception:
        pass
    return ""


def classify_slope(elem):
    """Return (slope_ratio, reason_string) or (None, reason_string).
    Precedence: Group rules > Assembly rules > None.
    """
    # Group-driven rules (highest precedence)
    try:
        gid = getattr(elem, "GroupId", ElementId.InvalidElementId)
        if gid and gid != ElementId.InvalidElementId:
            ginst = doc.GetElement(gid)
            if ginst and ginst.IsValidObject:
                gtn = _group_type_name(ginst).lower()
                if "hwa option a" in gtn:
                    return (SLOPE_75, "group:HWA Option A")
                if "vwa option a" in gtn:
                    return (SLOPE_50, "group:VWA Option A")
    except Exception:
        pass

    # Assembly-driven rules
    an = _assembly_name_for_member(elem).lower()
    if an:
        if "flex pipes assembly hwa option a" in an:
            return (SLOPE_75, "assembly:Flex Pipes HWA Option A")
        if "bg gc01" in an:
            return (SLOPE_50, "assembly:BG GC01")

    return (None, "unclassified")


# --- Slope application (geometry-level) ---
def horiz_length(p0, p1):
    dx = p1.X - p0.X
    dy = p1.Y - p0.Y
    return math.sqrt(dx * dx + dy * dy)


def set_curve_slope_keep_high_end(elem, slope_ratio):
    """
    Enforce slope magnitude by keeping higher endpoint fixed and lowering the other.
    Works best on straight MEPCurves.
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

    drop = slope_ratio * hl  # feet (unitless ratio * feet)

    # Determine which end is higher
    if p0.Z >= p1.Z:
        high = p0
        low = p1
        high_idx = 0
    else:
        high = p1
        low = p0
        high_idx = 1

    new_low = XYZ(low.X, low.Y, high.Z - drop)

    # Preserve endpoint ordering in the new curve
    if isinstance(crv, Line):
        if high_idx == 0:
            new_crv = Line.CreateBound(high, new_low)
        else:
            new_crv = Line.CreateBound(new_low, high)
        loc.Curve = new_crv
        return

    # Fallback attempt for non-lines: try to rebuild as a line between endpoint
    # (better than no-op; we will refine after we see your failures list)
    if high_idx == 0:
        loc.Curve = Line.CreateBound(high, new_low)
    else:
        loc.Curve = Line.CreateBound(new_low, high)


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


# --- Helpers ---


def _param(elem, bip):
    try:
        p = elem.get_Parameter(bip)
        return p if p and not p.IsReadOnly else None
    except Exception:
        return None


def _try_set_offsets_for_slope(elem, slope_ratio):
    """
    Apply slope by editing Start/End Offset parameters (preferred for Pipe/Duct).
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

    # Determine which endpoint is higher in Z
    if p0.Z >= p1.Z:
        high_idx = 0
    else:
        high_idx = 1

    # Offsets (pipes and ducts share these built-ins in most versions)
    p_start = _param(elem, BuiltInParameter.RBS_START_OFFSET_PARAM)
    p_end = _param(elem, BuiltInParameter.RBS_END_OFFSET_PARAM)

    if not p_start or not p_end:
        return False

    start_off = p_start.AsDouble()
    end_off = p_end.AsDouble()

    if high_idx == 0:
        # start is high, end is low
        p_start.Set(start_off)  # keep
        p_end.Set(start_off - drop)  # enforce drop
    else:
        # end is high, start is low
        p_end.Set(end_off)  # keep
        p_start.Set(end_off - drop)  # enforce drop

    return True


def _try_set_slope_param(elem, slope_ratio):
    """
    Best-effort set of a slope parameter if present (some templates expose it).
    Returns True if set.
    """
    # Pipes typically expose RBS_PIPE_SLOPE_PARAM; ducts may expose similar.
    # Not all templates/versions expose these as writable
    bip_names = [
        "RBS_PIPE_SLOPE",  # may or may not exist
        "RBS_PIPE_SLOPE_PARAM",  # may or may not exist
        "RBS_DUCT_SLOPE",  # may or may not exist
        "RBS_DUCT_SLOPE_PARAM",  # may or may not exist
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

    # fallback by parameter name (depends on template/locale)
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
    Preferred slope application:
    1) Offsets
    2) Slope Parameter (if any)
    3) Last Resort: Rewritee Curve
    """
    did = False
    # 1) offsets (most stable)
    if _try_set_offsets_for_slope(elem, slope_ratio):
        did = True

    # 2) slope param (optional)
    _try_set_slope_param(elem, slope_ratio)

    # 3) last resort curve edit (avoid unless absolutely needed)
    if not did:
        set_curve_slope_keep_high_end(elem, slope_ratio)
        did = True

    return did


class RollbackOnMEPFailures(IFailuresPreprocessor):
    def __init__(self, err_log):
        self.err_log = err_log

    def PreprocessFailures(self, fa):
        try:
            msgs = fa.GetFailureMessages()
            for m in msgs:
                sev = m.GetSeverity()
                if sev == FailureSeverity.Warning:
                    # safe: remove warnings
                    fa.DeleteWarning(m)
                else:
                    # log the real error text and rollback
                    try:
                        self.err_log.append(m.GetDescriptionText())
                    except Exception:
                        self.err_log.append("Non-warning failure (no description).")
                    return FailureProcessingResult.ProceedWithRollBack
            return FailureProcessingResult.Continue
        except Exception:
            return FailureProcessingResult.ProceedWithRollBack


def set_failure_opts(tx, err_log):
    """Attch failure preprocessor to a Transaction (not SubTransaction)"""
    opts = tx.GetFailureHandlingOptions()
    opts.SetFailuresPreprocessor(RollbackOnMEPFailures(err_log))
    opts.SetClearAfterRollback(True)
    tx.SetFailureHandlingOptions(opts)


# --- Collection ---


def collect_candidates_in_scopebox(sb):
    """
    Collect Pipes + Flex Pipes + Ducts by category (robust acress Revit versions/IronPython)
    """
    cats = [
        BuiltInCategory.OST_PipeCurves,
        BuiltInCategory.OST_FlexPipeCurves,
        BuiltInCategory.OST_DuctCurves,
    ]

    inside = []
    for bic in cats:
        try:
            elems = (
                FilteredElementCollector(doc)
                .OfCategory(bic)
                .WhereElementIsNotElementType()
                .ToElements()
            )
        except Exception:
            continue

        for e in elems:
            try:
                if _bbox_intersects_scopebox(e, sb):
                    inside.append(e)
            except Exception:
                pass

    return inside


# --- MAIN ---


def main():
    sb = pick_scopebox("Pick scope box (slope solving region)")
    if not sb:
        TaskDialog.Show("slope_solver", "Cancelled by user (no scope box picked).")
        return

    candidates = collect_candidates_in_scopebox(sb)
    if not candidates:
        TaskDialog.Show(
            "slope_solver", "No pipe/flex pipe/duct candidates found in scope box."
        )
        return

    # Partition by group instance (so we can use GroupEditScope for each group)
    skipped_in_group = 0  # gid_int > list(elem)
    non_group = []

    # Counters / diagnostics
    classified_75 = 0
    classified_50 = 0
    unclassified = 0

    for e in candidates:
        slope, reason = classify_slope(e)
        if slope is None:
            unclassified += 1
            continue

        if abs(slope - SLOPE_75) < 1e-9:
            classified_75 += 1
        elif abs(slope - SLOPE_50) < 1e-9:
            classified_50 += 1

        gid = getattr(e, "GroupId", ElementId.InvalidElementId)
        if gid and gid != ElementId.InvalidElementId:
            skipped_in_group += 1
            continue

        non_group.append(e)

    # --- Execution (single undo) ---
    tg = TransactionGroup(doc, "slope_solver: Apply Slopes")
    tg.Start()

    changed = 0
    failed = 0
    failures = []  # small sample for dialog

    try:
        for e in non_group:
            txe = Transaction(doc, "slope_solver: elem {}".format(e.Id.IntegerValue))
            started = False
            try:
                txe.Start()
                started = True
                set_failure_opts(txe, failures)  # failures list can store strings

                slope, reason = classify_slope(e)
                if slope is None:
                    txe.RollBack()
                    continue

                target = slope

                # IMPORTANT: use MEP-safe applier
                apply_slope_mep_safe(e, target)

                st = txe.Commit()
                if st != TransactionStatus.Committed:
                    failed += 1
                    if len(failures) < 30:
                        failures.append(
                            "TX not commited (elem {})".format(e.Id.IntegerValue)
                        )
                    continue

                # Validate AFTER commit
                actual = achieved_slope_ratio(e)
                if actual is None or abs(actual - target) > 1e-4:
                    failed += 1
                    if len(failures) < 30:
                        failures.append(
                            "Slope mismatch (elem {}): target {:.6f}, actual {}".format(
                                e.Id.IntegerValue, target, actual
                            )
                        )
                else:
                    changed += 1

            except Exception as ex:
                failed += 1
                if len(failures) < 30:
                    failures.append("Elem {}: {}".format(e.Id.IntegerValue, ex))
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

    # Report
    msg = (
        "Scope candidates: {0}\n"
        "Classified 7.5%: {1}\n"
        "Classified 5.0%: {2}\n"
        "Unclassified (skipped): {3}\n"
        "Skipped (in group): {4}\n\n"
        "Changed: {5}\n"
        "Failed: {6}\n\n"
        "Failure samples:\n- {7}"
    ).format(
        len(candidates),
        classified_75,
        classified_50,
        unclassified,
        skipped_in_group,
        changed,
        failed,
        "\n- ".join(failures) if failures else "None",
    )

    TaskDialog.Show("slope_solver", msg)


if __name__ == "__main__":
    main()
