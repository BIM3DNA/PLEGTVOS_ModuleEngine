# -*- coding: utf-8 -*-
__title__ = "transform_engine"
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

# ensure local imports (module_state, etc.)
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
# Selection Filters
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


# ==================================================
# Frame helpers (scope box based)
# ==================================================


def build_frame_from_scopebox(scopebox):
    bb = scopebox.get_BoundingBox(None)
    if not bb or not bb.Transform:
        raise Exception("Scope box has no bounding box/transform.")
    tf = bb.Transform
    dx = bb.Max.X - bb.Min.X
    dy = bb.Max.Y - bb.Min.Y
    bx = tf.BasisX.Normalize()
    by = tf.BasisY.Normalize()
    if dy > dx:
        bx, by = by, bx
    bz = tf.BasisZ.Normalize()
    origin_local = XYZ(
        (bb.Min.X + bb.Max.X) * 0.5,
        (bb.Min.Y + bb.Max.Y) * 0.5,
        (bb.Min.Z + bb.Max.Z) * 0.5,
    )
    origin_world = tf.OfPoint(origin_local)
    by = bz.CrossProduct(bx).Normalize()
    bx = by.CrossProduct(bz).Normalize()
    return {"origin": origin_world, "x": bx, "y": by, "z": bz}


def frame_to_transform(frame):
    t = Transform.Identity
    t.Origin = frame["origin"]
    t.BasisX = frame["x"]
    t.BasisY = frame["y"]
    t.BasisZ = frame["z"]
    return t


def compute_transform(src_frame, tgt_frame):
    src_t = frame_to_transform(src_frame)
    tgt_t = frame_to_transform(tgt_frame)
    return tgt_t.Multiply(src_t.Inverse)


def log_frame(label, frame):
    o = frame["origin"]
    print(
        "{} origin: ({:.3f}, {:.3f}, {:.3f})".format(
            label, float(o.X), float(o.Y), float(o.Z)
        )
    )


def summarize_transform(xf):
    trans = xf.Origin
    bx = xf.BasisX
    angle = math.atan2(bx.Y, bx.X)
    deg = angle * 180.0 / math.pi
    print(
        "Transform: translate ({:.3f}, {:.3f}, {:.3f}), rotateZ {:.3f} deg".format(
            float(trans.X), float(trans.Y), float(trans.Z), float(deg)
        )
    )


# ==================================================
# Main workflow
# ==================================================


def pick_scopebox(prompt):
    ref = uidoc.Selection.PickObject(
        ObjectType.Element, ScopeBoxSelectionFilter(), prompt
    )
    return doc.GetElement(ref.ElementId)


def pick_elements():
    ids = list(uidoc.Selection.GetElementIds())
    if ids:
        return [doc.GetElement(i) for i in ids]
    # fallback to saved collected_latest.json
    try:
        import module_state

        def find_state_file(name):
            for d in module_state._candidate_dirs(doc):
                print("transform_engine: checking {}".format(d))
                p = os.path.join(d, name)
                if os.path.isfile(p):
                    return p
            return None

        collected_path = find_state_file("collected_latest.json")
        if collected_path and os.path.isfile(collected_path):
            with open(collected_path, "r") as fp:
                data = json.load(fp)
            ids_saved = (
                data.get("source_state", {})
                .get("payload", {})
                .get("elements", {})
                .get("ids", [])
            )
            if not ids_saved:
                ids_saved = data.get("elements", {}).get("valid_ids", [])
            elems = [
                doc.GetElement(ElementId(int(i))) for i in ids_saved if i is not None
            ]
            elems = [e for e in elems if e and e.IsValidObject]
            if elems:
                print(
                    "transform_engine: loaded {} ids from {}".format(
                        len(elems), collected_path
                    )
                )
                return elems
    except Exception:
        pass
    # last resort: prompt for selection
    td = TaskDialog("transform_engine")
    td.MainInstruction = "No elements provided"
    td.MainContent = "Use window/box selection now?"
    td.CommonButtons = TaskDialogCommonButtons.Yes | TaskDialogCommonButtons.No
    if td.Show() == TaskDialogResult.Yes:
        try:
            refs = uidoc.Selection.PickObjects(
                ObjectType.Element, "Box-select elements to copy/transform"
            )
            return [doc.GetElement(r.ElementId) for r in refs]
        except Exception:
            return []
    return []


class DupTypeHandler(IDuplicateTypeNamesHandler):
    def OnDuplicateTypeNamesFound(self, args):
        return DuplicateTypeAction.UseDestinationTypes


