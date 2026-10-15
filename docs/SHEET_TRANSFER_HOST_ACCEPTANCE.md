# Current host acceptance: M1.1 retest pending

The first existing-toolbar preview is user-reported and its JSON independently reviewed.
Use [M1.1 evidence and exact retest procedure](SHEET_TRANSFER_M1_1_HOST_REVIEW.md).
Use the registered ORIGINAL checkout, not the isolated-worktree attachment proposed in
the historical M1 guide below. No new extension registration. M1 inventory NOT ACCEPTED.

# Sheet Transfer host acceptance

## M1 checkpoint - 2026-10-14

M0 completed. M1 read-only preview implemented; HOST_ACCEPTANCE_PENDING.
Destination writes disabled: no transfer/apply implementation exists. M2/M3/M4 pending.
GC01 remains paused at M1.1h in the original experimental worktree; FULL disabled.

Implementation worktree: `C:\00_WORKS\DEVELOPMENT\PLEGTVOS_ModuleEngine_sheet_transfer`.
Branch `feature/sheet-transfer-m1`, base HEAD `afd71060631faac89559aecf13c2dfeb582f87cd`.
Original checkout remains `C:\00_WORKS\DEVELOPMENT\PLEGTVOS_ModuleEngine` on main.
No commit, push, stash, reset, clean or original file modification. Three approved M0
files were copied explicitly; none of the uncommitted GC01 code/tests were copied.
Historical project-state sections describe the original checkout, not a resumed GC01
implementation in this worktree. The M0 audit remains byte-identical.

## Implemented scope

Button: `PLEGTVOS_ModuleEngine.extension/PLEGTVOS_ModuleEngine.tab/Dev.panel/Sheet_Transfer.pushbutton`.
Seven modules separate pure models, conflict analysis, native adapter, inventory,
pyRevit UI, reporting and entry point. The original OVT source was read completely;
its useful source type discovery, view/dependency association, names and viewport
center reads inform the preview. No original write helpers were imported or executed.

Explicit document choice proposes the active source first; labels include paths and
session keys to distinguish duplicate titles. Only valid open non-linked project
documents are offered; destination must differ and not be read-only. No automatic
open/close, source selection change, active-view change, save or sync. Sheets are
selected explicitly and deduplicated by document-scoped UniqueId.

Preview inspects sheet IDs/numbers/names/placeholder state, title-block family/type,
sheet-owned viewports and centers/rotation, placed view types, primary/template/scope
references, accessible crop flags/split-region count, placed schedule references and
positions, and unsupported sheet-owned content. Target sheets, views/templates,
title-block types and scopes are collected once per preview. Matching by names yields
candidates/conflicts only; no destination identity is inferred from a source ElementId.
Document keys qualify identities only within the current invocation; not resumable
cross-session identity or a future transfer authorization.

View-owned annotations and host references, revisions, shared-parameter parity,
annotation crop and detailed crop geometry remain explicitly NOT_INSPECTED/UNRESOLVED.
Legend/schedule transfer and non-plan transfer kinds are UNSUPPORTED. Plan kinds are
only future candidates, never accepted transfer capabilities. Missing title blocks,
reference-read exceptions and unresolved types are visible as UNKNOWN with context.
All model transfer remains NOT_IMPLEMENTED even with a clean preview.

Bounds: 100 selected sheets, 10,000 native iterator advances per API phase, 60 seconds
cooperative budget per phase, 8 MiB JSON limit. Sheet-picker waiting is excluded from
the subsequent inventory phase. Limits stop with PREVIEW INCOMPLETE, not partial success.
No recursive traversal, background API calls or whole-document per-element scans.
A blocking Revit API call cannot be forcibly interrupted by this budget.

Reports are created in a new `%TEMP%\plegtvos-sheet-preview-*` directory, containing
preview.json (ASCII-escaped Unicode JSON) and preview.txt (UTF-8 summary plus complete
inventory). No existing report/model is overwritten. Dialog summary is bounded to
6,000 characters and links the full report directory by displayed path. No apply button.
On collection failure, the dialog contains an ASCII-safe traceback; no complete report
is claimed. A file-write failure can leave a partial report directory, not model changes.

