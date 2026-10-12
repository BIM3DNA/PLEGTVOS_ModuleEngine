# M1.1 GC01 read-only diagnostics: implementation and host acceptance

Date: 2026-10-11. Implementation baseline: `ba692cd913aab8eb9d5e77aa519696454fc75fed` plus the uncommitted M1.1 files. **First host attempt: FAILED_RUNTIME - UnicodeDecodeError. Retest NOT RUN; M1.1 not accepted.** Offline tests are not evidence of Revit behavior. No mirror, slope or extractor repair is included.

## Command and safety boundary

Button: `PLEGTVOS_ModuleEngine.extension/PLEGTVOS_ModuleEngine.tab/Dev.panel/GC01_Mirror_Diagnostics.pushbutton`.

- `script.py`: preselected-scope validation, report/export UI and concise output.
- `revit_reader.py`: document-wide read adapter; geometry, identity, MEP inventory, parameters, dependencies, connector references, slopes and issue ledger.
- `diagnostic_core.py`: pure rectangular-wireframe validation, conservative classification, rigid frame mapping, reflection, slope math and deterministic serialization.
- `report_store.py`: exclusive immutable report creation and diagnostic-only pointer publication.
- `bundle.yaml`: button title, tooltip and project-document context. Python metadata follows existing buttons; no explicit CPython override.

No existing button or module_state is imported. Existing helpers mix button execution, state probes, bounding-box axis assumptions or writing workflows, so they are not safe reusable entry points. Existing scripts and extractor behavior are unchanged. The new command contains no Revit transactions, regeneration, selection/view setters, element changes, connector writes, linked-document access or RVT save/open operations. Category collection includes pipes/flex pipes, ducts/flex ducts, fittings/accessories, equipment, plumbing fixtures, sprinklers, conduit/tray and their fittings, insulation and lining.

The default engine is IronPython. Installed Revit 2025 attachment currently points to IPY2712PR; configured extension roots include this repository. This is configuration evidence, not a live invocation. Reload pyRevit to discover the new button. Record the actual loaded path and engine from the report before accepting host results.

## JSON contract and storage

Schema: `plegtvos.gc01_mirror_diagnostic/1`; feature ID: `GC01_MIRROR_DIAGNOSTICS`; collector version: `1.1.0`.

The M1.0 envelope is retained: `schema`, `status`, `run`, `snapshot`, `content_sha256`. Additional envelope fields are `feature_id` and `safety`. Snapshot fields include document/coordinates/source/target/prediction/policy/coverage/elements/connectors/edges/systems/issues/predicted_risks, plus `pipes`, `summary` and `confirmed_defects`. Element references use document key plus UniqueId and decimal-string Revit 2025 64-bit IDs. Code provenance is a SHA-256 of the five implementation files and the loaded directory; `code_sha` stays null for uncommitted source. Revit version/build and actual Python engine are recorded in `run`.

`content_sha256` hashes canonical snapshot only, excluding timestamps and runtime provenance. Serialization uses sorted keys, fixed separators, ASCII-escaped JSON in UTF-8, LF, finite numbers and normalized negative zero. Implementation precision is 12 decimal places for all floats (the audit suggested 9 for feet and 12 for ratios); raw values are used for calculations. Record arrays, dependencies, references and directional edge observations are sorted. The numeric precision is serialization policy, not engineering tolerance. Duplicate connector keys remain in the ledger with an ambiguity issue; they are not silently dropped.

A valid selection collects observations before asking whether to export. Cancel/close at either export dialog writes nothing. Default root is `<saved-local-RVT-folder>/_PLEGTVOS_ModuleEngine/state`, or `%APPDATA%/pyRevit/PLEGTVOS_ModuleEngine/state` for unsaved/cloud/nonlocal paths. The user may choose an external root instead. No central-folder probing or project state reading occurs.

Within the chosen root, only `gc01_mirror_diagnostics/<document-key>/` is used. Each report is `gc01_<UTC timestamp>_<unique suffix>.json`, created exclusively with no overwrite. `latest-report.json` is a diagnostic-only relative pointer with report filename and snapshot hash, published through an atomic filesystem replace. It never updates extractor `latest.json` or acceptance records. This dedicated latest pointer is explicitly authorized by the M1.1 brief, superseding M1.0's proposal to avoid any latest-state update. A pointer failure is reported while preserving the immutable report; a failed report write may leave a partial file, which must not be accepted as evidence. No silent fallback on an unwritable selected root.

## Interpretation and limitations

