# -*- coding: utf-8 -*-
__title__ = "element_collector"
__doc__ = """Load latest module_state payload and bucket elements for ModuleEngine.
No UI, prints a concise report and saves collected payloads.
"""

from Autodesk.Revit.DB import (
    BuiltInCategory,
    ElementId,
    FilteredElementCollector,
    IndependentTag,
    TextNote,
)
from Autodesk.Revit.UI import TaskDialog

import os
import sys
import json
from collections import defaultdict
from datetime import datetime
from System.Collections.Generic import List

# ensure local modules are importable
_here = os.path.dirname(__file__)
_parent = os.path.dirname(_here)
for _p in (_here, _parent):
    if _p not in sys.path:
        sys.path.append(_p)

import module_state

uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document


def _bic(name):
    """Return BuiltInCategory value if it exists, else None."""
    try:
        return getattr(BuiltInCategory, name)
    except Exception:
        return None


def warn(msg):
    TaskDialog.Show("element_collector", msg)


def load_latest_payload():
    payload = module_state.load_latest_payload(doc)
    if not payload:
        warn("No latest.json found. Run region_scanner first.")
        sys.exit()
    return payload


def validate_doc(payload):
    pdoc = payload.get("doc", {})
    title = pdoc.get("title", "")
    path = pdoc.get("path", "")
    if doc.Title != title:
        warn(
            "Payload doc title mismatch.\nPayload: {}\nCurrent: {}".format(
                title, doc.Title
            )
        )
        sys.exit()
    # optional path check
    if path and getattr(doc, "PathName", None) and path != doc.PathName:
        warn(
            "Payload path differs from current doc.\nPayload: {}\nCurrent: {}\nContinuing anyway.".format(
                path, doc.PathName
            )
        )


def bucket_pipeline(elem):
    """Return pipeline bucket key or None."""
    cat = elem.Category
    bic = cat.Id.IntegerValue if cat else None
    bic_map = {
        "pipes": _bic("OST_PipeCurves"),
        "pipe_fittings": _bic("OST_PipeFitting"),
        "pipe_accessories": _bic("OST_PipeAccessory"),
        "ducts": _bic("OST_DuctCurves"),
        "duct_fittings": _bic("OST_DuctFitting"),
        "mechanical_equipment": _bic("OST_MechanicalEquipment"),
        "plumbing_fixtures": _bic("OST_PlumbingFixtures"),
        "piping_systems": _bic("OST_PipingSystem"),
        "duct_systems": _bic("OST_DuctSystem"),
        "grids": _bic("OST_Grids"),
        "levels": _bic("OST_Levels"),
        "model_groups": _bic("OST_IOSModelGroups"),
        "rvt_links": _bic("OST_RvtLinks"),
        "views": _bic("OST_Views"),
        "section_boxes": _bic("OST_SectionBox"),
        "scope_boxes": _bic("OST_ScopeBoxes"),
        "cameras": _bic("OST_Cameras"),
        "pipe_tags": _bic("OST_PipeTags"),
        "duct_tags": _bic("OST_DuctTags"),
        "me_tags": _bic("OST_MechanicalEquipmentTags"),
    }

    def _eq(bic_val):
        return bic is not None and bic_val is not None and bic == int(bic_val)

    if _eq(bic_map["pipes"]):
        return "pipeline.mep.pipes"
    if _eq(bic_map["pipe_fittings"]):
        return "pipeline.mep.pipe_fittings"
    if _eq(bic_map["pipe_accessories"]):
        return "pipeline.mep.pipe_accessories"
    if _eq(bic_map["ducts"]):
        return "pipeline.mep.ducts"
    if _eq(bic_map["duct_fittings"]):
        return "pipeline.mep.duct_fittings"
    if _eq(bic_map["mechanical_equipment"]):
        return "pipeline.mep.mechanical_equipment"
    if _eq(bic_map["plumbing_fixtures"]):
        return "pipeline.mep.plumbing_fixtures"
    if _eq(bic_map["piping_systems"]):
        return "pipeline.systems.piping_systems"
    if _eq(bic_map["duct_systems"]):
        return "pipeline.systems.duct_systems"
    if (
        _eq(bic_map["pipe_tags"])
        or _eq(bic_map["duct_tags"])
        or _eq(bic_map["me_tags"])
    ):
        return "pipeline.annotation.tags"
    if isinstance(elem, TextNote):
        return "pipeline.annotation.text_notes"
    if _eq(bic_map["grids"]):
        return "pipeline.reference.grids"
    if _eq(bic_map["levels"]):
        return "pipeline.reference.levels"
    if _eq(bic_map["model_groups"]):
        return "pipeline.containers.groups"
    if _eq(bic_map["rvt_links"]):
        return "pipeline.links.rvt_links"
    if (
        _eq(bic_map["views"])
        or _eq(bic_map["section_boxes"])
        or _eq(bic_map["scope_boxes"])
        or _eq(bic_map["cameras"])
    ):
        return "pipeline.exclusions.view_like"
    return None


