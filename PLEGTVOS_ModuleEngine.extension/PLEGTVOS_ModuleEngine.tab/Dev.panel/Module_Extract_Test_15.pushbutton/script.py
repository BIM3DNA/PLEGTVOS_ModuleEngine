# -*- coding: utf-8 -*-
__title__ = "Extract\nTest"
__doc__ = """Phase 2 prototype: create a TEST module RVT from a scope box.

Safety model:
- The active source document is never modified and never closed.
- The source RVT is copied with the filesystem.
- Revit opens the copied RVT as a separate document.
- Deletions and SaveAs run only in that copied document.
"""

from Autodesk.Revit.DB import (
    AssemblyInstance,
    BuiltInCategory,
    BuiltInParameter,
    CategoryType,
    DetachFromCentralOption,
    ElementId,
    ElementType,
    FilteredElementCollector,
    FailureProcessingResult,
    FailureSeverity,
    IFailuresPreprocessor,
    Grid,
    Group,
    ImportInstance,
    Level,
    ModelPathUtils,
    OpenOptions,
    RevitLinkInstance,
    SaveAsOptions,
    Transaction,
    TransactionStatus,
    View,
    ViewSchedule,
    ViewSheet,
    WorksetConfiguration,
    WorksetConfigurationOption,
    WorksharingSaveAsOptions,
    XYZ,
)
from Autodesk.Revit.UI import TaskDialog, TaskDialogCommonButtons, TaskDialogResult
from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType

import json
import os
import shutil
import sys
from collections import defaultdict
from datetime import datetime

try:
    from Autodesk.Revit.DB import AssemblyViewUtils
except Exception:
    AssemblyViewUtils = None
from System.Collections.Generic import List

try:
    from System.Windows.Forms import DialogResult, SaveFileDialog
except Exception:
    DialogResult = None
    SaveFileDialog = None

_here = os.path.dirname(__file__)
_parent = os.path.dirname(_here)
for _p in (_here, _parent):
    if _p not in sys.path:
        sys.path.append(_p)

import module_state

app = __revit__.Application
uidoc = __revit__.ActiveUIDocument
source_doc = uidoc.Document

TOOL_NAME = "Module Extract Test"
SCHEMA_VERSION = 1
TOL = 1e-6
DEFAULT_EXPORT_DIR = (
    r"C:\Users\bim3d\OneDrive\Documenten\_PLEGTVOS_ModuleEngine\exports"
)
DEBUG_FULL_ID_LISTS = False
DEFAULT_DETACH_MODE = "DISCARD_WORKSETS"
ALLOW_PRESERVE_WORKSETS_FALLBACK = False
ALLOW_DELETE_FULLY_OUTSIDE_ASSEMBLIES = True
ALLOW_DISASSEMBLE_MIXED_ASSEMBLIES = False


def _bic(name):
    try:
        return getattr(BuiltInCategory, name)
    except Exception:
        return None


TARGET_CATEGORIES = set(
    [
        int(x)
        for x in [
            _bic("OST_PipeCurves"),
            _bic("OST_PipeFitting"),
            _bic("OST_PipeAccessory"),
            _bic("OST_PipeInsulations"),
            _bic("OST_PlumbingFixtures"),
            _bic("OST_DuctCurves"),
            _bic("OST_DuctFitting"),
            _bic("OST_DuctAccessory"),
            _bic("OST_DuctInsulations"),
            _bic("OST_MechanicalEquipment"),
            _bic("OST_DuctTerminal"),
            _bic("OST_GenericModel"),
            _bic("OST_Conduit"),
            _bic("OST_ConduitFitting"),
            _bic("OST_CableTray"),
            _bic("OST_CableTrayFitting"),
            _bic("OST_FlexPipeCurves"),
            _bic("OST_FlexDuctCurves"),
            _bic("OST_ElectricalEquipment"),
            _bic("OST_ElectricalFixtures"),
            _bic("OST_LightingFixtures"),
        ]
        if x is not None
    ]
)

MEP_CURVE_CATEGORIES = set(
    [
        int(x)
        for x in [
            _bic("OST_PipeCurves"),
            _bic("OST_DuctCurves"),
            _bic("OST_Conduit"),
            _bic("OST_CableTray"),
            _bic("OST_FlexPipeCurves"),
            _bic("OST_FlexDuctCurves"),
        ]
        if x is not None
    ]
)

INFRA_CATEGORIES = set(
    [
        int(x)
        for x in [
            _bic("OST_Levels"),
            _bic("OST_Grids"),
            _bic("OST_VolumeOfInterest"),
            _bic("OST_ProjectBasePoint"),
            _bic("OST_SurveyPoint"),
            _bic("OST_IOS_GeoSite"),
            _bic("OST_ProjectInformation"),
            _bic("OST_Materials"),
            _bic("OST_MaterialAssets"),
            _bic("OST_PipingSystem"),
            _bic("OST_DuctSystem"),
            _bic("OST_PipeSegments"),
            _bic("OST_Cameras"),
            _bic("OST_Sun"),
        ]
        if x is not None
    ]
)

VIEW_LIKE_CATEGORIES = set(
    [
        int(x)
        for x in [
            _bic("OST_Views"),
            _bic("OST_Sheets"),
            _bic("OST_Schedules"),
            _bic("OST_LegendComponents"),
            _bic("OST_Cameras"),
        ]
        if x is not None
    ]
)

LINKED_MODEL_CATEGORIES = set(
    [
        int(x)
        for x in [
            _bic("OST_RvtLinks"),
            _bic("OST_ImportObjectStyles"),
            _bic("OST_CADLinkType"),
        ]
        if x is not None
    ]
)


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


class DeleteFailurePreprocessor(IFailuresPreprocessor):
    def __init__(self, messages):
        self.messages = messages

    def PreprocessFailures(self, failures_accessor):
        has_error = False
        try:
            failures = list(failures_accessor.GetFailureMessages())
        except Exception:
            failures = []
        for failure in failures:
            severity_text = "Unknown"
            definition_id_text = None
            try:
                severity_text = str(failure.GetSeverity())
            except Exception:
                pass
            try:
                definition_id = failure.GetFailureDefinitionId()
                definition_id_text = str(definition_id)
            except Exception:
                definition_id_text = None
            try:
                text = failure.GetDescriptionText()
                if text:
                    if definition_id_text:
                        self.messages.append(
                            "[{0}] {1} | failure_definition_id: {2}".format(
                                severity_text, text, definition_id_text
                            )
                        )
                    else:
                        self.messages.append("[{0}] {1}".format(severity_text, text))
            except Exception:
                pass
            try:
                severity = failure.GetSeverity()
                if severity == FailureSeverity.Warning:
                    failures_accessor.DeleteWarning(failure)
                else:
                    has_error = True
            except Exception:
                has_error = True
        if has_error:
            return FailureProcessingResult.ProceedWithRollBack
        return FailureProcessingResult.Continue


def timestamp():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def file_stamp():
    return datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")


def id_int(elem_or_id):
    try:
        return elem_or_id.Id.IntegerValue
    except Exception:
        try:
            return elem_or_id.IntegerValue
        except Exception:
            return None


def get_category_id(element):
    try:
        if element.Category:
            return element.Category.Id.IntegerValue
    except Exception:
        pass
    return None


def get_category_name(element):
    try:
        if element.Category and element.Category.Name:
            return element.Category.Name
    except Exception:
        pass
    return "<None>"


def normalize_category_name(element):
    text = " ".join((get_category_name(element) or "<None>").strip().split())
    if not text:
        return "<None>"
    normalized = text.title()
    for src, dst in {"Rvt": "RVT", "Cad": "CAD", "Mep": "MEP", "Hvac": "HVAC"}.items():
        normalized = normalized.replace(src, dst)
    return normalized


def bbox_corners(bbox):
    mn = bbox.Min
    mx = bbox.Max
    return [
        XYZ(mn.X, mn.Y, mn.Z),
        XYZ(mn.X, mn.Y, mx.Z),
        XYZ(mn.X, mx.Y, mn.Z),
        XYZ(mn.X, mx.Y, mx.Z),
        XYZ(mx.X, mn.Y, mn.Z),
        XYZ(mx.X, mn.Y, mx.Z),
        XYZ(mx.X, mx.Y, mn.Z),
        XYZ(mx.X, mx.Y, mx.Z),
    ]


def get_world_bbox(element_or_bbox):
    try:
        bbox = element_or_bbox
        if hasattr(element_or_bbox, "get_BoundingBox"):
            bbox = element_or_bbox.get_BoundingBox(None)
        if not bbox:
            return None
        transform = getattr(bbox, "Transform", None)
        points = []
        for point in bbox_corners(bbox):
            try:
                points.append(transform.OfPoint(point) if transform else point)
            except Exception:
                points.append(point)
        return {
            "min": XYZ(
                min(p.X for p in points),
                min(p.Y for p in points),
                min(p.Z for p in points),
            ),
            "max": XYZ(
                max(p.X for p in points),
                max(p.Y for p in points),
                max(p.Z for p in points),
            ),
        }
    except Exception:
        return None


def bbox_to_dict(world_bbox):
    return {
        "min": [world_bbox["min"].X, world_bbox["min"].Y, world_bbox["min"].Z],
        "max": [world_bbox["max"].X, world_bbox["max"].Y, world_bbox["max"].Z],
    }


def point_inside_bbox(point, world_bbox):
    mn = world_bbox["min"]
    mx = world_bbox["max"]
    return (
        point.X >= mn.X - TOL
        and point.X <= mx.X + TOL
        and point.Y >= mn.Y - TOL
        and point.Y <= mx.Y + TOL
        and point.Z >= mn.Z - TOL
        and point.Z <= mx.Z + TOL
    )


def bbox_relation_to_scope(element_bbox_world, scope_bbox_world):
    if not element_bbox_world:
        return "UNKNOWN"
    elem_min = element_bbox_world["min"]
    elem_max = element_bbox_world["max"]
    scope_min = scope_bbox_world["min"]
    scope_max = scope_bbox_world["max"]
    if (
        elem_min.X >= scope_min.X - TOL
        and elem_max.X <= scope_max.X + TOL
        and elem_min.Y >= scope_min.Y - TOL
        and elem_max.Y <= scope_max.Y + TOL
        and elem_min.Z >= scope_min.Z - TOL
        and elem_max.Z <= scope_max.Z + TOL
    ):
        return "INSIDE"
    if (
        elem_max.X < scope_min.X - TOL
        or elem_min.X > scope_max.X + TOL
        or elem_max.Y < scope_min.Y - TOL
        or elem_min.Y > scope_max.Y + TOL
        or elem_max.Z < scope_min.Z - TOL
        or elem_min.Z > scope_max.Z + TOL
    ):
        return "OUTSIDE"
    return "CROSSING"


