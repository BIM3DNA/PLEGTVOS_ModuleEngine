# PLEGTVOS ModuleEngine project state


## Sheet Transfer M1.1 evidence review - 2026-10-14

First preview host path succeeded (18 sheets, Motor A to unsaved Project1, no transfer).
Actual JSON confirms all 523 errors are Element.Name.GetValue descriptor AttributeError;
None names are read failures, not evidence that Revit names are absent. Corrected the
base descriptor getter; M1.1 host retest pending. Reports now use persistent LOCALAPPDATA
PLEGTVOS/SheetTransfer/reports with error summaries. The 239 unimplemented sheet-owned
objects include annotation candidates and dependencies; no transfer capability claimed.
See [evidence, counts and retest](docs/SHEET_TRANSFER_M1_1_HOST_REVIEW.md).
Both button copies are synchronized narrowly; existing original toolbar registration
unchanged. 35 tests pass under CPython and IronPython 2.7.12/.NET 8.0.22. GC01 paused and
unchanged; no M2/M3, transactions/model writes, commit or push. Earlier records below
are historical; use the original existing-toolbar path for all current host retests.


## Current checkpoint - Sheet Transfer M1 existing-toolbar integration, 2026-10-14

Sheet Transfer M1 preview is now installed in the existing registered extension at
`PLEGTVOS_ModuleEngine.extension/PLEGTVOS_ModuleEngine.tab/Dev.panel/Sheet_Transfer.pushbutton/`.
Only its seven independent Python modules were copied byte-identically from
`C:\00_WORKS\DEVELOPMENT\PLEGTVOS_ModuleEngine_sheet_transfer`.
No existing command, panel, tab or extension was replaced. The pyRevit registration
and isolated development worktree remain unchanged. No second extension/tab registered.

After pyRevit Reload, verify Sheet Transfer beside GC01 Mirror Diagnostics in the
existing PLEGTVOS Dev panel. Actual ribbon visibility and Revit host acceptance are
pending; no Revit session was controlled during integration. ALT-click the button
and verify the script is under this original checkout, not the isolated worktree.
Use two approved disposable open projects; choose source, destination, then sheets.
Confirm READ-ONLY PREVIEW ? NO ELEMENTS WILL BE TRANSFERRED. Check the report path,
conflicts/UNKNOWN/UNSUPPORTED entries, cancellation, unchanged source/destination
contents and no new model transaction/Undo item. Do not save/synchronize for this test.

All 27 existing M1 tests pass against the copied location in CPython and IronPython
2.7.12/.NET 8.0.22, including static no-write checks. Seven integrated modules compile;
sibling import paths and installed pyRevit forms are resolved statically. Actual
Autodesk/pyRevit imports remain a host check. No model-write/transfer API is introduced.
The existing GC01 files remain byte-identical; GC01 is PAUSED at M1.1h, FULL disabled.
M2-M4 Sheet Transfer development remains in the intact isolated worktree; none started.
No commit, push, reset, clean or stash. Prior state below is preserved as history.


## Current priority - SHEET_TRANSFER_M0 audit, 2026-10-14

OVT-style Sheet Transfer is the active priority. M0 is AUDIT_AND_PLAN_ONLY:
[audit](docs/SHEET_TRANSFER_M0_AUDIT.md) and
[implementation gates](docs/SHEET_TRANSFER_MILESTONES.md). Original source located at
`C:\BIM3DNA\BIM3DNA_API\BIM3DNARevitAPI\BIM3DNA.extension\BIM3DNA.tab\QuickFix.panel\Sheet Transfer.pushbutton\script.py`.
No executable port, transfer operation, Revit test, commit or push was performed.

GC01 Mirror Diagnostics is PAUSED at M1.1h. Preserve all tracked and untracked work.
M1.1g native filtered collection is host-verified on the recorded path; M1.1h batching
is implemented with 95 previously passing offline tests, not rerun for this audit.
M1.1h Revit host acceptance remains pending. FULL is disabled. M1.2 has not started.
The prior checkpoint and failure/acceptance history below remain unchanged.

Live Git at audit: main, HEAD afd71060631faac89559aecf13c2dfeb582f87cd,
origin https://github.com/BIM3DNA/PLEGTVOS_ModuleEngine.git. Existing dirty work is
preserved. Only this state update and the two Sheet Transfer documents are M0 changes.
The dedicated plan reprioritizes the historical M4 Sheet Transfer topic without
starting later mirror milestones. A separate implementation worktree is proposed,
not created; future implementation and model writes need their own authorization.

## Current checkpoint - M1.1h bounded FAST detail parts, 2026-10-14