def normalize_category(cat):
    if not cat:
        return ("<None>", -1)
    name = (cat.Name or "").strip()
    norm_name = name.title()
    return (norm_name, cat.Id.IntegerValue)


def main():
    payload = load_latest_payload()
    validate_doc(payload)
    core = payload.get("payload", {})
    id_list = core.get("elements", {}).get("ids", [])
    if not id_list:
        warn("No element ids in payload.")
        sys.exit()

    valid_ids = []
    invalid_ids = []

    by_cat_id = defaultdict(list)
    cat_name_by_id = {}
    pipeline_buckets = defaultdict(list)

    for i in id_list:
        try:
            eid = ElementId(int(i))
        except Exception:
            invalid_ids.append(i)
            continue
        elem = doc.GetElement(eid)
        if not elem or not elem.IsValidObject:
            invalid_ids.append(i)
            continue
        valid_ids.append(eid.IntegerValue)

        cname, cid = normalize_category(elem.Category)
        by_cat_id[cid].append(eid.IntegerValue)
        if cid not in cat_name_by_id:
            cat_name_by_id[cid] = cname

        bucket = bucket_pipeline(elem)
        if bucket:
            pipeline_buckets[bucket].append(eid.IntegerValue)

    collected = {
        "schema_version": 1,
        "source_state": payload,
        "collected_utc": datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ"),
        "doc": {
            "title": doc.Title,
            "path": getattr(doc, "PathName", None),
        },
        "elements": {
            "valid_ids": valid_ids,
            "invalid_ids": invalid_ids,
            "by_category_id": dict(by_cat_id),
            "category_name_by_id": cat_name_by_id,
        },
        "pipeline": dict(pipeline_buckets),
    }

    # Persist collected payload (prefer project/central, then fallback)
    base_dir, loc_label = module_state.get_state_dir(doc)
    if not os.path.isdir(base_dir):
        os.makedirs(base_dir)
    stamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    ts_path = os.path.join(base_dir, "collected_{}.json".format(stamp))
    latest_path = os.path.join(base_dir, "collected_latest.json")
    with open(ts_path, "w") as fp:
        json.dump(collected, fp, indent=2, sort_keys=True)
    with open(latest_path, "w") as fp:
        json.dump(collected, fp, indent=2, sort_keys=True)

    # Report
    print("Element Collector")
    print(" - Loaded ids: {}".format(len(id_list)))
    print(" - Valid: {} | Invalid: {}".format(len(valid_ids), len(invalid_ids)))
    top_cats = sorted(by_cat_id.items(), key=lambda x: len(x[1]), reverse=True)[:15]
    print(" - Top categories (by count):")
    for cid, lst in top_cats:
        print("    {} | {} elem".format(cat_name_by_id.get(cid, cid), len(lst)))

    # Key pipeline buckets
    key_buckets = [
        "pipeline.mep.pipes",
        "pipeline.mep.pipe_fittings",
        "pipeline.mep.pipe_accessories",
        "pipeline.mep.ducts",
        "pipeline.mep.duct_fittings",
        "pipeline.mep.mechanical_equipment",
        "pipeline.systems.piping_systems",
        "pipeline.systems.duct_systems",
        "pipeline.annotation.tags",
        "pipeline.annotation.text_notes",
    ]
    print(" - Pipeline buckets:")
    for kb in key_buckets:
        print("    {}: {}".format(kb, len(pipeline_buckets.get(kb, []))))

    TaskDialog.Show(
        "element_collector",
        "Collected {}\nValid {}\nInvalid {}\nSaved:\n{}".format(
            len(id_list), len(valid_ids), len(invalid_ids), latest_path
        ),
    )


if __name__ == "__main__":
    main()