def safe_param_text(doc, element, bip):
    try:
        param = element.get_Parameter(bip)
        if not param:
            return None
        value = param.AsValueString() or param.AsString()
        if value:
            return value
        eid = param.AsElementId()
        if eid and eid != ElementId.InvalidElementId:
            target = doc.GetElement(eid)
            if target:
                return getattr(target, "Name", None) or str(eid.IntegerValue)
    except Exception:
        pass
    return None


def get_type_name(doc, element):
    try:
        type_id = element.GetTypeId()
        if type_id and type_id != ElementId.InvalidElementId:
            elem_type = doc.GetElement(type_id)
            if elem_type:
                return getattr(elem_type, "Name", None)
    except Exception:
        pass
    return None


def get_mep_system_info(doc, element):
    return {
        "system_type": safe_param_text(
            doc, element, BuiltInParameter.RBS_PIPING_SYSTEM_TYPE_PARAM
        )
        or safe_param_text(doc, element, BuiltInParameter.RBS_DUCT_SYSTEM_TYPE_PARAM),
        "system_classification": safe_param_text(
            doc, element, BuiltInParameter.RBS_SYSTEM_CLASSIFICATION_PARAM
        ),
        "system_name": safe_param_text(
            doc, element, BuiltInParameter.RBS_SYSTEM_NAME_PARAM
        ),
        "type_name": get_type_name(doc, element),
    }


def get_endpoint_report(element, scope_world_bbox):
    report = {
        "endpoint_0_inside": None,
        "endpoint_1_inside": None,
        "both_inside": None,
        "both_outside": None,
        "one_inside_one_outside": None,
    }
    try:
        curve = getattr(getattr(element, "Location", None), "Curve", None)
        if not curve:
            return report
        e0 = point_inside_bbox(curve.GetEndPoint(0), scope_world_bbox)
        e1 = point_inside_bbox(curve.GetEndPoint(1), scope_world_bbox)
        report["endpoint_0_inside"] = e0
        report["endpoint_1_inside"] = e1
        report["both_inside"] = e0 and e1
        report["both_outside"] = (not e0) and (not e1)
        report["one_inside_one_outside"] = e0 != e1
    except Exception:
        pass
    return report


def is_scope_box(element):
    return get_category_id(element) == int(BuiltInCategory.OST_VolumeOfInterest)


def is_view_specific(element):
    try:
        owner_view_id = element.OwnerViewId
        return owner_view_id and owner_view_id != ElementId.InvalidElementId
    except Exception:
        return False


def is_view_or_type(element):
    if isinstance(element, ElementType):
        return True
    if isinstance(element, (View, ViewSheet, ViewSchedule)):
        return True
    try:
        if isinstance(element, View) or getattr(element, "IsTemplate", False):
            return True
    except Exception:
        pass
    return False


def is_infrastructure(element):
    cid = get_category_id(element)
    if cid in INFRA_CATEGORIES:
        return True
    if isinstance(element, (Level, Grid)):
        return True
    return False


def is_linked_or_imported(element):
    cid = get_category_id(element)
    if cid in LINKED_MODEL_CATEGORIES:
        return True
    try:
        return isinstance(element, (RevitLinkInstance, ImportInstance))
    except Exception:
        return False


def is_candidate_model_element(element):
    if not element or not getattr(element, "IsValidObject", False):
        return False
    if (
        is_view_or_type(element)
        or is_view_specific(element)
        or is_infrastructure(element)
    ):
        return False
    cid = get_category_id(element)
    if cid not in TARGET_CATEGORIES or cid in VIEW_LIKE_CATEGORIES:
        return False
    try:
        return element.Category and element.Category.CategoryType == CategoryType.Model
    except Exception:
        return False


def classify_element(element, scope_world_bbox):
    element_bbox = get_world_bbox(element)
    bucket = bbox_relation_to_scope(element_bbox, scope_world_bbox)
    endpoint_report = None
    if get_category_id(element) in MEP_CURVE_CATEGORIES:
        endpoint_report = get_endpoint_report(element, scope_world_bbox)
    return bucket, endpoint_report


def selected_scope_box():
    try:
        selected_ids = list(uidoc.Selection.GetElementIds())
    except Exception:
        selected_ids = []
    scopes = []
    for elem_id in selected_ids:
        elem = source_doc.GetElement(elem_id)
        if elem and is_scope_box(elem):
            scopes.append(elem)
    if len(scopes) == 1:
        return scopes[0]
    if len(scopes) > 1:
        TaskDialog.Show(TOOL_NAME, "Select exactly one scope box.")
        return None
    try:
        ref = uidoc.Selection.PickObject(
            ObjectType.Element,
            ScopeBoxSelectionFilter(),
            "Pick one scope box for TEST extraction",
        )
        return source_doc.GetElement(ref) if ref else None
    except Exception:
        return None


def new_breakdown():
    return {
        "INSIDE": defaultdict(int),
        "OUTSIDE": defaultdict(int),
        "CROSSING": defaultdict(int),
        "UNKNOWN": defaultdict(int),
    }


def as_regular_dict(value):
    if isinstance(value, defaultdict):
        return dict((k, as_regular_dict(v)) for k, v in value.items())
    if isinstance(value, dict):
        return dict((k, as_regular_dict(v)) for k, v in value.items())
    return value


def build_classification(doc, scope_box):
    scope_world_bbox = get_world_bbox(scope_box)
    if not scope_world_bbox:
        raise Exception("Scope box has no usable bounding box.")

    buckets = {"INSIDE": [], "OUTSIDE": [], "CROSSING": [], "UNKNOWN": []}
    counts = {
        "total_candidates": 0,
        "inside": 0,
        "outside": 0,
        "crossing": 0,
        "unknown": 0,
    }
    category_breakdown = new_breakdown()
    mep_breakdown = new_breakdown()
    crossing_mep_count = 0
    unknown_mep_count = 0

    for element in FilteredElementCollector(doc).WhereElementIsNotElementType():
        if is_linked_or_imported(element):
            continue
        try:
            if isinstance(element, (Group, AssemblyInstance)):
                continue
        except Exception:
            pass
        if not is_candidate_model_element(element):
            continue

        bucket, endpoint_report = classify_element(element, scope_world_bbox)
        buckets[bucket].append(element.Id.IntegerValue)
        counts["total_candidates"] += 1
        counts[bucket.lower()] += 1
        category_name = normalize_category_name(element)
        category_breakdown[bucket][category_name] += 1
        if get_category_id(element) in MEP_CURVE_CATEGORIES:
            if bucket == "CROSSING":
                crossing_mep_count += 1
            elif bucket == "UNKNOWN":
                unknown_mep_count += 1
        mep_info = get_mep_system_info(doc, element)
        if any(mep_info.values()):
            key = "{} | {} | {} | {} | {}".format(
                category_name,
                mep_info.get("system_type") or "<None>",
                mep_info.get("system_classification") or "<None>",
                mep_info.get("system_name") or "<None>",
                mep_info.get("type_name") or "<None>",
            )
            mep_breakdown[bucket][key] += 1

    can_continue = (
        counts["inside"] > 0 and crossing_mep_count == 0 and unknown_mep_count == 0
    )
    if can_continue:
        reason = "Ready: physical elements found and no crossing/unknown MEP curves."
    elif counts["inside"] <= 0:
        reason = "Blocked: no inside physical module candidates were found."
    elif crossing_mep_count > 0:
        reason = "Blocked: crossing MEP curve elements require review."
    else:
        reason = "Blocked: unknown MEP curve elements require review."

    return {
        "scope_box": {
            "id": scope_box.Id.IntegerValue,
            "name": getattr(scope_box, "Name", None),
            "bbox": bbox_to_dict(scope_world_bbox),
        },
        "counts": counts,
        "refined_counts": {
            "inside_physical_count": counts["inside"],
            "outside_physical_count": counts["outside"],
            "crossing_physical_count": counts["crossing"],
            "unknown_physical_count": counts["unknown"],
            "crossing_mep_count": crossing_mep_count,
            "unknown_mep_count": unknown_mep_count,
        },
        "extraction_readiness": {
            "can_continue_to_phase_2": can_continue,
            "reason": reason,
            "inside_physical_count": counts["inside"],
            "outside_physical_count": counts["outside"],
            "crossing_physical_count": counts["crossing"],
            "unknown_physical_count": counts["unknown"],
            "crossing_mep_count": crossing_mep_count,
            "unknown_mep_count": unknown_mep_count,
        },
        "buckets": buckets,
        "category_breakdown": as_regular_dict(category_breakdown),
        "mep_breakdown": as_regular_dict(mep_breakdown),
    }


def find_scope_box_in_doc(doc, source_scope_id, source_scope_name):
    try:
        elem = doc.GetElement(ElementId(int(source_scope_id)))
        if elem and is_scope_box(elem):
            return elem
    except Exception:
        pass
    for elem in (
        FilteredElementCollector(doc)
        .OfCategory(BuiltInCategory.OST_VolumeOfInterest)
        .WhereElementIsNotElementType()
    ):
        try:
            if getattr(elem, "Name", None) == source_scope_name:
                return elem
        except Exception:
            pass
    return None


def safe_filename(text):
    invalid = '<>:"/\\|?*'
    cleaned = "".join("_" if ch in invalid else ch for ch in (text or "Module"))
    cleaned = "_".join(cleaned.strip().split())
    return cleaned or "Module"


