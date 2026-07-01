# -*- coding: utf-8 -*-
__title__ = "Module\nExtractor"
__doc__ = """Phase 1 report-only module extraction classifier.

Selects one scope box and reports which model elements are inside, outside,
crossing, or unknown. This script intentionally opens no Transaction and makes
no model changes.
"""

from Autodesk.Revit.DB import (
    AssemblyInstance,
    BuiltInCategory,
    BuiltInParameter,
    CategoryType,
    ElementId,
    ElementType,
    FilteredElementCollector,
    Grid,
    Group,
    ImportInstance,
    Level,
    RevitLinkInstance,
    View,
    ViewSchedule,
    ViewSheet,
    XYZ,
)
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType

import json
import os
import sys
from collections import defaultdict
from datetime import datetime

_here = os.path.dirname(__file__)
_parent = os.path.dirname(_here)
for _p in (_here, _parent):
    if _p not in sys.path:
        sys.path.append(_p)

import module_state

uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

TOOL_NAME = "Module Extractor Phase 1"
SCHEMA_VERSION = 1
TOL = 1e-6


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


def get_category_name(element):
    try:
        if element.Category and element.Category.Name:
            return element.Category.Name
    except Exception:
        pass
    return "<None>"


def normalize_category_name(element):
    raw = get_category_name(element)
    text = " ".join((raw or "<None>").strip().split())
    if not text:
        return "<None>"
    normalized = text.title()
    replacements = {
        "Rvt": "RVT",
        "Cad": "CAD",
        "Mep": "MEP",
        "Hvac": "HVAC",
        "Pvc": "PVC",
    }
    for src, dst in replacements.items():
        normalized = normalized.replace(src, dst)
    return normalized


def get_category_id(element):
    try:
        if element.Category:
            return element.Category.Id.IntegerValue
    except Exception:
        pass
    return None


def point_to_list(point):
    return [point.X, point.Y, point.Z]


def bbox_to_dict(world_bbox):
    return {
        "min": [world_bbox["min"].X, world_bbox["min"].Y, world_bbox["min"].Z],
        "max": [world_bbox["max"].X, world_bbox["max"].Y, world_bbox["max"].Z],
    }


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

    fully_inside = (
        elem_min.X >= scope_min.X - TOL
        and elem_max.X <= scope_max.X + TOL
        and elem_min.Y >= scope_min.Y - TOL
        and elem_max.Y <= scope_max.Y + TOL
        and elem_min.Z >= scope_min.Z - TOL
        and elem_max.Z <= scope_max.Z + TOL
    )
    if fully_inside:
        return "INSIDE"

    separated = (
        elem_max.X < scope_min.X - TOL
        or elem_min.X > scope_max.X + TOL
        or elem_max.Y < scope_min.Y - TOL
        or elem_min.Y > scope_max.Y + TOL
        or elem_max.Z < scope_min.Z - TOL
        or elem_min.Z > scope_max.Z + TOL
    )
    if separated:
        return "OUTSIDE"

    return "CROSSING"


def safe_param_text(element, bip):
    try:
        param = element.get_Parameter(bip)
        if not param:
            return None
        value = param.AsValueString()
        if value:
            return value
        value = param.AsString()
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


def get_type_name(element):
    try:
        type_id = element.GetTypeId()
        if type_id and type_id != ElementId.InvalidElementId:
            elem_type = doc.GetElement(type_id)
            if elem_type:
                return getattr(elem_type, "Name", None)
    except Exception:
        pass
    return None


def get_mep_system_info(element):
    info = {
        "system_type": None,
        "system_classification": None,
        "system_name": None,
        "type_name": None,
    }
    try:
        info["system_type"] = safe_param_text(
            element, BuiltInParameter.RBS_PIPING_SYSTEM_TYPE_PARAM
        ) or safe_param_text(element, BuiltInParameter.RBS_DUCT_SYSTEM_TYPE_PARAM)
    except Exception:
        pass
    try:
        info["system_classification"] = safe_param_text(
            element, BuiltInParameter.RBS_SYSTEM_CLASSIFICATION_PARAM
        )
    except Exception:
        pass
    try:
        info["system_name"] = safe_param_text(
            element, BuiltInParameter.RBS_SYSTEM_NAME_PARAM
        )
    except Exception:
        pass
    info["type_name"] = get_type_name(element)
    return info


