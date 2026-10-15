# M1.1 GC01 read-only diagnostics: implementation and host acceptance

## M1.1h complete FAST detail coverage - 2026-10-14

### Host evidence entering this milestone

User reports Revit 2025.3, IronPython 2.7.12/.NET 8.0.22,
IGN_W-INS_Technische motor_A(R25)_bim3dnapc6.rvt, GC01 1405931, schema /3.
ElementMulticategoryFilter with all 18 categories exhausted: 6,526 classified,
763 INSIDE, 5,763 OUTSIDE, zero CROSSING/UNKNOWN. Retained 500 INSIDE details;
263-detail gap. limits_reached=candidates; inventory_blockers=API_READ_ERRORS,
candidates. Export about 41.4 seconds. The 500 retained elements included 140 pipes,
113 measured slopes and 23 vertical pipes: these are PARTIAL detail totals.

M1.1g category filtering and collector exhaustion are host-verified on this path.
M1.1 itself remains unaccepted. Original reports are not modified. Exact external
artifact hashes/paths still require the user's report files; supplied counts are
not a new execution by this agent. The observed central_guid error was
stage=document_identity, field=central_guid, 'An internal error has occurred.'
That message does not establish the exact exception type/cause. Earlier failures
remain documented below.

### Architecture, bounds and schema /4

Preserved: the entire native collector/filter block, 18 category values, explicit
GetElementIterator path, stable IDs, conservative membership/slope calculations,
Unicode encoder and read-only API thread. FULL stays disabled.

Classification already reads FAST basic details (identity/category/bbox/location)
for every supported candidate. M1.1h retains in-scope rows after classification,
then processes slope work and exports stable-key detail batches of at most 500.
There is one supported-category collector pass per invocation, never one per part.
References/rows remain bounded by scanned_elements=10,000. The candidates=500 limit
now explicitly means PER_FAST_DETAIL_BATCH, not a larger or absent total scan cap.
UNKNOWN retains its 500 cap and cannot establish complete classification. All four
membership classes remain in the ledger. A qualified 763-detail run has 500+263
records, with no promise that its full pipe totals equal the historical partial ones.

Schema plegtvos.gc01_mirror_diagnostic/4, collector_version 1.1h:

- plan.json: complete=false; source contract/hash, expected IDs, explicit missing IDs,
  expected/missing pipe IDs, ordered part descriptors/covered IDs/content hashes,
  classification inventory, source-run and safety evidence.
- part-0000.json etc.: zero-based batch index, snapshot hash, ordered covered IDs,
  at most 500 element records and their pipe/slope records.
- manifest.json: written only after every expected part is read back and validated;
  binds plan/content hashes, counts and exactly-once coverage. Reports classification
  inventory, element-detail coverage, pipe/slope-detail coverage, NOT_INSPECTED
  connector topology, saved-source identity confidence and UNRESOLVED mirror readiness.
  Pipe detail coverage means records/statuses accounted for, not that every pipe is
  measurable or its slope complies with an engineering rule.
- Every file is an envelope with payload and SHA-256 of canonical payload. Plan and
  part contracts are checked as well as hashes; missing/duplicate/mismatched IDs,
  pipe records, wrong batch numbers and invalid filenames cannot produce completeness.
  A finished PARTIAL_UNRESOLVED manifest remains explicit when recorded gaps/blockers
  exist. No completed manifest means incomplete export, even if some parts exist.

Each plan, part and manifest retains the 4 MiB JSON limit (plus existing newline).
The 60-second cooperative budget includes qualification, classification, processing,
export prompts and writes; it is not reset between batches. The 64 scope-geometry,
4,096-character and existing connector/reference limits remain. No wall-clock
check can interrupt an active Revit API call. Large plans/parts or time expiry stop;
limits are not silently increased. Historical monolithic /3 files are not rewritten.
New bundles use unique directories and exclusive writes, with no latest-pointer
replacement. Consumers must explicitly support /4 rather than treating it as /3.

### Snapshot qualification and manual continuation

Qualification requires an already saved, unmodified, non-cloud document and a
readable source RVT. No automatic save/sync or forced rollback is offered.
DB.Document.GetDocumentVersion(doc) must match BasicFileInfo.Extract(path).
GetDocumentVersion() in both GUID and save count. A streaming whole-RVT SHA-256
and project UID are captured; source file size/mtime and document state/version
are checked during hashing. Qualification runs before and after collection, and
both results must match. The source RVT is read only, never copied or modified.

Authoritative installed RevitAPI.xml notes that DocumentVersion.VersionGUID may
not update on every edit, and GetDocumentVersion must be combined with IsModified
to compare memory with disk. Accordingly, path equality, version GUID alone, file
time alone, or a false IsModified flag alone is never the continuation contract.
Cloud, unsaved, modified, unavailable or mismatched-version sources fail closed.
This intentionally restricts the host test to an already qualified local source.

For Continue incomplete bundle, the user explicitly selects the original plan.json
in a subsequent command. That invocation independently requalifies the source and
performs one fresh classification. It must match document/scope identities, scope
geometry/frame, categories, schema/code hashes, membership ledger/hash, complete
inventory evidence and every planned detail/pipe hash. Existing parts are validated
and retained byte-for-byte; missing parts are written. No automatic repeated command,
merged unrelated snapshot or unbounded Revit-object cache. A finalized bundle cannot
be resumed or overwritten. A partially written/corrupt part is rejected, not replaced;
start a new bundle after investigation. If the plan itself was never written before
stopping, no continuation data exists: a fresh diagnostic is required. Repeated
qualification/time failure needs further investigation, not a raised budget.

### central_guid handling

The installed Document.WorksharingCentralGUID contract applies to qualifying Revit
Server centrals, not file-based centrals. The reader now inspects the documented
ModelPath.ServerPath and Empty flags. A positive non-empty, non-server result records
central_guid=null, central_guid_status=NOT_APPLICABLE_NON_SERVER_CENTRAL; it does not
call a getter whose contract does not apply. Independent project UID, memory/disk
version and RVT hash qualify identity before any bundle export.

A failed/ambiguous central-path read remains UNAVAILABLE/READ_ERROR. An applicable
server GUID read still executes and preserves any actual exception/type/context/
traceback. These errors continue to block completeness. The earlier internal error
is preserved as historical evidence, not silently reclassified as a known benign
exception. No GUID is fabricated. Host validation of this new branch remains pending.

### Offline validation

95 CPython tests pass. New cases cover 0/1/499/500/501/763 INSIDE records, deterministic
500+263 partitioning, exactly-once IDs, missing/duplicate detail and pipe records,
document/scope/geometry/ledger/code/freshness/read-evidence mismatches, corrupt/partial
parts, manifest/hash verification, interrupted writes and continuation, unchanged
existing parts, JSON/cooperative limits, Unicode, modified/cloud/version rejection,
binary RVT hashing, legitimate non-server metadata and unexpected API errors.

