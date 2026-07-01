# -*- coding: utf-8 -*-
__title__ = "sheet_generator.py"
__doc__ = """PLEGTVOS sheet generator with editor, coded comments, plan/sheet/3D creation, and schedule placement."""

from Autodesk.Revit.DB import (
    BuiltInCategory,
    BuiltInParameter,
    BoundingBoxXYZ,
    ElementId,
    FamilyInstance,
    FamilySymbol,
    FilteredElementCollector,
    IndependentTag,
    Reference,
    ScheduleFilter,
    ScheduleFilterType,
    ScheduleSheetInstance,
    ScheduleSortGroupField,
    ScheduleSortOrder,
    Transaction,
    TransactionGroup,
    TextNote,
    TextNoteOptions,
    TextNoteType,
    TagMode,
    TagOrientation,
    View3D,
    ViewDiscipline,
    ViewDuplicateOption,
    ViewFamily,
    ViewFamilyType,
    ViewPlan,
    Viewport,
    ViewSchedule,
    ViewSheet,
    ViewType,
    UV,
    XYZ,
)
from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType
from Autodesk.Revit.UI import TaskDialog, TaskDialogCommonButtons, TaskDialogResult
from Autodesk.Revit.Exceptions import ArgumentException, OperationCanceledException

import clr
import math
import re
import traceback
import System
from System import Array
from System.Collections.Generic import List

clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")
from System.Windows.Forms import (
    Form,
    DataGridView,
    DataGridViewColumn,
    DataGridViewTextBoxColumn,
    DataGridViewButtonColumn,
    DataGridViewAutoSizeColumnsMode,
    DataGridViewSelectionMode,
    TextBox,
    Button,
    DialogResult,
    ListBox,
)
from System.Drawing import Point, Rectangle, Size, Color


uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

FUND_PREFIX = "1."
FORCE_FUND_PREFIX = False
SCHEDULE_NAME_SEP = " - "
DEBUG_TAG_FALLBACK = False


def log(*parts):
    print(" ".join([str(p) for p in parts]))


def warn(msg):
    TaskDialog.Show("sheet_generator", msg)


class DetailLineSelectionFilter(ISelectionFilter):
    def AllowElement(self, elem):
        try:
            return (
                elem
                and elem.Category
                and elem.Category.Id.IntegerValue == int(BuiltInCategory.OST_Lines)
            )
        except Exception:
            return False

    def AllowReference(self, ref, point):
        return False


def distance_xyz(a, b):
    return math.sqrt(
        ((a.X - b.X) ** 2) + ((a.Y - b.Y) ** 2) + ((a.Z - b.Z) ** 2)
    )


def plane_basis_from_points(points):
    origin = points[0]
    normal = XYZ.BasisZ
    try:
        normal = uidoc.ActiveView.ViewDirection.Normalize()
    except Exception:
        pass
    axis_x = None
    for pt in points[1:]:
        vec = pt - origin
        if vec.GetLength() > 1e-9:
            axis_x = vec.Normalize()
            break
    if axis_x is None:
        axis_x = XYZ.BasisX
    axis_y = normal.CrossProduct(axis_x)
    if axis_y.GetLength() < 1e-9:
        axis_y = XYZ.BasisY
    else:
        axis_y = axis_y.Normalize()
    return origin, normal.Normalize(), axis_x, axis_y


def project_point_to_plane(pt, origin, normal):
    vec = pt - origin
    return pt - normal.Multiply(vec.DotProduct(normal))


def cluster_points(points, tol, origin, normal):
    nodes = []
    mapping = []
    for pt in points:
        proj = project_point_to_plane(pt, origin, normal)
        found = None
        best = None
        for idx, node in enumerate(nodes):
            dist = distance_xyz(proj, node)
            if dist <= tol and (best is None or dist < best):
                found = idx
                best = dist
        if found is None:
            nodes.append(proj)
            mapping.append(len(nodes) - 1)
        else:
            mapping.append(found)
    return nodes, mapping


def build_graph(curves, tol):
    raw_points = []
    for curve in curves:
        raw_points.append(curve.GetEndPoint(0))
        raw_points.append(curve.GetEndPoint(1))
    origin, normal, axis_x, axis_y = plane_basis_from_points(raw_points)
    nodes, mapping = cluster_points(raw_points, tol, origin, normal)
    adj = {}
    segments = []
    edge_keys = set()
    dup_count = 0
    max_gap = 0.0

    for idx, curve in enumerate(curves):
        p0 = project_point_to_plane(curve.GetEndPoint(0), origin, normal)
        p1 = project_point_to_plane(curve.GetEndPoint(1), origin, normal)
        a = mapping[idx * 2]
        b = mapping[idx * 2 + 1]
        max_gap = max(max_gap, distance_xyz(p0, nodes[a]), distance_xyz(p1, nodes[b]))
        key = tuple(sorted((a, b)))
        if key in edge_keys:
            dup_count += 1
        else:
            edge_keys.add(key)
        seg = {"a": a, "b": b, "curve": curve, "index": idx}
        segments.append(seg)
        adj.setdefault(a, []).append(seg)
        adj.setdefault(b, []).append(seg)

    visited = set()
    components = 0
    for node in adj:
        if node in visited:
            continue
        components += 1
        stack = [node]
        while stack:
            cur = stack.pop()
            if cur in visited:
                continue
            visited.add(cur)
            for seg in adj.get(cur, []):
                nxt = seg["b"] if seg["a"] == cur else seg["a"]
                if nxt not in visited:
                    stack.append(nxt)

    open_nodes = [node for node, edges in adj.items() if len(edges) == 1]
    branch_nodes = [node for node, edges in adj.items() if len(edges) > 2]
    return {
        "nodes": nodes,
        "segments": segments,
        "adj": adj,
        "origin": origin,
        "normal": normal,
        "axis_x": axis_x,
        "axis_y": axis_y,
        "components": components,
        "duplicates": dup_count,
        "open_nodes": open_nodes,
        "branch_nodes": branch_nodes,
        "max_gap": max_gap,
    }


def extract_component(graph, seed):
    nodes = set()
    stack = [seed]
    while stack:
        cur = stack.pop()
        if cur in nodes:
            continue
        nodes.add(cur)
        for seg in graph["adj"].get(cur, []):
            nxt = seg["b"] if seg["a"] == cur else seg["a"]
            if nxt not in nodes:
                stack.append(nxt)
    return nodes


def chain_loop(graph, component_nodes):
    component = set(component_nodes)
    local_adj = {}
    segments = []
    for seg in graph["segments"]:
        if seg["a"] in component and seg["b"] in component:
            segments.append(seg)
            local_adj.setdefault(seg["a"], []).append(seg)
            local_adj.setdefault(seg["b"], []).append(seg)
    if not segments:
        return None
    if any(len(local_adj.get(node, [])) != 2 for node in component):
        return None

    start_seg = segments[0]
    current = start_seg["a"]
    used = set()
    ordered = [current]
    while True:
        next_seg = None
        for seg in local_adj.get(current, []):
            if seg["index"] not in used:
                next_seg = seg
                break
        if next_seg is None:
            break
        used.add(next_seg["index"])
        nxt = next_seg["b"] if next_seg["a"] == current else next_seg["a"]
        ordered.append(nxt)
        current = nxt
        if current == ordered[0]:
            break
    if len(used) != len(segments) or ordered[-1] != ordered[0]:
        return None
    return ordered[:-1]


