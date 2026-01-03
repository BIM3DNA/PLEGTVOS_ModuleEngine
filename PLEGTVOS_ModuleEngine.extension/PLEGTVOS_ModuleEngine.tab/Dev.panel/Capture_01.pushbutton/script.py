# -*- coding: utf-8 -*-
__title__ = "region_scanner"
__doc__ = """Minimal region scanner
Version = 0.1
Date    = 03.04.2026
______________________________________________
Description:
- Let user pick a scope box OR a closed loop of detail lines.
- Collect elements in the active view whose bounding-box center is inside the region.
- Show a quick count + list in the console and a dialog.
______________________________________________
How-To:
1) Click button.
2) Choose Scope Box (Yes) or Detail Lines (No).
3) Pick the element(s) as prompted.
______________________________________________
Author: PLEGTVOS
"""

from Autodesk.Revit.DB import (
    BuiltInCategory,
    ElementId,
    FilteredElementCollector,
    Transaction,
    XYZ,
    Reference,
    Category,
)
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
from Autodesk.Revit.UI import TaskDialog, TaskDialogCommonButtons, TaskDialogResult
from Autodesk.Revit.Exceptions import InvalidOperationException

import sys

app = __revit__.Application
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document


# -----------------------------
# Selection filters
# -----------------------------
class DetailLineSelectionFilter(ISelectionFilter):
    def AllowElement(self, elem):
        return elem.Category and elem.Category.Id.IntegerValue == int(
            BuiltInCategory.OST_Lines
        )

    def AllowReference(self, ref, point):
        return False


class ScopeBoxSelectionFilter(ISelectionFilter):
    def AllowElement(self, elem):
        return elem.Category and elem.Category.Id.IntegerValue == int(
            BuiltInCategory.OST_VolumeOfInterest
        )

    def AllowReference(self, ref, point):
        return False


# -----------------------------
# Geometry helpers
# -----------------------------
def points_are_close(pt1, pt2, tol=1e-6):
    return (
        abs(pt1.X - pt2.X) < tol
        and abs(pt1.Y - pt2.Y) < tol
        and abs(pt1.Z - pt2.Z) < tol
    )


def order_segments_to_polygon(segments):
    if not segments:
        return None
    polygon = [segments[0][0], segments[0][1]]
    segments.pop(0)
    changed = True
    while segments and changed:
        changed = False
        last_pt = polygon[-1]
        for idx, seg in enumerate(segments):
            ptA, ptB = seg
            if points_are_close(last_pt, ptA):
                polygon.append(ptB)
                segments.pop(idx)
                changed = True
                break
            elif points_are_close(last_pt, ptB):
                polygon.append(ptA)
                segments.pop(idx)
                changed = True
                break
    if polygon and points_are_close(polygon[0], polygon[-1]):
        polygon.pop()
        return polygon
    return None


def is_point_inside_polygon(point, polygon):
    x, y = point.X, point.Y
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i].X, polygon[i].Y
        xj, yj = polygon[j].X, polygon[j].Y
        if ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi
        ):
            inside = not inside
        j = i
    return inside


def bbox_center(elem, view):
    try:
        bb = elem.get_BoundingBox(view)
    except Exception:
        return None
    if not bb:
        return None
    return XYZ(
        (bb.Min.X + bb.Max.X) * 0.5,
        (bb.Min.Y + bb.Max.Y) * 0.5,
        (bb.Min.Z + bb.Max.Z) * 0.5,
    )


# -----------------------------
# Region acquisition
# -----------------------------
def pick_scope_box():
    try:
        ref = uidoc.Selection.PickObject(
            ObjectType.Element,
            ScopeBoxSelectionFilter(),
            "Pick a scope box",
        )
    except Exception:
        return None
    if not ref:
        return None
    elem = doc.GetElement(ref)
    if not elem:
        return None
    bb = elem.get_BoundingBox(None)
    if not bb:
        return None
    return ("scopebox", bb)


def pick_detail_lines_polygon():
    try:
        refs = uidoc.Selection.PickObjects(
            ObjectType.Element,
            DetailLineSelectionFilter(),
            "Select boundary detail lines (closed loop)",
        )
    except Exception:
        return None
    if not refs:
        return None
    segments = []
    for r in refs:
        crv = doc.GetElement(r).GeometryCurve
        segments.append((crv.GetEndPoint(0), crv.GetEndPoint(1)))
    poly = order_segments_to_polygon(segments[:])
    if not poly:
        TaskDialog.Show("Region Scanner", "Detail lines do not form a closed loop.")
        return None
    return ("polygon", poly)


def choose_region():
    td = TaskDialog("Region Scanner")
    td.MainInstruction = "Choose region source"
    td.MainContent = "Yes = Scope Box\nNo = Detail Lines"
    td.CommonButtons = (
        TaskDialogCommonButtons.Yes
        | TaskDialogCommonButtons.No
        | TaskDialogCommonButtons.Cancel
    )
    res = td.Show()
    if res == TaskDialogResult.Yes:
        return pick_scope_box()
    if res == TaskDialogResult.No:
        return pick_detail_lines_polygon()
    return None


# -----------------------------
# Main logic
# -----------------------------
def main():
    region = choose_region()
    if not region:
        sys.exit("Cancelled.")

    kind, shape = region
    view = uidoc.ActiveView
    elems = (
        FilteredElementCollector(doc, view.Id)
        .WhereElementIsNotElementType()
        .ToElements()
    )

    inside = []
    for e in elems:
        ctr = bbox_center(e, view)
        if not ctr:
            continue
        if kind == "scopebox":
            bb = shape
            if (
                ctr.X >= bb.Min.X
                and ctr.X <= bb.Max.X
                and ctr.Y >= bb.Min.Y
                and ctr.Y <= bb.Max.Y
            ):
                inside.append(e)
        elif kind == "polygon":
            if is_point_inside_polygon(ctr, shape):
                inside.append(e)

    msg = "Found {} element(s) in region.".format(len(inside))
    print(msg)
    for e in inside:
        cname = e.Category.Name if e.Category else "NoCategory"
        name = e.Name if hasattr(e, "Name") else ""
        print(" - {} | {} | Id {}".format(cname, name, e.Id))

    TaskDialog.Show("Region Scanner", msg)


if __name__ == "__main__":
    main()