- Exactly one preselected scope box is required. No selection prompts or selection setters are used. Missing, wrong or multiple selections exit before report collection/export. Family documents are rejected.
- Scope geometry must validate as a complete orthogonal eight-vertex/twelve-edge rectangular wireframe. Geometry-derived axes are deterministic geometric axes, **not approved L/R design axes**. The element bounding-box transform is recorded separately and never treated as the mirror frame. Unsupported geometry yields UNKNOWN membership, with all supported MEP candidates retained.
- INSIDE means the complete element bounding box is inside the validated box. OUTSIDE means a separating scope-axis interval proves the bounding box outside. CROSSING requires a bounded straight location curve to intersect and extend outside. Other bbox intersections stay UNKNOWN. This is conservative, not exact solid intersection; family flip controls may enlarge boxes.
- All supported-category instances are inventoried across the document, independent of view visibility. Connector/slope scans include INSIDE, CROSSING and UNKNOWN; proven OUTSIDE rows explicitly say connectors were not scanned. Unsupported model categories have a count/name/ID ledger, not invented per-element measurements. Large projects can take time; there is no progress-cancellation UI during synchronous collection.
- Host, group, assembly, shared-subcomponent and direct dependent references are recorded without modifying or opening anything. Full transitive dependency closure and non-shared nested family content remain unresolved. Coverage is deliberately `complete: false`; this release cannot certify a complete mirrored module. External connector references carry owner identity even when that owner is outside the supported category set.
- Connector fingerprints use geometry/type/domain if API IDs are inaccessible; no enumeration-index identity. AllRefs is not assumed physical: physical connector types require IsConnectedTo evidence, with reciprocal reads retained. Physical edges are deduplicated while retaining directional observations. Logical and unknown edges stay distinct.
- Open ports have `UNKNOWN_ENGINEERING_INTENT`, never an automatic defect. Near-face status uses a documented diagnostic distance of 0.0001 ft, not an approved engineering tolerance; it cannot prove an intentional boundary. Physical boundary edges and geometric near-face counts are reported separately. `confirmed_defects` is empty; observed open ports create review risks only.
- Pipe slope sign is `(Z1-Z0)/horizontal_run`, ordered by Revit curve endpoints 0 to 1. It is not flow direction. Actual curve length is separate from endpoint chord length. Vertical/degenerate/unsupported curves have null ratios and explicit status. All hydraulic flow and slope compliance remain UNKNOWN until approved rules exist.
- No approved mirror plane, target frame or anchor policy was supplied. Prediction is `MIRROR_FRAME_UNCONFIRMED`; no production plane or predicted target points/connectors are invented. Pure frame-map and reflection mathematics are implemented and tested but not used to manufacture target evidence. There is no target comparison in this one-scope command.
- Document key includes available path, ProjectInformation UID and central/cloud GUIDs. Unsaved or copied documents are not durably qualified for comparison; `durable_comparison` remains UNRESOLVED. Links are recorded as instance transforms only. No linked documents are opened/read.
- Guarded read failures retain field, subject, stable reason and exception type, with null values. NOT_APPLICABLE parameter data is distinct from failed reads. Some nullable relationships are conservatively marked unavailable. A fatal collector failure prints an error and exports nothing; it never publishes an empty success report.
- Safety flags describe this command's paths; before/after IsModified, active-view ID and selection are observed separately. Equal values do not prove all model invariance or Undo behavior. Those require the manual host procedure below. Every report is `OBSERVATION_ONLY_UNRESOLVED`, never mirror PASS.

## Exact Revit 2025 manual procedure

Use an approved disposable GC01 fixture. Do not run the existing mirror/slope/extractor buttons as part of this test. Do not create or edit production geometry to manufacture test cases. Obtain prepared fixtures for the edge cases below.