def polygon_area_in_plane(points, axis_x, axis_y, origin):
    coords = []
    for pt in points:
        vec = pt - origin
        coords.append((vec.DotProduct(axis_x), vec.DotProduct(axis_y)))
    area = 0.0
    count = len(coords)
    for i in range(count):
        x1, y1 = coords[i]
        x2, y2 = coords[(i + 1) % count]
        area += (x1 * y2) - (x2 * y1)
    return 0.5 * area


def build_polygon_from_lines(elements):
    curves = []
    for elem in elements:
        curve = None
        try:
            loc = getattr(elem, "Location", None)
            if loc and hasattr(loc, "Curve") and loc.Curve:
                curve = loc.Curve
            else:
                curve = elem.GeometryCurve
        except Exception:
            curve = None
        if curve is None:
            continue
        p0 = curve.GetEndPoint(0)
        p1 = curve.GetEndPoint(1)
        log(
            "curve",
            elem.Id.IntegerValue,
            "p0=({:.6f},{:.6f},{:.6f})".format(p0.X, p0.Y, p0.Z),
            "p1=({:.6f},{:.6f},{:.6f})".format(p1.X, p1.Y, p1.Z),
            "len={:.6f}".format(curve.Length),
        )
        curves.append(curve)

    if not curves:
        raise Exception("No usable curves found in selected detail lines.")

    tol = max(1e-4, __revit__.Application.ShortCurveTolerance * 10.0)
    graph = build_graph(curves, tol)
    log("detail loop diagnostics:")
    log(" - max endpoint gap found:", graph["max_gap"])
    log(" - nodes degree!=2 open:", len(graph["open_nodes"]))
    log(" - nodes degree>2 branch:", len(graph["branch_nodes"]))
    log(" - connected components:", graph["components"])
    log(" - duplicate segments:", graph["duplicates"])

    loops = []
    seen_nodes = set()
    for node in graph["adj"]:
        if node in seen_nodes:
            continue
        component = extract_component(graph, node)
        seen_nodes |= component
        loop_idx = chain_loop(graph, component)
        if not loop_idx:
            continue
        pts = [graph["nodes"][idx] for idx in loop_idx]
        area = abs(
            polygon_area_in_plane(
                pts, graph["axis_x"], graph["axis_y"], graph["origin"]
            )
        )
        loops.append((area, pts))

    if not loops:
        raise Exception(
            "Not a simple closed loop. Open ends: {}, branch nodes: {}, components: {}, max_gap: {:.6f}".format(
                len(graph["open_nodes"]),
                len(graph["branch_nodes"]),
                graph["components"],
                graph["max_gap"],
            )
        )

    loops.sort(key=lambda item: item[0], reverse=True)
    return loops[0][1]


def is_point_inside_polygon(point, polygon):
    x = point.X
    y = point.Y
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        xi = polygon[i].X
        yi = polygon[i].Y
        xj = polygon[j].X
        yj = polygon[j].Y
        if ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi
        ):
            inside = not inside
        j = i
    return inside


def bbox_center(elem, view):
    try:
        bb = elem.get_BoundingBox(view)
        if not bb:
            return None
        return XYZ(
            (bb.Min.X + bb.Max.X) * 0.5,
            (bb.Min.Y + bb.Max.Y) * 0.5,
            (bb.Min.Z + bb.Max.Z) * 0.5,
        )
    except Exception:
        return None


def pick_boundary_detail_lines():
    try:
        refs = uidoc.Selection.PickObjects(
            ObjectType.Element,
            DetailLineSelectionFilter(),
            "Select boundary detail lines (closed loop)",
        )
    except OperationCanceledException:
        return []
    return [doc.GetElement(r.ElementId) for r in refs if r]


def get_region_polygon(selected):
    if not selected:
        raise Exception("No boundary detail lines selected.")
    return build_polygon_from_lines(selected)


def gather_elements_in_region(view, polygon, boundary_ids):
    elems = (
        FilteredElementCollector(doc, view.Id)
        .WhereElementIsNotElementType()
        .ToElements()
    )
    inside = []
    for elem in elems:
        if elem.Id.IntegerValue in boundary_ids:
            continue
        center = bbox_center(elem, view)
        if not center:
            continue
        if is_point_inside_polygon(center, polygon):
            inside.append(elem)
    return inside


def convert_param_to_string(param_obj):
    if not param_obj:
        return ""
    try:
        txt = param_obj.AsValueString()
        if txt:
            return txt
    except Exception:
        pass
    try:
        return str(param_obj.AsString() or "")
    except Exception:
        pass
    try:
        val = param_obj.AsDouble()
        return "{:.1f} mm".format(val * 304.8)
    except Exception:
        return ""


def lookup_first_param(elem, names):
    for name in names:
        try:
            p = elem.LookupParameter(name)
            if p:
                return p
        except Exception:
            pass
    return None


def get_comments(elem):
    p = elem.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
    if p:
        try:
            return p.AsString() or ""
        except Exception:
            return ""
    return ""


def normalize_category_name(cat):
    if not cat:
        return "<None>"
    return (cat.Name or "").strip()


def calc_center_xy(elem, view):
    center = bbox_center(elem, view)
    if not center:
        return (0.0, 0.0)
    return (center.X, center.Y)


def filter_relevant_elements(gathered_elements, view):
    relevant = []
    for elem in gathered_elements:
        if not elem or not elem.Category:
            continue
        cat = normalize_category_name(elem.Category)
        if cat not in (
            "Pipes",
            "Pipe Fittings",
            "Ducts",
            "Duct Fittings",
            "Text Notes",
        ):
            continue
        default_code = get_comments(elem)
        outside = convert_param_to_string(
            lookup_first_param(elem, ["Outside Diameter", "Diameter"])
        )
        length_val = convert_param_to_string(lookup_first_param(elem, ["Length"]))
        size_val = convert_param_to_string(lookup_first_param(elem, ["Size"]))
        article_val = convert_param_to_string(
            lookup_first_param(
                elem,
                [
                    "Artikelnummer",
                    "Article Nr",
                    "Article Number",
                    "NLRS_C_code_fabrikant_product",
                ],
            )
        )
        relevant.append(
            {
                "Id": str(elem.Id.IntegerValue),
                "Category": cat,
                "Name": getattr(elem, "Name", "") or "",
                "DefaultCode": default_code,
                "NewCode": default_code,
                "OutsideDiameter": outside,
                "Length": length_val,
                "Size": size_val,
                "TagStatus": "",
                "Warning": "",
                "Bend45": "",
                "ArticleNumber": article_val,
                "_center": calc_center_xy(elem, view),
            }
        )
    return relevant


def normalize_base_code(raw):
    match = re.search(r"([\d\.]+)", raw or "")
    if not match:
        raise Exception("Could not parse numeric code from '{}'".format(raw))
    return match.group(1)