def choose_output_path(scope_name):
    if not os.path.isdir(DEFAULT_EXPORT_DIR):
        os.makedirs(DEFAULT_EXPORT_DIR)
    default_name = "{}_Module_Test_v7.rvt".format(safe_filename(scope_name))
    default_path = os.path.join(DEFAULT_EXPORT_DIR, default_name)
    if os.path.exists(default_path):
        default_name = "{}_Module_Test_{}.rvt".format(
            safe_filename(scope_name), file_stamp()
        )
        default_path = os.path.join(DEFAULT_EXPORT_DIR, default_name)
    if SaveFileDialog and DialogResult:
        try:
            dialog = SaveFileDialog()
            dialog.Title = "Save TEST module RVT"
            dialog.Filter = "Revit Project (*.rvt)|*.rvt"
            dialog.InitialDirectory = DEFAULT_EXPORT_DIR
            dialog.FileName = default_name
            result = dialog.ShowDialog()
            if result == DialogResult.OK and dialog.FileName:
                return dialog.FileName
            return None
        except Exception as ex:
            print("SaveFileDialog unavailable, using default path. {}".format(ex))
    td = TaskDialog(TOOL_NAME)
    td.MainInstruction = "Use automatic output path?"
    td.MainContent = default_path
    td.CommonButtons = TaskDialogCommonButtons.Ok | TaskDialogCommonButtons.Cancel
    if td.Show() != TaskDialogResult.Ok:
        return None
    return default_path


def make_working_copy(source_path, output_path):
    out_dir = os.path.dirname(output_path)
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    base = os.path.splitext(os.path.basename(output_path))[0]
    working_path = os.path.join(out_dir, "{}_working_{}.rvt".format(base, file_stamp()))
    shutil.copy2(source_path, working_path)
    return working_path


def open_working_copy(working_path, source_is_workshared):
    diagnostics = {
        "copy_opened_detached": False,
        "detach_option_used": None,
        "copy_doc_is_workshared_after_open": None,
        "open_worksets_option": None,
        "open_failure": None,
    }
    try:
        model_path = ModelPathUtils.ConvertUserVisiblePathToModelPath(working_path)
    except Exception:
        model_path = working_path

    def _open_options(detach_option=None):
        opts = OpenOptions()
        try:
            workset_config = WorksetConfiguration(
                WorksetConfigurationOption.OpenAllWorksets
            )
            opts.SetOpenWorksetsConfiguration(workset_config)
            diagnostics["open_worksets_option"] = "OpenAllWorksets"
        except Exception as ex:
            diagnostics["open_worksets_option"] = "failed: {}".format(ex)
        if detach_option is not None:
            try:
                opts.DetachFromCentralOption = detach_option
            except Exception:
                try:
                    opts.SetDetachFromCentralOption(detach_option)
                except Exception:
                    raise
        return opts

    if source_is_workshared:
        failures = []
        if DEFAULT_DETACH_MODE == "DISCARD_WORKSETS":
            primary_label = "DetachAndDiscardWorksets"
            primary_option = DetachFromCentralOption.DetachAndDiscardWorksets
            fallback_label = "DetachAndPreserveWorksets"
            fallback_option = DetachFromCentralOption.DetachAndPreserveWorksets
        else:
            primary_label = "DetachAndPreserveWorksets"
            primary_option = DetachFromCentralOption.DetachAndPreserveWorksets
            fallback_label = "DetachAndDiscardWorksets"
            fallback_option = DetachFromCentralOption.DetachAndDiscardWorksets

        try:
            diagnostics["detach_option_used"] = primary_label
            copy_doc = app.OpenDocumentFile(model_path, _open_options(primary_option))
            diagnostics["copy_opened_detached"] = True
            diagnostics["copy_doc_is_workshared_after_open"] = getattr(
                copy_doc, "IsWorkshared", None
            )
            return copy_doc, diagnostics
        except Exception as ex:
            failures.append("{} failed: {}".format(primary_label, ex))
        if ALLOW_PRESERVE_WORKSETS_FALLBACK:
            try:
                diagnostics["detach_option_used"] = fallback_label
                copy_doc = app.OpenDocumentFile(
                    model_path, _open_options(fallback_option)
                )
                diagnostics["copy_opened_detached"] = True
                diagnostics["copy_doc_is_workshared_after_open"] = getattr(
                    copy_doc, "IsWorkshared", None
                )
                diagnostics["open_failure"] = " | ".join(failures) if failures else None
                return copy_doc, diagnostics
            except Exception as ex:
                failures.append("{} failed: {}".format(fallback_label, ex))
        diagnostics["open_failure"] = " | ".join(failures)
        raise Exception(
            "Could not open working copy detached from central: {}".format(
                diagnostics["open_failure"] or "unknown error"
            )
        )

    try:
        copy_doc = app.OpenDocumentFile(model_path, _open_options())
    except Exception:
        copy_doc = app.OpenDocumentFile(working_path)
    diagnostics["copy_doc_is_workshared_after_open"] = getattr(
        copy_doc, "IsWorkshared", None
    )
    return copy_doc, diagnostics


def ids_to_element_ids(ids):
    return [ElementId(int(i)) for i in ids]


def category_sort_key(doc, eid_int):
    elem = doc.GetElement(ElementId(int(eid_int)))
    if not elem:
        return 99
    cid = get_category_id(elem)
    order = [
        [_bic("OST_PipeInsulations"), _bic("OST_DuctInsulations")],
        [_bic("OST_PipeAccessory"), _bic("OST_DuctAccessory")],
        [
            _bic("OST_PipeFitting"),
            _bic("OST_DuctFitting"),
            _bic("OST_ConduitFitting"),
            _bic("OST_CableTrayFitting"),
        ],
        [
            _bic("OST_PipeCurves"),
            _bic("OST_DuctCurves"),
            _bic("OST_Conduit"),
            _bic("OST_CableTray"),
            _bic("OST_FlexPipeCurves"),
            _bic("OST_FlexDuctCurves"),
        ],
    ]
    for idx, group in enumerate(order):
        if cid in set(int(x) for x in group if x is not None):
            return idx
    return 10


def existing_ids(doc, ids):
    result = []
    for eid_int in ids:
        try:
            if doc.GetElement(ElementId(int(eid_int))):
                result.append(eid_int)
        except Exception:
            pass
    return result


def sample_ids(ids, limit=200):
    return list(ids or [])[:limit]


def mark_delete_rolled_back(result):
    attempted = result.get("attempted_delete_count", 0)
    result["attempted_outside_deleted_count"] = 0
    result["dependent_deleted_count"] = 0
    result["remaining_attempted_outside_count"] = attempted
    result["result"] = "FAILED"


def assembly_member_ids(assembly):
    try:
        return [eid.IntegerValue for eid in assembly.GetMemberIds()]
    except Exception as ex:
        return None, str(ex)


def empty_assembly_precheck():
    return {
        "total_assemblies": 0,
        "fully_outside_assembly_ids": [],
        "mixed_assembly_ids": [],
        "inside_assembly_ids": [],
        "unknown_assembly_ids": [],
        "deleted_assembly_ids": [],
        "blocked_by_mixed_assemblies": False,
        "blocked_by_unknown_assemblies": False,
        "allow_delete_fully_outside_assemblies": ALLOW_DELETE_FULLY_OUTSIDE_ASSEMBLIES,
        "allow_disassemble_mixed_assemblies": ALLOW_DISASSEMBLE_MIXED_ASSEMBLIES,
        "samples": [],
    }


def analyze_assemblies(copy_doc, classification):
    outside_ids = set(classification["buckets"]["OUTSIDE"])
    inside_ids = set(classification["buckets"]["INSIDE"])
    crossing_ids = set(classification["buckets"]["CROSSING"])
    unknown_ids = set(classification["buckets"]["UNKNOWN"])
    physical_ids = set()
    physical_ids.update(outside_ids)
    physical_ids.update(inside_ids)
    physical_ids.update(crossing_ids)
    physical_ids.update(unknown_ids)

    report = empty_assembly_precheck()
    for assembly in FilteredElementCollector(copy_doc).OfClass(AssemblyInstance):
        assembly_id = assembly.Id.IntegerValue
        report["total_assemblies"] += 1
        member_result = assembly_member_ids(assembly)
        if isinstance(member_result, tuple):
            member_ids, error = member_result
        else:
            member_ids = member_result
            error = None
        if member_ids is None:
            report["unknown_assembly_ids"].append(assembly_id)
            report["blocked_by_unknown_assemblies"] = True
            report["samples"].append(
                {
                    "assembly_id": assembly_id,
                    "classification": "UNKNOWN_ASSEMBLY",
                    "reason": "GetMemberIds failed: {}".format(error),
                    "member_ids_sample_first_50": [],
                    "outside_member_ids_sample_first_50": [],
                    "protected_member_ids_sample_first_50": [],
                }
            )
            continue

        member_set = set(member_ids)
        physical_member_ids = sorted(member_set.intersection(physical_ids))
        outside_member_ids = sorted(member_set.intersection(outside_ids))
        inside_member_ids = sorted(member_set.intersection(inside_ids))
        crossing_member_ids = sorted(member_set.intersection(crossing_ids))
        unknown_member_ids = sorted(member_set.intersection(unknown_ids))
        protected_member_ids = sorted(
            set(inside_member_ids + crossing_member_ids + unknown_member_ids)
        )

        if outside_member_ids and protected_member_ids:
            classification_name = "MIXED_ASSEMBLY"
            report["mixed_assembly_ids"].append(assembly_id)
            report["blocked_by_mixed_assemblies"] = True
        elif outside_member_ids and not protected_member_ids:
            classification_name = "FULLY_OUTSIDE_ASSEMBLY"
            report["fully_outside_assembly_ids"].append(assembly_id)
        elif protected_member_ids and not outside_member_ids:
            classification_name = "INSIDE_ASSEMBLY"
            report["inside_assembly_ids"].append(assembly_id)
        elif physical_member_ids:
            classification_name = "UNKNOWN_ASSEMBLY"
            report["unknown_assembly_ids"].append(assembly_id)
            report["blocked_by_unknown_assemblies"] = True
        else:
            classification_name = "NO_PHYSICAL_MEMBERS"

        if len(report["samples"]) < 100 and (
            classification_name not in ["INSIDE_ASSEMBLY", "NO_PHYSICAL_MEMBERS"]
            or len(report["samples"]) < 20
        ):
            report["samples"].append(
                {
                    "assembly_id": assembly_id,
                    "classification": classification_name,
                    "member_ids_sample_first_50": sample_ids(member_ids, 50),
                    "physical_member_ids_sample_first_50": sample_ids(
                        physical_member_ids, 50
                    ),
                    "outside_member_ids_sample_first_50": sample_ids(
                        outside_member_ids, 50
                    ),
                    "inside_member_ids_sample_first_50": sample_ids(
                        inside_member_ids, 50
                    ),
                    "crossing_member_ids_sample_first_50": sample_ids(
                        crossing_member_ids, 50
                    ),
                    "unknown_member_ids_sample_first_50": sample_ids(
                        unknown_member_ids, 50
                    ),
                    "protected_member_ids_sample_first_50": sample_ids(
                        protected_member_ids, 50
                    ),
                }
            )

    for key in [
        "fully_outside_assembly_ids",
        "mixed_assembly_ids",
        "inside_assembly_ids",
        "unknown_assembly_ids",
    ]:
        report[key] = sorted(set(report[key]))
    return report