Latest user-reported M1.1g Revit 2025.3 / IronPython 2.7.12 / .NET 8.0.22 evidence:
IGN_W-INS_Technische motor_A(R25)_bim3dnapc6.rvt, GC01 1405931, schema /3.
The native 18-category collector exhausted: 6,526 classified, 763 INSIDE,
5,763 OUTSIDE, zero CROSSING/UNKNOWN. Only 500 INSIDE details were retained;
263 were omitted. limits_reached=candidates; inventory_blockers=API_READ_ERRORS,
candidates. Runtime/export about 41.4 seconds. The 140 pipes, 113 measured slopes
and 23 vertical pipes belonged only to those 500 retained details. M1.1g filtering
and collector exhaustion are host-verified along this tested path, not whole M1.1
acceptance. Historical reports remain untouched. central_guid failed at
stage=document_identity with 'An internal error has occurred.'; its cause/type
is not established from that message alone.

M1.1h preserves the native collector, category set, iterator, classification and
Unicode implementation. FAST now retains eligible details up to the unchanged
10,000 scan bound and processes/exports them in stable-key batches of at most 500.
The existing candidates=500 value is explicitly a PER_FAST_DETAIL_BATCH bound,
not a total cap. UNKNOWN retains its separate 500 cap. No higher scan/time/JSON
limits or FULL access. FAST basic detail data was already read during classification;
there is no extra collector pass per batch. Revit references remain bounded by the
scan cap, not accumulated without limit.

Schema /4 introduces immutable plan.json, hashed part-NNNN.json files and a final
manifest.json, each bounded to 4 MiB (plus its newline). A 763-record qualified run
plans 500+263 records. Manifest completeness is published only after read-back
validation, exactly-once ID accounting and hash checks. Classification, element
details, pipe/slope details, topology, source identity and mirror readiness have
separate statuses. Connector topology remains NOT_INSPECTED; mirror UNRESOLVED.

Continuation is manual through Continue incomplete bundle / plan.json. It requires
an already saved, unmodified, non-cloud RVT; matching memory/disk DocumentVersion
GUID and save count; whole-file SHA-256; project UID; and identical source/scope/
geometry/categories/code/schema/ledger, inventory evidence and every planned detail
hash. Qualification runs before and after collection. Version GUID alone is not
sufficient. Changes, corrupt partial files or unqualified identity fail closed,
without overwriting evidence. If time expires before a plan is written, nothing
can resume. Each invocation keeps the 60-second cooperative budget; no automatic
commands, saves or sync. File hashing adds host performance work still to validate.

For a positively identified non-empty non-server central ModelPath, central GUID
is NOT_APPLICABLE_NON_SERVER_CENTRAL and the unsupported GUID getter is not called.
Independent saved-source qualification supplies identity evidence. Unexpected path
or applicable server-GUID exceptions remain READ_ERROR with traceback and block
completeness. The historical internal error is not reclassified or erased.

Validation: 95 CPython tests; 36 coverage/filter/batch tests and Unicode probe on
IronPython 2.7.12/.NET 8.0.22; all 15 Python files compile. Tests cover boundaries,
exactly-once/missing/duplicate records, pipe coverage, continuation mismatches,
corrupt/partial files, hashes, interruption, budgets, Unicode and central metadata.
Static safety, protected-script and preserved collector/iterator/classification/
Unicode checks and git diff --check pass. Evidence directory:
C:\Users\Korisnik\AppData\Local\Temp\plegtvos-m11h-4u_03_mm.
Actual BasicFileInfo/version qualification and multipart export remain host-unverified.
M1.1 is NOT ACCEPTED. No commit, push, FULL enablement or M1.2 work.

## Historical M1.1g native MEP filtering, 2026-10-14

User-reported M1.1f host result: Revit 2025.3 / IronPython 2.7.12 / .NET 8.0.22,
IGN_W-INS_Technische motor_A(R25)_bim3dnapc6.rvt, GC01 1405931, schema /2.
10,000 document instances: 1,552 supported candidates (460 INSIDE, 1,092 OUTSIDE,
zero observed CROSSING/UNKNOWN), 8,448 unsupported instances across 65 category IDs.
460 INSIDE details retained; JSON export in 12.8 seconds. TRUNCATED_UNRESOLVED /
scanned_elements; scan_exhausted=false; scope_inventory_complete=false. These are
partial document counts. A central_guid read error was also observed. Original /2
JSON remains external and untouched; no new Revit execution was performed here.

M1.1g adds native ElementMulticategoryFilter with explicit List[BuiltInCategory],
all original 18 categories, and WhereElementIsNotElementType before the preserved
GetElementIterator/Reset/MoveNext/Current path. Missing/mismatched categories or
filter errors stop collection; no partial-set or unfiltered fallback. Limits and
classification/slope/Unicode behavior remain unchanged. Revit-object storage is
bounded by 10,000 inspected instances; no unbounded collector materialization.