def maybe_apply_fund_prefix(code):
    if not FORCE_FUND_PREFIX:
        return code
    if FUND_PREFIX and not code.startswith(FUND_PREFIX):
        return "{}{}".format(FUND_PREFIX, code)
    return code


def apply_auto_codes(elements_data, base_code):
    pipe_rows = []
    for idx, row in enumerate(elements_data):
        if row["Category"] == "Pipes":
            pipe_rows.append((idx, row.get("_center", (0.0, 0.0))))
        elif row["Category"] == "Pipe Fittings":
            row["NewCode"] = maybe_apply_fund_prefix(base_code)

    pipe_rows.sort(key=lambda item: (item[1][0], item[1][1]))
    for seq, (idx, _center) in enumerate(pipe_rows, 1):
        elements_data[idx]["NewCode"] = maybe_apply_fund_prefix(
            "{}.{}".format(base_code, seq)
        )


def set_comments_value(elem, code, manage_transaction=True):
    if not elem:
        return False
    tx = None
    started = False
    try:
        if manage_transaction:
            tx = Transaction(doc, "Set Comments for Tag")
            tx.Start()
            started = True
        param = elem.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        if not param:
            param = elem.LookupParameter("Comments")
        if not param or param.IsReadOnly:
            raise Exception("Comments parameter is missing or read-only.")
        param.Set(str(code or ""))
        if started:
            tx.Commit()
        return True
    except Exception:
        if started:
            try:
                tx.RollBack()
            except Exception:
                pass
        raise


def can_tag_in_view(view):
    try:
        return view and view.ViewType in (
            ViewType.FloorPlan,
            ViewType.CeilingPlan,
            ViewType.EngineeringPlan,
            ViewType.Section,
            ViewType.Detail,
            ViewType.DraftingView,
        )
    except Exception:
        return False


def get_element_bbox_center(elem, view):
    bb = elem.get_BoundingBox(view)
    if not bb:
        return None
    return XYZ(
        (bb.Min.X + bb.Max.X) * 0.5,
        (bb.Min.Y + bb.Max.Y) * 0.5,
        (bb.Min.Z + bb.Max.Z) * 0.5,
    )


def get_tag_collector_category(elem):
    cat = normalize_category_name(elem.Category)
    if cat == "Pipes":
        return BuiltInCategory.OST_PipeTags
    if cat == "Ducts":
        return BuiltInCategory.OST_DuctTags
    return None


def find_tags_for_host_in_view(host_elem_id, tag_bic, view_id):
    hits = []
    if tag_bic is None:
        return hits
    tags = (
        FilteredElementCollector(doc, view_id)
        .OfCategory(tag_bic)
        .WhereElementIsNotElementType()
        .ToElements()
    )
    for tag in tags:
        try:
            if hasattr(tag, "GetTaggedElementIds"):
                ids = tag.GetTaggedElementIds() or []
                for lid in ids:
                    try:
                        if hasattr(lid, "HostElementId") and lid.HostElementId == host_elem_id:
                            hits.append(tag)
                            break
                        elif hasattr(lid, "LinkedElementId") and lid.LinkedElementId == host_elem_id:
                            hits.append(tag)
                            break
                        elif hasattr(lid, "IntegerValue") and lid.IntegerValue == host_elem_id.IntegerValue:
                            hits.append(tag)
                            break
                    except Exception:
                        pass
            elif hasattr(tag, "TaggedElementId") and tag.TaggedElementId:
                try:
                    if tag.TaggedElementId == host_elem_id:
                        hits.append(tag)
                    elif tag.TaggedElementId.IntegerValue == host_elem_id.IntegerValue:
                        hits.append(tag)
                except Exception:
                    pass
        except Exception:
            pass
    return hits


def get_tag_symbol_for_category(bic):
    syms = list(
        FilteredElementCollector(doc).OfCategory(bic).OfClass(FamilySymbol).ToElements()
    )
    print("available tag symbols:", len(syms))
    if not syms:
        return None
    active_sym = next((s for s in syms if s.IsActive), None)
    return active_sym or syms[0]


def get_tag_type_label(tag_bic):
    if tag_bic == BuiltInCategory.OST_PipeTags:
        return "Pipe"
    if tag_bic == BuiltInCategory.OST_DuctTags:
        return "Duct"
    return "Model"


def place_debug_text_marker(view, point, text="TAG_TEST"):
    tx = Transaction(doc, "Place Debug Text")
    tx.Start()
    try:
        note_type = FilteredElementCollector(doc).OfClass(TextNoteType).FirstElement()
        if not note_type:
            raise Exception("No TextNoteType found for debug marker.")
        opts = TextNoteOptions(note_type.Id)
        TextNote.Create(doc, view.Id, point, text, opts)
        tx.Commit()
        print("fallback marker placed")
    except Exception:
        tx.RollBack()
        raise


def ensure_tag_visibility_for_view(view, tag_bic, manage_transaction=True):
    try:
        cat = doc.Settings.Categories.get_Item(tag_bic)
    except Exception:
        cat = None
    hidden = False
    try:
        if cat and view.CanCategoryBeHidden(cat.Id):
            hidden = view.GetCategoryHidden(cat.Id)
    except Exception:
        hidden = False
    print("{} tags hidden: {}".format(get_tag_type_label(tag_bic), hidden))
    tx = None
    started = False
    try:
        if manage_transaction:
            tx = Transaction(doc, "Debug Tag Visibility")
            tx.Start()
            started = True
        if cat and hidden and view.CanCategoryBeHidden(cat.Id):
            view.SetCategoryHidden(cat.Id, False)
            print("tag category unhidden")
        anno = view.get_Parameter(BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE)
        if anno:
            print("annotation crop active:", anno.AsInteger())
            if not anno.IsReadOnly:
                anno.Set(0)
                print("annotation crop set to OFF for debug")
        crop_vis = view.get_Parameter(BuiltInParameter.VIEWER_CROP_REGION_VISIBLE)
        if crop_vis:
                print("crop region visible:", crop_vis.AsInteger())
                if not crop_vis.IsReadOnly:
                    crop_vis.Set(1)
        if started:
            tx.Commit()
    except Exception as ex:
        if started:
            tx.RollBack()
        print("ensure_tag_visibility failed:", ex)
        print(traceback.format_exc())


def remove_tags_for_host(host_elem_id, tag_bic, view, manage_transaction=True):
    tags = find_tags_for_host_in_view(host_elem_id, tag_bic, view.Id)
    if not tags:
        return []
    tx = None
    started = False
    try:
        if manage_transaction:
            tx = Transaction(doc, "Remove Tag")
            tx.Start()
            started = True
        for tag in tags:
            print("tag remove ->", host_elem_id.IntegerValue, "tag", tag.Id.IntegerValue)
            doc.Delete(tag.Id)
        if started:
            tx.Commit()
        return tags
    except Exception:
        if started:
            try:
                tx.RollBack()
            except Exception:
                pass
        raise