def empty_assembly_associated_cleanup():
    return {
        "fully_outside_assembly_ids": [],
        "associated_view_ids_to_delete": [],
        "associated_sheet_ids_to_delete": [],
        "associated_other_ids_to_delete": [],
        "unconfirmed_fully_outside_assembly_ids": [],
        "collection_errors": [],
        "collection_warnings": [],
        "collection_method": None,
        "deleted_associated_view_ids": [],
        "deleted_associated_sheet_ids": [],
        "deleted_associated_other_ids": [],
        "deleted_associated_view_count": 0,
        "deleted_associated_sheet_count": 0,
        "deleted_associated_other_count": 0,
    }


def element_id_to_int(value):
    if value is None:
        return None
    try:
        if isinstance(value, ElementId):
            return value.IntegerValue
    except Exception:
        pass
    try:
        if hasattr(value, "IntegerValue"):
            return value.IntegerValue
    except Exception:
        pass
    try:
        return int(value)
    except Exception:
        return None


def safe_lookup_parameter_int(element, names):
    for name in names:
        try:
            param = element.LookupParameter(name)
            if not param:
                continue
            try:
                eid = param.AsElementId()
                eid_int = element_id_to_int(eid)
                if eid_int is not None and eid_int > 0:
                    return eid_int
            except Exception:
                pass
            try:
                value_int = param.AsInteger()
                if value_int and value_int > 0:
                    return value_int
            except Exception:
                pass
        except Exception:
            pass
    return None


def associated_assembly_id_from_element(element):
    attribute_names = [
        "AssociatedAssemblyInstanceId",
        "AssemblyInstanceId",
        "OwnerAssemblyInstanceId",
        "ReferencedAssemblyInstanceId",
    ]
    for attr_name in attribute_names:
        try:
            eid_int = element_id_to_int(getattr(element, attr_name))
            if eid_int is not None and eid_int > 0:
                return eid_int
        except Exception:
            pass
    return safe_lookup_parameter_int(
        element,
        [
            "Associated Assembly Instance",
            "Associated Assembly",
            "Assembly Instance",
            "Assembly",
        ],
    )


def add_associated_cleanup_id(copy_doc, cleanup, eid_int):
    elem = copy_doc.GetElement(ElementId(int(eid_int)))
    if not elem:
        return
    if isinstance(elem, ViewSheet):
        cleanup["associated_sheet_ids_to_delete"].append(eid_int)
    elif isinstance(elem, (View, ViewSchedule)):
        cleanup["associated_view_ids_to_delete"].append(eid_int)
    else:
        cleanup["associated_other_ids_to_delete"].append(eid_int)


def collect_assembly_associated_cleanup(copy_doc, assembly_precheck):
    cleanup = empty_assembly_associated_cleanup()
    assembly_ids = sorted(set(assembly_precheck.get("fully_outside_assembly_ids", [])))
    cleanup["fully_outside_assembly_ids"] = assembly_ids
    if not assembly_ids:
        cleanup["collection_method"] = "none_no_fully_outside_assemblies"
        return cleanup

    assembly_id_set = set(assembly_ids)
    found_by_assembly = dict((eid, set()) for eid in assembly_ids)
    api_errors = []
    api_available = AssemblyViewUtils is not None
    if api_available:
        cleanup["collection_method"] = "AssemblyViewUtils.GetAssociatedViews"
        for assembly_id in assembly_ids:
            try:
                associated_ids = AssemblyViewUtils.GetAssociatedViews(
                    copy_doc, ElementId(int(assembly_id))
                )
                for associated_id in associated_ids:
                    associated_int = associated_id.IntegerValue
                    found_by_assembly[assembly_id].add(associated_int)
                    add_associated_cleanup_id(copy_doc, cleanup, associated_int)
            except Exception as ex:
                api_errors.append(
                    "Assembly {} associated view lookup failed: {}".format(
                        assembly_id, ex
                    )
                )
    else:
        cleanup["collection_method"] = "fallback_view_sheet_association_scan"

    cleanup["collection_method"] = (
        cleanup["collection_method"] + " + fallback_view_sheet_association_scan"
        if cleanup["collection_method"]
        else "fallback_view_sheet_association_scan"
    )
    try:
        view_like = []
        view_like.extend(list(FilteredElementCollector(copy_doc).OfClass(View)))
        view_like.extend(list(FilteredElementCollector(copy_doc).OfClass(ViewSheet)))
        view_like.extend(list(FilteredElementCollector(copy_doc).OfClass(ViewSchedule)))
        seen_view_like = set()
        for elem in view_like:
            elem_id = elem.Id.IntegerValue
            if elem_id in seen_view_like:
                continue
            seen_view_like.add(elem_id)
            associated_assembly_id = associated_assembly_id_from_element(elem)
            if associated_assembly_id in assembly_id_set:
                found_by_assembly[associated_assembly_id].add(elem_id)
                add_associated_cleanup_id(copy_doc, cleanup, elem_id)
    except Exception as ex:
        if (not api_available) or api_errors:
            cleanup["collection_errors"].append(
                "Fallback associated view/sheet scan failed: {}".format(ex)
            )
        else:
            cleanup.setdefault("collection_warnings", []).append(
                "Fallback associated view/sheet scan failed after API lookup succeeded: {}".format(
                    ex
                )
            )

    if api_errors:
        cleanup["collection_warnings"] = cleanup.get("collection_warnings", []) + (
            api_errors
        )
    for assembly_id in assembly_ids:
        if not found_by_assembly.get(assembly_id):
            cleanup["unconfirmed_fully_outside_assembly_ids"].append(assembly_id)
            cleanup["collection_warnings"].append(
                "No associated assembly views/sheets found or confirmed for assembly {}; proceeding because assembly is fully outside.".format(
                    assembly_id
                )
            )
    cleanup["unconfirmed_fully_outside_assembly_ids"] = sorted(
        set(cleanup["unconfirmed_fully_outside_assembly_ids"])
    )

    cleanup["associated_view_ids_to_delete"] = sorted(
        set(cleanup["associated_view_ids_to_delete"])
    )
    cleanup["associated_sheet_ids_to_delete"] = sorted(
        set(cleanup["associated_sheet_ids_to_delete"])
    )
    cleanup["associated_other_ids_to_delete"] = sorted(
        set(cleanup["associated_other_ids_to_delete"])
    )
    return cleanup


def delete_order_from_precheck(precheck, outside_ids, associated_cleanup):
    assembly_ids = []
    if ALLOW_DELETE_FULLY_OUTSIDE_ASSEMBLIES:
        assembly_ids = list(precheck.get("fully_outside_assembly_ids", []))
    return {
        "associated_assembly_views_first": (
            associated_cleanup.get("associated_view_ids_to_delete", [])
            + associated_cleanup.get("associated_sheet_ids_to_delete", [])
            + associated_cleanup.get("associated_other_ids_to_delete", [])
        ),
        "assembly_instances_second": assembly_ids,
        "physical_outside_after_assemblies": list(outside_ids),
    }


