# M0 repository and reference audit

Date: 2026-10-11. Scope: source inspection and documentation only. No command was run inside Revit. Findings below distinguish implementation evidence, historical reports and hypotheses.

## Evidence map and Git reconciliation

`P` below means `PLEGTVOS_ModuleEngine.extension/PLEGTVOS_ModuleEngine.tab/Dev.panel/`. Unless marked **remote**, line numbers and paths refer to local HEAD `a10c8575e8c4e196a7734e7031d616bfa33ce9b1`. **Remote** means `f56f0ffe530032e78b3571f2b2637093d2686058`, inspected with `git show`, without checkout or merge.

Initial branch: `main`; 48 tracked files; clean index/worktree; no non-ignored untracked files. Ignored `venv/` exists. There were no pre-existing `AGENTS.md` or `PROJECT_STATE.md` in this repository and no applicable ancestor guidance was supplied. Existing README and `docs/AI_TASKS.md` were reviewed before documentation changes; the historical log is preserved.

Configured remote: `https://github.com/Emin-A/PLEGTVOS_ModuleEngine`. `git ls-remote` against this and the supplied `https://github.com/BIM3DNA/PLEGTVOS_ModuleEngine` returned the same HEAD/main `f56f0ff`. `git fetch origin` updated a stale tracking ref; `git rev-list --left-right --count HEAD...origin/main` returned `0 8`. No other advertised branches/tags appeared in those remote queries. Equal tips do not establish repository ownership or redirect semantics.

Eight commits missing locally, oldest first:

| Commit | Author-reported subject (not host proof) |
| --- | --- |
| `b77ad8b` | Distant mirror-copy works; left/right placement, two roof duct plates and one cyan pipe still problematic |
| `650ef05` | Mirror handler described as complete |
| `fe4f0df` | Correct HWA/VWA slopes but not beyond ground floor |
| `af7051d` | Slopes 5 and 7.5 per 1000 reported correct; debug interaction still needs cleanup |
| `b2c9f6b` | Final tweaks before another project |
| `951619e` | Module/state extraction update |
| `c0eb8cf` | GC01/GC04 extraction success; GC02/GC06 testing pending at that time |
| `f56f0ff` | Stabilize extraction with detached output verification (commit date 2026-07-03) |

Diff from local to remote: 26 files, 7,715 insertions and 782 deletions as reported by Git. New extractor/test buttons, expanded Documentation_09, changed transform/mirror/slope implementations, and several renamed bundle directories. `Capture_1`, `Capture_2`, `State_04`, `Documentation_09`, `Documentation_10`, `Systems_08`, `UI_11`, `Validation_12` and `Validation_13` lose the `.pushbutton` suffix remotely. This changes ribbon discovery; do not describe their remote source as currently exposed buttons. `module_state.py` and Capture_01/02 are unchanged in that comparison.

Sheet-Generator was fetched into **this repository's Git metadata only**, at `refs/audit/sheet-generator-main`, pinned to `2665476d3e95cbc48464b214d1e293346b867f26`. No clone/port was written into any other repository. Its tracked environment contains a large vendored Python environment; this is not evidence that the pyRevit entry point runs in CPython.

## Command inventory

All Python command entries below use the default **IronPython** selection: first line is an encoding declaration, not `#! python3`; no per-command CPython override was found. The Revit 2025 attachment is `IPY2712PR` (IronPython 2.7.12). This is installed/source configuration, not a captured live invocation.