def create_tag_for_host(host, tag_bic, view, manage_transaction=True, debug_focus=True):
    sym = get_tag_symbol_for_category(tag_bic)
    if not sym:
        TaskDialog.Show(
            "Tags",
            "No {} Tag type loaded in this project.".format(
                get_tag_type_label(tag_bic)
            ),
        )
        return None, None
    bbox = host.get_BoundingBox(view)
    if not bbox:
        raise Exception("Element has no bounding box in active view.")
    try:
        type_name = (
            sym.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
            if sym and sym.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM)
            else "<none>"
        )
    except Exception:
        type_name = "<none>"
    try:
        fam_name = sym.Family.Name if sym and sym.Family else "<none>"
    except Exception:
        fam_name = "<none>"
    pt = XYZ(
        (bbox.Min.X + bbox.Max.X) * 0.5,
        (bbox.Min.Y + bbox.Max.Y) * 0.5,
        (bbox.Min.Z + bbox.Max.Z) * 0.5,
    )
    try:
        pt = pt + view.RightDirection.Multiply(0.5) + view.UpDirection.Multiply(0.5)
    except Exception as ex:
        print("view offset failed:", ex)
    ref = Reference(host)
    print(
        "tag symbol:",
        fam_name,
        "|",
        type_name,
        "| id:",
        sym.Id.IntegerValue,
    )
    print(
        "active view:",
        view.Name,
        "| type:",
        view.ViewType,
        "| id:",
        view.Id.IntegerValue,
    )
    print("host cat:", host.Category.Name if host.Category else None)
    ensure_tag_visibility_for_view(view, tag_bic, manage_transaction=manage_transaction)
    tx = None
    started = False
    try:
        if manage_transaction:
            tx = Transaction(doc, "Add Tag")
            tx.Start()
            started = True
        if not sym.IsActive:
            sym.Activate()
            doc.Regenerate()
        try:
            tag = IndependentTag.Create(
                doc,
                sym.Id,
                view.Id,
                ref,
                True,
                TagOrientation.Horizontal,
                pt,
            )
        except (TypeError, ArgumentException):
            print("tag create primary overload failed, trying NewTag fallback")
            tag = doc.Create.NewTag(
                view,
                host,
                False,
                TagMode.TM_ADDBY_CATEGORY,
                TagOrientation.Horizontal,
                pt,
            )
        if started:
            tx.Commit()
        print("tag create result:", tag)
        if tag:
            print("tag created id={}".format(tag.Id.IntegerValue))
            if debug_focus:
                ids = List[ElementId]()
                ids.Add(tag.Id)
                uidoc.Selection.SetElementIds(ids)
                uidoc.ShowElements(tag.Id)
                if hasattr(tag, "TagHeadPosition"):
                    print("tag head:", tag.TagHeadPosition)
                else:
                    print("no TagHeadPosition prop")
        return tag, pt
    except Exception as ex:
        if started:
            try:
                tx.RollBack()
            except Exception:
                pass
        print("tag create exception:", ex)
        print(traceback.format_exc())
        raise