Schema /3, collector_version 1.1g: scanned_elements explicitly means supported-
category instances inspected. Unsupported inventory is NOT_INSPECTED_BY_FILTERED_COLLECTION
with null totals rather than zero. Duplicate IDs/keys are not counted twice and
remain coverage blockers. scan_exhausted records actual native MoveNext=false.
At the scan cap exhaustion remains conservatively unproven without an extra advance.
Explicit inventory_blockers cover limits, unproven exhaustion, invalid frame,
UNKNOWN, API errors, category anomalies, missing identities and duplicates.

Installed Revit 2025 API documentation says WorksharingCentralGUID requires a
qualifying Revit Server central; a file-based central can legitimately raise
InapplicableDataException. The host exception type was not supplied. The observed
read error is preserved with context/traceback and central_guid_status=UNAVAILABLE;
no GUID substitution. It still blocks completeness even if collection exhausts.

Validation: 81 CPython tests; 22 coverage/filter tests, Unicode and real CLR enum/List
probes on IronPython 2.7.12/.NET 8.0.22; 12 Python files compile. Static safety,
protected-script and unchanged algorithm/limit checks, plus git diff --check pass.
Real Revit filter execution remains NOT host-validated. Evidence directory:
C:\Users\Korisnik\AppData\Local\Temp\plegtvos-m11g-y5j_k0ug.
See acceptance notes for retest and conditional continuation proposal. No commit,
push, FULL enablement or M1.2 work. M1.1 remains NOT ACCEPTED.

## Historical M1.1f scope-first FAST coverage, 2026-10-12

Latest user-reported M1.1e FAST host run succeeded: 7,853 document instances
scanned, 500 inventoried (433 INSIDE, 67 OUTSIDE), 98 pipes, 72 measured slopes,
22 vertical pipes, JSON exported in approximately 11.5 seconds. Result was
TRUNCATED_UNRESOLVED (candidate cap); no write API/transaction reported invoked.
This verifies the tested iterator/Unicode export path, not complete scope coverage
or every Unicode boundary. M1.1 remains NOT ACCEPTED; FULL remains disabled.

The diagnostic RVT is IGN_W-INS_Technische motor_A(R25)_bim3dnapc6.rvt.
Historical extraction used IGN_W-INS_Technische motor_A(R25)_e.avdovicQREF7.rvt.
They are NOT qualified as the same document/revision. The successful JSON was not
attached or found in the repository/default AppData diagnostic location; its path
was requested. Exact source path, document key, scope UID/frame and snapshot hash
remain UNVERIFIED. GC01 / ElementId 1405931 is prior user-provided scope evidence.
No exact-RVT independent extractor report is available; baseline comparison PENDING.
No historical count is used as an oracle. The reported 4,734 issue entries have
not been independently categorized without that JSON.

Code now classifies supported candidates during the bounded document scan before
applying detail budgets. OUTSIDE evidence goes to a compact stable-identity ledger;
INSIDE/CROSSING share 500 retained details, UNKNOWN has a separate 500-detail cap.
All scanned supported classifications are counted, including over-budget records.
Unsupported/no-category instances are counted separately. Selection of retained
records is stable-key ordered. Actual over-budget details mark the named resource;
exactly 500 details are not truncated unless another eligible record exists.
The original native iterator, geometry/slope math and Unicode encoder are preserved.

Schema is plegtvos.gc01_mirror_diagnostic/2: elements contains retained non-outside
details; coverage.classification_ledger contains all supported scanned identities
and memberships. Explicit scope_inventory_complete differs from complete=False
for the whole unresolved diagnostic. FAST omissions and optional category absence
are aggregated; required missing data and actual read errors remain detailed.
Read errors now retain stage/element/field and ASCII-safe traceback.

Bounds remain 10,000 scanned instances, 60 cooperative seconds, 64 scope geometry
objects, eight bbox corners per supported instance and 4 MiB final JSON, with the
existing text/connector/reference limits. Classification storage is bounded by the
scan cap. At the scan cap exhaustion is conservatively unproven (no extra native
MoveNext). Budget expiry or oversize JSON stops without a new report; an API call
cannot be forcibly interrupted. All other limitations remain documented below.

Validation: 69 CPython tests pass; 10 new coverage tests and the existing Unicode
probe pass on IronPython 2.7.12/.NET 8.0.22; all 11 diagnostic/test Python files
compile there. Static safety, protected-script comparisons and git diff --check
pass. No Revit execution, model write, commit, push, FULL enablement or M1.2 work.
M1.1f host retest and external JSON identity review remain pending. See the acceptance
ledger for exact retest and schema compatibility requirements.

## Historical M1.1e Unicode serialization boundary, 2026-10-12