| Directory under P (local suffix unless stated) | Actual behavior and shared state | Remote difference / status |
| --- | --- | --- |
| `Capture_01.pushbutton` / region_scanner | Active-view collector; scope-box XY center inclusion or detail-line polygon; records IDs, counts and view/region transform in `latest.json` via module_state. `TEMP_ISOLATE=True`; transaction-based temporary isolate and hide-elements fallback. | Same; useful capture prototype, not read-only and not full-model dependency extraction |
| `Capture_02.pushbutton` / element_collector | Loads latest payload; title check, path mismatch warning continues; resolves IDs and reports missing elements; category/pipeline buckets to `collected_latest.json`. No Revit transaction. | Same; identity checks do not validate central GUID or content revision |
| `Capture_1.pushbutton` / region_editor | Windows Forms review of collection and duplicated-view state; stages code/tag decisions to `review_latest.json`. | Renamed to `Capture_1` (not button); source unchanged |
| `Capture_2.pushbutton` / region_apply | Consumes review/view/region JSON; transaction creates region text, writes pipe/fitting Comments and attempts pipe tags; writes result JSON. | Renamed to `Capture_2`; source unchanged |
| `State_04.pushbutton` / state_serializer | Imports, document setup and optional Pillow detection only; no serialization workflow. | Renamed to `State_04`; placeholder. Actual storage is module_state.py |
| `Placement_05.pushbutton` / transform_engine | Selection/saved state to source/target scope-box frame; model, view-specific, view and assembly copy attempts; fallbacks and best-effort system-type assignment. Writes model. | Remote adds multiple target scope boxes and `copy_to_target`; experimental |
| `Placement_06.pushbutton` / mirror_handler | Saved collected IDs filtered against source box; groups/assembly handling, mirror modes, optional target, transactions and explicit section recreation. | Remote changes target mapping to copy then mirror about target face, per-element execution and host-aware fallback; experimental |
| `Systems_07.pushbutton` / slope_solver.py | Pipe type-name filter, system rules, parameter/offset/curve slope edits, per-pipe transactions and post-commit magnitude check. | Remote hard-coded type ID, all-elevation option, forensic UI, multiple passes and disconnect/reconnect retry; experimental |
| `Systems_08.pushbutton` / fitting_rebuilder.py | Imports/document setup only; no fitting reconstruction. | Renamed to `Systems_08`; placeholder |
| `Documentation_09.pushbutton` / sheet_generator.py | 143-line import/setup scaffold; no sheet creation. | Renamed to `Documentation_09`, expanded to 1,801-line workflow; not a discovered `.pushbutton` |
| `Documentation_10.pushbutton` / view_duplicator | Latest region to duplicated FloorPlan (WithDetailing, fallback Duplicate); clears template; timestamp name/crop; persists `view_duplicator_latest.json`. Injects XYZ conversion helpers into module_state. | Renamed to `Documentation_10`; source unchanged |
| `UI_11.pushbutton` | Two XAML files, no script.py entry point. | Renamed to `UI_11`; UI assets, not a working command |
| `Validation_12.pushbutton` / preflight.py | Imports/setup only. | Renamed to `Validation_12`; no validation gate |
| `Validation_13.pushbutton` / postflight.py | Imports/setup only. | Renamed to `Validation_13`; no validation gate |
| `Module_Extractor_14.pushbutton` | **Absent locally.** Remote report-only scope classifier: INSIDE, OUTSIDE, CROSSING, UNKNOWN, exclusions, MEP/assembly diagnostics and readiness. JSON output, no Revit transaction. | 959 lines; remote extraction prototype |
| `Module_Extract_Test_15.pushbutton` | **Absent locally.** Remote interactive extraction into filesystem-copied RVT with detached open, deletion, SaveAs and reopen classification. | 2,495 lines; host workflow, not an automated unit test |
| `module_state.py` | Shared schema 1 metadata and JSON storage; described below. | Same; shared module, not button |

Local panel inventory: 14 `.pushbutton` directories, 13 script entry points, one XAML-only directory and one shared Python module. Remote: seven `.pushbutton` directories, nine plain feature directories and module_state. There are no independent `transform_engine.py`, `mirror_handler.py`, `slope_solver.py` or `sheet_generator.py` files in this repository; those are command titles for the scripts above.

Outside Dev.panel, `lib/Samples` holds examples for creation, collectors, parameters, selection, transactions, views/sheets and templates; `lib/Snippets/_customprint.py` is a helper. They do not implement the named subsystem architecture. The import hook reads event/document context but its CAD-blocking code is commented. Tab bundle layout lists About/Resources/PlaceholderPanel/Dev/LearnRevitAPI, although the audited functionality is under Dev.

### Engine and tests evidence

The local `%APPDATA%/Autodesk/Revit/Addins/2025/pyRevit.addin` attachment points to `pyRevit-Master/bin/netcore/engines/IPY2712PR/pyRevitLoader.dll`. Installed `pyrevitlib/pyrevit/extensions/__init__.py:44` defines the CPython selector as `#! python3`; `genericcomps.py:812–817` checks the first script line. Config `cpyengine=3123` is available CPython configuration, not command selection. The configured extension roots include this workspace and the BIM3DNA repository.