class ElementEditorForm(Form):
    def __init__(self, elements_data, region_elements=None, region_polygon=None, active_view=None):
        self.Text = "Edit Element Codes"
        self.Width = 1050
        self.Height = 550
        self.MinimumSize = Size(800, 450)
        self.Result = None
        self.elements_data = elements_data
        self.region_elements = region_elements or []
        self.region_polygon = region_polygon
        self.active_view = active_view or uidoc.ActiveView
        self.textNotePlaced = False
        self.tag_cache = {}

        self.grid = DataGridView()
        self.grid.Dock = System.Windows.Forms.DockStyle.Fill
        self.grid.AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill
        self.grid.SelectionMode = DataGridViewSelectionMode.FullRowSelect
        self.grid.AllowUserToAddRows = False
        self.grid.MultiSelect = True
        self.grid.SelectionChanged += self.on_row_selected
        self.grid.CellContentClick += self.dataGrid_CellContentClick
        self.Controls.Add(self.grid)

        footer = System.Windows.Forms.Panel()
        footer.Height = 48
        footer.Dock = System.Windows.Forms.DockStyle.Bottom
        self.Controls.Add(footer)

        self.txtCode = TextBox()
        self.txtCode.Width = 180
        self.txtCode.Text = "prefab 1.6.1"
        self.txtCode.Location = Point(10, 12)
        footer.Controls.Add(self.txtCode)

        self.btnPlaceTextNote = Button()
        self.btnPlaceTextNote.Text = "Place Text Note"
        self.btnPlaceTextNote.Width = 120
        self.btnPlaceTextNote.Location = Point(200, 10)
        self.btnPlaceTextNote.Click += self.btnPlaceTextNote_Click
        footer.Controls.Add(self.btnPlaceTextNote)

        self.btnAuto = Button()
        self.btnAuto.Text = "Auto-Fill Codes"
        self.btnAuto.Width = 120
        self.btnAuto.Location = Point(330, 10)
        self.btnAuto.Click += self.on_auto_fill
        footer.Controls.Add(self.btnAuto)

        self.btnBulkTags = Button()
        self.btnBulkTags.Text = "Add/Remove Tags"
        self.btnBulkTags.Width = 130
        self.btnBulkTags.Location = Point(460, 10)
        self.btnBulkTags.Click += self.btnBulkTags_Click
        footer.Controls.Add(self.btnBulkTags)

        self.btnOk = Button()
        self.btnOk.Text = "OK"
        self.btnOk.Width = 80
        self.btnOk.Location = Point(870, 10)
        self.btnOk.Click += self.on_ok
        footer.Controls.Add(self.btnOk)

        self.btnCancel = Button()
        self.btnCancel.Text = "Cancel"
        self.btnCancel.Width = 80
        self.btnCancel.Location = Point(960, 10)
        self.btnCancel.DialogResult = DialogResult.Cancel
        footer.Controls.Add(self.btnCancel)

        cols = []
        for name, header, readonly in [
            ("Id", "Element Id", True),
            ("Category", "Category", True),
            ("Name", "Name", True),
            ("Warning", "Warning", True),
            ("Bend45", "Bend45", True),
            ("DefaultCode", "Default Code", True),
            ("NewCode", "New Code", False),
            ("OutsideDiameter", "Outside Diameter", True),
            ("Length", "Length", True),
            ("Size", "Size", True),
            ("ArticleNumber", "Article Number", True),
        ]:
            col = DataGridViewTextBoxColumn()
            col.Name = name
            col.HeaderText = header
            col.ReadOnly = readonly
            cols.append(col)
        self.grid.Columns.AddRange(Array[DataGridViewColumn](cols))
        tag_col = DataGridViewButtonColumn()
        tag_col.Name = "TagStatus"
        tag_col.HeaderText = "TagStatus"
        tag_col.UseColumnTextForButtonValue = False
        self.grid.Columns.Add(tag_col)

        for row_data in elements_data:
            idx = self.grid.Rows.Add()
            row = self.grid.Rows[idx]
            for key in (
                "Id",
                "Category",
                "Name",
                "Warning",
                "Bend45",
                "DefaultCode",
                "NewCode",
                "OutsideDiameter",
                "Length",
                "Size",
                "ArticleNumber",
                "TagStatus",
            ):
                row.Cells[key].Value = row_data.get(key, "")
            cat = row_data.get("Category", "")
            if cat == "Pipes":
                row.DefaultCellStyle.BackColor = Color.LightBlue
            elif cat == "Pipe Fittings":
                row.DefaultCellStyle.BackColor = Color.LightGoldenrodYellow
            elif cat == "Ducts":
                row.DefaultCellStyle.BackColor = Color.LightGreen
            elif cat == "Duct Fittings":
                row.DefaultCellStyle.BackColor = Color.MistyRose
            self.refresh_tag_status_for_row(row)

    def on_auto_fill(self, sender, event):
        try:
            base = normalize_base_code(self.txtCode.Text.strip())
        except Exception as ex:
            TaskDialog.Show("sheet_generator", str(ex))
            return
        apply_auto_codes(self.elements_data, base)
        for idx, row_data in enumerate(self.elements_data):
            self.grid.Rows[idx].Cells["NewCode"].Value = row_data.get("NewCode", "")

    def on_ok(self, sender, event):
        updated = []
        for row in self.grid.Rows:
            data = {}
            for key in (
                "Id",
                "Category",
                "Name",
                "Warning",
                "Bend45",
                "DefaultCode",
                "NewCode",
                "OutsideDiameter",
                "Length",
                "Size",
                "ArticleNumber",
                "TagStatus",
            ):
                data[key] = row.Cells[key].Value
            updated.append(data)
        self.Result = {
            "Elements": updated,
            "TextNote": self.txtCode.Text.strip(),
            "TextNotePlaced": self.textNotePlaced,
        }
        self.DialogResult = DialogResult.OK
        self.Close()

    def refresh_tag_status_for_row(self, row):
        try:
            cat = row.Cells["Category"].Value
            eid = int(str(row.Cells["Id"].Value))
            elem = doc.GetElement(ElementId(eid))
            if cat not in ("Pipes", "Ducts") or elem is None:
                row.Cells["TagStatus"].Value = ""
                row.Cells["TagStatus"].ReadOnly = True
                return
            tag_category = get_tag_collector_category(elem)
            if tag_category is None:
                row.Cells["TagStatus"].Value = ""
                row.Cells["TagStatus"].ReadOnly = True
                return
            tags = find_tags_for_host_in_view(
                ElementId(eid), tag_category, self.active_view.Id
            )
            if tags:
                self.tag_cache[eid] = tags[0].Id.IntegerValue
                row.Cells["TagStatus"].Value = "Remove Tag"
            else:
                row.Cells["TagStatus"].Value = "Add Tag"
            row.Cells["TagStatus"].ReadOnly = False
        except Exception:
            row.Cells["TagStatus"].Value = ""
            row.Cells["TagStatus"].ReadOnly = True

    def _next_pipe_code(self, base_code):
        prefix = "{}.".format(base_code)
        max_suffix = 0
        for scan_row in self.grid.Rows:
            try:
                cat = scan_row.Cells["Category"].Value or ""
                if cat != "Pipes":
                    continue
                code_val = scan_row.Cells["NewCode"].Value or scan_row.Cells["DefaultCode"].Value or ""
                code_val = str(code_val).strip()
                if not code_val.startswith(prefix):
                    continue
                suffix = code_val[len(prefix) :]
                if suffix.isdigit():
                    max_suffix = max(max_suffix, int(suffix))
                    continue
                parts = code_val.split(".")
                if parts and parts[-1].isdigit():
                    max_suffix = max(max_suffix, int(parts[-1]))
            except Exception:
                pass
        return "{}.{}".format(base_code, max_suffix + 1)

    def _resolve_code_for_row(self, row):
        code = row.Cells["NewCode"].Value or row.Cells["DefaultCode"].Value or ""
        code = str(code).strip()
        if code:
            return code
        base_code = maybe_apply_fund_prefix(normalize_base_code(self.txtCode.Text.strip()))
        category_name = row.Cells["Category"].Value or ""
        if category_name == "Pipes":
            code = self._next_pipe_code(base_code)
        else:
            code = base_code
        row.Cells["NewCode"].Value = code
        return code

    def on_row_selected(self, sender, event):
        try:
            selected_rows = list(self.grid.SelectedRows)
            ids = System.Collections.Generic.List[ElementId]()
            if len(selected_rows) > 1:
                for row in selected_rows[:50]:
                    try:
                        eid = int(str(row.Cells["Id"].Value))
                        print("highlight ->", eid)
                        ids.Add(ElementId(eid))
                    except Exception:
                        pass
            else:
                row = self.grid.CurrentRow
                if row:
                    eid = int(str(row.Cells["Id"].Value))
                    print("highlight ->", eid)
                    ids.Add(ElementId(eid))
            if ids.Count > 0:
                uidoc.Selection.SetElementIds(ids)
                try:
                    uidoc.RefreshActiveView()
                except Exception as ex:
                    print("highlight failed:", ex)
        except Exception as ex:
            print("highlight failed:", ex)

    def btnPlaceTextNote_Click(self, sender, event):
        if not self.region_elements and not self.region_polygon:
            TaskDialog.Show("sheet_generator", "No region elements available.")
            return
        text_val = self.txtCode.Text.strip()
        if not text_val:
            TaskDialog.Show("sheet_generator", "Enter a code first.")
            return
        region_min, region_max = get_region_bounding_box(
            self.region_elements, self.region_polygon, self.active_view
        )
        point = XYZ(region_min.X, region_min.Y - 0.5, region_min.Z)
        tx = Transaction(doc, "Place Text Note")
        tx.Start()
        try:
            note_type = FilteredElementCollector(doc).OfClass(TextNoteType).FirstElement()
            if not note_type:
                raise Exception("No TextNoteType found.")
            opts = TextNoteOptions(note_type.Id)
            TextNote.Create(doc, self.active_view.Id, point, text_val, opts)
            tx.Commit()
            self.textNotePlaced = True
        except Exception as ex:
            tx.RollBack()
            TaskDialog.Show("sheet_generator", str(ex))

    def toggle_tag_for_row(self, row):
        try:
            allowed = (
                ViewType.FloorPlan,
                ViewType.CeilingPlan,
                ViewType.EngineeringPlan,
                ViewType.Section,
                ViewType.Detail,
                ViewType.DraftingView,
            )
            if uidoc.ActiveView.ViewType not in allowed:
                TaskDialog.Show(
                    "Tags",
                    "Tagging is not supported in this view type: {}".format(
                        uidoc.ActiveView.ViewType
                    ),
                )
                return
            eid = int(str(row.Cells["Id"].Value))
            elem = doc.GetElement(ElementId(eid))
            category_name = row.Cells["Category"].Value or ""
            if category_name not in ("Pipes", "Ducts"):
                row.Cells["TagStatus"].Value = ""
                row.Cells["TagStatus"].ReadOnly = True
                return
            tag_category = get_tag_collector_category(elem) if elem else None
            if tag_category is None:
                return
            status = row.Cells["TagStatus"].Value or ""
            if status == "Add Tag":
                existing_tags = find_tags_for_host_in_view(
                    ElementId(eid), tag_category, uidoc.ActiveView.Id
                )
                print("existing tags found for host {}: {}".format(eid, len(existing_tags)))
                if existing_tags:
                    remove_tags_for_host(ElementId(eid), tag_category, uidoc.ActiveView)
                    self.refresh_tag_status_for_row(row)
                    return
                code = self._resolve_code_for_row(row)
                set_comments_value(elem, code)
                print("tag create ->", eid)
                tag, tag_point = create_tag_for_host(elem, tag_category, uidoc.ActiveView)
                if tag:
                    self.tag_cache[eid] = tag.Id.IntegerValue
                elif DEBUG_TAG_FALLBACK:
                    place_debug_text_marker(uidoc.ActiveView, tag_point)
            elif status == "Remove Tag":
                remove_tags_for_host(ElementId(eid), tag_category, uidoc.ActiveView)
                if eid in self.tag_cache:
                    del self.tag_cache[eid]
            self.refresh_tag_status_for_row(row)
        except Exception as ex:
            print("tag toggle failed:", ex)
            print(traceback.format_exc())
            TaskDialog.Show("Tags", str(ex))

    def btnBulkTags_Click(self, sender, event):
        row_map = {}
        for row in list(self.grid.SelectedRows):
            if (row.Cells["Category"].Value or "") in ("Pipes", "Ducts"):
                row_map[row.Index] = row
        rows = [row_map[idx] for idx in sorted(row_map.keys())]
        if not rows:
            TaskDialog.Show(
                "Tags", "Select one or more Pipes or Ducts rows first."
            )
            return
        rows_to_add = [row for row in rows if (row.Cells["TagStatus"].Value or "") == "Add Tag"]
        rows_to_remove = [row for row in rows if (row.Cells["TagStatus"].Value or "") == "Remove Tag"]
        tg = TransactionGroup(doc, "Bulk Tags")
        tg.Start()
        try:
            self.grid.SelectionChanged -= self.on_row_selected
            if rows_to_remove:
                tx_remove = Transaction(doc, "Bulk Remove Tags")
                tx_remove.Start()
                try:
                    for row in rows_to_remove:
                        eid = int(str(row.Cells["Id"].Value))
                        elem = doc.GetElement(ElementId(eid))
                        tag_category = get_tag_collector_category(elem) if elem else None
                        if tag_category is None:
                            continue
                        remove_tags_for_host(
                            ElementId(eid),
                            tag_category,
                            uidoc.ActiveView,
                            manage_transaction=False,
                        )
                        if eid in self.tag_cache:
                            del self.tag_cache[eid]
                    tx_remove.Commit()
                except Exception:
                    tx_remove.RollBack()
                    raise
            if rows_to_add:
                tx_add = Transaction(doc, "Bulk Add Tags")
                tx_add.Start()
                try:
                    for row in rows_to_add:
                        eid = int(str(row.Cells["Id"].Value))
                        elem = doc.GetElement(ElementId(eid))
                        tag_category = get_tag_collector_category(elem) if elem else None
                        if tag_category is None:
                            continue
                        existing_tags = find_tags_for_host_in_view(
                            ElementId(eid), tag_category, uidoc.ActiveView.Id
                        )
                        print("existing tags found for host {}: {}".format(eid, len(existing_tags)))
                        if existing_tags:
                            remove_tags_for_host(
                                ElementId(eid),
                                tag_category,
                                uidoc.ActiveView,
                                manage_transaction=False,
                            )
                            continue
                        code = self._resolve_code_for_row(row)
                        set_comments_value(elem, code, manage_transaction=False)
                        print("tag create ->", eid)
                        tag, _tag_point = create_tag_for_host(
                            elem,
                            tag_category,
                            uidoc.ActiveView,
                            manage_transaction=False,
                            debug_focus=False,
                        )
                        if tag:
                            self.tag_cache[eid] = tag.Id.IntegerValue
                    tx_add.Commit()
                except Exception:
                    tx_add.RollBack()
                    raise
            for row in rows:
                self.refresh_tag_status_for_row(row)
            tg.Assimilate()
        except Exception:
            tg.RollBack()
            raise
        finally:
            try:
                self.grid.SelectionChanged += self.on_row_selected
            except Exception:
                pass

    def dataGrid_CellContentClick(self, sender, event):
        if event.RowIndex < 0 or event.ColumnIndex < 0:
            return
        col = self.grid.Columns[event.ColumnIndex]
        if col.Name != "TagStatus":
            return
        row = self.grid.Rows[event.RowIndex]
        self.toggle_tag_for_row(row)