def get_endpoint_report(element, scope_world_bbox):
    report = {
        "endpoint_0_inside": None,
        "endpoint_1_inside": None,
        "both_inside": None,
        "both_outside": None,
        "one_inside_one_outside": None,
    }
    try:
        loc = getattr(element, "Location", None)
        curve = getattr(loc, "Curve", None)
        if not curve:
            return report
        p0 = curve.GetEndPoint(0)
        p1 = curve.GetEndPoint(1)
        e0 = point_inside_bbox(p0, scope_world_bbox)
        e1 = point_inside_bbox(p1, scope_world_bbox)
        report["endpoint_0_inside"] = e0
        report["endpoint_1_inside"] = e1
        report["both_inside"] = e0 and e1
        report["both_outside"] = (not e0) and (not e1)
        report["one_inside_one_outside"] = e0 != e1
    except Exception:
        pass
    return report


def classify_element(doc, element, scope_world_bbox):
    element_bbox = get_world_bbox(element)
    bucket = bbox_relation_to_scope(element_bbox, scope_world_bbox)
    endpoint_report = None
    if get_category_id(element) in MEP_CURVE_CATEGORIES:
        endpoint_report = get_endpoint_report(element, scope_world_bbox)
    return bucket, element_bbox, endpoint_report


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
        if isinstance(element, (RevitLinkInstance, ImportInstance)):
            return True
    except Exception:
        pass
    return False


def is_candidate_model_element(element):
    if not element or not getattr(element, "IsValidObject", False):
        return False
    if is_view_or_type(element):
        return False
    if is_view_specific(element):
        return False
    if is_infrastructure(element):
        return False
    cid = get_category_id(element)
    if cid not in TARGET_CATEGORIES:
        return False
    if cid in VIEW_LIKE_CATEGORIES:
        return False
    try:
        cat = element.Category
        if not cat or cat.CategoryType != CategoryType.Model:
            return False
    except Exception:
        return False
    return True


def selected_scope_box():
    try:
        selected_ids = list(uidoc.Selection.GetElementIds())
    except Exception:
        selected_ids = []
    scopes = []
    for elem_id in selected_ids:
        elem = doc.GetElement(elem_id)
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
            "Pick one scope box for report-only module extraction",
        )
        return doc.GetElement(ref) if ref else None
    except Exception:
        return None


def warning_bucket(warnings, key, element):
    warnings[key]["count"] += 1
    if len(warnings[key]["ids"]) < 50:
        warnings[key]["ids"].append(id_int(element))


def summary_bucket(summary, key, element):
    item = summary[key]
    item["count"] += 1
    display_name = normalize_category_name(element)
    item["by_category"][display_name] += 1
    if len(item["ids"]) < 50:
        item["ids"].append(id_int(element))


def named_summary_bucket(summary, key, name, element=None):
    item = summary[key]
    item["count"] += 1
    item["by_name"][name or "<None>"] += 1
    if element is not None and len(item["ids"]) < 50:
        item["ids"].append(id_int(element))


def collect_candidate_summaries(element, summaries):
    try:
        design_option = element.DesignOption
        if design_option:
            name = getattr(design_option, "Name", None) or str(id_int(design_option))
            named_summary_bucket(
                summaries["design_option_summary"], "design_options", name, element
            )
    except Exception:
        pass
    try:
        workset_id = element.WorksetId
        if workset_id and workset_id.IntegerValue > 0:
            ws_name = str(workset_id.IntegerValue)
            try:
                ws_table = doc.GetWorksetTable()
                ws = ws_table.GetWorkset(workset_id)
                ws_name = ws.Name
            except Exception:
                pass
            named_summary_bucket(
                summaries["workset_summary"], "worksets", ws_name, element
            )
    except Exception:
        pass


def new_breakdown():
    return {
        "INSIDE": defaultdict(int),
        "OUTSIDE": defaultdict(int),
        "CROSSING": defaultdict(int),
        "UNKNOWN": defaultdict(int),
    }


def increment_mep_breakdown(mep_breakdown, bucket, category, info):
    system_type = info.get("system_type") or "<None>"
    system_class = info.get("system_classification") or "<None>"
    system_name = info.get("system_name") or "<None>"
    type_name = info.get("type_name") or "<None>"
    key = "{} | {} | {} | {} | {}".format(
        category, system_type, system_class, system_name, type_name
    )
    mep_breakdown[bucket][key] += 1


def as_regular_dict(value):
    if isinstance(value, defaultdict):
        return dict((k, as_regular_dict(v)) for k, v in value.items())
    if isinstance(value, dict):
        return dict((k, as_regular_dict(v)) for k, v in value.items())
    return value