Latest user-reported host evidence: Revit 2025.3, IronPython 2.7.12/.NET 8.0.22,
Original Motor A, GC01 1405931, FAST. All 18 categories, collector and explicit
iterator setup/advance passed. Approximately 7,800 elements were scanned, 500
candidates classified and 433 slope-stage candidates inspected; connectors were
correctly skipped. **M1.1d iteration is host-verified along this tested path.**
This does not accept the whole diagnostic or FULL mode.

Snapshot finalization failed: revit_reader.py:466 -> diagnostic_core.py:186
(finalize) -> :170 (canonical) -> json.dumps -> py_encode_basestring_ascii.
UnicodeDecodeError: unknown codec, byte 0xB0 at position 41. No external report
was generated. Offending model field/its original runtime type is not established.
M1.1 remains NOT ACCEPTED; all earlier failure records are preserved below.

Matching-runtime reproduction shows str is unicode in this IronPython engine.
The standard JSON ASCII encoder mistakes a proper Unicode degree symbol for
byte text and calls decode('utf-8'), reproducing the B0 failure without any legacy
model bytes. The observed B0 therefore does not prove CP1252 source data.

Added text-only recursive normalization before snapshot sorting/canonical encoding.
Unicode/.NET strings are preserved, real byte values decode strictly as UTF-8,
unknown byte encodings fail with complete path/type/encoding/outcome and at most
16 preview bytes in hex. No CP1252 fallback, replacement or transliteration.
Serialization uses the standard Unicode JSON encoder followed by JSON-compatible
ASCII escapes (including surrogate pairs), avoiding the faulty ASCII path. Schema,
canonical ordering and existing numeric normalization are unchanged. Finalization
now works on a copy; no original snapshot mutation. Shared bounded encoding uses
the same text policy. Iteration, category/classification/slope/connector logic,
FAST/FULL limits and disabled FULL gate are unchanged.

Validation: 59 offline tests pass. The actual serialization modules pass the
IronPython 2.7.12/.NET 8.0.22 probe with Unicode/UTF-8/.NET strings, degree/BCS/Dutch
text, nested data, stable IDs/numeric types and precise rejection of unknown bytes.
Ten files compile on that runtime. Static no-write checks, protected-script and
iterator/math preservation checks, and git diff --check pass. Host retest remains
NOT RUN; no live Revit execution, commit, push or M1.2 work.
**M1_1E_READY_FOR_FAST_RETEST**.

## Historical M1.1d bounded iterator correction, 2026-10-12

Latest host result: **FAILED_RUNTIME_ITERATOR_SETUP**. Revit 2025.3, IronPython
2.7.12/.NET 8.0.22, Original Motor A, GC01 1405931, FAST. All 18 categories,
collector construction and instance filtering passed. Last checkpoint:
`instance_filter_after; bounded_generator_create_before`; ValueError: must be
reducible node at pre-change revit_reader.py:340. No elements/JSON; no model
modification reported. Previous Unicode, >30-minute hang and category_setup
failures remain recorded. M1.1 remains NOT ACCEPTED.

Confirmed OFFLINE defect: the unchanged Control.items generator reproduces the
same reducible-node error at generator creation with a plain Python list using
installed pyRevit IronPython 2.7.12/.NET 8.0.22. The stack enters GeneratorRewriter
before the generator returns. No Revit collector/API/model is needed to reproduce.
The same probe passes on .NET Framework. This distinguishes the demonstrated
compiler defect from speculation about category enums or first MoveNext.

Replaced only bounded iteration: Control.items now returns a non-generator class;
candidate collection uses GetElementIterator/Reset/MoveNext/Current with cleanup.
Revit 2025 installed API XML confirms those operations. Normal/exception/limit
completion closes the iterator; the caller closes it on candidate-cap break before
disposing the collector. No eager list, threading, limit removal or other strategy
change. All original supported categories, filtering, classification/math, FAST
and FULL gate, schema and ordering remain unchanged.

Validation: 50 offline tests pass. Nine Python files compile under IronPython
2.7.12 on both .NET Framework and .NET 8.0.22. The replacement source-extracted
methods pass Python-input and fake native-enumerator execution on .NET 8;
old helper fails there (before exit 1 / after exit 0). Static no-write and git diff
--check pass. Real Revit collector execution/retest remains NOT RUN; the Unicode
issue is not declared resolved. Only execution_control.py, revit_reader.py,
tests/test_gc01_execution.py and the two checkpoint documents changed in M1.1d.
All earlier local changes are preserved. No commit/push or M1.2 work.
**M1_1D_READY_FOR_FAST_RETEST**.

## Historical M1.1c category/iterator boundary instrumentation, 2026-10-12

