# -*- coding: utf-8 -*-
__title__ = "region_apply"
__doc__ = """Apply region editor decisions to the model.

Loads:
  - review_latest.json (from region_editor)
  - view_duplicator_latest.json (for target view)
  - latest.json (for region corner)

Actions (single transaction):
  - Place one text note at region corner (if available)
  - For Pipes: set Comments = NewCode, create tag when TagAction == 'add'
  - For Pipe Fittings: set Comments = NewCode (no tagging)

Writes region_apply_<timestamp>.json and region_apply_latest.json with results.
"""

from Autodesk.Revit.DB import (
    BuiltInCategory,
    AssemblyInstance,
    ElementId,
    FilteredElementCollector,
    IndependentTag,
    Reference,
    TagMode,
    TagOrientation,
    TextNote,
    TextNoteOptions,
    TextNoteType,
    Transaction,
    XYZ,
)
from Autodesk.Revit.UI import TaskDialog

import os
import sys
import json
from datetime import datetime

# local imports
_here = os.path.dirname(__file__)
_parent = os.path.dirname(_here)
for _p in (_here, _parent):
    if _p not in sys.path:
        sys.path.append(_p)
import module_state

uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document


def warn(msg):
    TaskDialog.Show("region_apply", msg)


def load_first_existing(names):
    for name in names:
        for d in module_state._candidate_dirs(doc):
            p = os.path.join(d, name)
            if os.path.isfile(p):
                with open(p, "r") as fp:
                    return p, json.load(fp)
    return None, None


def ensure_payloads():
    review_path, review = load_first_existing(["review_latest.json"])
    if not review:
        warn("Missing review_latest.json. Run region_editor first.")
        sys.exit()

    viewdup_path, viewdup = load_first_existing(["view_duplicator_latest.json"])
    latest_path, latest = load_first_existing(["latest.json"])

    print("region_apply: review payload -> {}".format(review_path))
    if viewdup_path:
        print("region_apply: view_duplicator payload -> {}".format(viewdup_path))
    else:
        print("region_apply: no view_duplicator payload found, using review view")
    if latest_path:
        print("region_apply: latest scan payload -> {}".format(latest_path))

    return review, viewdup, latest


def pick_view(review, viewdup):
    vid = None
    if viewdup and viewdup.get("new_view", {}).get("id"):
        vid = viewdup["new_view"]["id"]
    elif review.get("view", {}).get("id"):
        vid = review["view"]["id"]
    if vid:
        v = doc.GetElement(ElementId(int(vid)))
        if v and v.IsValidObject:
            return v
    return uidoc.ActiveView


def region_corner(latest_payload):
    try:
        region = latest_payload.get("payload", {}).get("region", {})
        bb_min = region.get("bbox_min")
        if bb_min and len(bb_min) >= 3:
            return XYZ(bb_min[0], bb_min[1], bb_min[2])
    except Exception:
        pass
    return None


def place_text_note(view, text, corner):
    try:
        nt = FilteredElementCollector(doc).OfClass(TextNoteType).FirstElement()
        if not nt:
            return False
        opts = TextNoteOptions(nt.Id)
        TextNote.Create(doc, view.Id, corner, text, opts)
        return True
    except Exception:
        return False


def tag_exists(view, host_id, tag_cat):
    try:
        tags = (
            FilteredElementCollector(doc, view.Id)
            .OfCategory(tag_cat)
            .WhereElementIsNotElementType()
        )
        for t in tags:
            tagged_ids = (
                t.GetTaggedElementIds()
                if hasattr(t, "GetTaggedElementIds")
                else [t.TaggedElementId]
            )
            for tid in tagged_ids:
                if tid and tid.IntegerValue == host_id:
                    return True
    except Exception:
        return False
    return False