Each inventory Python entry and both reference buttons has the same default engine selection. Shared modules inherit their caller's engine; XAML files have none. M0 did not inspect an executing command's runtime version or prove which duplicate installed toolbar was loaded. Existing README/log CPython claims were therefore corrected rather than repeated.

No repository test suite, CI workflow or documentation-check configuration was found in local/remote project trees. The extraction Test button is a model-writing host command and was not run. Historical `docs/AI_TASKS.md` reports scan/transform work (including warnings and copy counts); its architecture and compatibility statements are historical, not new acceptance.

### Shared state and extraction contract

`module_state.py` stores schema version, UTC/user, title/path/central path/GUID, worksharing status and Revit build. Save priority: local RVT directory, available central directory, then AppData/title fallback; saves timestamped JSON and `latest.json`. Path probing creates/deletes a temporary file. Loads use first existing latest file in candidate order, not newest timestamp across all locations; no atomic replacement or concurrency locking is implemented. A same-title fallback or stale state is not safe cross-document identity. Capture_02/Documentation_10 reject title mismatches but continue on path mismatch.

Remote Extractor_14 classifies model bounding boxes/endpoints, filters infrastructure/views/types/links/imports from the candidate population, and reports MEP, assembly and crossing/unknown diagnostics. It is a report generator with filesystem side effects, not a model writer. Bounding-box classification is not exact solid containment or a complete linked/nested-content traversal.

Remote Extract_Test_15 requires a saved filesystem RVT (`main`, lines 2093 onward); active-document unsaved edits are not automatically included in the disk copy. It rejects output equal to source path. `make_working_copy` copies the file; `open_working_copy` detaches workshared copies and opens worksets. Defaults: DISCARD_WORKSETS, preserve-worksets fallback disabled, fully-outside assembly deletion enabled, mixed-assembly disassembly disabled (lines 79–86). Assembly-associated views/sheets and protected deletion checks are part of copy cleanup. The active source is not the transaction target.

Save uses overwrite-enabled SaveAs, optional worksharing SaveAsCentral if the copy remains workshared, and then closes/reopens for verification (`save_copy_as_output`, `verify_saved_output`, lines 1580–1651). Default export directory is a user-specific `C:\Users\bim3d\OneDrive\Documenten\_PLEGTVOS_ModuleEngine\exports`; do not assume this VM has it. Output selection and safe destination need checking in a future authorized host run.

`build_acceptance` (line 1701 onward) requires saved/reopened output, inside > 0, outside = 0, unknown = 0, failed deletes = 0, protected deletes = 0. Crossing is allowed only if zero, or the pre-classification had no crossing MEP and reopened crossing count does not exceed the pre-count. Infrastructure and excluded categories are outside that physical-candidate acceptance. `source_unchanged=True` is assigned, not measured. Do not equate accepted classifier counts with connector integrity, exact geometry equality, source hash proof or complete dependency preservation.

Historical host reports and missing evidence are recorded in [PROJECT_STATE.md](../PROJECT_STATE.md). No per-module JSON acceptance artifacts were in the tracked repository inputs or supplied attachment; the expected local AppData module-state location was absent. No broader model-data search or model opening was performed.

## Sheet Generator audit

