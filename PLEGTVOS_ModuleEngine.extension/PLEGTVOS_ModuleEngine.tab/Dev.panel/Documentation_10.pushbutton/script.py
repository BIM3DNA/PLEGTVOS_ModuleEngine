# -*- coding: utf-8 -*-
__title__ = "view_duplicator"
__doc__ = """Duplicate and crop a plan view to the saved region (latest.json)."""

from Autodesk.Revit.DB import (
    BoundingBoxXYZ,
    BuiltInParameter,
    ElementId,
    Transform,
    ViewDuplicateOption,
    ViewPlan,
    ViewType,
    Transaction,
)
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.Exceptions import ArgumentException

import os
import sys
import json
from datetime import datetime

# ensure local imports
_here = os.path.dirname(__file__)
_parent = os.path.dirname(_here)
for _p in (_here, _parent):
    if _p not in sys.path:
        sys.path.append(_p)

import module_state

uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document


def warn(msg):
    TaskDialog.Show("view_duplicator", msg)


def load_latest():
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
    if path and getattr(doc, "PathName", None) and path != doc.PathName:
        warn(
            "Payload path differs from current doc.\nPayload: {}\nCurrent: {}\nContinuing anyway.".format(
                path, doc.PathName
            )
        )


def make_transform(tdict):
    if not tdict:
        return Transform.Identity
    try:
        t = Transform.Identity
        t.Origin = module_state.DBPointFrom(tdict.get("origin"))
    except Exception:
        t = Transform.Identity
    try:
        bx = tdict.get("basisX")
        by = tdict.get("basisY")
        bz = tdict.get("basisZ")
        if bx and by and bz:
            t.BasisX = module_state.DBVectorFrom(bx)
            t.BasisY = module_state.DBVectorFrom(by)
            t.BasisZ = module_state.DBVectorFrom(bz)
    except Exception:
        pass
    return t


def main():
    payload = load_latest()
    validate_doc(payload)
    core = payload.get("payload", {})
    view_info = core.get("view", {})
    region = core.get("region", {})

    src_view_id = view_info.get("id")
    if not src_view_id:
        warn("Payload missing view id.")
        sys.exit()
    src_view = doc.GetElement(ElementId(int(src_view_id)))
    if not src_view:
        warn("Source view not found in document.")
        sys.exit()

    if src_view.ViewType != ViewType.FloorPlan:
        warn(
            "Source view type is {}, expected FloorPlan for V1.".format(
                src_view.ViewType
            )
        )
        sys.exit()

    tx = Transaction(doc, "Duplicate cropped view")
    tx.Start()
    try:
        # Duplicate view
        try:
            new_view_id = src_view.Duplicate(ViewDuplicateOption.WithDetailing)
        except ArgumentException:
            new_view_id = src_view.Duplicate(ViewDuplicateOption.Duplicate)
        new_view = doc.GetElement(new_view_id)

        # Detach template so we can edit crop
        new_view.ViewTemplateId = ElementId.InvalidElementId

        # Name with timestamp
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        try:
            new_view.Name = "PV_ME_Region_{}".format(ts)
        except ArgumentException:
            new_view.Name = "PV_ME_Region_{}_alt".format(ts)

        # Build crop box
        if region.get("bbox_min") and region.get("bbox_max"):
            bb = BoundingBoxXYZ()
            bb.Min = module_state.DBPointFrom(region["bbox_min"])
            bb.Max = module_state.DBPointFrom(region["bbox_max"])
            bb.Transform = make_transform(region.get("view_crop_transform"))
            new_view.CropBox = bb

        new_view.CropBoxActive = True
        new_view.CropBoxVisible = True
        anno = new_view.get_Parameter(BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE)
        if anno and not anno.IsReadOnly:
            anno.Set(1)
        tx.Commit()
    except Exception:
        tx.RollBack()
        raise

    # Persist result
    state_dir, _loc = module_state.get_state_dir(doc)
    if not os.path.isdir(state_dir):
        os.makedirs(state_dir)
    result = {
        "created_utc": datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ"),
        "source_view": {"id": src_view.Id.IntegerValue, "name": src_view.Name},
        "new_view": {"id": new_view.Id.IntegerValue, "name": new_view.Name},
        "region": region,
    }
    stamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    res_ts = os.path.join(state_dir, "view_duplicator_{}.json".format(stamp))
    res_latest = os.path.join(state_dir, "view_duplicator_latest.json")
    with open(res_ts, "w") as fp:
        json.dump(result, fp, indent=2, sort_keys=True)
    with open(res_latest, "w") as fp:
        json.dump(result, fp, indent=2, sort_keys=True)

    print("View duplicator:")
    print(" - Source: {} ({})".format(src_view.Name, src_view.Id.IntegerValue))
    print(" - New: {} ({})".format(new_view.Name, new_view.Id.IntegerValue))
    print(" - Crop applied: {}".format(region.get("bbox_min")))
    print("Saved: {}".format(res_latest))

    TaskDialog.Show(
        "view_duplicator",
        "New view created:\n{}\nId {}\nSaved:\n{}".format(
            new_view.Name, new_view.Id.IntegerValue, res_latest
        ),
    )


# Helpers for vector/point from tuples
def _tuple_to_xyz(tpl):
    from Autodesk.Revit.DB import XYZ

    return XYZ(tpl[0], tpl[1], tpl[2])


module_state.DBPointFrom = _tuple_to_xyz
module_state.DBVectorFrom = _tuple_to_xyz

if __name__ == "__main__":
    main()