def delete_outside_in_copy(copy_doc, classification):
    outside_ids = sorted(
        classification["buckets"]["OUTSIDE"],
        key=lambda eid: category_sort_key(copy_doc, eid),
    )
    attempted_outside_ids = list(outside_ids)
    protected_ids = set(classification["buckets"]["INSIDE"])
    protected_ids.update(classification["buckets"]["CROSSING"])
    protected_ids.update(classification["buckets"]["UNKNOWN"])
    protected_inside_ids = set(classification["buckets"]["INSIDE"])
    protected_crossing_unknown_ids = set(classification["buckets"]["CROSSING"])
    protected_crossing_unknown_ids.update(classification["buckets"]["UNKNOWN"])

    result = {
        "attempted_delete_count": len(outside_ids),
        "revit_deleted_return_count": 0,
        "attempted_outside_deleted_count": 0,
        "remaining_attempted_outside_count": len(outside_ids),
        "dependent_deleted_count": 0,
        "failed_delete_count": 0,
        "protected_deleted_count": 0,
        "deleted_ids_sample_first_200": [],
        "remaining_attempted_outside_ids_sample_first_200": sample_ids(outside_ids),
        "protected_deleted_ids_sample_first_200": [],
        "protected_inside_missing_ids_sample_first_200": [],
        "protected_crossing_unknown_missing_ids_sample_first_200": [],
        "failed_ids_sample_first_200": [],
        "failure_messages": [],
        "assembly_precheck": empty_assembly_precheck(),
        "assembly_associated_cleanup": empty_assembly_associated_cleanup(),
        "delete_order": {
            "associated_assembly_views_first": [],
            "assembly_instances_second": [],
            "physical_outside_after_assemblies": sample_ids(outside_ids),
        },
        "transaction_start_status": None,
        "transaction_commit_status": None,
        "result": "FAILED",
    }
    if DEBUG_FULL_ID_LISTS:
        result["attempted_outside_ids"] = attempted_outside_ids[:]
        result["revit_deleted_return_ids"] = []
        result["remaining_attempted_outside_ids"] = []
        result["protected_deleted_ids"] = []
        result["failed_ids"] = []

    assembly_precheck = analyze_assemblies(copy_doc, classification)
    result["assembly_precheck"] = assembly_precheck
    if (
        assembly_precheck.get("blocked_by_mixed_assemblies")
        and not ALLOW_DISASSEMBLE_MIXED_ASSEMBLIES
    ):
        result["result"] = "FAILED_PRECHECK"
        result["failure_messages"].append(
            "Mixed assemblies contain both protected and outside physical members; aborting before deletion."
        )
        return result
    if assembly_precheck.get("blocked_by_unknown_assemblies"):
        result["result"] = "FAILED_PRECHECK"
        result["failure_messages"].append(
            "Unknown assembly membership prevented safe deletion; aborting before deletion."
        )
        return result
    if (
        assembly_precheck.get("fully_outside_assembly_ids")
        and not ALLOW_DELETE_FULLY_OUTSIDE_ASSEMBLIES
    ):
        result["result"] = "FAILED_PRECHECK"
        result["failure_messages"].append(
            "Fully outside assemblies were found but assembly deletion is disabled."
        )
        return result

    associated_cleanup = collect_assembly_associated_cleanup(
        copy_doc, assembly_precheck
    )
    result["assembly_associated_cleanup"] = associated_cleanup
    for cleanup_warning in associated_cleanup.get("collection_warnings", []):
        result["failure_messages"].append(cleanup_warning)
    if associated_cleanup.get("collection_errors"):
        result["result"] = "FAILED_PRECHECK"
        result["failure_messages"].append(
            "Associated assembly view/sheet cleanup could not be confirmed; aborting before deletion."
        )
        for cleanup_error in associated_cleanup.get("collection_errors", []):
            result["failure_messages"].append(cleanup_error)
        return result

    delete_order = delete_order_from_precheck(
        assembly_precheck, outside_ids, associated_cleanup
    )
    result["delete_order"] = {
        "associated_assembly_views_first": sample_ids(
            delete_order["associated_assembly_views_first"]
        ),
        "assembly_instances_second": sample_ids(
            delete_order["assembly_instances_second"]
        ),
        "physical_outside_after_assemblies": sample_ids(
            delete_order["physical_outside_after_assemblies"]
        ),
    }
    if DEBUG_FULL_ID_LISTS:
        result["delete_order_full"] = delete_order

    tx = Transaction(copy_doc, "Delete outside physical elements - TEST")
    failure_messages = result["failure_messages"]
    try:
        try:
            opts = tx.GetFailureHandlingOptions()
            opts.SetFailuresPreprocessor(DeleteFailurePreprocessor(failure_messages))
            tx.SetFailureHandlingOptions(opts)
        except Exception as fex:
            failure_messages.append(
                "Could not attach failure preprocessor: {}".format(fex)
            )

        start_status = tx.Start()
        result["transaction_start_status"] = str(start_status)
        if start_status != TransactionStatus.Started:
            failure_messages.append(
                "Transaction did not start: {}".format(start_status)
            )
            result["result"] = "FAILED"
            return result

        revit_deleted_return_ids = []
        try:
            associated_ids = existing_ids(
                copy_doc, delete_order["associated_assembly_views_first"]
            )
            associated_deleted_ids = []
            if associated_ids:
                deleted = copy_doc.Delete(
                    List[ElementId]([ElementId(int(eid)) for eid in associated_ids])
                )
                for deleted_id in deleted:
                    deleted_int = deleted_id.IntegerValue
                    revit_deleted_return_ids.append(deleted_int)
                    if deleted_int in associated_ids:
                        associated_deleted_ids.append(deleted_int)
                associated_deleted_set = set(associated_deleted_ids)
                deleted_view_ids = sorted(
                    associated_deleted_set.intersection(
                        set(associated_cleanup.get("associated_view_ids_to_delete", []))
                    )
                )
                deleted_sheet_ids = sorted(
                    associated_deleted_set.intersection(
                        set(
                            associated_cleanup.get("associated_sheet_ids_to_delete", [])
                        )
                    )
                )
                deleted_other_ids = sorted(
                    associated_deleted_set.intersection(
                        set(
                            associated_cleanup.get("associated_other_ids_to_delete", [])
                        )
                    )
                )
                associated_cleanup["deleted_associated_view_ids"] = deleted_view_ids
                associated_cleanup["deleted_associated_sheet_ids"] = deleted_sheet_ids
                associated_cleanup["deleted_associated_other_ids"] = deleted_other_ids
                associated_cleanup["deleted_associated_view_count"] = len(
                    deleted_view_ids
                )
                associated_cleanup["deleted_associated_sheet_count"] = len(
                    deleted_sheet_ids
                )
                associated_cleanup["deleted_associated_other_count"] = len(
                    deleted_other_ids
                )

            assembly_ids = existing_ids(
                copy_doc, delete_order["assembly_instances_second"]
            )
            if assembly_ids:
                deleted = copy_doc.Delete(
                    List[ElementId]([ElementId(int(eid)) for eid in assembly_ids])
                )
                assembly_deleted_ids = []
                for deleted_id in deleted:
                    deleted_int = deleted_id.IntegerValue
                    revit_deleted_return_ids.append(deleted_int)
                    if deleted_int in assembly_ids:
                        assembly_deleted_ids.append(deleted_int)
                assembly_precheck["deleted_assembly_ids"] = sorted(
                    set(assembly_deleted_ids)
                )
            remaining_outside_for_delete = existing_ids(copy_doc, outside_ids)
            result["delete_order"]["physical_outside_after_assemblies"] = sample_ids(
                remaining_outside_for_delete
            )
            if DEBUG_FULL_ID_LISTS:
                result["delete_order_full"][
                    "physical_outside_after_assemblies"
                ] = remaining_outside_for_delete
            if remaining_outside_for_delete:
                delete_ids = List[ElementId](
                    [ElementId(int(eid)) for eid in remaining_outside_for_delete]
                )
                deleted = copy_doc.Delete(delete_ids)
                for deleted_id in deleted:
                    revit_deleted_return_ids.append(deleted_id.IntegerValue)
        except Exception as ex:
            failure_messages.append("Batch delete failed: {}".format(ex))
            try:
                tx.RollBack()
            except Exception:
                pass
            mark_delete_rolled_back(result)
            result["transaction_commit_status"] = "RolledBack"
            return result

        try:
            copy_doc.Regenerate()
        except Exception as regen_ex:
            failure_messages.append(
                "Regenerate inside delete transaction failed: {}".format(regen_ex)
            )

        protected_inside_missing_in_tx = []
        protected_crossing_unknown_missing_in_tx = []
        for protected_id in protected_inside_ids:
            try:
                if not copy_doc.GetElement(ElementId(int(protected_id))):
                    protected_inside_missing_in_tx.append(protected_id)
            except Exception:
                pass
        for protected_id in protected_crossing_unknown_ids:
            try:
                if not copy_doc.GetElement(ElementId(int(protected_id))):
                    protected_crossing_unknown_missing_in_tx.append(protected_id)
            except Exception:
                pass

        revit_deleted_return_ids = sorted(set(revit_deleted_return_ids))
        result["revit_deleted_return_count"] = len(revit_deleted_return_ids)
        result["deleted_ids_sample_first_200"] = sample_ids(revit_deleted_return_ids)
        protected_deleted_in_tx = sorted(
            set(
                protected_inside_missing_in_tx
                + protected_crossing_unknown_missing_in_tx
            )
        )
        result["protected_deleted_count"] = len(protected_deleted_in_tx)
        result["protected_deleted_ids_sample_first_200"] = sample_ids(
            protected_deleted_in_tx
        )
        result["protected_inside_missing_ids_sample_first_200"] = sample_ids(
            protected_inside_missing_in_tx
        )
        result["protected_crossing_unknown_missing_ids_sample_first_200"] = sample_ids(
            protected_crossing_unknown_missing_in_tx
        )
        if DEBUG_FULL_ID_LISTS:
            result["revit_deleted_return_ids"] = revit_deleted_return_ids
            result["protected_deleted_ids"] = protected_deleted_in_tx

        if protected_deleted_in_tx:
            tx.RollBack()
            mark_delete_rolled_back(result)
            result["transaction_commit_status"] = "RolledBack"
            result["failure_messages"].append(
                "Protected elements would be deleted; transaction rolled back."
            )
        else:
            commit_status = tx.Commit()
            result["transaction_commit_status"] = str(commit_status)
            if commit_status == TransactionStatus.Committed:
                remaining_attempted_outside_ids = existing_ids(
                    copy_doc, attempted_outside_ids
                )
                protected_inside_missing_ids = []
                protected_crossing_unknown_missing_ids = []
                for protected_id in protected_inside_ids:
                    try:
                        if not copy_doc.GetElement(ElementId(int(protected_id))):
                            protected_inside_missing_ids.append(protected_id)
                    except Exception:
                        pass
                for protected_id in protected_crossing_unknown_ids:
                    try:
                        if not copy_doc.GetElement(ElementId(int(protected_id))):
                            protected_crossing_unknown_missing_ids.append(protected_id)
                    except Exception:
                        pass
                protected_deleted_ids = sorted(
                    set(
                        protected_inside_missing_ids
                        + protected_crossing_unknown_missing_ids
                    )
                )
                attempted_outside_deleted_count = len(attempted_outside_ids) - len(
                    remaining_attempted_outside_ids
                )
                dependent_deleted_count = (
                    len(revit_deleted_return_ids) - attempted_outside_deleted_count
                )
                if dependent_deleted_count < 0:
                    dependent_deleted_count = 0
                result["attempted_outside_deleted_count"] = (
                    attempted_outside_deleted_count
                )
                result["remaining_attempted_outside_count"] = len(
                    remaining_attempted_outside_ids
                )
                result["dependent_deleted_count"] = dependent_deleted_count
                result["protected_deleted_count"] = len(protected_deleted_ids)
                result["remaining_attempted_outside_ids_sample_first_200"] = sample_ids(
                    remaining_attempted_outside_ids
                )
                result["protected_deleted_ids_sample_first_200"] = sample_ids(
                    protected_deleted_ids
                )
                result["protected_inside_missing_ids_sample_first_200"] = sample_ids(
                    protected_inside_missing_ids
                )
                result["protected_crossing_unknown_missing_ids_sample_first_200"] = (
                    sample_ids(protected_crossing_unknown_missing_ids)
                )
                if DEBUG_FULL_ID_LISTS:
                    result["remaining_attempted_outside_ids"] = (
                        remaining_attempted_outside_ids
                    )
                    result["protected_deleted_ids"] = protected_deleted_ids
                result["result"] = "DELETE COMMITTED"
            else:
                mark_delete_rolled_back(result)
                failure_messages.append(
                    "Transaction commit status was not Committed: {}".format(
                        commit_status
                    )
                )
    except Exception as ex:
        result["failure_messages"].append("Fatal delete exception: {}".format(ex))
        try:
            tx.RollBack()
        except Exception:
            pass
        mark_delete_rolled_back(result)
        result["transaction_commit_status"] = "RolledBack"

    result["deleted_count"] = result["attempted_outside_deleted_count"]
    return result


