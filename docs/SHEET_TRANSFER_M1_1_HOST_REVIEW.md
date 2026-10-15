# Sheet Transfer M1.1 host evidence review

Date: 2026-10-14. M1 remains read-only and NOT ACCEPTED as a complete inventory.
M2/M3/M4 not started. GC01 M1.1h remains paused and unchanged.

## Observed run and preserved evidence

User reports existing PLEGTVOS Dev button visible, successful document/sheet selection,
Motor A source, unsaved Project1 destination, all 18 sheets selected, preview displayed
and no transfer. These are host observations of this path, not full acceptance.

The actual report was found recursively, not at the top-level process TEMP:
`C:\Users\Korisnik\AppData\Local\Temp\f73c57ab-33a9-4345-ae54-4e4672960f8a\plegtvos-sheet-preview-e1akd0`.
Both preview.json and preview.txt were inspected/preserved byte-for-byte at:
`C:\Users\Korisnik\AppData\Local\PLEGTVOS\SheetTransfer\evidence\m1-first-host-bw3g6yfc`.
The preservation.json file records original location and SHA-256 values:

- preview.json: `b990a69a0181508527ef9489e556d36e64d0c6ee4e8d226ea2d88a7bc61ab93c`
- preview.txt: `5e1f29eb1932786bd41065dbec3d2985ba90b96e0ce97b43e8e216be378bd7ea`

Original evidence was not rewritten. Archive is outside TEMP and both Git worktrees.

## Confirmed root cause and error accounting

| Field | Failing API expression | Exception | Frequency |
| --- | --- | --- | --- |
| name | Element.Name.GetValue(element), revit_adapter.py:66 | AttributeError: 'getset_descriptor' object has no attribute 'GetValue' | 523 |

All 523 records have this one traceback signature. They cover 457 distinct document-
qualified identity contexts: 473 source read attempts and 50 destination attempts.
Repeated reads of shared types/references explain why attempts are not unique objects.
No crop, scope, template, placement or serialization exceptions occur in this error list.
This does not prove uninspected fields or all API branches are valid.

Adapter.read catches the descriptor exception and returns None; Adapter.named stores
that as name, and the UI renders it literally. Thus None does NOT establish missing
sheet names. Actual sheet/type/view names were not obtained by the failed getter and
remain unknown until retest. This is a reader defect, not 523 absent Revit names.

Minimal correction: use the base descriptor `Element.Name.__get__(element)` and retain
errors with explicit name_status and API-call evidence. No fallback manufactures names
or hides failures. The installed Revit API XML defines Element.Name as a readable
property. An offline IronPython 2.7.12/.NET 8 probe loaded RevitAPI.dll, confirmed the
__get__ accessor, and successfully read an inherited CLR FileSystemInfo.Name using the
same descriptor pattern. The standalone probe also exposed GetValue, unlike the actual
host traceback; do not treat standalone descriptor binding as identical host behavior.
The host report remains authoritative for the observed failure. Actual Revit element
name reads after this correction require host retest.

## Inventory counts and unsupported classification

18 sheets; 41 viewports; 16 schedule instances; 16 title-block instances; 239 objects in
the former blanket unsupported bucket; zero recorded destination sheet-number conflicts.
All 18 sheets are non-placeholder; 801-1 and A101 have no collected title blocks.
Do not invent missing blocks or assume these sheets are invalid.

| Runtime type in unsupported bucket | Count | Interpretation |
| --- | --- | --- |
| TextNote | 88 | Annotation; API creation route exists, not implemented/accepted in M1 |
| DetailLine | 40 | Detail geometry; API creation route exists, not implemented/accepted in M1 |
| DetailEllipse | 5 | Detail geometry; API creation route exists, not implemented/accepted in M1 |
| ImageInstance | 4 | Image placement API exists; target type/view eligibility unresolved |
| SketchPlane | 18 | Supporting dependency requiring review; not automatically visible content |
| GraphicsStyle | 12 | Supporting dependency requiring review |
| ViewSchedule | 12 | Definition/internal ownership role not established; not a schedule placement count |
| Element | 60 | Generic runtime type is insufficient to determine role or transfer eligibility |

The collector uses OwnedByView(sheet.Id), so the bucket includes dependencies, not just
visible drawing objects. Nothing was removed from the inventory. The new status is
UNSUPPORTED_BY_M1_NOT_API_VERDICT, with annotation-candidate, dependency-review or
unclassified-review metadata. Transfer remains NOT_IMPLEMENTED_NOT_HOST_VERIFIED or
UNRESOLVED_NOT_IMPLEMENTED. The existing unsupported array is retained for compatibility.
137 objects have annotation runtime types with candidate creation APIs; this does NOT
mean these exact 137 objects have demonstrated transferable fidelity.