def show_element_editor(elements_data, region_elements=None, region_polygon=None, active_view=None):
    form = ElementEditorForm(elements_data, region_elements, region_polygon, active_view)
    if form.ShowDialog() == DialogResult.OK:
        return form.Result
    return None


def get_region_bounding_box(boundary_elements, polygon, view):
    if polygon:
        xs = [p.X for p in polygon]
        ys = [p.Y for p in polygon]
        zs = [p.Z for p in polygon]
        return XYZ(min(xs), min(ys), min(zs)), XYZ(max(xs), max(ys), max(zs))
    all_min = [1e99, 1e99, 1e99]
    all_max = [-1e99, -1e99, -1e99]
    for elem in boundary_elements:
        bb = elem.get_BoundingBox(view)
        if not bb:
            continue
        all_min[0] = min(all_min[0], bb.Min.X)
        all_min[1] = min(all_min[1], bb.Min.Y)
        all_min[2] = min(all_min[2], bb.Min.Z)
        all_max[0] = max(all_max[0], bb.Max.X)
        all_max[1] = max(all_max[1], bb.Max.Y)
        all_max[2] = max(all_max[2], bb.Max.Z)
    return (
        XYZ(all_min[0], all_min[1], all_min[2]),
        XYZ(all_max[0], all_max[1], all_max[2]),
    )


def write_comments_codes(result):
    t = Transaction(doc, "Update Comments")
    t.Start()
    try:
        base_code = maybe_apply_fund_prefix(normalize_base_code(result["TextNote"]))
        for row in result["Elements"]:
            try:
                elem = doc.GetElement(ElementId(int(str(row["Id"]))))
            except Exception:
                elem = None
            if not elem:
                continue
            p = elem.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
            if not p or p.IsReadOnly:
                continue
            if row["Category"] == "Pipe Fittings":
                p.Set(base_code)
            else:
                p.Set(str(row.get("NewCode") or ""))
        t.Commit()
    except Exception:
        t.RollBack()
        raise


class TBPicker(Form):
    def __init__(self, symbols):
        self.Text = "Choose a Title Block"
        self.ClientSize = Size(320, 360)
        self.symbols = symbols
        self.lb = ListBox()
        self.lb.Bounds = Rectangle(10, 10, 300, 300)
        for sym in symbols:
            fam = sym.FamilyName
            type_name = (
                sym.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM).AsString() or ""
            )
            self.lb.Items.Add("{} - {}".format(fam, type_name))
        self.Controls.Add(self.lb)
        ok = Button(Text="OK", DialogResult=DialogResult.OK, Location=Point(10, 320))
        ca = Button(
            Text="Cancel", DialogResult=DialogResult.Cancel, Location=Point(100, 320)
        )
        self.Controls.Add(ok)
        self.Controls.Add(ca)
        self.AcceptButton = ok
        self.CancelButton = ca


