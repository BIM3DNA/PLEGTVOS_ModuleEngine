# -*- coding: utf-8 -*-
__title__ = "region_editor"
__doc__ = """Review region elements, input base code, and stage numbering/tag actions.
Reads collected_latest.json and view_duplicator_latest.json; no model writes.
Saves review payload for apply_changes step."""

from Autodesk.Revit.DB import (
    BuiltInCategory,
    ElementId,
    FilteredElementCollector,
)
from Autodesk.Revit.UI import TaskDialog

import os
import sys
import json
import re
from datetime import datetime
from System.Collections.Generic import List
import System
import io
import clr
from System import Array

clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")
from System.Windows.Forms import (
    Form,
    DataGridView,
    DataGridViewColumn,
    DataGridViewTextBoxColumn,
    DataGridViewComboBoxColumn,
    DataGridViewAutoSizeColumnsMode,
    DataGridViewSelectionMode,
    DockStyle,
    TextBox,
    Button,
    DialogResult,
    MessageBox,
)
from System.Drawing import Point, Size, Color

# ensure local imports
_here = os.path.dirname(__file__)
_parent = os.path.dirname(_here)
for _p in (_here, _parent):
    if _p not in sys.path:
        sys.path.append(_p)

import module_state

uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document


def _to_unicode(s):
    """Normalize IronPython 2.7 str (bytes) to unicode safely."""
    try:
        unicode_type = unicode
    except NameError:
        unicode_type = str
    if s is None:
        return ""
    if isinstance(s, unicode_type):
        return s
    if isinstance(s, str):
        try:
            return s.decode("utf-8")
        except Exception:
            try:
                return s.decode("cp1252")
            except Exception:
                return s.decode("utf-8", "replace")
    return s