def build_report(scope_box, scope_world_bbox):
    counts = {
        "total_candidates": 0,
        "inside": 0,
        "outside": 0,
        "crossing": 0,
        "unknown": 0,
    }
    category_breakdown = new_breakdown()
    raw_category_breakdown = new_breakdown()
    mep_breakdown = new_breakdown()
    endpoint_breakdown = new_breakdown()
    endpoint_samples = []
    crossing_ids = []
    unknown_ids = []
    all_crossing_ids = []
    all_unknown_ids = []
    crossing_mep_count = 0
    unknown_mep_count = 0
    skipped = defaultdict(
        lambda: {"count": 0, "ids": [], "by_category": defaultdict(int)}
    )
    summaries = {
        "workset_summary": defaultdict(
            lambda: {"count": 0, "ids": [], "by_name": defaultdict(int)}
        ),
        "design_option_summary": defaultdict(
            lambda: {"count": 0, "ids": [], "by_name": defaultdict(int)}
        ),
        "group_summary": defaultdict(
            lambda: {"count": 0, "ids": [], "by_category": defaultdict(int)}
        ),
        "assembly_summary": defaultdict(
            lambda: {"count": 0, "ids": [], "by_category": defaultdict(int)}
        ),
    }
    infrastructure = defaultdict(int)
    linked_models = defaultdict(
        lambda: {"count": 0, "ids": [], "by_category": defaultdict(int)}
    )

    collector = FilteredElementCollector(doc).WhereElementIsNotElementType()
    for element in collector:
        if is_linked_or_imported(element):
            summary_bucket(linked_models, "links_and_imports", element)
            continue
        try:
            if isinstance(element, Group):
                summary_bucket(summaries["group_summary"], "groups", element)
                summary_bucket(skipped, "groups", element)
                continue
        except Exception:
            pass
        try:
            if isinstance(element, AssemblyInstance):
                summary_bucket(summaries["assembly_summary"], "assemblies", element)
                summary_bucket(skipped, "assemblies", element)
                continue
        except Exception:
            pass
        if is_infrastructure(element):
            infrastructure[normalize_category_name(element)] += 1
            continue
        if is_view_or_type(element):
            summary_bucket(skipped, "view_or_type", element)
            continue
        if is_view_specific(element):
            summary_bucket(skipped, "view_specific", element)
            continue
        if not is_candidate_model_element(element):
            summary_bucket(skipped, "non_physical_or_excluded", element)
            continue

        counts["total_candidates"] += 1
        collect_candidate_summaries(element, summaries)

        bucket, element_bbox, endpoint_report = classify_element(
            doc, element, scope_world_bbox
        )
        bucket_key = bucket.lower()
        counts[bucket_key] += 1

        raw_category_name = get_category_name(element)
        category_name = normalize_category_name(element)
        category_breakdown[bucket][category_name] += 1
        raw_category_breakdown[bucket][raw_category_name] += 1
        if get_category_id(element) in MEP_CURVE_CATEGORIES:
            if bucket == "CROSSING":
                crossing_mep_count += 1
            elif bucket == "UNKNOWN":
                unknown_mep_count += 1

        if bucket == "CROSSING":
            all_crossing_ids.append(id_int(element))
            if len(crossing_ids) < 50:
                crossing_ids.append(id_int(element))
        elif bucket == "UNKNOWN":
            all_unknown_ids.append(id_int(element))
            if len(unknown_ids) < 50:
                unknown_ids.append(id_int(element))

        mep_info = get_mep_system_info(element)
        if any(mep_info.values()):
            increment_mep_breakdown(mep_breakdown, bucket, category_name, mep_info)

        if endpoint_report:
            for key, value in endpoint_report.items():
                if value is True:
                    endpoint_breakdown[bucket][key] += 1
            if len(endpoint_samples) < 50:
                sample = {
                    "id": id_int(element),
                    "bucket": bucket,
                    "category": category_name,
                }
                sample.update(endpoint_report)
                endpoint_samples.append(sample)

    refined_counts = {
        "inside_physical_count": counts["inside"],
        "outside_physical_count": counts["outside"],
        "crossing_physical_count": counts["crossing"],
        "unknown_physical_count": counts["unknown"],
        "crossing_mep_count": crossing_mep_count,
        "unknown_mep_count": unknown_mep_count,
    }
    can_continue = (
        refined_counts["inside_physical_count"] > 0
        and crossing_mep_count == 0
        and unknown_mep_count == 0
    )
    if can_continue:
        reason = "Ready for Phase 2: physical elements found and no crossing/unknown MEP curves."
        if counts["crossing"] > crossing_mep_count:
            reason = "Ready with warning: non-MEP physical crossing elements exist; review before extraction."
    elif refined_counts["inside_physical_count"] <= 0:
        reason = "Blocked: no inside physical module candidates were found."
    elif crossing_mep_count > 0:
        reason = "Blocked: crossing MEP curve elements require review."
    else:
        reason = "Blocked: unknown MEP curve elements require review."

    extraction_readiness = {
        "can_continue_to_phase_2": can_continue,
        "reason": reason,
        "inside_physical_count": refined_counts["inside_physical_count"],
        "outside_physical_count": refined_counts["outside_physical_count"],
        "crossing_physical_count": refined_counts["crossing_physical_count"],
        "unknown_physical_count": refined_counts["unknown_physical_count"],
        "crossing_mep_count": crossing_mep_count,
        "unknown_mep_count": unknown_mep_count,
    }

    payload = {
        "schema_version": SCHEMA_VERSION,
        "tool": "module_extractor_phase_1",
        "timestamp": timestamp(),
        "document": {
            "title": doc.Title,
            "path": getattr(doc, "PathName", None),
            "is_workshared": getattr(doc, "IsWorkshared", False),
        },
        "scope_box": {
            "id": id_int(scope_box),
            "name": getattr(scope_box, "Name", None),
            "bbox": bbox_to_dict(scope_world_bbox),
        },
        "counts": counts,
        "refined_counts": refined_counts,
        "extraction_readiness": extraction_readiness,
        "category_breakdown": as_regular_dict(category_breakdown),
        "category_raw_breakdown": as_regular_dict(raw_category_breakdown),
        "mep_breakdown": as_regular_dict(mep_breakdown),
        "mep_endpoint_breakdown": as_regular_dict(endpoint_breakdown),
        "mep_endpoint_samples": endpoint_samples,
        "crossing_ids": crossing_ids,
        "unknown_ids": unknown_ids,
        "diagnostics": {
            "all_crossing_count": len(all_crossing_ids),
            "all_unknown_count": len(all_unknown_ids),
            "skipped": as_regular_dict(skipped),
            "infrastructure_summary": dict(infrastructure),
            "target_category_ids": sorted(list(TARGET_CATEGORIES)),
        },
        "workset_summary": as_regular_dict(summaries["workset_summary"]),
        "design_option_summary": as_regular_dict(summaries["design_option_summary"]),
        "group_summary": as_regular_dict(summaries["group_summary"]),
        "assembly_summary": as_regular_dict(summaries["assembly_summary"]),
        "linked_model_summary": as_regular_dict(linked_models),
        "infrastructure_summary": dict(infrastructure),
        "skipped_summary": as_regular_dict(skipped),
        "warnings": {},
    }
    return payload