**FAILED_RUNTIME_CATEGORY_SETUP; M1.1 NOT ACCEPTED.** Latest user-reported FAST
run: Original Motor A, GC01 ElementId 1405931, intended repository extension,
IronPython 2.7.12 on .NET 8.0.22 / Revit 2025. Validate selection and Resolve scope
box passed; Collect candidate elements was entered. At about 5.3 seconds,
`ValueError: must be reducible node` was reported at pre-change
`revit_reader.py:321`, context category_setup, ElementId/field None. No JSON was
written; no model edits were reported. Earlier UnicodeDecodeError and >30-minute
unresponsive Revit failures remain recorded and unresolved.

The exact line was `for element in self.control.items(collector, 'scanned_elements'):`.
Category conversion and collector/filter setup precede it. Context category_setup
was stale until the first element reached the loop body. Root cause is NOT
CONFIRMED: entering the IronPython generator or adapting/advancing the Revit
collector iterator are hypotheses. No LINQ or .NET generic collection creation
occurs at this boundary. No enum or collector strategy workaround was justified.

Added operation-level checkpoints and accurate candidate_collection_setup context.
Category preparation is isolated for tests with its original name order/conversion
unchanged. New checkpoints cover constructor/filter, generator creation/body entry,
iter(collector), and first next(iterator). Limits, classification, schema, report
ordering and FULL gate remain unchanged. M1.1c changes only revit_reader.py,
execution_control.py, tests/test_gc01_execution.py and these two checkpoint docs;
all earlier uncommitted work is preserved.

Validation: 44 offline tests pass, including supported-name/synthetic-ID mapping,
unsupported/missing enums, deterministic preparation and iterator failure context.
Nine files compile with installed IronPython 2.7.12 on .NET Framework 4.8. Generic
.NET enum conversion also passes there; actual Revit enums/collector behavior on
.NET 8 are not established by those checks. Static no-write and git diff --check
pass. No live Revit execution, commit, push or M1.2. **M1_1C_INSTRUMENTED**.

## Historical M1.1b bounded diagnostics, 2026-10-12

**Host acceptance FAILED/HUNG; M1.1 NOT ACCEPTED.** User reports GC01 Mirror
Diagnostics left Revit 2025 unresponsive for over 30 minutes in Original Motor A.
The earlier UnicodeDecodeError remains unresolved; no supplied stack proves either
failure's cause, and absence of a new Unicode error does not establish a fix.

Verified workspace/root/remote remain Plechtvos. Entry main was
`afd71060631faac89559aecf13c2dfeb582f87cd`; the three M1.1a modified files were
preserved. No unrelated repository or production toolbar was accessed.

M1.1b adds a single-threaded execution controller and phased progress, capped
candidate/connector/reference/dependency processing, cached element lookups,
deduplicated direct references, bounded serialization and cooperative stopping.
FAST is the only enabled host mode: scope/inventory and basic slopes, without
connector managers, reference traversal, detailed parameters/dependencies or link
inventory. FULL is implemented and tested offline but remains gated by
`FULL_HOST_ENABLED=False` until FAST host acceptance is recorded and reviewed.
No mirror/transform/slope mathematics or existing write command was changed.

Count caps produce explicitly truncated, incomplete reports. Time, cancellation
callback, oversized text/JSON and repeated Unicode errors stop at checkpoints;
fatal collection stop writes no report. No timeout forcibly interrupts an active
Revit API call. Root cause remains unverified; see the hotspot audit, exact limits
and safe retest procedure in `docs/M1_1_HOST_ACCEPTANCE.md`.

Validation: 39 offline tests, nine IronPython 2.7.12 syntax compilations, static
no-model-write checks and git diff --check pass. These are offline results only.
Protected extension scripts and diagnostic math are unchanged from entry. No
Revit host execution, transaction, selection/view change, model save/sync, commit
or push was performed. **M1_1B_READY_FOR_FAST_HOST_TEST**.

## Historical M1.1a workspace-verified retest preparation, 2026-10-12

Verified workspace and Git root: `C:\00_WORKS\DEVELOPMENT\PLEGTVOS_ModuleEngine`;
origin fetch/push: `https://github.com/BIM3DNA/PLEGTVOS_ModuleEngine.git`.
The project rules, extension and GC01 diagnostic button are present. Entry branch
was `main`, HEAD `afd71060631faac89559aecf13c2dfeb582f87cd`, with a clean index and
worktree, matching the local origin/main tracking reference (no fetch performed).
M1.1/M1.1a files are already tracked in this commit; older statements below that
describe them as uncommitted are historical. No existing local changes were lost.

Reverified the existing traceback instrumentation; no production Python change or
speculative encoding correction was necessary. Added an ASCII-only console sink
regression for failure emission. All 26 offline tests pass (19 original plus seven
Unicode regressions), including the static no-model-write scan. Seven Python files
compile using installed IronPython 2.7.12. Synthetic invalid-byte traceback emission
passes under that engine; an initial standalone probe invocation lacked its own
sys import, which was corrected in the probe only. This is not host reproduction.