IronPython 2.7.12/.NET 8.0.22: 36 coverage/filter/batch tests plus existing Unicode
probe pass; all 15 diagnostic/test Python files compile. These use fake Revit objects;
they do not prove actual BasicFileInfo, version or ModelPath behavior in Revit.
Evidence: C:\Users\Korisnik\AppData\Local\Temp\plegtvos-m11h-4u_03_mm (run.py, net8.log).
Static no-write checks include both new modules. Protected scripts, native collector,
iterator, numeric/classification/Unicode functions and unchanged numeric limit values
are verified; git diff --check passes.

### Exact user-facing Revit host test

1. Preserve the existing /3 JSON and console evidence. Use the same original local
   bim3dnapc6 RVT, already saved and unmodified. Do not save/sync as part of this command.
   If it has unsaved changes, stop; do not discard them merely to pass qualification.
2. Reload the repository extension, restart Revit if needed to clear cached modules,
   and verify loaded path/version/engine. Record source path/project UID, modification
   state, active view and selection. Select only GC01 / 1405931 in this document.
3. Run FAST. Qualification must pass before collection and again after it. Confirm
   the preserved native collector exhausts and compare the expected 6,526/763/5,763
   classifications only for the same unchanged source; investigate any difference.
   Preserve every actual read error and central-path/GUID status.
4. Choose Use diagnostic folder or Choose external folder promptly. The console prints
   the immutable bundle plan path before part writes. Expect schema /4, version 1.1h,
   two parts of 500 and 263 if this exact source still has 763 eligible detail IDs.
5. Require manifest.json plus a valid plan and both validated parts. Reconcile all
   expected stable IDs exactly once, content/snapshot hashes, no missing detail or
   pipe IDs, classification/detail/pipe coverage flags and source freshness evidence.
   Connector topology must remain NOT_INSPECTED, mirror UNRESOLVED. Full pipe totals
   are newly observed evidence, not assumed to be 140/113/23.
6. If a cooperative stop leaves a plan and only some valid parts, do not edit the RVT
   or evidence. Run the command yourself again, select Continue incomplete bundle and
   that original plan.json. Requalification must pass; completed parts must remain
   unchanged. If source/scope/code changed, or a part is corrupt, expect rejection;
   retain the evidence and start a fresh qualified diagnostic, never manually merge.
7. On any failure keep the complete console/traceback, plan/partial files and paths.
   If no plan was written, there is nothing to resume. Verify unchanged model/view/
   selection and record total runtime, source hashes and output paths. Do not enable
   FULL or begin M1.2. Do not intentionally modify the original model just to test
   stale-snapshot rejection; that scenario is covered offline pending a separate fixture.

Remaining acceptance blockers: real Revit saved-source/ModelPath API behavior,
qualification and hashing overhead within 60 seconds, complete 763-ID export and
manual continuation in the host, and external report/identity verification.
**M1.1h host test NOT RUN; M1.1 remains NOT ACCEPTED.**

## M1.1g filtered MEP collection - 2026-10-14

### Latest host evidence

User-reported M1.1f: Revit 2025.3, IronPython 2.7.12/.NET 8.0.22,
IGN_W-INS_Technische motor_A(R25)_bim3dnapc6.rvt, GC01 ElementId 1405931,
schema plegtvos.gc01_mirror_diagnostic/2. First 10,000 document instances:
1,552 supported candidates; 460 INSIDE, 1,092 OUTSIDE, zero observed CROSSING/UNKNOWN.
8,448 unsupported instances across 65 category IDs. All 460 INSIDE details retained.
JSON export in 12.8 seconds; TRUNCATED_UNRESOLVED / scanned_elements;
scan_exhausted=false, scope_inventory_complete=false. A central_guid read error
was observed. These are partial counts, not complete-document acceptance.

Original /2 JSON remains external and untouched. Exact source path/key/scope UID/
frame/hash review and independent same-RVT baseline comparison remain pending.
The other historical extractor RVT is not a count oracle. Earlier failure records
are preserved below. No live Revit execution occurred during this implementation.

### Collector and supported categories

Before: FilteredElementCollector(doc).WhereElementIsNotElementType(), followed by
Python category checks; unsupported instances consumed the scan cap.
After: the same collector additionally uses WherePasses(ElementMulticategoryFilter(
typed_categories)) before iteration. Explicit System.Collections.Generic.List[
DB.BuiltInCategory] selects the ICollection[BuiltInCategory] overload without enum
integer reconstruction. All 18 original categories, in original order:

```text
OST_PipeCurves, OST_FlexPipeCurves, OST_PipeFitting, OST_PipeAccessory,
OST_DuctCurves, OST_FlexDuctCurves, OST_DuctFitting, OST_DuctAccessory,
OST_MechanicalEquipment, OST_PlumbingFixtures, OST_Sprinklers,
OST_Conduit, OST_ConduitFitting, OST_CableTray, OST_CableTrayFitting,
OST_PipeInsulations, OST_DuctInsulations, OST_DuctLinings
```

Name/ID equivalence is checked against all 18 prepared entries. Missing entries,
mismatches or filter exceptions stop collection, without a smaller category set or
unfiltered fallback. Native list/filter/application checkpoints identify failures.
Filter, collector and enumerator are disposed on normal/exception paths.
GetElementIterator/Reset/MoveNext/Current remain; no Python collector adaptation,
ToElements/ToElementIds, extra whole-document scan or background API access.
Classification data/Revit references are bounded by the 10,000 scan cap. Stable-key
ordering, geometry/membership/slope calculations, Unicode encoding, FAST omissions
and 500 INSIDE/CROSSING plus 500 UNKNOWN detail budgets are preserved.

### Schema /3 and completeness

Schema plegtvos.gc01_mirror_diagnostic/3; collector_version 1.1g. Historical /2
reports are not rewritten and their scan counts must not be interpreted as /3.

- processing_counts.scanned_elements now means SUPPORTED_CATEGORY_INSTANCES_INSPECTED,
  not total document size. coverage records that basis and the exact native filter.
- excluded_category_inventory=NOT_INSPECTED_BY_FILTERED_COLLECTION; excluded and
  summary.unsupported_categories are null, not zero or an empty measured inventory.
  Unexpected returned-category anomalies have separate evidence and block coverage.
- Duplicate IDs/keys do not duplicate ledger/details. duplicate_observations/issues
  preserve evidence; scanned counts still include these anomalous observations.
- scan_exhausted is true only after native MoveNext=false and a cooperative check.
  Limit/error/early close cannot imply exhaustion. Exactly 10,000 remains unproven
  because the preserved cap performs no extra advance; empty/below-cap exhaustion
  is recognized.