def tag_element(view, elem, tag_cat, tag_type_id=None, label_text=None):
    try:
        bb = elem.get_BoundingBox(view)
        if not bb:
            return False
        ctr = XYZ(
            (bb.Min.X + bb.Max.X) * 0.5,
            (bb.Min.Y + bb.Max.Y) * 0.5,
            (bb.Min.Z + bb.Max.Z) * 0.5,
        )
        ref = Reference(elem)
        new_tag = IndependentTag.Create(
            doc,
            view.Id,
            ref,
            True,
            TagMode.TM_ADDBY_CATEGORY,
            TagOrientation.Horizontal,
            ctr,
        )
        if tag_type_id and new_tag and new_tag.GetTypeId() != tag_type_id:
            try:
                new_tag.ChangeTypeId(tag_type_id)
            except Exception:
                pass
        if label_text and new_tag:
            try:
                new_tag.TagText = label_text
            except Exception:
                pass
        return True
    except Exception:
        return False


def find_tag_type(tag_cat, preferred_names=None):
    preferred_names = preferred_names or []
    try:
        types = (
            FilteredElementCollector(doc)
            .OfCategory(tag_cat)
            .WhereElementIsElementType()
            .ToElements()
        )
        # prefer by exact name match
        for name in preferred_names:
            for t in types:
                try:
                    if (t.Name or "").strip().lower() == name.strip().lower():
                        return t.Id
                except Exception:
                    continue
        # fallback first available
        if types:
            return types[0].Id
    except Exception:
        return None
    return None


def fmt_mm(param):
    if not param:
        return ""
    try:
        val = param.AsDouble()
        if val is None:
            return ""
        return str(int(round(val * 304.8)))
    except Exception:
        try:
            return param.AsValueString() or ""
        except Exception:
            return ""


def pipe_label(elem, new_code):
    diam = ""
    for pname in ("Outside Diameter", "Diameter", "Nominal Diameter"):
        p = elem.LookupParameter(pname)
        diam = fmt_mm(p)
        if diam:
            break
    length = fmt_mm(elem.LookupParameter("Length"))
    parts = [new_code]
    sub = []
    if diam:
        sub.append("\u2300{} mm".format(diam))
    if length:
        sub.append("L = {} mm".format(length))
    if sub:
        parts.append(" / ".join(sub))
    return "\n".join(parts)