def save_json_report(payload):
    state_dir, label = module_state.get_state_dir(source_doc)
    if not os.path.isdir(state_dir):
        os.makedirs(state_dir)
    stamp = file_stamp()
    ts_path = os.path.join(
        state_dir, "module_extract_test_report_{}.json".format(stamp)
    )
    latest_path = os.path.join(state_dir, "module_extract_test_latest.json")
    payload["json_report_path"] = ts_path
    payload["json_latest_path"] = latest_path
    payload["state_dir_label"] = label
    with open(ts_path, "w") as fp:
        json.dump(payload, fp, indent=2, sort_keys=True)
    with open(latest_path, "w") as fp:
        json.dump(payload, fp, indent=2, sort_keys=True)
    return ts_path, latest_path, label


def save_copy_as_output(copy_doc, output_path):
    diagnostics = {
        "saveas_used_worksharing_options": False,
        "saveas_central": False,
        "saveas_exception": None,
    }
    opts = SaveAsOptions()
    opts.OverwriteExistingFile = True
    try:
        opts.MaximumBackups = 1
    except Exception:
        pass
    try:
        if getattr(copy_doc, "IsWorkshared", False):
            ws_opts = WorksharingSaveAsOptions()
            ws_opts.SaveAsCentral = True
            opts.SetWorksharingOptions(ws_opts)
            diagnostics["saveas_used_worksharing_options"] = True
            diagnostics["saveas_central"] = True
        copy_doc.SaveAs(output_path, opts)
        return diagnostics
    except Exception as ex:
        diagnostics["saveas_exception"] = str(ex)
        raise


def outside_category_sample(doc, outside_ids, limit=100):
    sample = {}
    for eid_int in outside_ids[:limit]:
        try:
            elem = doc.GetElement(ElementId(int(eid_int)))
            if elem:
                cat = normalize_category_name(elem)
                sample[cat] = sample.get(cat, 0) + 1
        except Exception:
            pass
    return sample


def verify_saved_output(output_path, scope_id, scope_name, attempted_outside_ids):
    verify_doc = None
    try:
        verify_doc = app.OpenDocumentFile(output_path)
        verify_scope = find_scope_box_in_doc(verify_doc, scope_id, scope_name)
        if not verify_scope:
            raise Exception("Scope box was not found in saved output.")
        verification = build_classification(verify_doc, verify_scope)
        verify_outside_ids = verification["buckets"]["OUTSIDE"]
        attempted_set = set(int(x) for x in attempted_outside_ids)
        verify_outside_set = set(int(x) for x in verify_outside_ids)
        intersection = sorted(verify_outside_set.intersection(attempted_set))
        return {
            "verify_doc_path": getattr(verify_doc, "PathName", None),
            "output_is_workshared": getattr(verify_doc, "IsWorkshared", None),
            "verify_counts": verification["counts"],
            "verify_refined_counts": verification["refined_counts"],
            "verify_outside_ids_sample_first_100": sample_ids(verify_outside_ids, 100),
            "verify_outside_category_breakdown": outside_category_sample(
                verify_doc, verify_outside_ids, 100
            ),
            "verify_outside_intersects_attempted": len(intersection) > 0,
            "verify_outside_attempted_intersection_count": len(intersection),
            "verify_outside_attempted_intersection_sample_first_100": sample_ids(
                intersection, 100
            ),
        }
    finally:
        if verify_doc:
            try:
                verify_doc.Close(False)
            except Exception as close_ex:
                print("Could not close verify document: {}".format(close_ex))


def output_file_size_mb(path):
    try:
        if path and os.path.isfile(path):
            return round(os.path.getsize(path) / (1024.0 * 1024.0), 2)
    except Exception:
        pass
    return None


def split_failure_messages(
    messages, accepted, transaction_commit_status, verify_outside_count
):
    blocking_errors = []
    non_blocking_warnings = []
    for msg in messages or []:
        text = str(msg)
        lower = text.lower()
        group_or_assembly = ("group" in lower) or ("assembl" in lower)
        if accepted:
            non_blocking_warnings.append(text)
        elif (
            group_or_assembly
            and str(transaction_commit_status).endswith("Committed")
            and verify_outside_count == 0
        ):
            non_blocking_warnings.append(text)
        elif any(
            key in lower
            for key in [
                "failed",
                "error",
                "fatal",
                "rolled back",
                "not committed",
                "protected",
                "saveas",
                "could not",
                "abort",
                "mixed assemblies",
                "unknown assembly",
            ]
        ):
            blocking_errors.append(text)
        else:
            non_blocking_warnings.append(text)
    return blocking_errors, non_blocking_warnings


def build_acceptance(payload):
    verify_counts = payload.get("verify_counts", {})
    pre_counts = payload.get("pre_counts", {})
    pre_refined = payload.get("pre_refined_counts", {})
    verify_crossing = verify_counts.get("crossing", 0)
    pre_crossing = pre_counts.get("crossing", 0)
    crossing_allowed = verify_crossing == 0 or (
        pre_refined.get("crossing_mep_count", 0) == 0
        and verify_crossing <= pre_crossing
    )
    accepted = (
        bool(payload.get("output_saved"))
        and bool(payload.get("verify_doc_path"))
        and verify_counts.get("inside", 0) > 0
        and verify_counts.get("outside", 0) == 0
        and crossing_allowed
        and verify_counts.get("unknown", 0) == 0
        and payload.get("delete_result", {}).get("failed_delete_count", 0) == 0
        and payload.get("delete_result", {}).get("protected_deleted_count", 0) == 0
    )
    if accepted:
        if verify_crossing:
            reason = "Output RVT reopened and verified with preserved non-MEP crossing physical candidates."
        else:
            reason = (
                "Output RVT reopened and verified with only inside physical candidates."
            )
    elif not payload.get("output_saved"):
        reason = "Output RVT was not saved."
    elif not payload.get("verify_doc_path"):
        reason = "Output RVT could not be reopened for verification."
    elif verify_counts.get("outside", 0) != 0:
        reason = "Verification still reports outside physical candidates."
    elif verify_counts.get("unknown", 0) != 0:
        reason = "Verification reports unknown physical candidates."
    elif not crossing_allowed:
        reason = "Verification crossing count exceeded the allowed preserved non-MEP crossing count."
    else:
        reason = "Verification counts did not satisfy extraction acceptance criteria."
    return {
        "source_unchanged": True,
        "output_reopened": bool(payload.get("verify_doc_path")),
        "verify_inside_count": verify_counts.get("inside", 0),
        "verify_outside_count": verify_counts.get("outside", 0),
        "verify_crossing_count": verify_counts.get("crossing", 0),
        "verify_unknown_count": verify_counts.get("unknown", 0),
        "pre_crossing_count": pre_crossing,
        "crossing_allowed": crossing_allowed,
        "accepted": accepted,
        "reason": reason,
    }