- inventory_blockers includes caps, unproven exhaustion, invalid frame, UNKNOWN,
  read errors, category anomalies, missing document path/project UID/scope UID/
  element IDs/UIDs, and duplicate identities. scope_inventory_complete requires an
  empty blocker list. Overall complete remains false for unresolved topology,
  dependency closure and mirror policies; FULL remains disabled.

All limits remain unchanged: 10,000 inspected eligible instances, 60 cooperative
seconds, 64 scope geometry objects, 4,096 text characters, 4 MiB output, existing
detail/connector/reference caps. Time/text/JSON failures stop without a new report.
A wall-clock budget cannot interrupt an active blocking API call. Export also stops
on observed modification/view/selection changes.

### Central GUID availability

Authoritative installed source: C:\Program Files\Autodesk\Revit 2025\RevitAPI.xml,
P:Autodesk.Revit.DB.Document.WorksharingCentralGUID. It describes a server-based
model's central GUID: file-based central models and pre-2013 models do not have
this value; a qualifying Revit Server central is required. The documented exception
is Autodesk.Revit.Exceptions.InapplicableDataException. IsWorkshared therefore does
not guarantee availability in a local workshared file.

This is a legitimate possible explanation, not confirmation of the exact observed
exception without its traceback. The original attempted read, READ_ERROR and full
exception context remain. central_guid stays null and central_guid_status is
UNAVAILABLE after failure. No invented/replacement GUID, metadata write or suppressed
API error. API_READ_ERRORS still blocks scope_inventory_complete even if the eligible
collector exhausts. Successful runtime collection is not identity qualification.

The installed XML also documents the multicategory ICollection[BuiltInCategory]
constructor as a native quick filter, WherePasses as an added collector condition,
and MoveNext=false as actual exhaustion. This documentation does not prove host
execution of the new typed constructor.

### Validation

81 CPython tests pass, including 12 new filter tests: 18-category equivalence,
type exclusion, unsupported accounting, synthetic 8,448 unsupported + 1,552 eligible
fixture, empty/below/at/over limits, duplicate prevention, missing identity, central
GUID error evidence, filter failure and cleanup. Existing classification, deterministic
ordering, Unicode, cancellation/iterator and static no-write tests pass. Synthetic
counts are not a prediction of the real complete RVT inventory.

IronPython 2.7.12/.NET 8.0.22: 22 coverage/filter tests pass; all 12 Python files compile;
Unicode probe passes; the production typed-list factory passes using an actual CLR
enum (System.DayOfWeek). This validates generic adaptation, not the real Revit enum/
filter constructor. Evidence: C:\Users\Korisnik\AppData\Local\Temp\plegtvos-m11g-y5j_k0ug
(run.py, net8.log). Protected scripts, classification/numerical/Unicode functions
and limits remain unchanged. Static safety and git diff --check pass.

### Exact Revit 2025 FAST retest

1. Preserve the historical /2 JSON and console evidence. Use the same authorized
   bim3dnapc6 RVT, recording exact path/key/project UID and revision evidence. Do not
   substitute the historical e.avdovicQREF7 model or run extraction for this test.
2. Reload the repository extension; restart Revit if required to clear cached
   modules. Verify the printed Plechtvos repository path and Revit 2025.3 /
   IronPython 2.7.12/.NET 8.0.22. Record modification state, view and selection.
3. Select only GC01, verify ID 1405931 in this document, run FAST. Confirm all 18
   categories and native list/filter/application checkpoints pass. On exception,
   retain full traceback/stage/ElementId/field; do not remove filtering or raise caps.
4. Export promptly and preserve immutable schema /3 JSON. Verify collector version
   1.1g, source hashes/identity/scope geometry, scan basis, category metadata, ledger
   totals and unsupported NOT_INSPECTED/null fields. Counts may differ from 1,552/
   460 because the previous document scan was partial. Inspect scan_exhausted,
   limits_reached, inventory_blockers and central_guid error evidence separately.
5. Reconcile detail/slope counts against retained flags and unchanged budgets.
   Read/identity errors can still prevent completeness after scan exhaustion.
   Verify unchanged model state/view/selection; record runtime and evidence paths.
   Do not save/sync, enable FULL or begin M1.2 as part of this test.

### Conditional continuation proposal

If the filtered collector still hits 10,000, do not raise the cap or silently
restart and skip a first page. A future separately reviewed continuation could
partition natively by the fixed categories, then a validated disjoint secondary
partition if a category exceeds a page. Each partition retains budget/exhaustion/
blockers; bounded persisted manifests deduplicate by document key and UniqueId.
No cumulative in-memory Revit object list. Unassigned partition membership stays
explicit. Aggregate acceptance requires the same document identity, scope frame,
code/filter hash, qualified revision state and a reliable model-change counter
across pages. Any change or inability to prove consistency invalidates the aggregate.
Every partition must exhaust. This is a conditional proposal, NOT implemented or
evidence that the current eligible collector exceeds its cap.

**M1.1g host test NOT RUN. M1.1 remains NOT ACCEPTED. FULL remains disabled.**

## M1.1f scope-first FAST coverage - 2026-10-12

### Evidence boundary and identity

User reports a successful M1.1e FAST run: 7,853 scanned, 500 inventoried,
433 INSIDE / 67 OUTSIDE, 98 pipes / 72 measured / 22 vertical, exported JSON,
about 11.5 seconds, TRUNCATED_UNRESOLVED at candidates. No model-write API or
transaction invoked. This is runtime success with partial inventory, not M1.1
acceptance. Previous Unicode, hang, category and iterator failure records remain.

Reported source: IGN_W-INS_Technische motor_A(R25)_bim3dnapc6.rvt. Historical
extractor source: IGN_W-INS_Technische motor_A(R25)_e.avdovicQREF7.rvt. Do not
compare counts as if these are the same RVT. Prior selected scope evidence is
GC01 / 1405931. Exact path, document key, scope UID/geometry/frame and source
snapshot hash are UNVERIFIED: the successful JSON was not supplied/found in the
repository or default AppData diagnostic directory. Its path was requested.
Independent exact-document extractor baseline is PENDING; no extractor was run.
The 4,734 reported issues cannot be attributed to particular fields without JSON.
Code inspection establishes that every scanned null Category previously produced
UNAVAILABLE; it does not establish how many of the 4,734 had that cause.

### Scope-first budgets and schema compatibility

The old cap stopped after the first 500 supported categories, before classification.
Now the existing bounded native collector scans up to 10,000 instances, classifies
supported candidates, then stable element keys order the retained detail set.
INSIDE and CROSSING share candidates=500; UNKNOWN uses unknown_candidates=500.
OUTSIDE spends neither. No blind cap increase, extra collector scan, recursive
traversal, background API access or connector inspection is introduced.

