# -*- coding: utf-8 -*-
__title__ = "mirror_handler"
__doc__ = """Version = 1.0
Date    = 12.28.2025
________________________________________________________________
Description:

________________________________________________________________
How-To:

________________________________________________________________
Author: Emin Avdovic"""

# ==================================================
# Imports
# ==================================================
from Autodesk.Revit.DB import *
from Autodesk.Revit.DB import (
    BuiltInCategory,
    BuiltInParameter,
    DWGExportOptions,
    ElementId,
    FamilySymbol,
    FamilyInstance,
    FBXExportOptions,
    FilteredElementCollector,
    FormatOptions,
    FilterStringRule,
    FilterStringRuleEvaluator,
    FilterStringBeginsWith,
    FilterStringContains,
    FilterStringEquals,
    XYZ,
    Transaction,
    TextNote,
    TextNoteType,
    TextNoteOptions,
    IndependentTag,
    ImageExportOptions,
    ImageFileType,
    ImageResolution,
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
    Category,
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
from System.Collections.Generic import List as ClrList
from Autodesk.Revit.DB import IFailuresPreprocessor, FailureProcessingResult, FailureSeverity

import clr
import System
import System.IO
import os
import subprocess
import datetime
import tempfile
import json


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

# ensure local imports (module_state)
_here = os.path.dirname(__file__)
_parent = os.path.dirname(_here)
for _p in (_here, _parent):
    if _p not in sys.path:
        sys.path.append(_p)
import module_state

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
# Helpers
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


def load_collected_ids():
    """Load ids from collected_latest.json."""
    try:
        collected_path = None
        for d in module_state._candidate_dirs(doc):
            p = os.path.join(d, "collected_latest.json")
            if os.path.isfile(p):
                collected_path = p
                break
        if not collected_path:
            return []
        with open(collected_path, "r") as fp:
            data = json.load(fp)
        ids = (
            data.get("elements", {}).get("valid_ids", [])
            or data.get("elements", {}).get("ids", [])
        )
        if not ids:
            ids = (
                data.get("source_state", {})
                .get("payload", {})
                .get("elements", {})
                .get("ids", [])
            )
        elems = [
            doc.GetElement(ElementId(int(i))) for i in ids if i is not None
        ]
        return [e.Id for e in elems if e and e.IsValidObject]
    except Exception:
        return []


def pick_scopebox(prompt):
    ref = uidoc.Selection.PickObject(
        ObjectType.Element, ScopeBoxSelectionFilter(), prompt
    )
    return doc.GetElement(ref.ElementId)


def mirror_plane_from_scopebox(sb, mode="center", offset_ft=0.0):
    bb = sb.get_BoundingBox(None)
    if not bb or not bb.Transform:
        raise Exception("Scope box has no bounding box.")
    T = bb.Transform
    mn = bb.Min
    mx = bb.Max
    xmid = (mn.X + mx.X) * 0.5
    ymid = (mn.Y + mx.Y) * 0.5
    zmid = (mn.Z + mx.Z) * 0.5

    if mode == "left_face":
        xplane = mn.X
    elif mode == "right_face":
        xplane = mx.X
    elif mode == "offset":
        xplane = xmid + offset_ft
    else:
        xplane = xmid

    plocal = XYZ(xplane, ymid, zmid)
    pworld = T.OfPoint(plocal)
    nworld = T.BasisX
    nworld = XYZ(nworld.X, nworld.Y, 0.0)
    if nworld.GetLength() < 1e-6:
        nworld = XYZ(1, 0, 0)
    nworld = nworld.Normalize()
    plane = Plane.CreateByNormalAndOrigin(nworld, pworld)
    return plane


def ask_mode():
    td = TaskDialog("mirror_handler")
    td.MainInstruction = "Choose mirror mode"
    td.MainContent = (
        "Mirror relative to scope box X axis.\n"
        "None = no mirror.\n"
        "Center = about scope box centerline.\n"
        "Left/Right = about left/right face."
    )
    td.AddCommandLink(TaskDialogCommandLinkId.CommandLink1, "None")
    td.AddCommandLink(TaskDialogCommandLinkId.CommandLink2, "Centerline")
    td.AddCommandLink(TaskDialogCommandLinkId.CommandLink3, "Left face")
    td.AddCommandLink(TaskDialogCommandLinkId.CommandLink4, "Right face")
    res = td.Show()
    if res == TaskDialogResult.CommandLink1:
        return "none"
    if res == TaskDialogResult.CommandLink2:
        return "center"
    if res == TaskDialogResult.CommandLink3:
        return "left_face"
    if res == TaskDialogResult.CommandLink4:
        return "right_face"
    return "none"


def ask_copy():
    td = TaskDialog("mirror_handler")
    td.MainInstruction = "Create a mirrored copy?"
    td.MainContent = "Yes = mirror and keep original. No = mirror in place."
    td.CommonButtons = TaskDialogCommonButtons.Yes | TaskDialogCommonButtons.No
    res = td.Show()
    return res == TaskDialogResult.Yes


def filter_ids(ids):
    ids_ok = ClrList[ElementId]()
    skipped_group = 0
    expanded_assembly = 0
    seen = set()
    for eid in ids:
        e = doc.GetElement(eid)
        if not e or not e.IsValidObject:
            continue
        try:
            if getattr(e, "GroupId", ElementId.InvalidElementId) not in (
                None,
                ElementId.InvalidElementId,
            ):
                skipped_group += 1
                continue
            # if this is an assembly instance, expand to members
            if isinstance(e, AssemblyInstance):
                mem_ids = e.GetMemberIds()
                for mid in mem_ids:
                    if mid.IntegerValue in seen:
                        continue
                    ids_ok.Add(mid)
                    seen.add(mid.IntegerValue)
                expanded_assembly += 1
                continue
            # if element belongs to an assembly, still include it
        except Exception:
            pass
        if eid.IntegerValue in seen:
            continue
        ids_ok.Add(eid)
        seen.add(eid.IntegerValue)
    return ids_ok, skipped_group, expanded_assembly


def main():
    mode = ask_mode()
    if mode == "none":
        TaskDialog.Show("mirror_handler", "Mirror cancelled (mode = None).")
        return
    do_copy = ask_copy()

    try:
        sb = pick_scopebox("Pick TARGET scope box for mirror plane")
    except Exception:
        TaskDialog.Show("mirror_handler", "Scope box selection cancelled.")
        return

    try:
        plane = mirror_plane_from_scopebox(sb, mode=mode)
    except Exception as ex:
        TaskDialog.Show("mirror_handler", "Failed to build mirror plane: {}".format(ex))
        return

    ids = load_collected_ids()
    if not ids:
        TaskDialog.Show(
            "mirror_handler",
            "No ids loaded from collected_latest.json. Run element_collector first.",
        )
        return

    ids_clr, skipped_group, expanded_assembly = filter_ids(ids)
    if ids_clr.Count == 0:
        TaskDialog.Show("mirror_handler", "All elements skipped (group/assembly).")
        return

    mirrored = 0
    failures = 0
    pinned_reset = []
    hard_skipped = []
    created_ids = []
    created_bbox = None

    class SwallowWarnings(IFailuresPreprocessor):
        def __init__(self, err_list):
            self.err_list = err_list

        def PreprocessFailures(self, failuresAccessor):
            try:
                for fmsg in failuresAccessor.GetFailureMessages():
                    sev = fmsg.GetSeverity()
                    if sev == FailureSeverity.Warning:
                        failuresAccessor.DeleteWarning(fmsg)
                    else:
                        # capture description and force rollback
                        try:
                            self.err_list.append(fmsg.GetDescriptionText())
                        except Exception:
                            pass
                        return FailureProcessingResult.ProceedWithRollBack
                return FailureProcessingResult.Continue
            except Exception:
                return FailureProcessingResult.Continue

    def make_opts(tx, err_list):
        opts_local = tx.GetFailureHandlingOptions()
        opts_local.SetFailuresPreprocessor(SwallowWarnings(err_list))
        opts_local.SetClearAfterRollback(True)
        return opts_local

    # Preflight each element in a rollback transaction to avoid hard errors
    allowed_ids = []
    preflight_errors = []
    for eid in ids_clr:
        el = doc.GetElement(eid)
        if not el or not el.IsValidObject:
            continue
        pre = Transaction(doc, "mirror_preflight")
        try:
            pre.SetFailureHandlingOptions(make_opts(pre, preflight_errors))
            pre.Start()
            try:
                ElementTransformUtils.MirrorElements(
                    doc, ClrList[ElementId]([eid]), plane, do_copy
                )
                allowed_ids.append(eid)
            except Exception:
                hard_skipped.append(eid)
            pre.RollBack()
        except Exception:
            try:
                pre.RollBack()
            except Exception:
                pass
            hard_skipped.append(eid)

    if not allowed_ids:
        TaskDialog.Show(
            "mirror_handler",
            "All elements failed mirror preflight; nothing mirrored.",
        )
        return

    run_errors = []
    created_ids = []
    created_bbox = None
    t = Transaction(doc, "Mirror Handler")
    try:
        t.SetFailureHandlingOptions(make_opts(t, run_errors))
        t.Start()
        # handle each id individually so one bad category does not cancel all
        for eid in allowed_ids:
            try:
                el = doc.GetElement(eid)
                if not el or not el.IsValidObject:
                    failures += 1
                    continue
                # unpin temporarily if needed
                try:
                    if hasattr(el, "Pinned") and el.Pinned:
                        el.Pinned = False
                        pinned_reset.append(eid)
                except Exception:
                    pass
                res_ids = ElementTransformUtils.MirrorElements(
                    doc, ClrList[ElementId]([eid]), plane, do_copy
                )
                res_list = list(res_ids)
                mirrored += len(res_list)
                created_ids.extend(res_list)
                # accumulate bbox for visibility hint
                try:
                    for rid in res_list:
                        relem = doc.GetElement(rid)
                        if not relem:
                            continue
                        bb = relem.get_BoundingBox(None)
                        if not bb:
                            continue
                        if created_bbox is None:
                            created_bbox = BoundingBoxXYZ()
                            created_bbox.Min = XYZ(bb.Min.X, bb.Min.Y, bb.Min.Z)
                            created_bbox.Max = XYZ(bb.Max.X, bb.Max.Y, bb.Max.Z)
                        else:
                            created_bbox.Min = XYZ(
                                min(created_bbox.Min.X, bb.Min.X),
                                min(created_bbox.Min.Y, bb.Min.Y),
                                min(created_bbox.Min.Z, bb.Min.Z),
                            )
                            created_bbox.Max = XYZ(
                                max(created_bbox.Max.X, bb.Max.X),
                                max(created_bbox.Max.Y, bb.Max.Y),
                                max(created_bbox.Max.Z, bb.Max.Z),
                            )
                except Exception:
                    failures += 1
        # re-pin anything we unpinned
        for pid in pinned_reset:
            try:
                pel = doc.GetElement(pid)
                if pel and pel.IsValidObject:
                    pel.Pinned = True
            except Exception:
                pass
        t.Commit()
    except Exception:
        try:
            t.RollBack()
        except Exception:
            pass
        TaskDialog.Show("mirror_handler", "Mirror failed; transaction rolled back.")
        return

    # highlight new elements if any
    try:
        if created_ids:
            uidoc.Selection.SetElementIds(ClrList[ElementId](created_ids))
    except Exception:
        pass

    bbox_note = ""
    try:
        if created_bbox:
            cx = (created_bbox.Min.X + created_bbox.Max.X) * 0.5
            cy = (created_bbox.Min.Y + created_bbox.Max.Y) * 0.5
            cz = (created_bbox.Min.Z + created_bbox.Max.Z) * 0.5
            bbox_note = "\nNew bbox center: ({:.3f}, {:.3f}, {:.3f})".format(
                cx, cy, cz
            )
    except Exception:
        bbox_note = ""

    msg = (
        "Mode: {0}\nCopy mode: {1}\n"
        "Mirrored: {2}\n"
        "Failures: {3}\n"
        "Skipped groups: {4}\n"
        "Assemblies expanded: {5}\n"
        "Hard skipped (preflight): {6}\n"
        "Plane normal: ({7:.3f},{8:.3f},{9:.3f}){10}".format(
            mode,
            "Create copy" if do_copy else "In-place",
            mirrored,
            failures,
            skipped_group,
            expanded_assembly,
            len(hard_skipped),
            plane.Normal.X,
            plane.Normal.Y,
            plane.Normal.Z,
            bbox_note,
        )
    )
    TaskDialog.Show("mirror_handler", msg)


if __name__ == "__main__":
    main()