1. Record fixture path/identity, source revision, Revit 2025 build, pyRevit build, tester, date and evidence folder. Record current HEAD and SHA-256 of the five implementation files; retain the uncommitted diff used for the test.
2. Reload pyRevit, locate **GC01 Mirror Diagnostics** under this repository's Dev panel, and verify the loaded extension is the repository path above. Open the approved fixture through normal user workflow, not through this command.
3. Before invoking, record model element counts, source IDs/UniqueIds, selection IDs, active view, document dirty state, pins/hosts and visible Undo stack. Record representative connector topology and pipe endpoint/elevation/slope values using approved inspection tools. Capture screenshots/evidence paths.
4. Run once with nothing selected, with a nonscope element selected, and with two scope boxes selected. Each must exit without an export prompt, report files or model/view/selection/Undo changes.
5. Preselect the single GC01 scope box. Run the button and inspect the concise banner and counts. Close the export choice dialog. Repeat using Choose external folder and cancel that picker. Both must leave report folders unchanged.
6. Run again and choose an approved external evidence root. Confirm the immutable JSON and diagnostic-only latest pointer exist. Confirm the pointer targets that report and its hash matches the snapshot; confirm existing extractor records are unchanged. Compare `run.loaded_path`, `python_engine`, `revit_version`, `revit_build` and `source_sha256` with the recorded installation.
7. Inspect scope wireframe/bbox, family/type and parameter data, supported-category ledger, UNKNOWN entries, connector physical/logical edges and API errors. Compare representative inside/outside/crossing/rotated-scope cases against the prepared model. Unsupported geometry must stay explicit, not imply an approved axis.
8. Check prepared sloped, reversed-endpoint, horizontal, vertical and curved/flex pipes. Compare reported endpoints and curve length to model measurements. Confirm vertical ratios are null, endpoint slope sign is distinct from flow, and compliance remains UNKNOWN.
9. Check prepared intentional boundary ports, an isolated open port, logical references, fittings, hosted/grouped/assembled/nested content and an outside connected neighbor. Confirm identities/references, unresolved coverage and open-port review language; do not adjudicate a defect from open state alone.
10. Without changing document state, selection or view, run and export again to the same root. Confirm different immutable filenames but identical `content_sha256` and canonical snapshots. Confirm previous report bytes remain unchanged and only the diagnostic pointer advances.
11. Select an approved unwritable external location and attempt export. Expect explicit failure with no model changes and no claimed successful path. A pointer-publication failure must preserve the report and print its warning; do not alter production permissions to induce a failure.
12. Repeat observations from step 3. Confirm identical model counts, elements/geometry/parameters, connectors, pins/hosts, links/coordinates, active view and selection, with no new Undo item and unchanged dirty state. Record actual results and artifacts per case. Do not mark PASS solely from `safety.observed_fields_unchanged`.
13. Repeat identity tests in separately prepared unsaved, same-title/copied and workshared/cloud fixtures when available. Missing fixtures remain NOT RUN. Close test models according to the approved fixture procedure; no model save is required by the diagnostic.

## Host acceptance ledger

H00 records the user-reported initial failure. Remaining cases are NOT RUN; no successful host acceptance is inferred.

| Case | Procedure / expected result | Status | Actual result | Evidence |
| --- | --- | --- | --- | --- |
| H00 First collection | Original Motor A; GC01; expected ID 1405931 | FAILED_RUNTIME - UnicodeDecodeError | Collection stopped; no JSON | User-supplied console excerpt; traceback unavailable |
| H01 Loaded code/engine | Steps 1-2, 6: correct repository, source hash, Revit 2025 and IronPython | NOT RUN | | |
| H02 Invalid selection | Step 4: zero, wrong, multiple; no report or model effect | NOT RUN | | |
| H03 Cancellation | Step 5: both dialogs; no artifact or model effect | NOT RUN | | |
| H04 Scope and inventory | Step 7: rotated/boundary/missing geometry; conservative classification | NOT RUN | | |
| H05 Connectors and boundaries | Steps 7, 9: physical/logical, outside owners, open intent unknown | NOT RUN | | |
| H06 Slopes | Step 8: endpoints/length/sign, vertical/degenerate/curved, no hydraulic assumptions | NOT RUN | | |
| H07 Dependency limits/errors | Step 9: host/group/assembly/nested, unavailable fields retained | NOT RUN | | |
| H08 Mirror gate | Step 7: no approved plane, no invented predictions; MIRROR_FRAME_UNCONFIRMED | NOT RUN | | |
| H09 Determinism/storage | Steps 6, 10: immutable reports, equal snapshot hashes, isolated pointer | NOT RUN | | |
| H10 Export failure | Step 11: explicit failure, no model effects or false success | NOT RUN | | |
| H11 No-write invariance | Steps 3, 12: geometry/parameters/connectors/view/selection/Undo/dirty state unchanged | NOT RUN | | |
| H12 Identity variants | Step 13: unsaved/same-title/copied/workshared/cloud uncertainty explicit | NOT RUN | | |

## Offline validation

Run `python -B -m unittest discover -s tests -v` from the repository. Tests cover wireframe validation/rotation, conservative classification, composed frame-map/reflection, slope/vertical/missing data, connector descriptor identity, invalid selection, deterministic serialization, immutable storage/pointer failures and an AST scan for prohibited mutation APIs. Static scanning is a guard, not proof of host behavior.