Schema **plegtvos.gc01_mirror_diagnostic/2**, collector_version **1.1f**:

- elements: retained non-OUTSIDE detail records only, ordered by stable key.
- coverage.classification_ledger: every supported scanned identity/key/category,
  INSIDE/CROSSING/OUTSIDE/UNKNOWN membership and detail_retained flag, including
  outside and over-budget evidence. Counts include all ledger entries.
- coverage.excluded: unsupported category counts and uncategorized/read-error
  counts for scanned instances; category-less objects are not claimed MEP.
- coverage.scope_inventory_complete: only supported-category inventory coverage;
  requires exhausted scan, valid scope frame, all 18 categories resolved, no UNKNOWN,
  read errors or truncation. coverage.complete remains false: no topology/dependency
  acceptance or engineering policy approval is implied.
- coverage.fast_omissions: aggregated connector/detail/link NOT_INSPECTED_FAST
  statuses and applicable retained-element counts. Optional null Category reads
  are counted in expected_absences, not individual UNAVAILABLE issues. Required
  null values remain issues; exceptions retain type, context and safe traceback.
- summary.issue_counts_by_reason separates missing/unsupported/read errors.
  Confirmed defects, predicted risks and limits remain separate report fields.
- Detail and slope totals describe retained records; classification counts describe
  scanned supported records. Consumers must check schema, coverage and limits.
  Version 1 files are preserved and must not be silently interpreted as version 2.

Exactly-at-detail-limit can be covered if no further eligible record exists.
Over-limit records keep ledger evidence and name candidates or unknown_candidates.
The unchanged scan iterator deliberately does not peek: reaching exactly 10,000
scanned is still TRUNCATED_UNRESOLVED / scanned_elements, since exhaustion is not
proven. Other retained bounds: 60 cooperative seconds (including export-dialog
wait), 64 scope geometry objects, eight bbox corners per supported element,
4,096 text characters and 4 MiB serialized JSON. Temporary classification storage
is bounded by the 10,000 scan limit. A time/text/JSON stop writes no new report;
a synchronous blocking API call cannot be forcibly interrupted. FULL stays disabled.

### Offline validation

69 CPython tests pass, including 10 new scope coverage tests: outside independence,
exact/over detail caps, unknown budget, conservative scan cap, classification counts,
reverse-order determinism, omissions, actual read failures, unsupported categories,
Unicode/JSON bounds and mismatching document identities. Existing geometry, slopes,
iterator disposal, cancellation, cyclic direct references and static no-write tests
remain passing. No mock test proves Revit compatibility or complete Motor A coverage.

IronPython 2.7.12/.NET 8.0.22: all 11 diagnostic/test files compile; all 10 new tests
and existing Unicode encoder probe pass. Evidence runner/log:
C:\Users\Korisnik\AppData\Local\Temp\plegtvos-m11f-xrrk4hgx.
The first synthetic run used an integer fake clock, triggering an IronPython numeric
format error; the fixture now supplies a float like the real clock. Production
progress code was not changed. Protected scripts, native iterator and numerical
geometry/slope implementations are unchanged. git diff --check passes.

### Exact Revit 2025 FAST retest

1. Preserve the previous JSON; provide its full path for identity/issue review.
   Use the same authorized bim3dnapc6 RVT, without running an extractor or saving
   or synchronizing as part of this diagnostic. Do not substitute the historical RVT.
2. Reload the repository extension (restart Revit if needed to unload cached modules):
   C:\00_WORKS\DEVELOPMENT\PLEGTVOS_ModuleEngine\PLEGTVOS_ModuleEngine.extension.
   Verify the printed loaded path and IronPython 2.7.12/.NET 8 engine/build. Record
   source modification state, active view and selection before invocation.
3. Select only GC01 (verify ID 1405931 in this exact document), invoke GC01 Mirror
   Diagnostics, leave FAST enabled and FULL disabled. Record checkpoints/elapsed
   time/counts. Do not repeatedly launch if Revit stops responding; budget checks
   cannot interrupt an active Revit API call.
4. Export promptly to the existing diagnostic state location or a chosen evidence
   directory. Preserve the new immutable JSON and console output. On failure keep
   the complete traceback/stage/ElementId/field; no new report means no acceptance.
5. Verify schema /2, collector_version 1.1f, document.path/key/project UID, source
   scope UID/ID/frame/bbox, snapshot hash and source module hashes. Compare against
   the previous exact-source JSON, not the other model's historical extractor count.
6. Reconcile classification ledger totals with category exclusion counts and scanned
   instances. Check detail_retained, both detail budgets, slope totals for retained
   records, omitted FAST statuses, actual read errors and limits_reached. Complete
   supported inventory requires scope_inventory_complete=true; any cap/UNKNOWN/error
   remains unresolved. Overall complete=false and engineering risks are expected.
7. Verify unchanged model modification state, active view and selected IDs. Record
   runtime, evidence paths and any warnings. Obtain an already-existing independent
   extractor report from the exact RVT/revision if available; otherwise baseline
   comparison remains pending. Do not enable FULL or begin M1.2.

**M1.1 remains NOT ACCEPTED. M1.1f host test NOT RUN.**

## M1.1e Unicode serialization failure and correction - 2026-10-12

Latest user-reported host result: Revit 2025.3 / pyRevit / IronPython 2.7.12 /
.NET 8.0.22, Original Motor A, GC01 scope 1405931, FAST. Category setup passed all
18 names; collector/explicit element iterator initialization and first advance
passed. Approximately 7,800 elements scanned, 500 candidates classified, 433
slope-stage candidates inspected (not a claim of 433 measured pipes). Connector
traversal was correctly skipped. The previous generator failure did not recur.
**M1.1d iteration is verified in the actual Revit host along this tested path.**

Snapshot finalization failed at pre-change revit_reader.py:466 / collect,
diagnostic_core.py:186 / finalize, :170 / canonical, json.dumps and
json.encoder.py_encode_basestring_ascii:
`UnicodeDecodeError: 'unknown' codec can't decode byte 0xb0 in position 41`.
No external JSON report was generated. M1.1 remains unaccepted. Earlier Unicode,
>30-minute hang and category/iterator failures remain documented below.

### Exact defect and source uncertainty

Old normalized() handled floats and collection containers but left text unchanged.
Finalization sorted records via canonical() before any full-snapshot validation,
so a failure inside a sort key did not expose the parent array/field path.