def save_report(doc, payload):
    state_dir, label = module_state.get_state_dir(doc)
    if not os.path.isdir(state_dir):
        os.makedirs(state_dir)
    stamp = file_stamp()
    ts_path = os.path.join(state_dir, "module_extractor_report_{}.json".format(stamp))
    latest_path = os.path.join(state_dir, "module_extractor_latest.json")
    with open(ts_path, "w") as fp:
        json.dump(payload, fp, indent=2, sort_keys=True)
    with open(latest_path, "w") as fp:
        json.dump(payload, fp, indent=2, sort_keys=True)
    return ts_path, latest_path, label


def print_bucket_breakdown(title, bucket_map, limit=25):
    print(title)
    for bucket in ["INSIDE", "OUTSIDE", "CROSSING", "UNKNOWN"]:
        items = sorted(
            bucket_map.get(bucket, {}).items(), key=lambda x: x[1], reverse=True
        )
        print(" - {}:".format(bucket))
        if not items:
            print("    <none>")
        for name, count in items[:limit]:
            print("    {}: {}".format(name, count))
        if len(items) > limit:
            print("    ... {} more".format(len(items) - limit))


def print_summary(title, summary, limit=20):
    print(title)
    if not summary:
        print(" - <none>")
        return
    for key in sorted(summary.keys()):
        data = summary[key]
        print(" - {}: {}".format(key, data.get("count", 0)))
        if data.get("ids"):
            print("    sample ids: {}".format(data.get("ids")))
        by_name = data.get("by_name") or data.get("by_category") or {}
        for name, count in sorted(by_name.items(), key=lambda x: x[1], reverse=True)[
            :limit
        ]:
            print("    {}: {}".format(name, count))


def print_simple_counts(title, counts_map, limit=25):
    print(title)
    if not counts_map:
        print(" - <none>")
        return
    for name, count in sorted(counts_map.items(), key=lambda x: x[1], reverse=True)[
        :limit
    ]:
        print(" - {}: {}".format(name, count))