IronPython 2.7.12 syntax compilation is performed without importing any Revit button or executing the collector. CPython runs pure logic/storage tests only. Live Revit cases above remain NOT RUN. Existing executable extension files and both extractor scripts must compare unchanged against the M1.0 baseline. No commit or push is authorized by this implementation request.

Validation result (2026-10-11): all 19 offline tests passed under CPython 3.14. IronPython 2.7.12 compiled the five implementation files and test file without execution. The static mutation scan passed. Standalone IronPython test execution was not performed because that bare engine lacks its standard-library search paths; syntax compilation does not establish pyRevit runtime success. All 12 host cases remain NOT RUN.

## M1.1a runtime investigation and retest

First host attempt: **FAILED_RUNTIME — UnicodeDecodeError**, reported by the user in Revit 2025 / pyRevit / IronPython 2.7.12, Original Motor A RVT, selected GC01 (expected ID 1405931). Button discovery after reload succeeded. Collection stopped before any JSON. The actual throw site is unknown; JSON serialization is not established as the cause.

The outer handler caught Exception but discarded message and traceback. Reader.read also retained only exception type/reason. Instrumentation now emits every Python traceback frame (file, line, function), safely obtainable exception message, stage, element ID and field. No source lines, locals or unrelated model data are dumped. Nested read fields are restored; aggregate phases clear element IDs rather than presenting stale context. Caught Unicode read failures are preserved outside the snapshot and printed on fatal failure or after collection completes.

New failure_diagnostics.py provides protected ASCII console rendering. Valid Unicode is shown as reversible escapes. Actual bytes decode strictly as UTF-8; invalid bytes are labelled INVALID_UTF8_BYTES and shown as escaped byte representations. Broken exception string conversion falls back safely. These are failure-display rules only: original model Unicode, JSON schema and file paths are not normalized or replaced. Source fingerprint now includes this fifth helper.

### Unicode boundary audit

| Boundary | Finding |
| --- | --- |
| Document title/path; scope/category/family/type/system names | Revit strings retained directly; no broad str conversion added. Actual type at host failure unknown. |
| Parameters | AsString data unchanged; built-in identifiers are ASCII, storage enum uses str. Instrumentation retains the parameter field. |
| Connector metadata | Numeric IDs/enums use str; geometry remains numeric. Calculations unchanged. |
| JSON | ensure_ascii=True round-trips valid Unicode, then storage encodes UTF-8. Invalid byte data is not silently rewritten. Original failure may occur elsewhere. |
| Report paths | ASCII generated filenames join the Unicode directory. Offline accented-directory export passes; host retest pending. |
| Console | Failure rendering is now protected. Normal success output is unchanged because observed failure precedes it. |
| IronPython | Installed 2.7.12 aliases str and unicode; b-prefixed bytes are distinct. Synthetic invalid bytes render correctly with this helper. This does not reproduce the model failure. |

### Exact next Revit 2025 test

1. Reload pyRevit. Use the same Original Motor A fixture under the read-only test authorization. Record actual loaded button path, source files and Revit/pyRevit/engine builds.
2. Preselect only GC01; verify ElementId 1405931. Record selection, active view, dirty state and Undo stack. Do not invoke mirror/slope/extractor or other workstreams.
3. Run GC01 Mirror Diagnostics once. If it fails, retain the entire console from the banner through exception message, all traceback frames, stage/element/field and any earlier caught Unicode failures. Preserve escaped sequences literally. No JSON is expected on fatal collection failure.
4. If collection completes, preserve any caught Unicode-read output and export to an approved external evidence root. Retain JSON/path/hash and verify document, family and parameter Unicode against the source. Completion alone is not M1.1 acceptance.
5. Verify unchanged selection, view, dirty state, Undo and model observations. Record actual results and return the complete console evidence for the next targeted correction. Unperformed acceptance cases remain NOT RUN.

Validation: 25 CPython tests passed (19 existing plus six Unicode regressions), including accented BCS/Dutch text, model fields, Unicode directories, deterministic JSON, invalid bytes and protected traceback rendering. Static prohibited-API scan includes the helper. Five command modules and two test files compile with IronPython 2.7.12. A synthetic UnicodeDecodeError rendering probe also passed under that engine; the original Revit failure was not reproduced. Full IronPython collector runtime remains unverified. No existing extractor/production script changes, commit, push or M1.2 work.

Disposition: M1_1A_INSTRUMENTED. Stop after instrumentation because the failing boundary is not established; no speculative conversion changes were applied.