Authoritative reference for this audit: [BIM3DNA/Sheet-Generator](https://github.com/BIM3DNA/Sheet-Generator/tree/2665476d3e95cbc48464b214d1e293346b867f26), entry `BvdKTools.extension/BvdKTools.tab/BvdKTools.panel/Sheet Generator.pushbutton/script.py` (3,533 lines), with `bundle.yaml`. One integrated command; supporting behavior is mostly in the same file. Imports Revit API, pyRevit, Windows Forms, .NET; repository lib samples are not a separate production sheet engine.

A local installed copy exists at `%APPDATA%/pyRevit/Extensions/BvdKTools.extension/BvdKTools.tab/BvdKTools.panel/Sheet Generator.pushbutton/script.py`. It is not a Git checkout and differs: Git blob `241631b9ecd63c81174b2a3a8f5db768b8ca3c09` versus reference `212fa79bc0a9b0fbeb672fea07aea36bd1feeef6`. The installed copy uses exact Comments schedule filtering and lacks the reference's canonical-numbering/pre-sheet verification functions. Do not assume the installed version equals GitHub. Another toolbar copy exists under BIM3DNA/BvdK; it is not substituted for the pinned reference. `SmartPipingSheetGen` is a different repository (`Emin-A/Geberit`, HEAD `f2db0b5`), not the requested Sheet-Generator.

### Implemented workflow and dependencies

- Entry-level workflow (lines 3124 onward): pick closed detail lines; collect active-view elements whose bounding-box centers fall inside; show element editor; choose sheet creation or tags/text only. Requires suitable active project/plan context and loaded model content. Not a scope-box command.
- Editor supports prefab codes, tag actions, reducer/fitting parameter operations and T-stuk actions. It can modify the model before sheet creation. Canceling/skipping the sheet stage does not undo all earlier editor/Comments/text changes.
- Canonical numbering (2956–3011): pipes sorted by annotation X/Y and element ID get `<base>.<n>`; fittings get base; pipe-tag rows follow host code. `sync_comments_from_result` persists Comments; `verify_prefab_comments_before_sheet` blocks on detected mismatch. This is not an approved left/right register and ordering can change under mirroring.
- View helpers resolve a plan/primary view, try duplication/recreation, clear the view template, set scale 25/Coordination and apply a region bounding box using source crop transform (3318–3351). Create orthographic 3D, scale 25, section box; not a general scope-box or arbitrary rotated crop mapping solution.
- Title-block type is selected from loaded symbols; ViewSheet.Create supplies the instance. Sheet number is base code and name is `Prefab <base>`; an existing number raises rather than updating a sheet (3387–3395).
- Plan and 3D viewports initially use title-block center/offset. Later both are set to the same center (3444–3451): overlapping viewports are a concrete layout concern. Schedules use fixed proportional spacing, without demonstrated collision/pagination control.
- Plan pipe tags use host references/type discovery and offsets. 3D annotation runs after sheet-group assimilation, locks view orientation, uses loaded/existing tag types, checks visibility and logs failures; its failure does not roll back the committed sheet. Text fallback helper exists; do not assume all annotation categories succeed in the host.
- Schedule logic (988–1360): template-name mappings for Geberit PE/Silent, Wavin Tigris/Wafix PP, pipe accessories and plumbing fixtures; system/type-name detection selects relevant templates. Duplicates schedules, adds a Comments field if schedulable, replaces Comments filters while preserving others; uses Contains with BeginsWith/Equal fallback. Unique schedule suffixes, pipe itemization/sorting and empty-schedule deletion are implemented. Missing template/filter errors can be logged/skipped, so a created sheet need not be complete.
- Family parameter dependencies include Comments, `waarschuwing`, `2x45°`, `bend_visible`, `reducer_eccentric`, `geom_exc`, `switch_excentriciteit`, `GEB_Article_Number`, diameter/length and type/system strings. Editor behavior depends on particular content; no general recursive nested-family parameter contract or arbitrary nested-family repair was found. Emir must confirm which hosted/shared/nested parameters actually drive his delivered tags and schedules.
- Validations include boundary closure, nonempty selection, eligible duplication sources, transaction context, code/Comments verification and sheet-number collision rejection. There is no independent host acceptance suite or proof of all rollback, layout, handedness, content and schedule correctness cases.

### Feature gap matrix

| Feature | PLEGTVOS local HEAD | PLEGTVOS remote Documentation_09 (plain folder) | Sheet-Generator reference | Plechtvos gap / gate |
| --- | --- | --- | --- | --- |
| Region input | Capture_01 scope/lines; saved state | Closed detail-line graph/polygon editor | Closed detail lines, active-view center selection | Approve scope/boundary/dependency policy |
| Codes/register | Review/apply Comments; no register | Auto codes, fundering prefix rules | Canonical pipe suffixes, fitting base, Comments verification | Unique left/right/building/revision contract (M2) |
| Plan view | Documentation_10 state-driven duplicate/crop | WithDetailing, unique name, template cleared, scale 25 | Source resolver and duplicate/recreate fallback | Template/crop/orientation acceptance |
| 3D and sheets | Documentation_09 scaffold only | Plan + 3D + title-block selection | Orthographic 3D, title block, base-number collision gate | Approved layout; avoid shared-center overlap |
| Tags | Capture_2 pipe tag attempts | Pipe/duct tag helpers and toggle/visibility handling | Plan and post-commit 3D annotation | Required categories, tag families, visibility, host correctness |
| Schedules | None in local Documentation_09/10 | Dyka fittings/pipes, fundering, GC01 WTW ducts and GC01/04 spaces; fixed master names | Detected systems, Geberit/Wavin/accessory/fixture template mappings | Plechtvos mapping and missing-template preflight |
| Schedule membership | None | Fixed filters/configuration; sheet code in duplicated name is not sufficient membership isolation | Comments Contains (installed copy uses Equal) | Exact module/hand/revision membership; prefix collision tests |
| Scope box | Capture state only | Polygon/bbox crop | Polygon/bbox crop | Explicit scope-box assignment and rotated mapping if required |
| Family operations | No general fitting rebuilder | Codes/tags; model-specific fields | Reducer/bend/T-stuk parameter actions | Review Emir content; no unrequested fitting mutation |
| Atomicity | Separate capture/review/apply/view transactions | Sheet transaction group after earlier editor/code writes | Sheet group; earlier edits and later 3D annotation separate | Define cancellation and partial-result semantics |
| Repeat runs | Latest files/timestamps; no register | Unique view name; model edits/schedule duplication | Sheet number blocks; schedule names suffix | Idempotence/collision policy and register reconciliation |

Remote PLEGTVOS references: `create_cropped_plan_view` at 1400, sheet helpers from 1435, schedule pipeline 1643–1695, main 1720 onward. Fixed schedule masters include `Dyka PVC Pipe Fittings`, its fundering version, `Dyka PVC Pipes U3`, its fundering version, `GC01 WTW Afzuiging`, `GC01 WTW Toevoer`, `GC01 WTW Balans`, `GC04 WTW Balans`. They are dependencies, not proof those families/views exist in a supplied model. No code was ported.

## OVT Sheet Transfer audit

Local repository: `C:\BIM3DNA\BIM3DNA_API\BIM3DNARevitAPI`, branch main, HEAD `a33f3f3edb8c85687feec2e73f3726b8743e1ddc`, origin `https://github.com/bim3dna-dev/BIM3DNA.git`. Audited file: `BIM3DNA.extension/BIM3DNA.tab/QuickFix.panel/Sheet Transfer.pushbutton/script.py`, 502 lines. Repository has unrelated existing Connect Pipes/Create Print Set edits and untracked Connect Pipes guidance/tests; none were changed. Sheet Transfer itself is clean. Its AppData-installed copy has identical SHA256 `07C616D748B39122486EE7BCB2FFCA8EF6F1211B18A68079C280CE25B91BAE09`. Archived copies were located but not treated as the live reference.

| Concern | Observed implementation and consequence |
| --- | --- |
| Source/target | Active source doc. At module load, find first other open document with title containing `BNZ_OMO_OV2_N_IT_MPO_Sanitaire Installatie` (132–143). No target picker, identity/coordinate/worksharing readiness contract. Failure can happen before main's reporting. |
| User interaction | Multiselect source plan names (424–445); cancellation handled there. Picker includes all non-template ViewPlans, including dependents; no mandatory target confirmation/preview. Header instruction to draw boundaries is stale: runtime does not request detail lines. |
| Selection | Named main plan plus direct dependent plans; sheets found through their viewports (147–196). This is not arbitrary sheet-content transfer. |
| Scope boxes | Looks up `Scope Box` on viewport, not its view (184); copies collected IDs with document CopyElements and no transform, then positional zip mapping (200–226). Count mismatch is checked after committing boxes. View assignment uses a `ScopeBox` attribute guard (292–294/329–335), not the documented view parameter path. Standard views do not expose that property in installed RevitAPI.xml; assignment can be skipped. |
| Views | Bulk document CopyElements for primary ViewPlan IDs (279–290), assumes equal count and positional mapping; recreates dependents with AsDependent (300–357). Actual plan-copy support must be proved in Revit 2025; no target level/plan creation mapping exists. |
| Templates | Reuses target template by `(Name, ViewType)`, otherwise InvalidElementId (235–261). No explicit missing-template transfer or definition-equality check. |
| Dependent crops | Copies crop flags, attempts shape in swallowed exception block (339–355). Calls `CanHaveShape()` although API exposes a property; passes `List[CurveLoop]` to SetCropShape although API takes one CurveLoop. Verified API mismatches; crop fidelity is not guaranteed. |
| Sheets/title blocks | Creates sheets and preserves name/number; `_copy`, `_copy2` collision suffixes. Source title-block type ID goes directly into target ViewSheet.Create (400–405), despite comment claiming family copy. No type transfer/mapping; can fail or resolve an unrelated target element. |
| Viewports | Recreates only mapped views at source box centers. No preservation of viewport type, rotation, detail number, label placement or all sheet annotations. |
| Tags/schedules/content | Imports mention tags and schedules, but there is no explicit host remapping/tag transfer, ViewSchedule copying or ScheduleSheetInstance placement. Sheet graphics, revisions and nested sheet contents are not handled explicitly. Incidental API copying is not a supported contract. |
| Coordinates | Copy transform is None; viewports use paper-space centers. No source/target project-location, internal/shared-coordinate, level or architectural-link comparison. No explicit repositioning is implemented, but alignment is not verified. |
| Failure/rollback | Separate committed scope/view/sheet transactions; no enclosing TransactionGroup. A later failure leaves previous stages committed. Main counts success only after all stages, so “No views were copied” can underreport partial persistent results. Exceptions are collected per selected plan. |
| Collisions | Sheet suffix loop and dependent-view name retry loop; no repeat-run manifest or deduplication of sheets reached through multiple selected plans. Dependent rename catches all exceptions with an unbounded loop, not only collisions. |

Installed Revit 2025 `RevitAPI.xml` confirms CopyElements document overload is for non-view-specific elements and gives no positional source-to-result correspondence guarantee. View-specific content needs the view overload, as also described by [Autodesk's copying-elements guide](https://help.autodesk.com/cloudhelp/2024/PTB/Revit-API/files/Revit_API_Developers_Guide/Basic_Interaction_with_Revit_Elements/Editing_Elements/Revit_API_Revit_API_Developers_Guide_Basic_Interaction_with_Revit_Elements_Editing_Elements_Copying_Elements_html.html). This does not by itself prove which primary plan IDs will copy; that remains a host test.

Reusable ideas: source view/dependent/sheet traversal, target-template lookup, dependent recreation, sheet numbering checks and viewport-center capture. Adaptation requires explicit source/target selection and identity, title-block/type mapping, view/level/content mapping, parameter-based scope assignment, valid crop APIs, bounded collisions, coordinate preflight and atomic/partial-result policy. Add required tags/schedules only after requirements review. Do not copy this button wholesale or alter BIM3DNA during M0.

## Mirror, transform and slope findings

### Verified source defects and limitations

| Finding | Evidence | Boundary |
| --- | --- | --- |
| Per-element mirror loses whole-network execution boundary | Remote Placement_06:1068–1199 copies/mirrors individual IDs, expands assemblies, skips group members and separately adds groups; no connector graph acceptance. Local has batch then per-element fallback. | Verified execution strategy and missing validation; actual disconnection mechanism needs host reproduction |
| Pin restoration outside transaction | Remote Placement_06:1166 commits, then 1174 sets original Pinned=True with exception swallowed; analogous local fallback | Verified invalid write placement can leave an originally pinned source unpinned; no model result measured |
| Fallback attempts share mutable transaction | Remote Placement_06:1091–1139 can copy successfully then fail mirror and attempt host+element copy without resetting the first attempt | Verified non-isolated control flow; duplicate/unmirrored residue is a scenario to reproduce, not an observed count |
| Warnings suppressed | Mirror failure preprocessor deletes warnings; slope paths also suppress warnings | Reduces evidence for connectivity/constraints; transaction success is insufficient |
| Element mapping inferred from returned order | Placement_05 uses positional CopyElements mapping when counts match, or first ID in a single-element result; reused for best-effort system assignment | No explicit source/target correspondence verification; system type assignment does not rebuild connectors |
| Orientation heuristic | Placement_05:178–213 derives basis from bounding box, swaps X/Y by extent, maps `target * source.Inverse` | Does not independently establish architectural handedness or rotation; source/target reference geometry needs checking |
| Stale or incomplete selected population | Mirror uses collected state and source filtering; Capture_01 is active-view/center-based, not full network closure | Can omit out-of-region/hidden/no-bbox/hosted dependencies. Which reported missing objects were excluded remains unknown |
| Local slope documentation contradicts executed rules | Systems_07 header advertises percentages/older assignments; actual lines 395–400 return VWA .0075 and HWA .005 | Verified documentation defect. Do not multiply ratios by 100 or swap systems from header text |
| Slope validation after commit | Local Systems_07:507–540 commits before measuring magnitude; mismatch only increases failure counter, group is assimilated | Failed validation does not undo already committed wrong geometry |
| Reconnection not an acceptance gate | Remote Systems_07:847–861 returns successful slope attempt plus `reconnect_failed`; 1844–1856 counts matching slope as succeeded and separately logs network reconnection failure | Verified acceptance defect; no proof the reported cyan pipe was caused by this path |
| Project-specific type filtering | Local filters type-name token; remote `PIPE_TYPE_ID=926396`, rules VWA .0075/HWA .005 (69–84), optional scope Z exclusion | Other documents/types/elevations can be excluded; hard-coded ID is not portable |
| Flow direction not established | Slope check is absolute rise/run; endpoint choice uses high end or connector-anchor heuristics, geometry fallback moves one end | Correct magnitude alone does not prove intended flow/fitting compatibility |
| No implemented repair/validation subsystem | Systems_08 and Validation_12/13 remain scaffolds | No general fitting rebuild or pre/postflight can be assumed |

Remote mirror target mode maps source center/basis to target then reflects about chosen target face (`main`:893–958); selecting a target forces copy even if in-place was requested. Sections are explicitly recreated with reflected bounds/settings. Neither recreated view counts nor mapped center distance proves that roof-hosted objects and connectors remain intact.

Revit API contract cross-check: installed `RevitAPI.xml:146785` documents the four-argument **MirrorElements returns copied IDs** (empty when mirrorCopies is false). It would be incorrect to apply the old no-return-value assumption to this Revit 2025 overload. M0 did not invent that defect.

### Historical reports versus hypotheses

Local history: `733d256` reports nearby mirror limitations for sections/groups/centerline; `d457f97` reports 624 physical copies and system-type reassignment; `a10c857` reports slopes only partially working outside groups/assemblies and across levels. Remote `b77ad8b` reports missing roof duct plates and a broken cyan pipe; `650ef05` subsequently claims mirror functionality complete. These reports do not resolve the October request for GC01 reliability and are not connector-graph evidence.

Plausible causes to test: copying incomplete connected networks individually; missing host/group/assembly/nested dependencies; axis/face interpretation; solver movement of adjacent fittings after endpoint changes; level/Z/type filtering; stale state; partial commits and failed reconnection. No unique causal explanation for the earlier model failures is verified without the actual fixture, IDs, before/after connectors and host warnings.

Next diagnostic case: unchanged GC01 source, approved left/right frame definition, full candidate/exclusion ledger, connector pairs/positions/directions, fitting host and group/assembly IDs, signed elevations/slope, and fixed architectural reference points. Record first divergence, cancellation and warnings. Repairs belong to separately authorized M1, not this audit.

## M0 documentation and validation

Updated README; created PROJECT_STATE, AGENTS, this audit, milestone plan and meeting note. Preserved historical AI_TASKS. No executable edits, reference ports, commits, pushes, model operations or RVT artifacts. Only this repository's documentation and Git metadata changed.

Validation passed: 14 local Markdown links/anchors, all 42 required milestone fields, whitespace/final-newline checks on six documents, exact change scope and `git diff --check`. Git confirmed the extension and historical AI_TASKS file are unchanged against HEAD. README is modified and five documents are untracked, with no staged changes. Offline checks do not establish Revit acceptance. The next action and implementation blockers are in [PROJECT_STATE.md](../PROJECT_STATE.md).