A matching IronPython 2.7.12/.NET 8.0.22 probe establishes `str is unicode`. In the
2.7.12 standard library's py_encode_basestring_ascii, isinstance(s,str) combined
with an 0x80-0xFF character test calls s.decode('utf-8'). A proper Unicode degree
symbol reproduces the reported B0 decoding failure. This is a verified encoder
compatibility defect; it does NOT prove the original model stored byte strings
or establish CP1252. The exact Motor A field/value type remains unknown. No source
parameter value was guessed or normalized as a supposed legacy encoding.

### Text-bearing snapshot inventory

| Paths / fields | Collected source and boundary |
| --- | --- |
| document.title/path/project_info_unique_id/active_view_unique_id and GUIDs/key | Revit .NET strings plus explicit GUID/hash strings; no observed per-field type dump from failed run |
| source.scope_box and all ElementRefs (name/id/unique_id/key/document_key) | Revit names/UIDs and decimal ID/hash strings; includes type, level, host, group, assembly, design option and dependency refs |
| elements[].class/category/category_id/workset; location.kind/curve_type/endpoint_order | .NET type/category names, decimal IDs, and fixed diagnostic labels |
| elements[].family_type; parameters dictionary names/storage_type/units/value/status | Revit family/type names, fixed built-in parameter names, AsString text or numeric/bool/null values; detailed fields omitted in FAST |
| connectors/edges/systems | Owner/connector/system keys and reference IDs/names, API enum labels, type/classification/direction/shape, edge/method/status labels; skipped in FAST |
| coordinates.project_location/architectural_links refs; source/target/prediction/policy | Revit references and fixed space/unit/derivation/status labels, inclusion names and keys; geometry remains numeric |
| coverage/count ledgers/summary, issues and predicted_risks | Category names/IDs and fixed method/reason/code/field/exception-type labels, subject keys, limits/omissions; counts and flags remain numeric/bool |
| report envelope/run/safety and diagnostic pointer | Schema/feature/status/version/mode, timestamp, source/content hash, loaded path, engine/build, limitations and generated report filename |

Valid Python Unicode and supported System.String values are treated as text,
never byte-decoded. Native JSON integers, floats, booleans and null retain their
semantic types. Lists/tuples become new lists; dictionaries become new dictionaries.
Values may originate as .NET strings, but the host evidence did not capture which
specific field raised the error. No general str(value) conversion is added.

### Deterministic boundary and byte policy

- core.json_text makes a recursive copy before sorting. Valid Unicode is preserved;
  .NET strings are converted to Unicode when needed. Numeric values and IDs are
  not modified by this function. Existing twelve-decimal canonical float policy
  remains unchanged in normalized(); geometry/slope calculations are untouched.
- Real bytes decode only with explicit strict UTF-8. Unknown encodings are rejected,
  with no CP1252 guessing, replacement characters, dropped text or transliteration.
  Rejection gives complete JSON bracket path and array indices, type, attempted
  encoding, rejected outcome, byte offset, preview start and at most 16 hex bytes.
  Invalid dictionary keys use a parent path plus key-entry index. Key collisions
  after decoding also reject instead of overwriting data. No full parameter dump.
- IronPython's str.encode can itself produce an aliased System.String, not a real
  bytes instance. Such values are already text and remain unchanged; heuristically
  undoing apparent mojibake would corrupt legitimate Unicode. The runtime probe
  uses real b-prefixed bytes to test the UTF-8 policy unambiguously.
- Standard json encoding uses ensure_ascii=False after normalization, then the
  already-encoded JSON is escaped to ASCII without decoding its strings. Non-BMP
  code points use JSON surrogate pairs, not invalid Python \U escapes. Existing
  backslash/quote/control escapes remain intact. Sorted keys/separators and schema
  `plegtvos.gc01_mirror_diagnostic/1` remain unchanged. CPython equivalence tests
  compare canonical output against the former ensure_ascii=True contract.
- Control.canonical uses the same boundary and counts final escaped bytes against
  the existing JSON limit. Report storage calls these existing canonical entry
  points, so no separate schema or storage strategy change is required. Fatal
  unsupported text stops before an immutable report file is opened.

### Validation and evidence

59 offline tests pass: ASCII, proper Unicode, real UTF-8, degree, BCS/Dutch text,
nested dictionaries/lists/tuples, unknown legacy/invalid UTF-8 bytes, deterministic
serialization, immutable input, stable IDs/numeric types, key handling, full paths,
bounded encoder/storage rejection, ASCII escape equivalence and existing safety.
The original ASCII-encoder failure and corrected module behavior are exercised
under installed pyRevit IronPython 2.7.12/.NET 8.0.22. The probe uses a System.String
returned by System.String.Concat as well as real byte literals and Unicode.
Ten Python files compile under that runtime; no button is executed.

Reusable probe: tests/probe_gc01_json_ironpython.py. Standalone evidence:
`C:\Users\Korisnik\AppData\Local\Temp\plegtvos-m11e-e38adb42864b4357b036de83be7190e9`
(run_probe.py, net8.log, matching standard library). The runner is the M1.1d
standalone host. Standard library was obtained from the version-pinned
IronPython.StdLib 2.7.12 NuGet package because the bare engine has no library path;
this is not proof that the running host loaded byte-identical standard-library files.
An initial synthetic .NET Char-constructor setup failed; the probe was corrected
to use String.Concat without changing production code. Final probe exits 0 and
prints M1_1E_NET8_JSON_PROBE_PASS. No Revit model was accessed.

Static no-write, protected-script and git diff --check checks pass. AST comparison
confirms existing core functions other than canonical/finalize are unchanged,
including numeric normalization and all geometry/slope math. BoundedIterator is
unchanged from the M1.1d validated source. Existing uncommitted work is preserved.
No model transaction/write/selection/view change, save/sync, commit/push or M1.2.

### Exact M1.1e FAST host retest

1. Once no prior invocation is active, reload pyRevit. Verify the Plechtvos loaded
   path, updated source fingerprint and Revit 2025.3 / IronPython 2.7.12 / .NET 8.0.22.
2. In approved read-only Original Motor A, record model/view/selection/dirty/Undo
   observations. Select only GC01 and verify document-local ElementId 1405931.
3. Run FAST once, with FULL still disabled and all limits unchanged. Retain the
   iterator/progress output through snapshot finalization and Serialize JSON.
4. If JSON_TEXT_REJECTED occurs, preserve the full path/type/encoding/outcome/hex
   message and traceback literally. Do not change encodings or increase limits.
   An unexpected Unicode failure still needs full context; actual source is unknown.
5. On completion, export promptly to an approved external evidence folder or cancel.
   Preserve JSON/hash/fingerprint, mode/limits and truncation status. Verify the
   decoded degree/BCS/Dutch model names against Revit; JSON Unicode escapes are
   intentional and must round-trip. A capped report is not complete inventory.
6. Verify unchanged model/view/selection/dirty/Undo state. Record results and return
   console/report evidence for review. Do not enable FULL or mark M1.1 accepted
   based on this offline validation. No automatic save/sync.