def make_unique_view_name(base_name):
    existing = {v.Name for v in FilteredElementCollector(doc).OfClass(ViewPlan)}
    if base_name not in existing:
        return base_name
    idx = 1
    while True:
        name = "{}_{}".format(base_name, idx)
        if name not in existing:
            return name
        idx += 1


def create_cropped_plan_view(active_view, base_code, region_min, region_max):
    if active_view.ViewType != ViewType.FloorPlan:
        raise Exception("Active view is not a Floor Plan.")
    tx = Transaction(doc, "Create Cropped Plan View")
    tx.Start()
    try:
        new_id = active_view.Duplicate(ViewDuplicateOption.WithDetailing)
        new_view = doc.GetElement(new_id)
        new_view.ViewTemplateId = ElementId.InvalidElementId
        try:
            new_view.Discipline = ViewDiscipline.Coordination
        except Exception:
            pass
        try:
            new_view.Scale = 25
        except Exception:
            pass
        new_view.Name = make_unique_view_name(base_code)
        bb = BoundingBoxXYZ()
        bb.Min = region_min
        bb.Max = region_max
        bb.Transform = active_view.CropBox.Transform
        new_view.CropBoxActive = True
        new_view.CropBoxVisible = True
        new_view.CropBox = bb
        anno = new_view.get_Parameter(BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE)
        if anno and not anno.IsReadOnly:
            anno.Set(1)
        tx.Commit()
        return new_view
    except Exception:
        tx.RollBack()
        raise


def pick_title_block():
    symbols = list(
        FilteredElementCollector(doc)
        .OfCategory(BuiltInCategory.OST_TitleBlocks)
        .OfClass(FamilySymbol)
        .ToElements()
    )
    if not symbols:
        raise Exception("No title block types found.")
    picker = TBPicker(symbols)
    if picker.ShowDialog() != DialogResult.OK or picker.lb.SelectedIndex < 0:
        raise Exception("Sheet creation cancelled.")
    return symbols[picker.lb.SelectedIndex]


def get_titleblock_center(sheet, title_block):
    inst = next(
        (
            e
            for e in FilteredElementCollector(doc, sheet.Id)
            .OfClass(FamilyInstance)
            .ToElements()
            if e.Symbol.Id == title_block.Id
        ),
        None,
    )
    bb = inst.get_BoundingBox(sheet) if inst else None
    if not bb:
        return XYZ(
            (sheet.Outline.Min.U + sheet.Outline.Max.U) * 0.5,
            (sheet.Outline.Min.V + sheet.Outline.Max.V) * 0.5,
            0,
        )
    return XYZ((bb.Min.X + bb.Max.X) * 0.5, (bb.Min.Y + bb.Max.Y) * 0.5, 0)


def create_sheet_with_views(base_code, plan_view, region_min, region_max):
    title_block = pick_title_block()
    tx = Transaction(doc, "Create Sheet and Views")
    tx.Start()
    try:
        sheet = ViewSheet.Create(doc, title_block.Id)
        sheet.SheetNumber = base_code
        sheet.Name = "Prefab " + base_code
        center = get_titleblock_center(sheet, title_block)
        Viewport.Create(doc, sheet.Id, plan_view.Id, center)

        vft = next(
            v
            for v in FilteredElementCollector(doc).OfClass(ViewFamilyType).ToElements()
            if v.ViewFamily == ViewFamily.ThreeDimensional
        )
        view3d = View3D.CreateIsometric(doc, vft.Id)
        view3d.Name = make_unique_view_name(base_code + "_3D")
        try:
            view3d.Discipline = ViewDiscipline.Architectural
        except Exception:
            pass
        try:
            view3d.Scale = 25
        except Exception:
            pass
        tmpl = next(
            (
                v
                for v in FilteredElementCollector(doc).OfClass(View3D).ToElements()
                if v.IsTemplate and v.Name in ("S4R_A00_Algemeen_3D", "A00_Algemeen_3D")
            ),
            None,
        )
        if tmpl:
            view3d.ViewTemplateId = tmpl.Id
        sb = BoundingBoxXYZ()
        sb.Min = region_min
        sb.Max = region_max
        view3d.SetSectionBox(sb)
        Viewport.Create(
            doc, sheet.Id, view3d.Id, XYZ(center.X + 0.25, center.Y + 0.25, 0)
        )
        tx.Commit()
        return sheet, view3d, center
    except Exception:
        tx.RollBack()
        raise


def find_schedule_field_by_name(sd, field_name):
    for field_id in sd.GetFieldOrder():
        field = sd.GetField(field_id)
        if field.GetName() == field_name:
            return field
    raise Exception("Field not found: {}".format(field_name))


def find_schedule_by_name(name):
    schedules = list(FilteredElementCollector(doc).OfClass(ViewSchedule).ToElements())
    for schedule in schedules:
        if schedule.Name == name:
            return schedule
    all_names = sorted([s.Name for s in schedules])
    raise Exception(
        "Required schedule '{}' not found.\nAvailable schedules:\n- {}".format(
            name, "\n- ".join(all_names)
        )
    )


def safe_remove_filters(defn, field_ids):
    for idx in reversed(range(defn.GetFilterCount())):
        flt = defn.GetFilter(idx)
        if flt.FieldId in field_ids:
            defn.RemoveFilter(idx)


def safe_add_string_filter(defn, field_name, filter_type, value):
    field = find_schedule_field_by_name(defn, field_name)
    safe_remove_filters(defn, [field.FieldId])
    defn.AddFilter(ScheduleFilter(field.FieldId, filter_type, value))


def safe_add_has_value_filter(defn, field_name):
    field = find_schedule_field_by_name(defn, field_name)
    safe_remove_filters(defn, [field.FieldId])
    defn.AddFilter(ScheduleFilter(field.FieldId, ScheduleFilterType.HasValue))


def reset_sorts(defn):
    for idx in reversed(range(defn.GetSortGroupFieldCount())):
        defn.RemoveSortGroupField(idx)


def add_sort(defn, field_name, order=ScheduleSortOrder.Ascending, show_header=False):
    field = find_schedule_field_by_name(defn, field_name)
    sg = ScheduleSortGroupField(field.FieldId, order)
    sg.ShowHeader = show_header
    defn.AddSortGroupField(sg)


def duplicate_schedule(master_name, sheet_code):
    master = find_schedule_by_name(master_name)
    dup_id = master.Duplicate(ViewDuplicateOption.Duplicate)
    dup = doc.GetElement(dup_id)
    try:
        dup.Name = "{}{}{}".format(master_name, SCHEDULE_NAME_SEP, sheet_code)
    except ArgumentException:
        dup.Name = "{}{}{}_alt".format(master_name, SCHEDULE_NAME_SEP, sheet_code)
    return dup


def configure_fittings_schedule(dup, is_fundering):
    sd = dup.Definition
    safe_add_string_filter(sd, "Manufacturer", ScheduleFilterType.Equal, "Dyka")
    safe_add_string_filter(
        sd, "Description", ScheduleFilterType.NotEqual, "Dyka Assembly"
    )
    if is_fundering and FUND_PREFIX:
        safe_add_string_filter(sd, "Comments", ScheduleFilterType.Contains, FUND_PREFIX)
    reset_sorts(sd)
    add_sort(sd, "NLRS_C_positie_nummer")
    add_sort(sd, "Description", show_header=True)
    add_sort(sd, "NLRS_P_c01_diameter")
    add_sort(sd, "NLRS_C_code_fabrikant_product")
    dup.Definition.IsItemized = True if is_fundering else False