def print_report(payload):
    print("=" * 72)
    print("Module Extract Test - Phase 2 PROTOTYPE")
    print("Active source document was not modified by this script.")
    print("=" * 72)
    print("Source document path: {}".format(payload["source_document"].get("path")))
    print("Source is workshared: {}".format(payload.get("source_doc_is_workshared")))
    print("Output is workshared: {}".format(payload.get("output_is_workshared")))
    print("Copied working path: {}".format(payload.get("working_copy_path")))
    print("Output module path: {}".format(payload.get("output_module_path")))
    print("Output file size MB: {}".format(payload.get("output_file_size_mb")))
    print("Copy opened detached: {}".format(payload.get("copy_opened_detached")))
    print("Detach option used: {}".format(payload.get("detach_option_used")))
    print(
        "Copy doc workshared after open: {}".format(
            payload.get("copy_doc_is_workshared_after_open")
        )
    )
    print(
        "SaveAs used worksharing options: {}".format(
            payload.get("saveas_used_worksharing_options")
        )
    )
    print("SaveAs central: {}".format(payload.get("saveas_central")))
    if payload.get("saveas_exception"):
        print("SaveAs exception: {}".format(payload.get("saveas_exception")))
    print(
        "copy_doc.PathName before delete: {}".format(
            payload.get("copy_doc_path_before_delete")
        )
    )
    print(
        "copy_doc.PathName before save: {}".format(
            payload.get("copy_doc_path_before_save")
        )
    )
    print("verify_doc.PathName: {}".format(payload.get("verify_doc_path")))
    print(
        "Scope Box: {} | ElementId {}".format(
            payload["scope_box"].get("name"), payload["scope_box"].get("id")
        )
    )
    print("")
    print("Pre-extraction counts")
    for key, value in payload["pre_counts"].items():
        print(" - {}: {}".format(key, value))
    print("")
    print("Assembly precheck")
    assembly_precheck = payload.get("assembly_precheck", {})
    print(
        " - total assemblies: {}".format(assembly_precheck.get("total_assemblies", 0))
    )
    print(
        " - fully outside assemblies: {} | first 100: {}".format(
            len(assembly_precheck.get("fully_outside_assembly_ids", [])),
            sample_ids(assembly_precheck.get("fully_outside_assembly_ids", []), 100),
        )
    )
    print(
        " - mixed assemblies: {} | first 100: {}".format(
            len(assembly_precheck.get("mixed_assembly_ids", [])),
            sample_ids(assembly_precheck.get("mixed_assembly_ids", []), 100),
        )
    )
    print(
        " - inside assemblies: {} | first 100: {}".format(
            len(assembly_precheck.get("inside_assembly_ids", [])),
            sample_ids(assembly_precheck.get("inside_assembly_ids", []), 100),
        )
    )
    print(
        " - unknown assemblies: {} | first 100: {}".format(
            len(assembly_precheck.get("unknown_assembly_ids", [])),
            sample_ids(assembly_precheck.get("unknown_assembly_ids", []), 100),
        )
    )
    print(
        " - deleted assembly ids: {}".format(
            assembly_precheck.get("deleted_assembly_ids", [])
        )
    )
    print(
        " - blocked by mixed assemblies: {}".format(
            assembly_precheck.get("blocked_by_mixed_assemblies")
        )
    )
    print(
        " - blocked by unknown assemblies: {}".format(
            assembly_precheck.get("blocked_by_unknown_assemblies")
        )
    )
    for sample in assembly_precheck.get("samples", [])[:10]:
        print(" - sample: {}".format(sample))
    print("")
    print("Assembly associated cleanup")
    assembly_cleanup = payload.get("assembly_associated_cleanup", {})
    print(
        " - fully outside assembly ids: {}".format(
            assembly_cleanup.get("fully_outside_assembly_ids", [])
        )
    )
    print(
        " - associated view ids to delete: {}".format(
            assembly_cleanup.get("associated_view_ids_to_delete", [])
        )
    )
    print(
        " - associated sheet ids to delete: {}".format(
            assembly_cleanup.get("associated_sheet_ids_to_delete", [])
        )
    )
    print(
        " - associated other ids to delete: {}".format(
            assembly_cleanup.get("associated_other_ids_to_delete", [])
        )
    )
    print(
        " - unconfirmed fully outside assemblies: {}".format(
            assembly_cleanup.get("unconfirmed_fully_outside_assembly_ids", [])
        )
    )
    print(
        " - collection errors: {}".format(assembly_cleanup.get("collection_errors", []))
    )
    print(
        " - collection warnings: {}".format(
            assembly_cleanup.get("collection_warnings", [])
        )
    )
    print(
        " - deleted associated views: {}".format(
            assembly_cleanup.get("deleted_associated_view_count", 0)
        )
    )
    print(
        " - deleted associated view ids: {}".format(
            assembly_cleanup.get("deleted_associated_view_ids", [])
        )
    )
    print(
        " - deleted associated sheets: {}".format(
            assembly_cleanup.get("deleted_associated_sheet_count", 0)
        )
    )
    print(
        " - deleted associated sheet ids: {}".format(
            assembly_cleanup.get("deleted_associated_sheet_ids", [])
        )
    )
    print("")
    print("Delete order")
    delete_order = payload.get("delete_order", {})
    print(
        " - associated_assembly_views_first: {}".format(
            delete_order.get("associated_assembly_views_first", [])
        )
    )
    print(
        " - assembly_instances_second: {}".format(
            delete_order.get("assembly_instances_second", [])
        )
    )
    print(
        " - physical_outside_after_assemblies: {}".format(
            delete_order.get("physical_outside_after_assemblies", [])
        )
    )
    print("")
    print("Deletion")
    print(
        " - Attempted outside deletions: {}".format(
            payload["delete_result"].get("attempted_delete_count", 0)
        )
    )
    print(
        " - Revit deleted return count: {}".format(
            payload["delete_result"].get("revit_deleted_return_count", 0)
        )
    )
    print(
        " - Attempted outside deleted count: {}".format(
            payload["delete_result"].get("attempted_outside_deleted_count", 0)
        )
    )
    print(
        " - Dependent deleted count: {}".format(
            payload["delete_result"].get("dependent_deleted_count", 0)
        )
    )
    print(
        " - Remaining attempted outside count: {}".format(
            payload["delete_result"].get("remaining_attempted_outside_count", 0)
        )
    )
    print(
        " - Failed delete count: {}".format(
            payload["delete_result"].get("failed_delete_count", 0)
        )
    )
    print(
        " - Protected deleted count: {}".format(
            payload["delete_result"].get("protected_deleted_count", 0)
        )
    )
    print("")
    print("Post-extraction counts from copy_doc memory")
    for key, value in payload.get("post_counts", {}).items():
        print(" - {}: {}".format(key, value))
    print("")
    print("Final verification counts from reopened output RVT")
    for key, value in payload.get("verify_counts", {}).items():
        print(" - {}: {}".format(key, value))
    if payload.get("verify_counts", {}).get("outside", 0) > 0:
        print(
            "Verify outside ids first 100: {}".format(
                payload.get("verify_outside_ids_sample_first_100", [])
            )
        )
        print(
            "Verify outside categories first 100: {}".format(
                payload.get("verify_outside_category_breakdown", {})
            )
        )
        print(
            "Verify outside intersects attempted ids: {} | count {}".format(
                payload.get("verify_outside_intersects_attempted"),
                payload.get("verify_outside_attempted_intersection_count"),
            )
        )
    print("")
    print("Acceptance")
    acceptance = payload.get("acceptance", {})
    print(" - accepted: {}".format(acceptance.get("accepted")))
    print(" - reason: {}".format(acceptance.get("reason")))
    print(" - source_unchanged: {}".format(acceptance.get("source_unchanged")))
    print(" - output_reopened: {}".format(acceptance.get("output_reopened")))
    print(" - verify inside: {}".format(acceptance.get("verify_inside_count")))
    print(" - verify outside: {}".format(acceptance.get("verify_outside_count")))
    print(" - verify crossing: {}".format(acceptance.get("verify_crossing_count")))
    print(" - verify unknown: {}".format(acceptance.get("verify_unknown_count")))
    print(" - pre crossing: {}".format(acceptance.get("pre_crossing_count")))
    print(" - crossing allowed: {}".format(acceptance.get("crossing_allowed")))
    print("")
    print("Result: {}".format(payload.get("result")))
    print("Revit warnings / failure processing messages")
    if payload.get("blocking_errors"):
        print(" - blocking_errors:")
        for msg in payload.get("blocking_errors", [])[:50]:
            print("    {}".format(msg))
    else:
        print(" - blocking_errors: <none>")
    if payload.get("non_blocking_warnings"):
        print(" - non_blocking_warnings:")
        for msg in payload.get("non_blocking_warnings", [])[:50]:
            print("    {}".format(msg))
    else:
        print(" - non_blocking_warnings: <none>")
    if payload["delete_result"].get("failure_messages"):
        print(" - raw messages:")
        for msg in payload["delete_result"]["failure_messages"][:50]:
            print(" - {}".format(msg))
    print("")
    print("JSON latest: {}".format(payload.get("json_latest_path")))