Only this document, `docs/M1_1_HOST_ACCEPTANCE.md` and
`tests/test_gc01_unicode.py` changed in this task. Executable extension files,
extractors, mirror/transform/slope code remain unchanged. No live Revit invocation,
model writes, selection changes, commit, push or M1.2 work. Root cause still needs
the Revit traceback; M1.1 is not accepted. **M1_1A_INSTRUMENTED**.

## Historical M1.1a instrumentation checkpoint, 2026-10-11

**FAILED_RUNTIME - UnicodeDecodeError. M1.1 is not accepted.** User-reported first run: Revit 2025 / pyRevit / IronPython 2.7.12, Original Motor A RVT, GC01 scope box (expected ElementId 1405931). Button appeared after reload, but collection failed and no JSON was generated. The original handler discarded the message and traceback; the actual failure boundary remains unknown.

M1.1a adds failure-only protected traceback output with stage, element ID and field, including caught Unicode read failures. No model text normalization, schema, classification, connector, scope or slope changes. See the [exact retest procedure](docs/M1_1_HOST_ACCEPTANCE.md#m11a-runtime-investigation-and-retest). Root cause is not established; disposition is M1_1A_INSTRUMENTED.

Validation: 25 offline tests pass; seven Python files compile with IronPython 2.7.12; a synthetic invalid-byte exception renders successfully under that engine. This does not reproduce the original host failure. Retest NOT RUN. No commit/push or M1.2 work.

## Historical M1.1 implementation checkpoint - 2026-10-11

M1.0 documentation was committed and normally pushed as `ba692cd913aab8eb9d5e77aa519696454fc75fed`; M1.1 began on clean `main` at that revision. The authorized independent **GC01 Mirror Diagnostics** button is implemented with four isolated Python files, bundle metadata and offline tests. Existing capture, placement, mirror, slope, state and extractor scripts remain unchanged. M1.1 changes are unstaged and uncommitted; no push was performed.

Exactly one preselected scope box is required. The collector records conservative scope membership, physical MEP inventory, connector references, endpoint slope measurements, API issues and unresolved risks without model writes. Export is explicitly chosen: immutable JSON plus a dedicated diagnostic-only latest pointer under the state/reporting convention or an external root. Extractor acceptance records are untouched.

Schema: `plegtvos.gc01_mirror_diagnostic/1`. Missing approved mirror anchors yields `MIRROR_FRAME_UNCONFIRMED`; hydraulic compliance and open-port intent remain UNKNOWN. Full dependency closure, non-shared family content, durable fixture comparison and target prediction remain unresolved. There is no mirror acceptance claim.

Validation: 19 offline tests passed, including pure transforms/classification/slopes, identity, deterministic JSON, storage failures and static prohibited-API scanning. Four implementation files and the test file compiled with IronPython 2.7.12. Documentation and whitespace checks are recorded in the [M1.1 host procedure and ledger](docs/M1_1_HOST_ACCEPTANCE.md). **All 12 host cases are NOT RUN.** Reload pyRevit and verify loaded source/engine on an approved disposable fixture. No repair or later milestone is started.

## Historical M1.0 checkpoint - 2026-10-11

The following preserves the audit-time record; its unstaged/untracked and proposed implementation statements are superseded by the current checkpoint.

**M1_0_AUDIT_COMPLETE.** M1.0 is source analysis and documentation only. M1.1 implementation has not begun. Read the [GC01 mirror audit](docs/M1_GC01_MIRROR_AUDIT.md) for the actual recovered architecture, line-level findings, proposed diagnostic JSON and Revit 2025 acceptance matrix.

- Verified entry state: branch `main`, clean worktree/index, HEAD `97d269ab009cea71528f4532bc1788874f7139ed`; live GitHub main advertised the same SHA.
- Correct remote: `https://github.com/BIM3DNA/PLEGTVOS_ModuleEngine.git`. M0.1 stopped on the local documentation commit's divergence. Authorized M0.2 then rebased `72b68e8a` onto `f56f0ff`, producing `97d269ab`, and the subsequently approved normal push completed. The eight remote implementation commits and extractor scripts are now present locally.
- M0.2 preserved all six documentation files and verified the full executable extension against `origin/main` at `f56f0ff`; syntax-only compilation passed for 31 files under IronPython 2.7.12. Those were offline checks, not Revit model acceptance. M1.0 also confirmed executable extension equality to `f56f0ff`.
- Verified M0.2 backups: branch `backup/pre-m0-rebase-72b68e8`; complete Git bundle `C:\Users\Korisnik\AppData\Local\Temp\PLEGTVOS-M0.2-250c605f13bd4c159532f972b509a44d\pre-m0-rebase.bundle`. No new backup was needed for documentation-only M1.0.
- M0.2 configuration and cached runtime assembly inspection identified the repository extension `C:\00_WORKS\DEVELOPMENT\PLEGTVOS_ModuleEngine\PLEGTVOS_ModuleEngine.extension`, with no duplicate Plechtvos source in configured roots. Reload was required to discover recovered buttons; completion of that reload and a new command invocation have not been observed here.
- The existing README/M0 audit below describe earlier snapshots. Their absent-extractor/eight-commits-behind statements no longer describe current Git. Historical files/evidence remain preserved; this checkpoint supersedes their current-state implications.

### Current findings and remaining gates

Verified source findings include post-commit pin restoration; unisolated mirror fallback attempts; partial group assimilation; wrong ViewSection/CopyElements API calls; unvalidated rotated-scope axes; stale integer-ID state binding; reconnection not gating slope success; and counters recorded before outer transaction commit. The main slope loop does not attach its defined failure preprocessor, and its component builder is unused. Existing capture/slope commands are not read-only diagnostic entry points.

These findings do not establish the actual cause of GC01's reported missing fittings, roof plates, cyan pipe damage, elbow/reducer orientation or reversed drainage. Those remain hypotheses pending a fixture, exact element/connector observations and approved transformation rules. No existing host success/failure report was replaced.

Historical extraction evidence is retained below: GC01/02/04/06/07/08 were user-reported successes; the M0.1 brief specifically described GC12 as visually successful. No new host tests were performed during M0.2 or M1.0. All new matrix cases are NOT RUN.

Alen/Emir decisions: approve L/R direction, mirror plane/anchors and center-versus-adjacent face placement; source/target GC01 fixtures; allowed boundary ports; VWA/HWA slope and flow/anchor rules; family/nested/host/group/assembly inclusion and handedness; geometric tolerances; target system identity; drawing/prefab codes and approval ownership. Existing code ratios .0075/.005 are not substituted for design approval.

### Current next action and backlog

After separate authorization, **M1.1 should implement only an independent read-only GC01 collector and deterministic JSON report**, with explicit unavailable/ambiguous data and no transaction, regeneration, isolation, geometry or connector manipulation. Do not import existing write buttons or change their behavior. Validate no-write behavior and report determinism in Revit 2025 before considering repairs. Prediction may remain UNRESOLVED until the team approves frames/tolerances; observation collection must not guess them.

Then use the evidence to propose the smallest separate mirror/MEP repair scope. M2 drawing register, M3 sheets, M4 transfer, M5 linking QA and M6 variants retain their existing order and approval gates. Extractor behavior remains protected throughout.

M1.0 change scope: PROJECT_STATE.md, docs/MILESTONES.md and new docs/M1_GC01_MIRROR_AUDIT.md only. No automatic commit/push, Python modification, Revit transaction, RVT generation or model write. Validation passed for six links/anchors, JSON skeleton, 17 finding and 14 test references, whitespace, exact change scope and `git diff --check`. Historical M0 state text and existing evidence files are preserved; the new audit remains untracked and changes are unstaged.

## Historical M0 record â€” preserved, superseded for current state

The following text records the M0 checkpoint before reconciliation. Its branch status, pending next action and file-status statements are historical, not the current state above.

Audit date: 2026-10-11, Europe/Sarajevo. Active milestone: **M0 repository audit and project bootstrap**. Implementation remains stopped after M0.

## Verified repository state

- Workspace: `C:\00_WORKS\DEVELOPMENT\PLEGTVOS_ModuleEngine`.
- Branch `main`; HEAD `a10c8575e8c4e196a7734e7031d616bfa33ce9b1`.
- Initial worktree clean: 48 tracked files, no non-ignored untracked files or staged changes. Ignored `venv/` is present and was preserved.
- Configured origin is `https://github.com/Emin-A/PLEGTVOS_ModuleEngine`. Live queries to it and the supplied `https://github.com/BIM3DNA/PLEGTVOS_ModuleEngine` returned the same `main`/HEAD: `f56f0ffe530032e78b3571f2b2637093d2686058`. This establishes equal advertised tips, not an ownership/redirect decision.
- After fetching origin, local is **0 ahead / 8 behind**. No merge, checkout update, commit or push was performed. The extractor buttons are absent locally but present at that remote revision.
- Sheet-Generator `main` was inspected at `2665476d3e95cbc48464b214d1e293346b867f26` using fetched Git objects under `refs/audit/sheet-generator-main`; no reference code was copied into the extension. Reference fetches changed only this repository's Git metadata.
- Final M0 scope is README replacement plus five new Markdown files: this file, `AGENTS.md`, `docs/M0_AUDIT.md`, `docs/MILESTONES.md`, and `docs/meetings/2026-10-11.md`. Existing `docs/AI_TASKS.md` is preserved.

See [M0 audit](docs/M0_AUDIT.md) for the complete command inventory, source references, engine configuration, reference implementation gap matrix and defects versus hypotheses.

## Host acceptance evidence

| Evidence | Status and boundary |
| --- | --- |
| GC01, GC02, GC04, GC06, GC07, GC08 extraction | Validated according to the supplied user brief. Original host reports, model identities and per-module revisions were not supplied or found in the tracked audit inputs. Not rerun in M0. |
| GC12 extraction | Also reported successful in the brief; same missing-artifact boundary. |
| Commit `c0eb8cf` | Historical author report of extraction success on GC01/GC04 and further GC02/GC06 testing needed at that time. The later user brief reports a broader accepted set; retain both chronologically. |
| Commit `f56f0ff` and source | Detached RVT output verification implemented. Reopened classifier acceptance requires saved/reopened output, positive inside count, zero outside/unknown, bounded non-MEP crossing, no failed/protected deletions. This is code evidence, not a new host run. |
| Mirror/slope history | Author reports range from partial results and broken objects to later success claims. No reproducible connector/slope/coordinate evidence closes GC01 reliability. |
| M0 | No Revit button executed, model written, RVT generated or host acceptance claimed. |

The extraction acceptance report's `source_unchanged: True` is a literal assertion; M0 did not independently measure source invariance. Model dependency, connector, linking and drawing QA remain separate gates.

## Prioritized backlog

1. Reconcile the local checkout with the audited remote baseline through an explicitly authorized integration step, preserving the M0 docs and extractor bytes. Verify the actual loaded extension path/engine and attach historical extraction evidence.
2. M1: reproduce GC01 left/right failures and collect read-only connector, fitting, missing-object, slope and coordinate diagnostics before choosing fixes.
3. M2: approve left/right drawing register, code uniqueness scope and revision/variant semantics.
4. M3: review Emir's actual prefab examples and adapt Sheet Generator against approved families, tags, schedules and layout.
5. M4: adapt OVT transfer with explicit document/type mapping, coordinate checks, collision policy and rollback.
6. M5: validate extracted-module dependencies and architectural linking without changing the proven extraction algorithm incidentally.
7. M6: implement only the selected building-specific options/variant workflow after its contract is approved.

Full objectives, expected files, non-goals and Revit 2025 acceptance gates: [milestone plan](docs/MILESTONES.md).

## Blockers and unresolved decisions

These are implementation/acceptance blockers, not missing M0 inspection work:

- **Baseline:** installed configuration points to this stale checkout. A future loaded host session and the intended integration baseline must be verified before reproducing or changing behavior.
- **Evidence:** original extractor reports and a disposable GC01 reproduction fixture are unavailable in the supplied inputs. Historical success cannot be independently reaccepted from commit text.
- **Alen/Emir:** confirm who approves mirror orientation, anchor/flow direction, VWA/HWA slopes, drawing codes and layout. The brief assigns no named owner or due date.
- **Emir review:** obtain representative left/right sheet, plan/3D, tags, schedules and nested-family parameter examples; the reference script is not proof that it matches Emir's current workflow.
- **M2:** decide project/building/module/handedness/revision code scope, duplicate/rerun behavior and whether Comments remains the authoritative field.
- **M3/M4:** agree template/title-block/tag/schedule mappings and transfer content expectations. OVT currently has cross-document ID, scope/crop and partial-commit defects.
- **M5/M6:** decide link placement convention and the selected building-specific modification workflow; no approval to move architectural coordinates or generate variants exists.

No meeting transcript or separate bootstrap drafts were supplied. Meeting notes explicitly distinguish the supplied requirements from proposals rather than inventing dialogue or assignments.

## Exact next task

After approval for the next stage, **reconcile this checkout with `f56f0ff` while preserving the reviewed M0 documentation and unchanged extractor implementation; verify the loaded pyRevit path/engine, then prepare a read-only GC01 left/right diagnostic baseline**. Record element and connector identities, fitting/host/group/assembly membership, signed endpoint elevations, flow/anchor expectations and architectural reference points. Attach the original extraction acceptance reports. Do not implement a speculative mirror or slope fix before locating the first failing boundary.

## M0 validation and completion

Validation passed: 14 local Markdown links/anchors, 42 required milestone fields, whitespace/final-newline checks across all six changed documents, and exact documentation-only change scope. `git diff --check` passed. `git diff --exit-code HEAD -- PLEGTVOS_ModuleEngine.extension docs/AI_TASKS.md` confirmed no changes to executable extension files or the historical task log. The five new documents remain untracked; README is modified; nothing is staged or committed.

No Revit scripts were imported or executed as validation. **M0_AUDIT_COMPLETE**: the audit and documentation are finished. Future implementation blockers remain open, and model workflows are not declared production-ready.