def configure_pipes_schedule(dup, is_fundering):
    sd = dup.Definition
    safe_add_string_filter(
        sd, "Segment Description", ScheduleFilterType.Contains, "U3"
    )
    safe_add_string_filter(sd, "Manufacturer", ScheduleFilterType.Equal, "Dyka")
    if is_fundering and FUND_PREFIX:
        safe_add_string_filter(sd, "Comments", ScheduleFilterType.Contains, FUND_PREFIX)
    reset_sorts(sd)
    add_sort(sd, "Segment Description", show_header=True)
    add_sort(sd, "Outside Diameter")
    add_sort(sd, "Artikelnummer")
    if is_fundering:
        add_sort(sd, "Comments")
        dup.Definition.IsItemized = True
    try:
        dup.Definition.ShowGrandTotal = True
        dup.Definition.ShowGrandTotalCount = True
    except Exception:
        pass


def configure_duct_schedule(dup, system_name):
    sd = dup.Definition
    safe_add_string_filter(sd, "System Name", ScheduleFilterType.Equal, system_name)
    reset_sorts(sd)
    add_sort(sd, "Section")


def configure_spaces_schedule(dup, comment_code):
    sd = dup.Definition
    safe_add_has_value_filter(sd, "Area")
    safe_add_string_filter(sd, "Comments", ScheduleFilterType.Equal, comment_code)
    reset_sorts(sd)
    dup.Definition.IsItemized = True
    try:
        dup.Definition.ShowGrandTotal = True
        dup.Definition.ShowGrandTotalTitle = False
        dup.Definition.ShowGrandTotalCount = True
    except Exception:
        pass


def duplicate_configure_and_place_schedules(sheet, sheet_code):
    tx = Transaction(doc, "Duplicate Configure Place Schedules")
    tx.Start()
    try:
        placements = []
        schedule_specs = [
            (
                "Dyka PVC Pipe Fittings",
                lambda dup: configure_fittings_schedule(dup, False),
            ),
            (
                "Dyka PVC Pipe Fittings fundering",
                lambda dup: configure_fittings_schedule(dup, True),
            ),
            ("Dyka PVC Pipes U3", lambda dup: configure_pipes_schedule(dup, False)),
            (
                "Dyka PVC Pipes U3 fundering",
                lambda dup: configure_pipes_schedule(dup, True),
            ),
            (
                "GC01 WTW Afzuiging",
                lambda dup: configure_duct_schedule(dup, "GC01 WTW Afzuiging"),
            ),
            (
                "GC01 WTW Toevoer",
                lambda dup: configure_duct_schedule(dup, "GC01 WTW Toevoer"),
            ),
            ("GC01 WTW Balans", lambda dup: configure_spaces_schedule(dup, "GC01")),
            ("GC04 WTW Balans", lambda dup: configure_spaces_schedule(dup, "GC04")),
        ]

        u_min = sheet.Outline.Min.U
        u_max = sheet.Outline.Max.U
        v_max = sheet.Outline.Max.V
        width = u_max - u_min
        height = sheet.Outline.Max.V - sheet.Outline.Min.V
        x = u_min + 0.05 * width
        y0 = v_max - 0.12 * height
        dy = 0.12 * height

        for idx, (master_name, cfg) in enumerate(schedule_specs):
            dup = duplicate_schedule(master_name, sheet_code)
            cfg(dup)
            placements.append(
                ScheduleSheetInstance.Create(
                    doc, sheet.Id, dup.Id, XYZ(x, y0 - (idx * dy), 0)
                )
            )
        tx.Commit()
        return placements
    except Exception:
        tx.RollBack()
        raise


def center_layout(sheet, center):
    tx = Transaction(doc, "Center Views and Schedules")
    tx.Start()
    try:
        for vp in FilteredElementCollector(doc, sheet.Id).OfClass(Viewport).ToElements():
            vp.SetBoxCenter(center)
        offset = 0.15
        schedules = [
            s
            for s in FilteredElementCollector(doc, sheet.Id)
            .OfClass(ScheduleSheetInstance)
            .ToElements()
            if not s.IsTitleblockRevisionSchedule
        ]
        for idx, sch in enumerate(schedules):
            sch.Point = XYZ(center.X, center.Y - (idx * offset), 0)
        tx.Commit()
    except Exception:
        tx.RollBack()
        raise


def main():
    log("sheet_generator: started")
    active_view = uidoc.ActiveView
    if active_view.ViewType != ViewType.FloorPlan:
        raise Exception("Active view must be a Floor Plan.")

    boundary = pick_boundary_detail_lines()
    if not boundary:
        warn("No boundary detail lines selected.")
        return

    polygon = get_region_polygon(boundary)
    boundary_ids = [e.Id.IntegerValue for e in boundary]
    gathered = gather_elements_in_region(active_view, polygon, boundary_ids)
    log("sheet_generator: gathered:", len(gathered))
    if not gathered:
        raise Exception("No elements found inside selected boundary.")

    elements_data = filter_relevant_elements(gathered, active_view)
    if not elements_data:
        raise Exception("No relevant elements found in selected region.")

    log("sheet_generator: opening editor")
    result = show_element_editor(elements_data, gathered, polygon, active_view)
    if result is None:
        return

    base_code = normalize_base_code(result["TextNote"])
    apply_auto_codes(result["Elements"], base_code)
    write_comments_codes(result)

    td = TaskDialog("Sheet Generator")
    td.MainInstruction = "Create sheet and schedules now?"
    td.MainContent = (
        "Yes = create sheet + duplicate schedules.\n"
        "No = only apply codes/tags/text note and stop."
    )
    td.CommonButtons = TaskDialogCommonButtons.Yes | TaskDialogCommonButtons.No
    if td.Show() == TaskDialogResult.No:
        TaskDialog.Show(
            "sheet_generator",
            "Codes applied. Sheet creation skipped by user choice.",
        )
        return

    region_min, region_max = get_region_bounding_box(boundary, polygon, active_view)

    tg = TransactionGroup(doc, "PLEGTVOS Sheet Generator")
    tg.Start()
    try:
        plan_view = create_cropped_plan_view(
            active_view, base_code, region_min, region_max
        )
        log("sheet_generator: creating sheet for", base_code)
        sheet, view3d, center = create_sheet_with_views(
            base_code, plan_view, region_min, region_max
        )
        duplicate_configure_and_place_schedules(sheet, base_code)
        center_layout(sheet, center)
        tg.Assimilate()
    except Exception:
        tg.RollBack()
        raise

    TaskDialog.Show(
        "sheet_generator",
        "Sheet generator completed.\nBase code: {}\nSheet: {}\nPlan: {}\n3D: {}".format(
            base_code, base_code, plan_view.Name, view3d.Name
        ),
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:
        tb = traceback.format_exc()
        print(tb)
        TaskDialog.Show(
            "sheet_generator",
            "sheet_generator failed:\n{}\n\n{}".format(str(ex), tb),
        )