## Offline validation

27 focused tests pass under CPython and IronPython 2.7.12 on .NET 8.0.22. All seven
button modules compile in IronPython; CPython compile checks also performed. Coverage:
missing/same destination; zero/one/multiple sheets; duplicate identities/numbers;
destination conflicts; title-block candidates/missing data; view-type classification;
template/scope reference candidate analysis; unsupported objects; Unicode/nonfinite
serialization; deterministic ordering; bounded native-iterator fakes, exhaustion,
exceptions/disposal and cooperative stop; field-error evidence; AST no-write checks.

The first standalone IronPython harness launch lacked its standard-library search path;
adding the existing Python 2.7 stdlib path fixed the harness. No application change was
needed. Native Revit/pyRevit UI behavior is NOT established by these offline tests.
Static checks reject known write calls and attribute assignments outside adapter state;
manual review confirms no Revit transactions, mutation calls or selection/view changes.
Protected existing files compare unchanged to this worktree's base; original checkout
files compare byte-identically to the captured pre-M1 manifest.

## Exact Revit 2025 acceptance procedure

1. Use approved disposable source/target projects with representative title blocks,
   plans/dependents, scope boxes, templates, schedules, legends and sheet annotations.
   Open both manually. Record paths, identities, engine (.NET/IronPython versions),
   before counts and IsModified states; do not save/sync as part of this test.
2. Arrange an explicitly approved test pyRevit attachment to the dedicated worktree's
   extension. No configuration change was performed by M1. Avoid simultaneous duplicate
   PLEGTVOS extensions. Reload as needed and ALT-click Sheet Transfer to verify its exact
   script path is under PLEGTVOS_ModuleEngine_sheet_transfer, not the original checkout
   or BIM3DNA production toolbar. Do not run GC01 from this older isolated baseline.
3. Run Sheet Transfer. Confirm banner: READ-ONLY PREVIEW ? NO ELEMENTS WILL BE TRANSFERRED.
   Choose source explicitly (active is proposed), then another destination, then sheets.
   Check duplicate document titles remain distinguishable. Cancel each picker on separate
   runs; confirm no model changes or transaction/Undo items.
4. Select one sheet, then multiple sheets sharing dependencies. Compare preview.json/text
   to Revit: sheet UniqueIds, numbers/names, title-block family/type, every viewport/view,
   placement, template/scope/primary references, crop flags, schedules and unsupported
   sheet-owned objects. Confirm deduplication and deterministic repeat output excluding
   invocation-local document keys/before states when contexts differ.
5. Use fixtures with a matching destination sheet number/view name and title-block names;
   confirm conflict/candidate reports, never automatic reuse or renaming. Test missing
   blocks/templates/scopes, legends, annotations and inaccessible properties: UNKNOWN,
   UNSUPPORTED or NOT_INSPECTED must remain explicit. No incomplete preview may say ready
   to transfer. Compare unsupported counts against actual fixture sheet-owned contents.
6. Test one open project (no destination), zero source sheets, read-only destination,
   Unicode names and bounded oversized selection/collector. Limit/error paths must state
   incomplete and produce no model changes. A host hang or exception is a failed test;
   record the stage/traceback and stop, do not infer offline compatibility.
7. Open the reported preview.json and preview.txt; verify complete inventory, error
   contexts, source/destination session identity and transfer_enabled=false. Confirm both
   documents' element counts, modified states and Undo histories unchanged. IsModified
   alone is not proof: compare actual fixture contents. Do not save/sync to validate.
8. Record code hashes, loaded path, fixture IDs, expected/actual results and evidence paths
   here. M1 remains pending until all required cases pass. No M2 apply operation exists.

## Host result ledger

No Revit host execution performed in this milestone. Result: NOT_RUN / PENDING.
Remaining risks: actual Revit collector ownership/crop applicability, pyRevit picker and
Unicode UI behavior, template/type name ambiguity, large-model API responsiveness,
fixture completeness and extension attachment. Offline checks are not host acceptance.