**M1_1E_READY_FOR_FAST_RETEST**

## M1.1d bounded iterator runtime correction - 2026-10-12

Latest user-reported result: **FAILED_RUNTIME_ITERATOR_SETUP** in Revit 2025.3 /
pyRevit / IronPython 2.7.12 / .NET 8.0.22, Original Motor A, only GC01 selected,
ElementId 1405931, FAST. Validate selection, scope resolution, all 18 category
conversions, collector constructor and instance filter passed. The last checkpoint
was `instance_filter_after; bounded_generator_create_before`. Error:
`ValueError: must be reducible node`, pre-change `revit_reader.py:340` in collect.
Zero elements processed, no JSON, no model modification reported.

The exact statement was:
`bounded = self.control.items(collector, 'scanned_elements', checkpoint=self.candidate_checkpoint)`.
The checkpoint alone originally left creation versus advance uncertain. Subsequent
offline reproduction now isolates an actual compiler defect: executing the exact
source-extracted Control.items method with a Python list on installed pyRevit's
IronPython 2.7.12/.NET 8.0.22 fails before AFTER_GENERATOR_CALL. The .NET exception
is ArgumentException: must be reducible node, in GeneratorRewriter.VisitExtension,
GetGeneratorOrNormalLambda and LazyCompileFirstTarget. This reproduces without
Revit or a .NET enumerable, so iterator adaptation/MoveNext is not necessary to
trigger it. On .NET Framework the original probe passes. This confirms the helper's
runtime compatibility defect, not successful operation of the corrected Revit tool.

### Minimal mechanism change

Control.items now returns BoundedIterator, an ordinary class implementing next /
__next__ / __iter__, without yield. All uses of that shared helper retain local and
global counters, no look-ahead, conservative truncation and cooperative checks.
The candidate collector uses Control.element_items: GetElementIterator, Reset,
MoveNext and Current, avoiding Python adaptation of FilteredElementCollector.
Other bounded inputs retain their Python iteration protocol; no whole collector
is materialized. RevitAPI.xml installed with Revit 2025 documents GetElementIterator,
FilteredElementIterator.Reset/MoveNext/Current; a filter is applied before access.
The iterator is disposed when it supports Dispose. Exceptions, exhaustion and caps
close it; collect's finally also closes early breaks, then always disposes the
collector. Repeated close is idempotent. Time is checked before and after reads;
no check can interrupt an API call already in progress.

All 18 categories, instance filter, FAST default, FULL disabled gate, classifications,
slope/transform math, JSON schema, ordering and configured limits are preserved.
The new first-item checkpoints separate bounded_iterator_created, iterator get,
reset, first MoveNext and first Current. Earlier generator checkpoint labels below
are historical. No model-write API, selection/view change, background work or
save/sync was introduced.

### Offline evidence and limitations

- 50 diagnostic tests pass, including empty/single/native-style input, scan and FAST
  candidate caps, deterministic order, truncation, factory/reset/MoveNext/Current
  exceptions, time-budget propagation, no Python adaptation of native collectors,
  idempotent disposal and collector cleanup. Existing Unicode/safety tests pass.
- Nine files compile with IronPython 2.7.12 on .NET Framework and .NET 8.0.22.
- Source-extracted replacement methods execute successfully on .NET 8.0.22 with
  Python input and fake native enumerators. These are not Revit objects.
- Before/after standalone evidence is retained in
  `C:\Users\Korisnik\AppData\Local\Temp\plegtvos-m11d-feabad02d39d4423a2295fe28c91372c`
  (`before.py`, `before.log`, `after.py`, `after.log`, Probe.cs/exe/runtimeconfig).
  Before exit 1; after exit 0. The runner uses installed engine DLLs and Revit's
  System.CodeDom dependency; it does not load or operate a model. Initial runner
  dependency-resolution failures were resolved before obtaining the reproduction.
- Static no-write checks, protected-script/core-math preservation and git diff
  --check pass. Actual Revit collector/host acceptance still requires retest.

Previous UnicodeDecodeError, >30-minute hang and FAILED_RUNTIME_CATEGORY_SETUP
records are retained below. Unicode resolution is not claimed. M1.1 remains
unaccepted and FULL remains disabled. No commit/push or M1.2 work.

### Exact M1.1d FAST host retest

1. With no prior diagnostic still running, reload pyRevit. Verify loaded Plechtvos
   path and updated source fingerprint, Revit 2025.3, IronPython 2.7.12/.NET 8.0.22.
2. In the approved read-only Original Motor A fixture, record active view, selection,
   dirty state, Undo and model observations. Select only GC01; confirm ID 1405931.
3. Run once in FAST with unchanged limits and FULL disabled. Retain complete output:
   categories=18, collector/filter, bounded_iterator_created, element_iterator_get,
   reset, first_MoveNext, first_Current, then candidate counts/classification.
4. On error or stall, preserve last checkpoint plus full stage/field/ElementId and
   traceback. Do not automatically retry, increase caps, enable FULL or treat an
   active API call as forcibly timed out. Retain any Unicode failure literally.
5. If collection finishes, export promptly to an approved external evidence folder
   or cancel. Preserve JSON/hash, mode/limits/truncation status and source fingerprint.
   Truncated output is not complete inventory or mirror acceptance.
6. Verify unchanged model/view/selection/dirty/Undo state. Record actual outcome and
   return evidence for acceptance review; no automatic save or synchronization.

**M1_1D_READY_FOR_FAST_RETEST**

## M1.1c category_setup host failure - 2026-10-12

**FAILED_RUNTIME_CATEGORY_SETUP.** User-reported Revit 2025 FAST run in Original
Motor A with only GC01 selected (ElementId 1405931), loading
`C:\00_WORKS\DEVELOPMENT\PLEGTVOS_ModuleEngine\PLEGTVOS_ModuleEngine.extension`,
IronPython 2.7.12 on .NET 8.0.22. Selection/scope stages passed; candidate collection
was entered, then failed after approximately 5.3 seconds:
`ValueError: must be reducible node`, `revit_reader.py:321`, context category_setup,
ElementId None, field None. No JSON; no model edits reported. The prior
UnicodeDecodeError was not observed on this run but is NOT considered resolved.
The earlier >30-minute hang remains FAILED/HUNG. M1.1 remains unaccepted.

### Exact source finding and evidence boundary

Pre-change line 321 was:
`for element in self.control.items(collector, 'scanned_elements'):`.
The enum loop used `str(int(getattr(DB.BuiltInCategory, name)))` before the progress
line. Collector setup used
`DB.FilteredElementCollector(doc).WhereElementIsNotElementType()` before line 321.
There is no BuiltInCategory constructor, generic .NET collection construction or
LINQ operation here. Category preparation uses a fixed tuple and ordinary loop;
Control.items is a Python generator with iter(values), next(iterator), limits and
yield. Unrelated comprehensions elsewhere do not establish this error's cause.
The category_setup label remained stale until the first candidate loop body.

