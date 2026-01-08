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
    skipped_details = []  # list of (id, reason, category)

    def is_view_elem(e):
        return isinstance(e, View)

    def cat_name(e):
        try:
            return e.Category.Name if e.Category else "<None>"
        except Exception:
            return "<Error>"

    for i in elem_ids:
        e = doc.GetElement(i)
        if not e or not e.IsValidObject:
            skipped_bad += 1
            skipped_details.append((i.IntegerValue, "invalid", "<None>"))
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
            skipped_details.append((i.IntegerValue, "no category", "<None>"))
            continue
        # skip systems explicitly (non-physical)
        cname = cat_name(e)
        if cname in ("Piping Systems", "Duct Systems"):
            skipped_details.append((i.IntegerValue, "system skipped", cname))
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
    copy_failed_ids = ClrList[ElementId]()
    fail_by_cat = {}
    system_cats = {"Piping Systems", "Duct Systems"}
    mapping_pairs = []  # (source_id, new_id)

    t = Transaction(doc, "Transform Engine Copy")
    try:
        t.Start()
        if idlist.Count > 0:
            try:
                new_ids = ElementTransformUtils.CopyElements(doc, idlist, doc, xf, opt)
                new_list = list(new_ids)
                copied = len(new_list)
                if len(new_list) == idlist.Count:
                    for idx, sid in enumerate(idlist):
                        mapping_pairs.append((sid, new_list[idx]))
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
                        res_list = list(res)
                        copied += len(res_list)
                        if len(res_list) == 1:
                            mapping_pairs.append((eid, res_list[0]))
                    except Exception:
                        skipped_bad += 1
                        copy_failed_ids.Add(eid)
                        try:
                            e = doc.GetElement(eid)
                            cname = cat_name(e)
                            fail_by_cat.setdefault(cname, []).append(eid)
                            skipped_details.append(
                                (eid.IntegerValue, "copy fail", cname)
                            )
                        except Exception:
                            pass
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
        # retry specific categories with pure translation if rotation ~0
        if abs(angle) < 1e-6 and fail_by_cat:
            retry_cats = ["Center line", "Center Line"]
            for catlabel in retry_cats:
                ids_for_cat = fail_by_cat.get(catlabel, [])
                if not ids_for_cat:
                    continue
                try:
                    rl = ClrList[ElementId]()
                    for rid in ids_for_cat:
                        rl.Add(rid)
                    trans_res = ElementTransformUtils.CopyElements(
                        uidoc.ActiveView, rl, xf.Origin
                    )
                    count_new = len(list(trans_res))
                    if count_new:
                        copied += count_new
                        # clear these failures from bookkeeping
                        for rid in ids_for_cat:
                            if rid in copy_failed_ids:
                                copy_failed_ids.Remove(rid)
                        # remove from skipped_details
                        skipped_details = [
                            sd
                            for sd in skipped_details
                            if not (sd[1] == "copy fail" and sd[2] == catlabel)
                        ]
                except Exception:
                    continue
        # retry any failed model ids via pure translation in active view if rotation ~ 0
        if copy_failed_ids.Count > 0 and abs(angle) < 1e-6:
            try:
                retry = ElementTransformUtils.CopyElements(
                    uidoc.ActiveView, copy_failed_ids, xf.Origin
                )
                copied += len(list(retry))
                copy_failed_ids = ClrList[ElementId]()  # clear failures
            except Exception:
                pass
        # attempt views copy if any
        if view_ids.Count > 0:
            try:
                v_new = ElementTransformUtils.CopyElements(doc, view_ids, doc, xf, opt)
                views_copied = len(list(v_new))
            except Exception:
                views_failed = view_ids.Count
        # recreate center lines that still failed by drawing model curves
        if fail_by_cat.get("Center line") or fail_by_cat.get("Center Line"):
            from Autodesk.Revit.DB import SketchPlane, Plane

            for catlabel in ("Center line", "Center Line"):
                ids_for_cat = fail_by_cat.get(catlabel, [])
                for rid in ids_for_cat:
                    try:
                        e = doc.GetElement(rid)
                        loc = getattr(e, "Location", None)
                        if not loc or not hasattr(loc, "Curve"):
                            continue
                        curve = loc.Curve
                        new_curve = curve.CreateTransformed(xf)
                        # build a sketch plane that contains the curve
                        try:
                            dir = new_curve.ComputeDerivatives(0.5, True).BasisX
                        except Exception:
                            dir = None
                        if dir is None:
                            continue
                        normal = dir.CrossProduct(XYZ.BasisZ)
                        if normal.GetLength() < 1e-6:
                            normal = dir.CrossProduct(XYZ.BasisX)
                        if normal.GetLength() < 1e-6:
                            normal = XYZ.BasisZ
                        normal = normal.Normalize()
                        plane = Plane.CreateByNormalAndOrigin(
                            normal, new_curve.GetEndPoint(0)
                        )
                        sp = SketchPlane.Create(doc, plane)
                        mc = doc.Create.NewModelCurve(new_curve, sp)
                        copied += 1
                        # add to mapping (best-effort)
                        mapping_pairs.append((rid, mc.Id))
                        # remove from skipped details
                        skipped_details = [
                            sd
                            for sd in skipped_details
                            if not (sd[1] == "copy fail" and sd[2] == catlabel)
                        ]
                    except Exception:
                        continue
        # recreate center lines that still failed by drawing model curves
        if fail_by_cat.get("Center line") or fail_by_cat.get("Center Line"):
            from Autodesk.Revit.DB import SketchPlane, Plane

            for catlabel in ("Center line", "Center Line"):
                ids_for_cat = fail_by_cat.get(catlabel, [])
                for rid in ids_for_cat:
                    try:
                        e = doc.GetElement(rid)
                        loc = getattr(e, "Location", None)
                        if not loc or not hasattr(loc, "Curve"):
                            continue
                        curve = loc.Curve
                        new_curve = curve.CreateTransformed(xf)
                        # build a sketch plane that contains the curve
                        try:
                            dir = new_curve.ComputeDerivatives(0.5, True).BasisX
                        except Exception:
                            dir = None
                        if dir is None:
                            continue
                        # choose a normal not parallel to dir
                        normal = dir.CrossProduct(XYZ.BasisZ)
                        if normal.GetLength() < 1e-6:
                            normal = dir.CrossProduct(XYZ.BasisX)
                        if normal.GetLength() < 1e-6:
                            normal = XYZ.BasisZ
                        normal = normal.Normalize()
                        plane = Plane.CreateByNormalAndOrigin(
                            normal, new_curve.GetEndPoint(0)
                        )
                        sp = SketchPlane.Create(doc, plane)
                        doc.Create.NewModelCurve(new_curve, sp)
                        copied += 1
                        # remove from skipped details
                        skipped_details = [
                            sd
                            for sd in skipped_details
                            if not (sd[1] == "copy fail" and sd[2] == catlabel)
                        ]
                    except Exception:
                        continue
        t.Commit()
    except Exception as ex:
        t.RollBack()
        TaskDialog.Show(
            "transform_engine",
            "Copy failed: {}\nModel elems: {}\nView-specific queued: {}\nSkipped invalid: {}".format(
                ex, idlist.Count, vs_ids.Count, skipped_bad
            ),
        )
        # log skipped details
        if skipped_details:
            print("Skipped (partial list):")
            for sid, reason, cat in skipped_details[:50]:
                print(" - Id {} | {} | {}".format(sid, reason, cat))
        return

    # assign systems to copied pipes/ducts based on source mapping
    sys_set = 0
    sys_fail = 0
    if mapping_pairs:
        for sid, nid in mapping_pairs:
            try:
                src = doc.GetElement(sid)
                dst = doc.GetElement(nid)
                if not src or not dst or not src.IsValidObject or not dst.IsValidObject:
                    continue
                catname = cat_name(src)
                if catname.lower().startswith("pipe"):
                    param = src.get_Parameter(BuiltInParameter.RBS_PIPING_SYSTEM_TYPE_PARAM)
                    dstp = dst.get_Parameter(BuiltInParameter.RBS_PIPING_SYSTEM_TYPE_PARAM)
                elif catname.lower().startswith("duct"):
                    param = src.get_Parameter(BuiltInParameter.RBS_DUCT_SYSTEM_TYPE_PARAM)
                    dstp = dst.get_Parameter(BuiltInParameter.RBS_DUCT_SYSTEM_TYPE_PARAM)
                else:
                    continue
                if param and dstp and not dstp.IsReadOnly:
                    stid = param.AsElementId()
                    if stid and stid != ElementId.InvalidElementId:
                        dstp.Set(stid)
                        sys_set += 1
                    else:
                        sys_fail += 1
            except Exception:
                sys_fail += 1

    # print skipped summary
    if skipped_details:
        cat_counts = {}
        for _, reason, cat in skipped_details:
            key = reason + " :: " + cat
            cat_counts[key] = cat_counts.get(key, 0) + 1
        print("Skipped breakdown (reason :: category):")
        for k, v in sorted(cat_counts.items(), key=lambda x: -x[1])[:20]:
            print(" - {} : {}".format(k, v))
        print("Total skipped detailed: {}".format(len(skipped_details)))

    TaskDialog.Show(
        "transform_engine",
        "Copied {} element(s).\nView-specific copied: {} | failed/skipped: {}\nViews copied: {} | failed/skipped: {}\nInvalid/unsupported skipped: {}\nSystems set: {} | failed: {}".format(
            copied,
            vs_copied,
            vs_ids.Count - vs_copied + vs_failed,
            views_copied,
            views_failed,
            skipped_bad,
            sys_set,
            sys_fail,
        ),
    )


if __name__ == "__main__":
    main()
