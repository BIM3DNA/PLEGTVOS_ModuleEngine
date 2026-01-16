# -*- coding: utf-8 -*-
__title__ = "slope_solver.py"
__doc__ = """Version = 1.0
Date    = 16.01.2025
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

# --- Constrants ---

SLOPE_HWA = 0.0075  # 7.5 mm / 1000 mm
SLOPE_VWA = 0.0050  # 5.0 mm / 1000 mm

HWA_GROUP_NAME = "HWA Option A"
VWA_GROUP_NAME = "VWA Option A"

HWA_ASM_NAME_TOKEN = "Flex Pipes Assembly HWA Option A"
VWA_ASM_NAME_TOKEN = "BG GC01"

PIPE_TYPE_TOKEN = "NLRS_52_PI_PVC U3 Grijs OD_Dyka"
FLEX_TYPE_TOKEN = "Flex - Round"
DUCT_TYPE_TOKEN = "DYKA AIR Buis Rond"

# --- Helpers ---


def _safe_name(e):
    try:
        return e.Name or ""
    except Exception:
        return ""


def get_elem_type_name(doc, e):
    try:
        tid = e.GetTypeId()
        t = doc.GetElement(tid) if tid and tid != ElementId.InvalidElementId else None
        return _safe_name(t)
    except Exception:
        return ""


def get_group_slope(doc, e):
    try:
        gid = getattr(e, "GroupId", ElementId.InvalidElementId)
        if not gid or gid == ElementId.InvalidElementId:
            return None
        g = doc.GetElement(gid)
        if not g:
            return None
        gt = g.GroupType
        gname = _safe_name(gt)
        if HWA_GROUP_NAME in gname:
            return SLOPE_HWA
        elif VWA_GROUP_NAME in gname:
            return SLOPE_VWA
    except Exception:
        pass
    return None


def get_assembly_slope(doc, e):
    # Works for many elements: AssemblyInstanceId on element
    try:
        aid = getattr(e, "AssemblyInstanceId", ElementId.InvalidElementId)
        if not aid or aid == ElementId.InvalidElementId:
            return None
        asm = doc.GetElement(aid)
        if not asm:
            return None
        # Assembly Instance name/type strings vary; we do token matching
        n = _safe_name(asm)
        # some builds store type name differently; this is best-effort
        if HWA_ASM_NAME_TOKEN in n:
            return SLOPE_HWA
        elif VWA_ASM_NAME_TOKEN in n:
            return SLOPE_VWA
    except Exception:
        pass
    return None


def get_target_slope(doc, e):
    # Priority: group > assembly > type/category fallback
    s = get_group_slope(doc, e)
    if s is not None:
        return s
    s = get_assembly_slope(doc, e)
    if s is not None:
        return s

    # fallback by type name token
    tname = get_elem_type_name(doc, e)
    if PIPE_TYPE_TOKEN in tname or FLEX_TYPE_TOKEN in tname or DUCT_TYPE_TOKEN in tname:
        # If you truly need to distinguish HWA vs VWA outside containers,
        # you must add a rule here (e.g., by workset, level, system name, etc.)
        return None
    return None


# --- Actual solver for single element ---


def is_mep_curve(e):
    try:
        return isinstance(e.Location, LocationCurve) and e.Location.Curve is not None
    except Exception:
        return False


def set_line_slope_keep_xy(e, slope_ratio, keep_end="start"):
    """
    keep_end: 'start; keeps start Z and adjusts end Z downward / upward to match slope 'end' keeps end Z and adjusts start
    """
    lc = e.Location
    crv = lc.Curve
    if not isinstance(crv, Line):
        return Exception("Non-line curve; skip")

    p0 = crv.GetEndPoint(0)
    p1 = crv.GetEndPoint(1)

    # horizontal distance in XY
    dx = p1.X - p0.X
    dy = p1.Y - p0.Y
    horiz = math.sqrt(dx * dx + dy * dy)
    if horiz < 1e-6:
        raise Exception("Zero horizontal length; skip")

    drop = slope_ratio * horiz  # feet

    # Convention: "slope down along direction from start > end"
    if keep_end == "start":
        new_p0 = XYZ(p0.X, p0.Y, p0.Z)
        new_p1 = XYZ(p1.X, p1.Y, p0.Z - drop)
    else:  # keep end
        new_p1 = XYZ(p1.X, p1.Y, p1.Z)
        new_p0 = XYZ(p0.X, p0.Y, p1.Z + drop)

    lc.Curve = Line.CreateBound(new_p0, new_p1)


# --- Group handling ---


def edit_group_apply_slope(doc, group_inst, slope_ratio, results_log):
    ges = GroupEditScope(doc, "SlopeSolver: Edit Group")
    gdoc = None
    try:
        gdoc = ges.Start(
            group_inst.Id
        )  # returns a document-like context in most builds
        # In some versions, you still modify via `doc` while in scope; test in your environment
        # To keep it pragmatic, use doc.GetElement(memeberId) and try edits.
        for mid in group_inst.GetMemberIds():
            e = doc.GetElement(mid)
            if not e or not e.IsValidObject:
                continue
            if not is_mep_curve(e):
                continue
            try:
                set_line_slope_keep_xy(e, slope_ratio, keep_end="start")
                results_log["group_modified"] += 1
            except Exception as ex:
                results_log["group_failed"] += 1
                results_log["errors"].append(
                    "Group member {}: {}".format(mid.IntegerValue, ex)
                )
        ges.Assimilate()
    except Exception as ex:
        results_log["errors"].append(
            "Group {} edit failed: {}".format(group_inst.Id.IntegerValue, ex)
        )
        try:
            ges.RollBack()
        except Exception:
            pass