The failing source statement is identified; the responsible dynamic operation is
not. Generator compilation/entry, collector iterator adaptation and first advance
remain hypotheses, not confirmed causes. Do not replace enums, generators or
collector strategy speculatively. No supported numeric Revit category IDs are
hardcoded or changed.

### Instrumentation and regression checks

Reader.prepare_categories preserves the exact 18 supported names, iteration order,
str/int/getattr conversion, issue handling and string-ID mapping. This narrow
extraction lets tests supply enum-like values without invoking Revit. Its before/
after checkpoints bracket preparation; field context retains the category name.
Reader.candidate_checkpoint records stage candidate_collection_setup, field equal
to the exact operation and ElementId None until a candidate exists. Checkpoints:

1. collector_constructor_before
2. collector_constructor_after; instance_filter_before
3. instance_filter_after; bounded_generator_create_before
4. bounded_generator_created; first_iteration_before
5. bounded_generator_enter; collector_iter_before
6. collector_iter_after
7. collector_first_next_before
8. collector_first_next_after

The optional callback on Control.items affects only this collector's first advance;
all other call sites retain their behavior. Generator-body entry preceding iter is
particularly important: absence of checkpoint 5 after checkpoint 4 narrows the
boundary without proving a particular DLR defect. If iteration throws, the full
traceback plus current operation is retained. Progress is ASCII-safe and flushed
where supported. Counts, ordering, FAST/FULL limits, mathematical classification,
JSON schema and disabled FULL gate are unchanged.

Validation: 44 CPython tests pass, including five new checks for the exact supported
name set and expected synthetic string IDs, missing/unsupported values with issues,
deterministic classification mappings, checkpoint order, iter failure and first
next failure. Synthetic IDs deliberately do not claim to validate Revit's enum
constants. Nine Python files compile under installed IronPython 2.7.12 on .NET
Framework 4.8; str(int(System.DayOfWeek.Monday)) passes as a generic .NET enum smoke
check. Neither establishes Revit collector compatibility on .NET 8.0.22. Static
no-model-write checks and git diff --check pass. No live host test performed.

### Exact next FAST retest (supersedes prior instructions)

1. Once no previous diagnostic is running, reload pyRevit. Verify the loaded
   Plechtvos path, source fingerprint and IronPython 2.7.12/.NET 8 build. Do not
   start another workstream, raise limits or enable FULL.
2. In the approved read-only Original Motor A fixture, record view, selection,
   dirty state and Undo observations. Select only GC01; verify ID 1405931 locally.
3. Run once in FAST. Retain the entire console, from loaded path/engine through
   both category checkpoints and every collector/iterator checkpoint. On failure,
   capture the last checkpoint and complete traceback, stage, field and ElementId.
   Do not infer Unicode resolution or a successful fix from reaching a new stage.
4. If collection completes, export promptly to an approved external evidence folder
   or cancel. Preserve JSON/hash, limits, truncation status and any caught Unicode
   failures. Never treat truncation as complete coverage.
5. Verify unchanged model/view/selection/dirty/Undo state. Record the actual result
   and return evidence before any targeted workaround or FULL acceptance. No
   automatic save/sync; no hard timeout can interrupt a blocked API call.

Disposition: **M1_1C_INSTRUMENTED**. No verified runtime correction is claimed.

## M1.1b hang investigation and FAST retest - 2026-10-12

**FAILED/HUNG - user-reported Revit unresponsive for more than 30 minutes** after
selecting GC01 in Original Motor A and running Diagnostics. The previous
UnicodeDecodeError remains FAILED_RUNTIME, not resolved. No host stack, final
checkpoint or timing profile was supplied. Root cause is UNVERIFIED. No host
execution was performed during this implementation. All earlier successful-host
cases remain NOT RUN. This checkpoint supersedes the earlier retest instructions.

### Source audit and bounded behavior

| Area | Finding and change |
| --- | --- |
| Collectors | Previously one all-instance scan and one link scan, not a repeated whole-document scan per element. Both lacked limits. Now one capped lazy inventory scan; FULL alone runs a capped link scan. Collectors are disposed in finally blocks. No count-enumeration pass is added; unknown totals display `?`. |
| Detailed elements | Previously family/type/parameters/system/dependencies were read before scope rejection. FAST stops after identity, category, bbox, location and classification; FULL rejects OUTSIDE before detailed reads. GetElement results are cached by document-local ID for this invocation. |
| Connectors | No recursive network traversal was found. Eager list conversion of Connectors/AllRefs and repeated neighbor descriptors were potential hotspots. Iteration is now capped locally and globally; direct reference records are deduplicated by connector key. Neighbor AllRefs are never followed. Duplicate visits still consume budget so repetition cannot bypass limits. |
| Nested/dependent content | Only one-hop references were read, not recursive family expansion. FULL now caps subcomponent and dependent-ID iteration separately. Revit GetDependentElements itself may still block before yielding; FAST never calls it. |
| Geometry | Scope geometry has an object cap; element bbox work is eight transformed corners. No tessellation or geometry recursion is introduced. Individual get_Geometry/get_BoundingBox calls may still block. |
| Parameters | The existing fixed 12 built-in names remain bounded; no generic parameter enumeration. FULL may lower the cap. FAST skips parameter reads and uses unchanged endpoint slope math. |
| JSON | Repeated canonical sorting/serialization can be expensive. Collection size is capped; full report encoding uses incremental chunks with a 4 MiB cap and time checks before file creation. Individual encoder chunks/sorts and filesystem calls are not forcibly interruptible. Oversized values stop rather than silently replace text. |
| Errors/console | Existing escaped traceback/stage/element/field reporting is preserved. At most ten caught Unicode tracebacks are retained; the next stops collection. Progress uses ASCII-safe output with best-effort flush. Time/stop exceptions bypass field-error swallowing. |

### Modes, progress and limits

Default and currently only selectable host mode: **FAST**. It records bounded
scope/element inventory and basic pipe slopes. Connector metrics are null and
explicitly NOT_INSPECTED_FAST, never measured zeroes. Detailed parameters, family
orientation/dependencies and architectural-link inventory are omitted explicitly.
FULL preserves the in-scope detailed path with direct-only bounded references.
The button does not offer FULL while `execution_control.FULL_HOST_ENABLED=False`.
Changing that gate requires recorded/reviewed FAST host acceptance, not a user's
unverified confirmation at run time.

Limits are configurable in `execution_control.DEFAULTS` and via the offline
Control constructor. The FULL defaults override candidate/time limits only.