Installed `C:\Program Files\Autodesk\Revit 2025\RevitAPI.xml` was checked for
TextNote.Create (graphic view/type/options), ItemFactoryBase.NewDetailCurve (bound curve
in view plane), and ImageInstance.Create (eligible view and ImageType). These are future
API routes, not calls added to M1. Sheet/view compatibility, type/style mapping, image
resources and layout fidelity still require authorized future prototypes. Generic
CopyElements must not be assumed to handle all these objects or their dependencies.

Viewport types: 19 FloorPlan, 9 ThreeD, 5 Legend, 4 Section, 4 Detail placements. M1 does
not implement transfer of any type. Unsupported/intentionally uninspected states are
not added to the exception count: view-owned annotations, host references, revisions,
parameter parity, detailed crop geometry and annotation crops remain NOT_INSPECTED.

## Identity and conflict review

Source: open-session-doc-1, workshared Motor A with recorded local path.
Destination: open-session-doc-3, Project1, path empty, not workshared. Blank path is valid
for an unsaved preview target and is not a persistent identity. Session keys qualify
UniqueIds within this invocation only. The picker excludes the actual source document
using Document.Equals; no source ElementId is interpreted in the target.

Sheet-number checks compare actual SheetNumber strings with independently collected
target sheets; they do not depend on the broken Name reader. Zero recorded conflicts is
plausible for Project1, but is not a promise that future target contents remain unchanged.
Name-based view/template/scope conflicts and title-block candidate matches were degraded
by failed name reads; empty match lists are not evidence of no matching destination
objects. These must be rechecked after the fix. No persistent mapping/resume identity is
introduced and no central GUID is invented.

Source IsModified was true before and after; destination false before and after. These
flags and the user observation support the read-only path but do not independently prove
unchanged contents in an already modified source. Static no-write checks still apply.

## Report discovery and preservation

New reports go to `%LOCALAPPDATA%\PLEGTVOS\SheetTransfer\reports\preview-*`, a unique
new directory per run, not nested process TEMP. There is no silent TEMP fallback if the
persistent root is unavailable. The preview dialog shows the exact directory. JSON and
UTF-8 text retain the full inventory and tracebacks; summary/JSON include deterministic
error groups by field, API call, exception type/message and frequency. reader_version
M1.1 distinguishes new reports; schema /1 and existing fields remain compatible.

A failed name displays [UNKNOWN: name read failed], not None. Report size remains capped
at 8 MiB; collection limits, explicit native iterator, FAST-independent behavior and UI
selection remain unchanged. Existing reports are never overwritten. Filesystem write
failure may leave a partial unique directory, which is not claimed as complete. To
preserve evidence externally, copy the entire reported directory and compare hashes;
no automatic cloud upload or model save is performed.

## Validation and remaining limitations

35 tests pass in CPython against both isolated and integrated modules, and all 35 pass
under IronPython 2.7.12/.NET 8.0.22 against the integrated modules. Seven modules compile
in both runtimes. Tests cover descriptor reads/error retention, historical aggregation,
classification without claiming transfer, unique persistent reports/Unicode, and the
existing identity/conflict/iterator/static no-write suite. An additional CLR descriptor
probe is offline evidence only. Protected-file hashes and git diff --check pass.

Both button copies receive only four changed modules: revit_adapter.py, preview_models.py,
inventory.py, reporting.py. Existing test file expanded only in the development worktree.
State/milestone/host-review documentation updated in both worktrees; original GC01 and
all other executable commands remain byte-identical. No transaction, copying, model
write, selection/view change, save/sync, commit/push, reset/clean/stash, or M2/M3 work.

## Revit host retest

1. Keep the existing original-root extension registration. pyRevit Reload, then ALT-click
   Sheet Transfer and verify script path is under PLEGTVOS_ModuleEngine, NOT the isolated
   worktree. No second extension/tab and no GC01 execution.
2. Open approved Motor A/test source and an unsaved Project1 manually. Record versions,
   loaded path and before-state evidence. Choose source, destination and all 18 sheets.
3. Verify real sheet names against Revit, plus view, template, scope and title-block type
   names. Confirm the former 523 GetValue descriptor errors disappear. Any remaining
   errors must retain field/API/traceback and UNKNOWN status, never be suppressed.
4. Compare 41 viewport/16 schedule/16 title-block/239 other-object counts only if using
   the same unchanged source fixture. Counts are historical evidence, not hard-coded
   acceptance targets. Check annotation candidates versus dependencies/unclassified rows.
5. Read the exact new report directory shown in the dialog under LOCALAPPDATA. Preserve
   preview.json and preview.txt; inspect error_breakdown. Name candidates are not identity
   equivalence; inspect missing/ambiguous dependencies and the two no-title-block sheets.
6. Separately test a disposable destination with a matching sheet number and name to prove
   positive conflict detection; do not modify models through this command. Test cancellation
   and Unicode names. Confirm no new model/Undo changes; do not save or synchronize.
7. Supply the complete new report directory/path and observed comparisons. M1 inventory
   acceptance remains pending; this milestone does not authorize transfer.
