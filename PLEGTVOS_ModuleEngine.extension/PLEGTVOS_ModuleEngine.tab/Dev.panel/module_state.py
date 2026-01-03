# -*- coding: utf-8 -*-
"""
Persistent storage for region_scanner payloads.

Writes versioned JSON under:
 - <rvt_dir>\\_PLEGTVOS_ModuleEngine\\state\\ (when doc is saved)
 - %APPDATA%\\pyRevit\\PLEGTVOS_ModuleEngine\\state\\<doc.Title>\\ (fallback)

Creates both timestamped file and latest.json on each save.
"""

import os
import json
import getpass
from datetime import datetime

try:
    from Autodesk.Revit.DB import ModelPathUtils, WorksharingUtils
except Exception:
    ModelPathUtils = None
    WorksharingUtils = None

SCHEMA_VERSION = 1


def _utc_now_iso():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_central_path(doc):
    if ModelPathUtils and hasattr(doc, "GetWorksharingCentralModelPath"):
        try:
            mp = doc.GetWorksharingCentralModelPath()
            if mp:
                return ModelPathUtils.ConvertModelPathToUserVisiblePath(mp)
        except Exception:
            return None
    return None


def _base_state_dir(doc):
    # Preferred: alongside RVT
    try:
        if doc.PathName:
            rvt_dir = os.path.dirname(doc.PathName)
            if rvt_dir and os.path.isdir(rvt_dir):
                return os.path.join(rvt_dir, "_PLEGTVOS_ModuleEngine", "state")
    except Exception:
        pass

    # Fallback: AppData
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    return os.path.join(
        appdata,
        "pyRevit",
        "PLEGTVOS_ModuleEngine",
        "state",
        (doc.Title or "unsaved_doc"),
    )


def _ensure_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path)


def to_payload(doc, core_payload):
    """Wrap core payload with metadata and schema info."""
    central_guid = None
    try:
        if WorksharingUtils and hasattr(doc, "IsWorkshared") and doc.IsWorkshared:
            central_guid = str(WorksharingUtils.GetCentralGUID(doc))
    except Exception:
        central_guid = None

    return {
        "schema_version": SCHEMA_VERSION,
        "created_utc": _utc_now_iso(),
        "user": getpass.getuser(),
        "doc": {
            "title": doc.Title,
            "path": getattr(doc, "PathName", None),
            "central_path": _safe_central_path(doc),
            "central_guid": central_guid,
            "is_workshared": getattr(doc, "IsWorkshared", False),
        },
        "revit": {
            "build": getattr(doc.Application, "VersionBuild", None),
            "version_name": getattr(doc.Application, "VersionName", None),
        },
        "payload": core_payload,
    }


def _write_json(path, data):
    with open(path, "w") as fp:
        json.dump(data, fp, indent=2, sort_keys=True)


def save_payload(doc, payload, name=None):
    """Save payload, return full path of timestamped file."""
    state_dir = _base_state_dir(doc)
    _ensure_dir(state_dir)

    stamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    fname = name or "module_state_{}.json".format(stamp)
    full_path = os.path.join(state_dir, fname)

    _write_json(full_path, payload)
    _write_json(os.path.join(state_dir, "latest.json"), payload)
    return full_path


def list_payloads(doc):
    """List available payload files (full paths)."""
    state_dir = _base_state_dir(doc)
    if not os.path.isdir(state_dir):
        return []
    files = [
        os.path.join(state_dir, f)
        for f in os.listdir(state_dir)
        if f.lower().endswith(".json")
    ]
    return sorted(files)


def load_latest_payload(doc):
    """Load latest payload json; returns dict or None."""
    state_dir = _base_state_dir(doc)
    latest_path = os.path.join(state_dir, "latest.json")
    if not os.path.isfile(latest_path):
        return None
    with open(latest_path, "r") as fp:
        return json.load(fp)