| Limit | FAST | FULL |
| --- | ---: | ---: |
| Whole-document instances visited | 10,000 | 10,000 |
| Supported-category candidates retained | 500 | 2,000 |
| Connectors total / per element | Not inspected | 1,024 / 32 |
| Direct reference visits total / per connector | Not inspected | 4,096 / 32 |
| Each dependency/subcomponent list | Not inspected | 32 |
| Scope geometry objects | 64 | 64 |
| Link instances | Not inspected | 32 |
| Built-in parameter names per element | Not inspected | 12 |
| Caught Unicode failures retained | 10 | 10 |
| Scalar model text characters | 4,096 | 4,096 |
| Serialized JSON ASCII bytes, excluding final LF | 4 MiB | 4 MiB |
| Cooperative elapsed budget | 60 seconds | 120 seconds |

Reaching an iterator cap is conservatively marked truncated without fetching an
extra item. A prefix is not a complete inventory and enumeration order is not a
cross-run matching contract. The report has `TRUNCATED_UNRESOLVED`,
`coverage.truncated=true`, explicit `limits_reached`, configured limits and counters.
All coverage remains incomplete regardless of caps because dependency closure and
mirror policy are unresolved. Time/text/JSON/cancellation stops do not fabricate a
partial success report; an export failure can leave an explicitly unaccepted file.
The time budget includes export-dialog wait. No UI cancellation is promised while
Revit is busy; a cancellation callback is supported at cooperative checkpoints.

Progress stages: Validate selection; Resolve scope box; Collect candidate elements;
Classify candidates; Inspect connector topology (skipped FAST); Inspect pipe slopes;
Calculate mirror preview (unapproved/no transform); Serialize JSON; Write report.
Each line includes elapsed seconds, processed count, known total or `?`, and current
ElementId or `-`. Stage entry is immediate; loops report every 100 items or two
seconds at a checkpoint. Output is flushed when the host stream supports it.
Progress timing is outside canonical snapshots. A blocked API call prevents the
next checkpoint/flush: **this is not a hard wall-clock timeout or UI responsiveness
guarantee**. All Revit access remains on the calling API thread; no workers/async.

### Exact safe FAST host retest

1. Do not start a second diagnostic while the earlier invocation is still active.
   Once Revit is recovered under the user's normal model-recovery procedure, reload
   pyRevit. Do not force-save/sync or run extractors/mirror/slope tools for this test.
2. Use the approved read-only Motor A fixture. Record Revit/pyRevit/IronPython builds,
   loaded Plechtvos command path, source revision/hash, view, selection, dirty state,
   Undo stack and relevant model observations. Preselect only GC01; verify its
   document-local ID (previously expected 1405931).
3. Run Diagnostics once. Confirm the console prints `GC01 diagnostic mode: FAST`,
   the intended loaded path and engine. FULL must not be offered. Retain every
   checkpoint, especially the last stage/count/ElementId if progress stops.
4. Expect either bounded completion/export choice, explicit truncation, or a
   cooperative stop with a traceback. Do not rerun automatically or increase caps
   to hide a stop. If no new progress follows the budget, a single API call may be
   blocked; preserve visible evidence and report FAILED/HUNG, not timeout success.
   Retain any Unicode traceback and escaped text literally.
5. On completion, export to an approved external evidence folder promptly (dialog
   wait counts toward the budget), or cancel to write nothing. Retain JSON, source
   fingerprint, content hash, mode, limits and truncation status. No truncated
   report is accepted as a complete module inventory.
6. Verify unchanged model, selection, active view, dirty state and Undo history.
   Record FAST acceptance only after reviewing progress, report/Unicode fidelity,
   all omissions/truncations and no-write evidence. Return these artifacts for
   review. FULL remains disabled until that acceptance is explicitly recorded;
   M1.1 overall acceptance remains open.

Offline validation: 39 tests pass, including cyclic/infinite references, large
collections, caps/truncation, FAST versus FULL, actual FAST detail skipping, cached
lookups, progress timing, cooperative stop propagation, Unicode failures and
bounded JSON. Six command modules and three test files compile with installed
IronPython 2.7.12. The static prohibited-write scan includes execution_control.
`git diff --check` passes. Core geometry/transform/slope math and all non-diagnostic
extension scripts remain unchanged. No commit, push or live Revit run.

**M1_1B_READY_FOR_FAST_HOST_TEST**

## Workspace-verified M1.1a checkpoint - 2026-10-12

Repository/root: `C:\00_WORKS\DEVELOPMENT\PLEGTVOS_ModuleEngine`; origin:
`https://github.com/BIM3DNA/PLEGTVOS_ModuleEngine.git`. All six workspace checks
passed before investigation. Entry main/HEAD was
`afd71060631faac89559aecf13c2dfeb582f87cd`, clean, with existing M1.1a instrumentation
already committed. Older uncommitted-state descriptions below are historical;
this task does not commit or push. No unrelated project was inspected or changed.

The fatal collection handler is `script.py`, immediately around `reader.collect`.
It calls `failure_diagnostics.failure_lines` and `emit`; `Reader.read` also retains
caught Unicode failures with stage, element ID and field. Full Python traceback
frames (filename, line, function) and exception type/message are escaped for ASCII
output without source-line/local-value dumping. This instrumentation was already
present at entry and is preserved. The supplied host excerpt cannot locate the
original throw site, so no model-string, serialization or global encoding change
is justified. The original failure remains FAILED_RUNTIME - UnicodeDecodeError;
host retest NOT RUN, M1.1 NOT ACCEPTED.

Revalidation: 26 CPython tests pass, including seven Unicode regressions and the
static no-model-write scan. The additional regression exercises actual emit calls
against a strict ASCII-only sink. Five diagnostic modules and both test files
compile with installed IronPython 2.7.12 (.NET Framework 4.8); a synthetic invalid
byte exception emits its traceback/context successfully under that engine. The
first standalone probe omitted its own sys import; correcting the probe resolved
that harness error without changing diagnostic source. Offline checks do not prove
Revit runtime behavior. `git diff --check` passes; executable extension bytes are
unchanged from entry, and existing non-diagnostic scripts match the M1.0 baseline.

Use the exact Revit retest procedure below. Capture the entire console, loaded
path and engine from the new invocation. Preserve the original no-JSON failure,
leave acceptance open, and stop for that evidence. **M1_1A_INSTRUMENTED**.

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

First host attempt: **FAILED_RUNTIME â€” UnicodeDecodeError**, reported by the user in Revit 2025 / pyRevit / IronPython 2.7.12, Original Motor A RVT, selected GC01 (expected ID 1405931). Button discovery after reload succeeded. Collection stopped before any JSON. The actual throw site is unknown; JSON serialization is not established as the cause.

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