def print_report(payload):
    counts = payload["counts"]
    refined = payload.get("refined_counts", {})
    readiness = payload.get("extraction_readiness", {})
    scope = payload["scope_box"]
    doc_info = payload["document"]

    print("=" * 72)
    print("Module Extractor Phase 1 - REPORT ONLY")
    print("No Transaction opened. No model changes were made by this script.")
    print("=" * 72)
    print("Document: {}".format(doc_info.get("title")))
    print("Path: {}".format(doc_info.get("path") or "<unsaved>"))
    print("Scope Box: {} | ElementId {}".format(scope.get("name"), scope.get("id")))
    print("Scope Min: {}".format(scope["bbox"]["min"]))
    print("Scope Max: {}".format(scope["bbox"]["max"]))
    print("")
    print("Counts")
    print(" - Total candidates: {}".format(counts["total_candidates"]))
    print(" - INSIDE: {}".format(counts["inside"]))
    print(" - OUTSIDE: {}".format(counts["outside"]))
    print(" - CROSSING: {}".format(counts["crossing"]))
    print(" - UNKNOWN: {}".format(counts["unknown"]))
    print("")
    print("Extraction readiness")
    print(
        " - Can continue to Phase 2: {}".format(
            readiness.get("can_continue_to_phase_2")
        )
    )
    print(" - Reason: {}".format(readiness.get("reason")))
    print(" - Inside physical: {}".format(refined.get("inside_physical_count", 0)))
    print(" - Outside physical: {}".format(refined.get("outside_physical_count", 0)))
    print(" - Crossing physical: {}".format(refined.get("crossing_physical_count", 0)))
    print(" - Unknown physical: {}".format(refined.get("unknown_physical_count", 0)))
    print(" - Crossing MEP curves: {}".format(refined.get("crossing_mep_count", 0)))
    print(" - Unknown MEP curves: {}".format(refined.get("unknown_mep_count", 0)))
    print("")
    print_bucket_breakdown("Category breakdown", payload["category_breakdown"])
    print("")
    print_bucket_breakdown(
        "MEP system/type breakdown", payload["mep_breakdown"], limit=30
    )
    print("")
    print_bucket_breakdown(
        "MEP endpoint breakdown", payload["mep_endpoint_breakdown"], limit=20
    )
    print("")
    print("First 50 crossing element ids:")
    print(payload["crossing_ids"] if payload["crossing_ids"] else "<none>")
    print("First 50 unknown element ids:")
    print(payload["unknown_ids"] if payload["unknown_ids"] else "<none>")
    print("")
    print_summary("Workset summary", payload.get("workset_summary", {}))
    print("")
    print_summary("Design option summary", payload.get("design_option_summary", {}))
    print("")
    print_summary("Group summary", payload.get("group_summary", {}))
    print("")
    print_summary("Assembly summary", payload.get("assembly_summary", {}))
    print("")
    print_summary("Linked model summary", payload.get("linked_model_summary", {}))
    print("")
    print_simple_counts(
        "Infrastructure summary", payload.get("infrastructure_summary", {})
    )
    print("")
    print_summary("Skipped summary", payload.get("skipped_summary", {}))
    print("")
    print("Diagnostics")
    print(
        " - Target physical category ids: {}".format(
            payload["diagnostics"].get("target_category_ids", [])
        )
    )


def main():
    scope_box = selected_scope_box()
    if not scope_box:
        TaskDialog.Show(TOOL_NAME, "Cancelled. Select or pick one scope box.")
        return None

    scope_world_bbox = get_world_bbox(scope_box)
    if not scope_world_bbox:
        TaskDialog.Show(TOOL_NAME, "Selected scope box has no usable bounding box.")
        return None

    payload = build_report(scope_box, scope_world_bbox)
    ts_path, latest_path, label = save_report(doc, payload)
    print_report(payload)
    print("")
    print("Saved timestamped JSON: {}".format(ts_path))
    print("Saved latest JSON: {}".format(latest_path))

    TaskDialog.Show(
        TOOL_NAME,
        "Report complete.\nCandidates: {0}\nInside: {1}\nOutside: {2}\nCrossing: {3}\nUnknown: {4}\n\nLatest:\n{5}".format(
            payload["counts"]["total_candidates"],
            payload["counts"]["inside"],
            payload["counts"]["outside"],
            payload["counts"]["crossing"],
            payload["counts"]["unknown"],
            latest_path,
        ),
    )
    return payload


if __name__ == "__main__":
    main()