def main():
    if not getattr(source_doc, "PathName", None):
        TaskDialog.Show(
            TOOL_NAME,
            "Source document must be saved to disk before creating a test extraction.",
        )
        return None
    if not os.path.isfile(source_doc.PathName):
        TaskDialog.Show(
            TOOL_NAME,
            "Source RVT path is not a local file:\n{}".format(source_doc.PathName),
        )
        return None

    scope_box = selected_scope_box()
    if not scope_box:
        TaskDialog.Show(TOOL_NAME, "Cancelled. Select or pick one scope box.")
        return None

    pre_source = build_classification(source_doc, scope_box)
    readiness = pre_source["extraction_readiness"]
    if not readiness["can_continue_to_phase_2"]:
        print("Extraction readiness failed: {}".format(readiness["reason"]))
        TaskDialog.Show(TOOL_NAME, readiness["reason"])
        return None

    output_path = choose_output_path(pre_source["scope_box"]["name"])
    if not output_path:
        TaskDialog.Show(TOOL_NAME, "Cancelled. No output path selected.")
        return None
    if (
        os.path.abspath(output_path).lower()
        == os.path.abspath(source_doc.PathName).lower()
    ):
        TaskDialog.Show(TOOL_NAME, "Output path cannot be the active source RVT.")
        return None

    working_path = make_working_copy(source_doc.PathName, output_path)
    copy_doc = None
    payload = None
    source_doc_is_workshared = getattr(source_doc, "IsWorkshared", False)
    copy_open_diagnostics = {
        "copy_opened_detached": False,
        "detach_option_used": None,
        "copy_doc_is_workshared_after_open": None,
        "open_worksets_option": None,
        "open_failure": None,
    }
    try:
        copy_doc, copy_open_diagnostics = open_working_copy(
            working_path, source_doc_is_workshared
        )
        if source_doc_is_workshared and not copy_open_diagnostics.get(
            "copy_opened_detached"
        ):
            raise Exception(
                "Workshared source copy was not opened detached; aborting before deletion."
            )
        copy_scope = find_scope_box_in_doc(
            copy_doc,
            pre_source["scope_box"]["id"],
            pre_source["scope_box"]["name"],
        )
        if not copy_scope:
            raise Exception("Scope box was not found in opened copy.")

        pre_copy = build_classification(copy_doc, copy_scope)
        if not pre_copy["extraction_readiness"]["can_continue_to_phase_2"]:
            raise Exception(pre_copy["extraction_readiness"]["reason"])

        protected_before = {
            "inside": pre_copy["buckets"]["INSIDE"][:],
            "crossing": pre_copy["buckets"]["CROSSING"][:],
            "unknown": pre_copy["buckets"]["UNKNOWN"][:],
        }

        copy_doc_path_before_delete = getattr(copy_doc, "PathName", None)
        delete_result = delete_outside_in_copy(copy_doc, pre_copy)
        post_copy = None
        verify_result = {}
        saveas_diagnostics = {
            "saveas_used_worksharing_options": False,
            "saveas_central": False,
            "saveas_exception": None,
        }
        output_saved = False
        final_result = delete_result["result"]
        if final_result == "DELETE COMMITTED":
            missing_inside = [
                eid
                for eid in protected_before["inside"]
                if not copy_doc.GetElement(ElementId(int(eid)))
            ]
            missing_crossing_unknown = [
                eid
                for eid in protected_before["crossing"] + protected_before["unknown"]
                if not copy_doc.GetElement(ElementId(int(eid)))
            ]
            protected_missing = sorted(set(missing_inside + missing_crossing_unknown))
            if protected_missing:
                delete_result["protected_deleted_count"] = len(protected_missing)
                delete_result["protected_deleted_ids_sample_first_200"] = sample_ids(
                    protected_missing
                )
                delete_result["protected_inside_missing_ids_sample_first_200"] = (
                    sample_ids(missing_inside)
                )
                delete_result[
                    "protected_crossing_unknown_missing_ids_sample_first_200"
                ] = sample_ids(missing_crossing_unknown)
                delete_result["failure_messages"].append(
                    "Protected ids missing after deletion; requested output was not saved."
                )

            # This is diagnostic only. Final validation is from verify_doc after SaveAs/reopen.
            post_copy = build_classification(copy_doc, copy_scope)
            copy_doc_path_before_save = getattr(copy_doc, "PathName", None)
            if delete_result.get("protected_deleted_count", 0) == 0:
                try:
                    saveas_diagnostics = save_copy_as_output(copy_doc, output_path)
                    output_saved = True
                except Exception as save_ex:
                    saveas_diagnostics["saveas_exception"] = str(save_ex)
                    delete_result["failure_messages"].append(
                        "SaveAs failed: {}".format(save_ex)
                    )
                    final_result = "FAILED"
                if output_saved:
                    try:
                        copy_doc.Close(False)
                    except Exception as close_ex:
                        delete_result["failure_messages"].append(
                            "Could not close copied document before verify: {}".format(
                                close_ex
                            )
                        )
                    copy_doc = None
                    verify_result = verify_saved_output(
                        output_path,
                        pre_source["scope_box"]["id"],
                        pre_source["scope_box"]["name"],
                        pre_copy["buckets"]["OUTSIDE"],
                    )
                    verify_counts = verify_result.get("verify_counts", {})
                    verify_crossing = verify_counts.get("crossing", 0)
                    pre_crossing = pre_copy["counts"].get("crossing", 0)
                    crossing_allowed = verify_crossing == 0 or (
                        pre_copy["refined_counts"].get("crossing_mep_count", 0) == 0
                        and verify_crossing <= pre_crossing
                    )
                    success = (
                        delete_result.get("failed_delete_count", 0) == 0
                        and delete_result.get("protected_deleted_count", 0) == 0
                        and verify_counts.get("outside", 0) == 0
                        and verify_counts.get("inside", 0) > 0
                        and crossing_allowed
                        and verify_counts.get("unknown", 0) == 0
                    )
                    final_result = "SUCCESS" if success else "PARTIAL"
                    if not success:
                        if verify_counts.get("outside", 0) > 0:
                            delete_result["failure_messages"].append(
                                "Verify document still reports {} outside physical elements.".format(
                                    verify_counts.get("outside", 0)
                                )
                            )
                        elif not crossing_allowed:
                            delete_result["failure_messages"].append(
                                "Verify document crossing count {} exceeds allowed preserved crossing count {}.".format(
                                    verify_crossing, pre_crossing
                                )
                            )
                else:
                    delete_result["failure_messages"].append(
                        "Verification skipped because SaveAs did not create output."
                    )
            else:
                final_result = "FAILED"
                copy_doc_path_before_save = getattr(copy_doc, "PathName", None)
        else:
            copy_doc_path_before_save = getattr(copy_doc, "PathName", None)

        payload = {
            "schema_version": SCHEMA_VERSION,
            "tool": "module_extract_test_phase_2",
            "timestamp": timestamp(),
            "source_document": {
                "title": source_doc.Title,
                "path": source_doc.PathName,
            },
            "source_doc_is_workshared": source_doc_is_workshared,
            "source_is_workshared": source_doc_is_workshared,
            "working_copy_path": working_path,
            "output_module_path": output_path,
            "output_file_size_mb": (
                output_file_size_mb(output_path) if output_saved else None
            ),
            "output_is_workshared": verify_result.get("output_is_workshared"),
            "copy_opened_detached": copy_open_diagnostics.get("copy_opened_detached"),
            "detach_option_used": copy_open_diagnostics.get("detach_option_used"),
            "copy_doc_is_workshared_after_open": copy_open_diagnostics.get(
                "copy_doc_is_workshared_after_open"
            ),
            "open_worksets_option": copy_open_diagnostics.get("open_worksets_option"),
            "copy_open_failure": copy_open_diagnostics.get("open_failure"),
            "saveas_used_worksharing_options": saveas_diagnostics.get(
                "saveas_used_worksharing_options"
            ),
            "saveas_central": saveas_diagnostics.get("saveas_central"),
            "saveas_exception": saveas_diagnostics.get("saveas_exception"),
            "copy_doc_path_before_delete": copy_doc_path_before_delete,
            "copy_doc_path_before_save": copy_doc_path_before_save,
            "verify_doc_path": verify_result.get("verify_doc_path"),
            "scope_box": pre_source["scope_box"],
            "pre_counts": pre_copy["counts"],
            "pre_refined_counts": pre_copy["refined_counts"],
            "pre_extraction_readiness": pre_copy["extraction_readiness"],
            "delete_result": delete_result,
            "assembly_precheck": delete_result.get(
                "assembly_precheck", empty_assembly_precheck()
            ),
            "assembly_associated_cleanup": delete_result.get(
                "assembly_associated_cleanup", empty_assembly_associated_cleanup()
            ),
            "delete_order": delete_result.get("delete_order", {}),
            "post_counts": post_copy["counts"] if post_copy else {},
            "post_refined_counts": post_copy["refined_counts"] if post_copy else {},
            "verify_counts": verify_result.get("verify_counts", {}),
            "verify_refined_counts": verify_result.get("verify_refined_counts", {}),
            "verify_outside_ids_sample_first_100": verify_result.get(
                "verify_outside_ids_sample_first_100", []
            ),
            "verify_outside_category_breakdown": verify_result.get(
                "verify_outside_category_breakdown", {}
            ),
            "verify_outside_intersects_attempted": verify_result.get(
                "verify_outside_intersects_attempted"
            ),
            "verify_outside_attempted_intersection_count": verify_result.get(
                "verify_outside_attempted_intersection_count"
            ),
            "verify_outside_attempted_intersection_sample_first_100": verify_result.get(
                "verify_outside_attempted_intersection_sample_first_100",
                [],
            ),
            "remaining_inside_count": (
                len(existing_ids(copy_doc, protected_before["inside"]))
                if copy_doc
                else None
            ),
            "remaining_crossing_unknown_count": (
                len(
                    existing_ids(
                        copy_doc,
                        protected_before["crossing"] + protected_before["unknown"],
                    )
                )
                if copy_doc
                else None
            ),
            "remaining_outside_count": (
                post_copy["counts"]["outside"] if post_copy else None
            ),
            "output_saved": output_saved,
            "result": final_result,
        }
        payload["acceptance"] = build_acceptance(payload)
        blocking_errors, non_blocking_warnings = split_failure_messages(
            delete_result.get("failure_messages", []),
            payload["acceptance"]["accepted"],
            delete_result.get("transaction_commit_status"),
            payload["acceptance"]["verify_outside_count"],
        )
        payload["blocking_errors"] = blocking_errors
        payload["non_blocking_warnings"] = non_blocking_warnings
        save_json_report(payload)
        print_report(payload)

        if payload["acceptance"]["accepted"]:
            if non_blocking_warnings:
                popup_message = (
                    "Extraction succeeded with non-blocking Revit warnings.\n"
                    "Inside: {0} | Outside: {1}"
                ).format(
                    payload["acceptance"]["verify_inside_count"],
                    payload["acceptance"]["verify_outside_count"],
                )
            else:
                popup_message = (
                    "Extracted module verified successfully.\n"
                    "Inside: {0} | Outside: {1}"
                ).format(
                    payload["acceptance"]["verify_inside_count"],
                    payload["acceptance"]["verify_outside_count"],
                )
        else:
            popup_message = (
                "Result: {0}\nAttempted outside deleted: {1}\n"
                "Remaining attempted outside: {2}\nVerify outside: {3}\nFailed: {4}\n\nOutput:\n{5}"
            ).format(
                final_result,
                delete_result.get("attempted_outside_deleted_count", 0),
                delete_result.get("remaining_attempted_outside_count", 0),
                payload.get("verify_counts", {}).get("outside"),
                delete_result.get("failed_delete_count", 0),
                output_path if output_saved else "<not saved>",
            )
        TaskDialog.Show(
            TOOL_NAME,
            popup_message,
        )
        return payload
    except Exception as ex:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "tool": "module_extract_test_phase_2",
            "timestamp": timestamp(),
            "source_document": {
                "title": source_doc.Title,
                "path": source_doc.PathName,
            },
            "source_doc_is_workshared": source_doc_is_workshared,
            "source_is_workshared": source_doc_is_workshared,
            "working_copy_path": working_path,
            "output_module_path": output_path,
            "output_file_size_mb": None,
            "output_is_workshared": None,
            "copy_opened_detached": copy_open_diagnostics.get("copy_opened_detached"),
            "detach_option_used": copy_open_diagnostics.get("detach_option_used"),
            "copy_doc_is_workshared_after_open": copy_open_diagnostics.get(
                "copy_doc_is_workshared_after_open"
            ),
            "open_worksets_option": copy_open_diagnostics.get("open_worksets_option"),
            "copy_open_failure": copy_open_diagnostics.get("open_failure"),
            "saveas_used_worksharing_options": False,
            "saveas_central": False,
            "saveas_exception": None,
            "copy_doc_path_before_delete": None,
            "copy_doc_path_before_save": None,
            "verify_doc_path": None,
            "scope_box": pre_source["scope_box"],
            "pre_counts": pre_source["counts"],
            "delete_result": {
                "attempted_delete_count": 0,
                "revit_deleted_return_count": 0,
                "attempted_outside_deleted_count": 0,
                "dependent_deleted_count": 0,
                "remaining_attempted_outside_count": 0,
                "failed_delete_count": 0,
                "protected_deleted_count": 0,
                "deleted_ids_sample_first_200": [],
                "remaining_attempted_outside_ids_sample_first_200": [],
                "protected_deleted_ids_sample_first_200": [],
                "failed_ids_sample_first_200": [],
                "failure_messages": [str(ex)],
                "assembly_precheck": empty_assembly_precheck(),
                "assembly_associated_cleanup": empty_assembly_associated_cleanup(),
                "delete_order": {},
            },
            "assembly_precheck": empty_assembly_precheck(),
            "assembly_associated_cleanup": empty_assembly_associated_cleanup(),
            "delete_order": {},
            "post_counts": {},
            "verify_counts": {},
            "verify_outside_ids_sample_first_100": [],
            "verify_outside_category_breakdown": {},
            "verify_outside_intersects_attempted": None,
            "verify_outside_attempted_intersection_count": None,
            "verify_outside_attempted_intersection_sample_first_100": [],
            "output_saved": False,
            "result": "FAILED",
        }
        payload["acceptance"] = build_acceptance(payload)
        blocking_errors, non_blocking_warnings = split_failure_messages(
            payload["delete_result"].get("failure_messages", []),
            False,
            payload["delete_result"].get("transaction_commit_status"),
            0,
        )
        payload["blocking_errors"] = blocking_errors
        payload["non_blocking_warnings"] = non_blocking_warnings
        save_json_report(payload)
        print_report(payload)
        TaskDialog.Show(TOOL_NAME, "FAILED:\n{}".format(ex))
        return payload
    finally:
        if copy_doc:
            try:
                copy_doc.Close(False)
            except Exception as close_ex:
                print("Could not close copied document: {}".format(close_ex))


if __name__ == "__main__":
    main()