def normalize_for_json(obj):
    try:
        unicode_type = unicode
    except NameError:
        unicode_type = str
    if isinstance(obj, dict):
        return {normalize_for_json(k): normalize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [normalize_for_json(x) for x in obj]
    if isinstance(obj, str) or isinstance(obj, unicode_type):
        return _to_unicode(obj)
    return obj


def dump_json_utf8(path, data):
    safe = normalize_for_json(data)
    with io.open(path, "w", encoding="utf-8") as fp:
        json.dump(safe, fp, indent=2, ensure_ascii=False)


def warn(msg):
    TaskDialog.Show("region_editor", msg)


def load_json(path):
    with open(path, "r") as fp:
        return json.load(fp)


def find_state_file(name):
    # look in candidate dirs
    for d in module_state._candidate_dirs(doc):
        p = os.path.join(d, name)
        if os.path.isfile(p):
            return p
    return None


def ensure_payloads():
    latest = module_state.load_latest_payload(doc)
    if not latest:
        warn("Missing latest.json. Run region_scanner first.")
        sys.exit()
    collected_path = find_state_file("collected_latest.json")
    if not collected_path:
        warn("Missing collected_latest.json. Run element_collector first.")
        sys.exit()
    collected = load_json(collected_path)
    viewdup_path = find_state_file("view_duplicator_latest.json")
    viewdup = load_json(viewdup_path) if viewdup_path else None
    print("region_editor: collected payload -> {}".format(collected_path))
    if viewdup_path:
        print("region_editor: view_duplicator payload -> {}".format(viewdup_path))
    else:
        print(
            "region_editor: no view_duplicator payload found (using source/active view)"
        )
    return latest, collected, viewdup, collected_path, viewdup_path


def normalize_category(cat):
    if not cat:
        return "<None>"
    return (cat.Name or "").strip().title()


def get_comments(elem):
    p = elem.LookupParameter("Comments")
    if p and not p.IsReadOnly:
        return p.AsString() or ""
    return ""


def calc_center(elem, view):
    try:
        bb = elem.get_BoundingBox(view)
        if not bb:
            return None
        return ((bb.Min.X + bb.Max.X) * 0.5, (bb.Min.Y + bb.Max.Y) * 0.5)
    except Exception:
        return None


def auto_number(elements, base_code):
    # elements: list of dict; mutate NewCode for pipes/flex pipes and tags; fittings = base
    # numbering scheme: base_code + "." + each digit of the index separated by dots (e.g. idx=10 -> ".1.0")
    pipes = []
    # normalize base (strip leading "prefab ")
    base_num = re.search(r"([\d\.]+)", base_code)
    base_val = base_num.group(1) if base_num else base_code

    for ed in elements:
        if ed["Category"] in ("Pipes", "Flex Pipes"):
            ctr = ed.get("_center")
            pipes.append((ctr[0] if ctr else 0, ctr[1] if ctr else 0, ed))
        elif ed["Category"] == "Pipe Fittings":
            ed["NewCode"] = base_val
        else:
            # reset others to base as well
            ed["NewCode"] = base_val
    pipes.sort(key=lambda x: (x[0], x[1]))
    for idx, (_, _, ed) in enumerate(pipes, 1):
        idx_str = ".".join(list(str(idx)))
        ed["NewCode"] = "{}.{}".format(base_val, idx_str)
    # mirror tags to pipe order
    tag_idx = 1
    for _, _, ed in pipes:
        for other in elements:
            if other["Category"] == "Pipe Tags":
                # align tag index with pipe index
                idx_str = ".".join(list(str(tag_idx)))
                other["NewCode"] = "{}.{}".format(base_val, idx_str)
        tag_idx += 1


def fmt_len_mm(param):
    if not param:
        return ""
    try:
        val = param.AsDouble()
        if val is None:
            return ""
        mm = val * 304.8
        return "{} mm".format(int(round(mm)))
    except Exception:
        try:
            return param.AsValueString() or ""
        except Exception:
            return ""


def fmt_diam_mm(elem):
    for pname in ("Outside Diameter", "Diameter", "Nominal Diameter"):
        p = elem.LookupParameter(pname)
        if p:
            s = fmt_len_mm(p)
            if s:
                return s
    return ""


class ReviewForm(Form):
    def __init__(self, rows, default_base=""):
        self.Text = "Region Editor"
        self.Width = 1000
        self.Height = 600
        self.MinimumSize = Size(800, 400)
        self.Padding = System.Windows.Forms.Padding(10)

        self.grid = DataGridView()
        self.grid.Dock = DockStyle.Fill
        self.grid.AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill
        self.grid.SelectionMode = DataGridViewSelectionMode.FullRowSelect
        self.grid.AllowUserToAddRows = False
        self.grid.MultiSelect = True
        self.Controls.Add(self.grid)

        # Footer panel for controls
        footer = System.Windows.Forms.Panel()
        footer.Height = 42
        footer.Dock = DockStyle.Bottom
        footer.Padding = System.Windows.Forms.Padding(0, 4, 0, 0)
        self.Controls.Add(footer)

        self.baseBox = TextBox()
        self.baseBox.Width = 200
        self.baseBox.Text = default_base or "prefab 0.0.0"
        self.baseBox.Location = Point(0, 8)
        footer.Controls.Add(self.baseBox)

        self.btnPlaceText = Button()
        self.btnPlaceText.Text = "Place Text Note"
        self.btnPlaceText.Width = 120
        self.btnPlaceText.Location = Point(self.baseBox.Right + 10, 6)
        self.btnPlaceText.Click += self.on_place_text
        footer.Controls.Add(self.btnPlaceText)

        self.btnTags = Button()
        self.btnTags.Text = "Add/Remove Tags"
        self.btnTags.Width = 140
        self.btnTags.Location = Point(self.btnPlaceText.Right + 10, 6)
        self.btnTags.Click += self.on_tags
        footer.Controls.Add(self.btnTags)

        self.autoButton = Button()
        self.autoButton.Text = "Auto-Fill Tag Codes"
        self.autoButton.Width = 150
        self.autoButton.Location = Point(self.btnTags.Right + 10, 6)
        self.autoButton.Click += self.on_auto
        footer.Controls.Add(self.autoButton)

        self.okButton = Button()
        self.okButton.Text = "OK"
        self.okButton.Width = 70
        self.okButton.Anchor = (
            System.Windows.Forms.AnchorStyles.Top
            | System.Windows.Forms.AnchorStyles.Right
        )
        self.okButton.Location = Point(footer.Width - 160, 6)
        self.okButton.Click += self.on_ok
        self.okButton.DialogResult = DialogResult.OK
        footer.Controls.Add(self.okButton)

        self.cancelButton = Button()
        self.cancelButton.Text = "Cancel"
        self.cancelButton.Width = 70
        self.cancelButton.Anchor = (
            System.Windows.Forms.AnchorStyles.Top
            | System.Windows.Forms.AnchorStyles.Right
        )
        self.cancelButton.Location = Point(footer.Width - 80, 6)
        self.cancelButton.DialogResult = DialogResult.Cancel
        footer.Controls.Add(self.cancelButton)

        def reposition(sender, evt):
            w = footer.Width
            self.cancelButton.Location = Point(w - self.cancelButton.Width, 6)
            self.okButton.Location = Point(
                self.cancelButton.Left - self.okButton.Width - 10, 6
            )

        footer.Resize += reposition
        reposition(None, None)
        self.AcceptButton = self.okButton
        self.CancelButton = self.cancelButton

        cols = []

        def add_col(name, header, readonly=True):
            col = DataGridViewTextBoxColumn()
            col.Name = name
            col.HeaderText = header
            col.ReadOnly = readonly
            cols.append(col)
            return col

        add_col("Id", "Id")
        add_col("Category", "Category")
        add_col("Name", "Name")
        add_col("DefaultCode", "Default Code")
        add_col("NewCode", "New Code", readonly=False)
        add_col("Outside", "Outside")
        add_col("Length", "Length")
        add_col("Size", "Size")
        add_col("TagAction", "Tag Action", readonly=False)
        self.grid.Columns.AddRange(Array[DataGridViewColumn](cols))

        for r in rows:
            idx = self.grid.Rows.Add()
            row = self.grid.Rows[idx]
            row.Cells["Id"].Value = r["Id"]
            row.Cells["Category"].Value = r["Category"]
            row.Cells["Name"].Value = r["Name"]
            row.Cells["DefaultCode"].Value = r["DefaultCode"]
            row.Cells["NewCode"].Value = r["NewCode"]
            row.Cells["Outside"].Value = r.get("Outside", "")
            row.Cells["Length"].Value = r.get("Length", "")
            row.Cells["Size"].Value = r.get("Size", "")
            row.Cells["TagAction"].Value = r.get("TagAction", "")

        self.rows = rows

    def on_auto(self, sender, event):
        base = self.baseBox.Text.strip()
        if not base:
            MessageBox.Show("Enter a base code first.")
            return
        auto_number(self.rows, base)
        # refresh grid values (all rows)
        for i, r in enumerate(self.rows):
            self.grid.Rows[i].Cells["NewCode"].Value = r["NewCode"]

    def on_ok(self, sender, event):
        base = self.baseBox.Text.strip()
        if not base:
            MessageBox.Show("Enter a base code.")
            return
        # push edits back
        for i, r in enumerate(self.rows):
            r["NewCode"] = self.grid.Rows[i].Cells["NewCode"].Value
            r["TagAction"] = self.grid.Rows[i].Cells["TagAction"].Value
        self.DialogResult = DialogResult.OK
        self.Close()

    def on_place_text(self, sender, event):
        MessageBox.Show("Text note placement will be handled in apply step.", "Info")

    def on_tags(self, sender, event):
        MessageBox.Show("Tag add/remove will be handled in apply step.", "Info")


def main():
    latest, collected, viewdup, collected_path, viewdup_path = ensure_payloads()
    # Resolve ids from collected payload
    ids = []
    try:
        ids = (
            collected.get("source_state", {})
            .get("payload", {})
            .get("elements", {})
            .get("ids", [])
        )
    except Exception:
        ids = []
    if not ids:
        ids = collected.get("elements", {}).get("valid_ids", []) or collected.get(
            "elements", {}
        ).get("ids", [])
    if not ids:
        warn("No element ids in collected payload.")
        sys.exit()

    target_view_id = None
    if viewdup and viewdup.get("new_view", {}).get("id"):
        target_view_id = viewdup["new_view"]["id"]
    elif latest.get("payload", {}).get("view", {}).get("id"):
        target_view_id = latest["payload"]["view"]["id"]
    target_view = (
        doc.GetElement(ElementId(int(target_view_id)))
        if target_view_id
        else uidoc.ActiveView
    )
    if not target_view or not target_view.IsValidObject:
        warn(
            "Target view from payload is missing in this document.\n"
            "Re-run view_duplicator, then retry region_editor."
        )
        sys.exit()

    rows = []
    for i in ids:
        eid = ElementId(int(i))
        elem = doc.GetElement(eid)
        if not elem or not elem.IsValidObject:
            continue
        cat_name = normalize_category(elem.Category)
        name = elem.Name if hasattr(elem, "Name") else ""
        default = get_comments(elem)
        center = calc_center(elem, target_view)
        outside = fmt_diam_mm(elem)
        length_val = fmt_len_mm(elem.LookupParameter("Length"))
        size_val = ""
        tag_action = ""
        if cat_name in ("Pipes", "Flex Pipes"):
            # basic default: if there is a tag in view, keep; else add
            try:
                tag_cat = (
                    BuiltInCategory.OST_PipeTags
                    if cat_name == "Pipes"
                    else BuiltInCategory.OST_FlexPipeTags
                )
                has_tag = any(
                    isinstance(t, object)
                    for t in FilteredElementCollector(doc, target_view.Id)
                    .OfCategory(tag_cat)
                    .WhereElementIsNotElementType()
                    if any(
                        (tid.IntegerValue == eid.IntegerValue)
                        for tid in (
                            t.GetTaggedElementIds()
                            if hasattr(t, "GetTaggedElementIds")
                            else [t.TaggedElementId]
                        )
                    )
                )
                tag_action = "keep" if has_tag else "add"
            except Exception:
                tag_action = "add"
        elif cat_name in ("Pipe Tags", "Flex Pipe Tags"):
            tag_action = "keep"
        elif cat_name == "Pipe Fittings":
            tag_action = "add"

        rows.append(
            {
                "Id": eid.IntegerValue,
                "Category": cat_name,
                "Name": name,
                "DefaultCode": default,
                "NewCode": default,
                "Outside": outside,
                "Length": length_val,
                "Size": size_val,
                "TagAction": tag_action,
                "_center": center,
            }
        )

    # guess base code from view name or first default
    guess = ""
    if target_view:
        guess = target_view.Name
    if rows and rows[0]["DefaultCode"]:
        guess = rows[0]["DefaultCode"]

    form = ReviewForm(rows, default_base=guess)
    if form.ShowDialog() != DialogResult.OK:
        sys.exit()

    # strip helper fields
    for r in rows:
        if "_center" in r:
            del r["_center"]

    review_payload = {
        "created_utc": datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ"),
        "doc": {"title": doc.Title, "path": getattr(doc, "PathName", None)},
        "source_state_path": collected_path,
        "view": {
            "id": target_view.Id.IntegerValue if target_view else None,
            "name": target_view.Name if target_view else "",
        },
        "base_code": form.baseBox.Text.strip(),
        "elements": rows,
    }

    state_dir, _loc = module_state.get_state_dir(doc)
    if not os.path.isdir(state_dir):
        os.makedirs(state_dir)
    stamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    ts_path = os.path.join(state_dir, "review_{}.json".format(stamp))
    latest_path = os.path.join(state_dir, "review_latest.json")
    dump_json_utf8(ts_path, review_payload)
    dump_json_utf8(latest_path, review_payload)

    TaskDialog.Show(
        "region_editor",
        "Review saved.\nBase code: {}\nRows: {}\nSaved:\n{}".format(
            review_payload["base_code"], len(rows), latest_path
        ),
    )


if __name__ == "__main__":
    main()