def main():
    review, viewdup, latest = ensure_payloads()
    view = pick_view(review, viewdup)
    if not view or not view.IsValidObject:
        warn("Target view not found. Re-run view_duplicator then region_editor.")
        sys.exit()

    base_code = review.get("base_code") or ""
    rows = review.get("elements", [])
    if not rows:
        warn("No rows found in review payload.")
        sys.exit()

    corner = region_corner(latest) if latest else None

    summary = {
        "placed_text": False,
        "text_content": base_code,
        "updated_comments": 0,
        "tag_added": 0,
        "skipped_grouped": 0,
        "skipped_group_locked": 0,
        "skipped_no_tag_family": 0,
        "skipped_tag_fail": 0,
        "skipped_missing": 0,
        "skipped_no_param": 0,
        "skipped_already_tagged": 0,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ"),
        "view": {"id": view.Id.IntegerValue, "name": view.Name},
    }

    t = Transaction(doc, "Apply Region Codes")
    t.Start()

    new_tag_ids = []

    if corner and base_code:
        if place_text_note(view, base_code, corner):
            summary["placed_text"] = True

    # tag category mapping
    TAG_MAP = {
        int(BuiltInCategory.OST_PipeCurves): BuiltInCategory.OST_PipeTags,
        int(BuiltInCategory.OST_FlexPipeCurves): BuiltInCategory.OST_FlexPipeTags,
        int(BuiltInCategory.OST_PipeFitting): BuiltInCategory.OST_PipeFittingTags,
    }
    TAG_PREFS = {
        int(BuiltInCategory.OST_PipeCurves): ["M_Pipe Size Tag"],
        int(BuiltInCategory.OST_FlexPipeCurves): ["M_Pipe Size Tag"],
        int(BuiltInCategory.OST_PipeFitting): [
            "M_Pipe Fitting Tag",
            "Pipe Fitting Tag",
        ],
    }
    COMMENT_SET_IDS = set(
        [
            int(BuiltInCategory.OST_PipeCurves),
            int(BuiltInCategory.OST_FlexPipeCurves),
            int(BuiltInCategory.OST_PipeFitting),
        ]
    )

    def process_one(eid, new_code, action):
        elem = doc.GetElement(eid)
        if not elem or not elem.IsValidObject:
            summary["skipped_missing"] += 1
            return

        cat_id = elem.Category.Id.IntegerValue if elem.Category else None

        # set Comments
        if cat_id in COMMENT_SET_IDS:
            p = elem.LookupParameter("Comments")
            if p and not p.IsReadOnly:
                try:
                    p.Set(new_code)
                    summary["updated_comments"] += 1
                except Exception:
                    summary["skipped_no_param"] += 1
            else:
                summary["skipped_no_param"] += 1

        # tags
        if action == "add" and cat_id in TAG_MAP:
            tag_cat = TAG_MAP[cat_id]
            tag_type_id = find_tag_type(tag_cat, TAG_PREFS.get(cat_id, []))
            if not tag_type_id:
                summary["skipped_no_tag_family"] += 1
                return
            if tag_exists(view, eid.IntegerValue, tag_cat):
                summary["skipped_already_tagged"] += 1
            else:
                try:
                    label_text = pipe_label(elem, new_code)
                    if tag_element(view, elem, tag_cat, tag_type_id, label_text):
                        summary["tag_added"] += 1
                        try:
                            tags = (
                                FilteredElementCollector(doc, view.Id)
                                .OfCategory(tag_cat)
                                .WhereElementIsNotElementType()
                            )
                            newest = max(
                                tags, key=lambda x: x.Id.IntegerValue, default=None
                            )
                            if newest:
                                new_tag_ids.append(newest.Id)
                        except Exception:
                            pass
                    else:
                        summary["skipped_tag_fail"] += 1
                except Exception:
                    summary["skipped_tag_fail"] += 1

    for r in rows:
        try:
            eid = ElementId(int(r.get("Id")))
        except Exception:
            continue

        new_code = r.get("NewCode", "") or base_code
        action = (r.get("TagAction") or "").lower()
        elem = doc.GetElement(eid)
        if not elem or not elem.IsValidObject:
            summary["skipped_missing"] += 1
            continue

        # expand assemblies to their members, otherwise process the element
        if isinstance(elem, AssemblyInstance):
            try:
                mem_ids = elem.GetMemberIds()
                for mid in mem_ids:
                    process_one(mid, new_code, action or "add")
            except Exception:
                summary["skipped_tag_fail"] += 1
        else:
            # attempt processing even if grouped; count grouped separately on failure
            try:
                process_one(eid, new_code, action)
            except Exception:
                summary["skipped_group_locked"] += 1

    t.Commit()

    # Highlight new tags (best-effort)
    try:
        if new_tag_ids:
            uidoc.Selection.SetElementIds(List[ElementId](new_tag_ids))
    except Exception:
        pass

    state_dir, _loc = module_state.get_state_dir(doc)
    if not os.path.isdir(state_dir):
        os.makedirs(state_dir)
    stamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    ts_path = os.path.join(state_dir, "region_apply_{}.json".format(stamp))
    latest_path = os.path.join(state_dir, "region_apply_latest.json")
    with open(ts_path, "w") as fp:
        json.dump(summary, fp, indent=2, sort_keys=True)
    with open(latest_path, "w") as fp:
        json.dump(summary, fp, indent=2, sort_keys=True)

    TaskDialog.Show(
        "region_apply",
        "Applied region edits.\n"
        "Base code: {0}\n"
        "Comments updated: {1}\n"
        "Tags added: {2}\n"
        "Skipped grouped: {3}\n"
        "Already tagged: {4}\n"
        "Missing elements: {5}\n"
        "Missing writable param: {6}\n"
        "No tag family: {7}\n"
        "Tag failures: {8}\n"
        "Group locked (errors): {9}\n"
        "Text note placed: {10}\n"
        "Saved: {11}".format(
            base_code,
            summary["updated_comments"],
            summary["tag_added"],
            summary["skipped_grouped"],
            summary["skipped_already_tagged"],
            summary["skipped_missing"],
            summary["skipped_no_param"],
            summary["skipped_no_tag_family"],
            summary["skipped_tag_fail"],
            summary["skipped_group_locked"],
            "Yes" if summary["placed_text"] else "No",
            latest_path,
        ),
    )


if __name__ == "__main__":
    main()