def main():
    try:
        src_sb = pick_scopebox("Pick SOURCE scope box")
        tgt_sb = pick_scopebox("Pick TARGET scope box")
    except Exception:
        TaskDialog.Show("transform_engine", "Scope box selection cancelled.")
        return

    try:
        src_frame = build_frame_from_scopebox(src_sb)
        tgt_frame = build_frame_from_scopebox(tgt_sb)
    except Exception as ex:
        TaskDialog.Show("transform_engine", "Frame build failed: {}".format(ex))
        return

    log_frame("Source", src_frame)
    log_frame("Target", tgt_frame)
    xf = compute_transform(src_frame, tgt_frame)
    summarize_transform(xf)

    elems = pick_elements()
    elem_ids = [e.Id for e in elems if e and e.IsValidObject]
    if not elem_ids:
        TaskDialog.Show(
            "transform_engine",
            "No elements provided (selection empty and no saved state found).",
        )
        return

    opt = CopyPasteOptions()
    opt.SetDuplicateTypeNamesHandler(DupTypeHandler())
    idlist = ClrList[ElementId]()
    vs_ids = ClrList[ElementId]()
    view_ids = ClrList[ElementId]()
    assembly_ids = set()
    skipped_bad = 0

    def is_view_elem(e):
        return isinstance(e, View)

    for i in elem_ids:
        e = doc.GetElement(i)
        if not e or not e.IsValidObject:
            skipped_bad += 1
            continue
        if is_view_elem(e):
            view_ids.Add(i)
            continue
        try:
            if e.ViewSpecific:
                vs_ids.Add(i)
                continue
        except Exception:
            pass
        # capture assemblies: if member, collect parent assembly instead
        try:
            asm_id = getattr(e, "AssemblyInstanceId", ElementId.InvalidElementId)
            if asm_id and asm_id != ElementId.InvalidElementId:
                assembly_ids.add(asm_id)
                continue
        except Exception:
            pass
        if e.Category is None:
            skipped_bad += 1
            continue
        idlist.Add(i)

    # add assembly instances (unique)
    for aid in assembly_ids:
        idlist.Add(aid)

    vs_copied = 0
    vs_failed = 0
    copied = 0
    views_copied = 0
    views_failed = 0

    t = Transaction(doc, "Transform Engine Copy")
    try:
        t.Start()
        if idlist.Count > 0:
            try:
                new_ids = ElementTransformUtils.CopyElements(doc, idlist, doc, xf, opt)
                copied = len(list(new_ids))
            except Exception:
                # fallback: copy one by one
                copied = 0
                for eid in idlist:
                    try:
                        solo = ClrList[ElementId]()
                        solo.Add(eid)
                        res = ElementTransformUtils.CopyElements(
                            doc, solo, doc, xf, opt
                        )
                        copied += len(list(res))
                    except Exception:
                        skipped_bad += 1
        # attempt view-specific move only if rotation is ~0 (translation only)
        angle = math.atan2(xf.BasisX.Y, xf.BasisX.X)
        if vs_ids.Count > 0 and abs(angle) < 1e-6:
            try:
                translation = xf.Origin
                vs_new = ElementTransformUtils.CopyElements(
                    uidoc.ActiveView, vs_ids, translation
                )
                vs_copied = len(list(vs_new))
            except Exception:
                vs_failed = vs_ids.Count
        elif vs_ids.Count > 0:
            vs_failed = vs_ids.Count
        # attempt views copy if any
        if view_ids.Count > 0:
            try:
                v_new = ElementTransformUtils.CopyElements(doc, view_ids, doc, xf, opt)
                views_copied = len(list(v_new))
            except Exception:
                views_failed = view_ids.Count
        t.Commit()
    except Exception as ex:
        t.RollBack()
        TaskDialog.Show(
            "transform_engine",
            "Copy failed: {}\nModel elems: {}\nView-specific queued: {}\nSkipped invalid: {}".format(
                ex, idlist.Count, vs_ids.Count, skipped_bad
            ),
        )
        return

    TaskDialog.Show(
        "transform_engine",
        "Copied {} element(s).\nView-specific copied: {} | failed/skipped: {}\nViews copied: {} | failed/skipped: {}\nInvalid/unsupported skipped: {}".format(
            copied,
            vs_copied,
            vs_ids.Count - vs_copied + vs_failed,
            views_copied,
            views_failed,
            skipped_bad,
        ),
    )


if __name__ == "__main__":
    main()
