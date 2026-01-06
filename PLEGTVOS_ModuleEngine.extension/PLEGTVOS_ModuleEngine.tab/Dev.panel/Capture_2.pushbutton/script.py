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


def tag_exists_for_pipe(view, pipe_id):
    try:
        tags = (
            FilteredElementCollector(doc, view.Id)
            .OfCategory(BuiltInCategory.OST_PipeTags)
            .WhereElementIsNotElementType()
        )
        for t in tags:
            tagged_ids = (
                t.GetTaggedElementIds()
                if hasattr(t, "GetTaggedElementIds")
                else [t.TaggedElementId]
            )
            for tid in tagged_ids:
                if tid and tid.IntegerValue == pipe_id:
                    return True
    except Exception:
        return False
    return False


def tag_pipe(view, pipe):
    try:
        bb = pipe.get_BoundingBox(view)
        if not bb:
            return False
        ctr = XYZ(
            (bb.Min.X + bb.Max.X) * 0.5,
            (bb.Min.Y + bb.Max.Y) * 0.5,
            (bb.Min.Z + bb.Max.Z) * 0.5,
        )
        ref = Reference(pipe)
        IndependentTag.Create(
            doc,
            view.Id,
            ref,
            True,
            TagMode.TM_ADDBY_CATEGORY,
            TagOrientation.Horizontal,
            ctr,
        )
        return True
    except Exception:
        return False


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
        "skipped_missing": 0,
        "skipped_no_param": 0,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ"),
        "view": {"id": view.Id.IntegerValue, "name": view.Name},
    }

    t = Transaction(doc, "Apply Region Codes")
    t.Start()

    if corner and base_code:
        if place_text_note(view, base_code, corner):
            summary["placed_text"] = True

    for r in rows:
        try:
            eid = ElementId(int(r.get("Id")))
        except Exception:
            continue
        elem = doc.GetElement(eid)
        if not elem or not elem.IsValidObject:
            summary["skipped_missing"] += 1
            continue

        cat = r.get("Category", "")
        new_code = r.get("NewCode", "") or base_code

        # set Comments for pipes and fittings
        if cat in ("Pipes", "Pipe Fittings"):
            p = elem.LookupParameter("Comments")
            if p and not p.IsReadOnly:
                try:
                    p.Set(new_code)
                    summary["updated_comments"] += 1
                except Exception:
                    summary["skipped_no_param"] += 1
            else:
                summary["skipped_no_param"] += 1

        # tags only for pipes
        if cat == "Pipes":
            action = (r.get("TagAction") or "").lower()
            if action == "add" and not tag_exists_for_pipe(view, eid.IntegerValue):
                if tag_pipe(view, elem):
                    summary["tag_added"] += 1

    t.Commit()

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
        "Missing elements: {3}\n"
        "Missing writable param: {4}\n"
        "Text note placed: {5}\n"
        "Saved: {6}".format(
            base_code,
            summary["updated_comments"],
            summary["tag_added"],
            summary["skipped_missing"],
            summary["skipped_no_param"],
            "Yes" if summary["placed_text"] else "No",
            latest_path,
        ),
    )


if __name__ == "__main__":
    main()
