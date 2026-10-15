# SHEET_TRANSFER_M0 audit

Date: 2026-10-14. Status: AUDIT_READY; implementation and Revit acceptance NOT_STARTED.
This milestone changes documentation only. GC01 is PAUSED at M1.1h.

## Repository and preservation

Authorized checkout: `C:\00_WORKS\DEVELOPMENT\PLEGTVOS_ModuleEngine`, branch
`main`, HEAD `afd71060631faac89559aecf13c2dfeb582f87cd`, origin
`https://github.com/BIM3DNA/PLEGTVOS_ModuleEngine.git`. No fetch or remote synchronization
was needed for this local audit. Initial status: nine tracked modifications and eight
untracked files, all retained. PROJECT_STATE already contained local changes.

M1.1g native filtered collection/exhaustion is host-verified on the recorded GC01 path.
M1.1h batching is implemented, with 95 previously passing offline tests; those tests
were not rerun for this documentation audit. M1.1h host acceptance remains pending,
FULL remains disabled, and M1.2 has not started. See [host ledger](M1_1_HOST_ACCEPTANCE.md).
Earlier milestones remain historical; this request changes the immediate priority.

## Exact original source and evidence

Primary entry point (read-only):
`C:\BIM3DNA\BIM3DNA_API\BIM3DNARevitAPI\BIM3DNA.extension\BIM3DNA.tab\QuickFix.panel\Sheet Transfer.pushbutton\script.py`.

Source repository: branch `main`, HEAD `a33f3f3edb8c85687feec2e73f3726b8743e1ddc`,
origin `https://github.com/bim3dna-dev/BIM3DNA.git`. The audited script is clean relative
to that checkout, 502 lines, SHA-256
`07c616d748b39122486ee7bcb2ffca8ef6f1211b18a68079c280ce25b91bae09`.
The directory contains script.py, icon.png and an existing __pycache__; no separate
source helpers or button bundle configuration were found. No source was executed,
imported, copied into PLEGTVOS or edited.

An archived alternative was located under that repository at
`BIM3DNA.extension/Resources/RibbonArchive/rollback_backup_numbered_panels_20260524_154352/05_Sheets.panel/Sheets.pulldown/Sheet Transfer.pushbutton/script.py`.
It is not the primary reference or evidence of the loaded Revit command. The old
[M0 audit](M0_AUDIT.md) recorded a matching installed copy; its installation/loaded
session was not reverified here. No different SheetTransfer tool was substituted.

The header identifies version 1.0, 03.08.2025, author Emin Avdovic. Its detail-line
boundary instruction is stale: runtime does not read a drawn boundary. Imports require
RevitAPI/RevitAPIUI, pyRevit forms, clr, .NET generic List, Windows Forms/Drawing and
WindowsBase. RevitServices/DocumentManager is loaded but unused, creating an avoidable
installation dependency. Numerous imported APIs are unused. There is no explicit
engine selector or version gate in the button; Python-2-compatible syntax is not
proof of IronPython 2.7.12/.NET 8 runtime compatibility. UnitTypeId implies a modern
Revit API. Revit 2025.3 host execution of this transfer was not performed.

Targeted searches of Python test filenames in the source repository found no references
to Sheet Transfer, copy_sheets or collect_views_and_sheets. No dedicated tests or host
acceptance ledger were found for this button; this is a scoped search, not a claim that
no external tests exist.

## What the existing button actually does

Line references below refer to the hashed primary script.

| Area | Observed behavior | Consequence |
| --- | --- | --- |
| Source/destination, 121-143 | Active document is source; first other open title containing BNZ_OMO_OV2_N_IT_MPO_Sanitaire Installatie is target, resolved at module load | No document picker or identity/readiness checks; failure can precede main error handling |
| Selection, 147-196, 423-445 | User selects plan names; collect exact named non-template ViewPlan, direct dependents and sheets containing their viewports | Not sheet selection; picker includes dependent/non-floor-plan ViewPlans; shared sheets can be selected repeatedly |
| Scope boxes, 184, 200-226 | LookupParameter("Scope Box") on viewport; copy collected IDs in separate transaction | Wrong parameter owner/localized name; count check occurs after commit; positional ID map is unverified |
| Primary views, 230-299 | Document-to-document CopyElements on primary ViewPlan IDs, count and zip returned IDs | No target level/type mapping; support and mapping not established by API contract or host test |
| Dependents, 300-358 | Duplicate mapped target primary AsDependent, set name/template/crop flags | Useful dependency order; no CanViewBeDuplicated preflight; generic name exception enters unbounded retry loop |
| Templates, 235-261 | Match destination by name and ViewType, otherwise InvalidElementId | No definition equivalence or explicit missing-template handling; incidental copying is not a contract |
| Scope assignment, 292-294, 329-335 | Guarded View.ScopeBox attribute access | Not the documented View parameter API; standard views can silently skip assignment |
| Crop, 339-355 | Attempt CanHaveShape() and SetCropShape(List[CurveLoop]); catch and ignore errors | Wrong property/method and argument signatures; no dependable crop fidelity, annotation-crop or split-region preservation |
| Sheets, 363-418 | Create target sheet, set name and number; append _copy/_copy2 on collision | No preview, parameter parity, placeholder handling or rerun identity |
| Title blocks, 366-405 | Source instance.GetTypeId(), then pass that source ID to ViewSheet.Create(target_doc, ...) | Correctly obtains source type rather than instance, but fails cross-document mapping; absent title block creates blank sheet |
| Viewports, 409-415 | Create only mapped views at source GetBoxCenter() | Other sheet views omitted; no viewport type, rotation, detail number, label offset/line-length preservation |
| Schedules/legends/annotations | Schedule API imports unused; no explicit content pipeline | Schedules, legends and other unmapped views, sheet graphics, revisions and tags lack supported transfer paths |
| Parameters/references | Names/numbers and selected view properties only | No general sheet/title-block parameter map, shared-parameter GUID contract, host/reference remapping or model correspondence |
| Failure, 200-502 | Separate scope/view/sheet transactions for each selected plan; exceptions caught per selection | Earlier commits persist on later failure; commit statuses ignored; totals updated only after all stages can misreport durable changes |
| Repeated run/worksharing | No manifest, ownership checks or dependency deduplication | Duplicate sheets/views or placement failure; editability/borrowing failures unresolved |

No explicit source transactions, saves or synchronizations are present. This source
inspection does not prove host-side source immutability or successful target transfer.
DEBUG output is unconditional in collection despite VERBOSE=False. Only five failure
messages are displayed; the instruction to see the console does not provide a complete
exception traceback ledger. A failure dialog can say no views were copied even when
an earlier view transaction committed.

## Findings by evidence strength

**Confirmed code/API defects:** hard-coded ambiguous destination; source title-block
ID reused in target; wrong scope-parameter owner and guarded undocumented ScopeBox
assignment; invalid crop calls hidden by blanket catch; positional copy mapping without
an API correspondence guarantee; partial commits outside a TransactionGroup; unchecked
commit statuses; unlimited dependent-name retry for every exception; success accounting
that excludes earlier committed stages; silent omission of unmapped sheet contents.
These are static defects, not newly observed corrupt-model incidents.

**Risks requiring host evidence:** whether primary ViewPlan elements copy successfully
in the intended fixture; automatic dependency/type behavior; template controls and
editable parameters; paper-space placement fidelity; coordinate/level alignment;
worksharing ownership and failure handling; Python/.NET UI/Unicode behavior; transaction
cleanup on exceptions. No claim that every ViewPlan CopyElements call necessarily fails.

**Unsupported requirements in the current implementation:** arbitrary selected sheets,
complete sheet contents, schedule/legend transfer, annotation and tag reference mapping,
annotation/split crops, deterministic reruns, preview/confirmation, verified atomic
rollback and complete result reporting. These must block affected sheets rather than
silently create an incomplete result.

## Revit API contracts and proposed handling

Primary local reference inspected: `C:\Program Files\Autodesk\Revit 2025\RevitAPI.xml`.
Member names below identify reproducible contracts, not Revit host acceptance.

| Dependency | Verified API boundary and proposed handling |
| --- | --- |
| Copy operations | ElementTransformUtils.CopyElements(Document,...Document,...) is for non-view-specific elements. The View overload permits suitable 2D graphics views and requires view-specific inputs to belong to the source view; additional transform must lie in the view plane. Neither promises positional source/result mapping. Collect created dependencies and establish validated per-object correspondence, not zip. |
| Plans/dependents | ViewPlan.Create requires destination ViewFamilyType and Level IDs; subtype eligibility must be checked. Prefer explicit supported plan recreation if OVT bulk view copying cannot prove identity/fidelity in a pilot. View.Duplicate(AsDependent) operates on a target parent; preflight capability and verify GetPrimaryViewId. Other view kinds require separately proved routes. |
| Title blocks/sheets | ViewSheet.Create requires a target title-block type ID. Resolve/copy a qualified type, verify family/type/category and dimensions; preserve instance placement and supported parameters. Multiple blocks or missing required types must be explicit blockers until supported. |
| Templates/types | Name/ViewType only discovers candidates. Compare required definitions, controlled parameters and applicability before reuse. CopyPasteOptions duplicate-type handling must use an explicit reviewed policy; never silently assume same names mean same types. |
| Scope/crops | Resolve view BuiltInParameter.VIEWER_VOLUME_OF_INTEREST_CROP to a target scope ID. Verify geometry/coordinate correspondence. CanHaveShape is a property; SetCropShape takes one CurveLoop. Split regions, CropBox and annotation crop need their own capability checks and fidelity tests; template-controlled settings affect write order. |
| Placement | Viewport.CanAddViewToSheet before Viewport.Create with target IDs; preserve paper-space center and separately verify type, rotation, detail number and label geometry. Paper-space centers do not prove model coordinate alignment. |
| Schedules | ViewSheet.GetAllViewports excludes schedules. Enumerate ScheduleSheetInstance by OwnerViewId; Create requires a target schedule and sheet, with a segment overload where appropriate. Internal/revision schedules are not ordinary placeable schedules. Definition, filters, fields and instances need separate mapping/verification. |
| Legends/annotations | No generic promise that all content copies. Prototype each supported kind and enumerate all sheet-owned content. Use appropriate view-to-view copy only for eligible content. Hosted tags/dimensions need verified target references; ambiguity blocks the sheet. No model-element transfer is implied. |
| Parameters | Match built-in IDs/shared GUIDs, storage type, units and writability; remap ElementId values through destination identity map. Do not match localized labels alone or write controlled/read-only parameters. |
| Atomicity | Transaction.Commit may return RolledBack or Pending. TransactionGroup.RollBack can undo inner committed transactions only after they finish, and cannot close in failure mode. Check statuses and final state; pending/uncertain rollback is not success. |

Autodesk's [copying-elements guide](https://help.autodesk.com/cloudhelp/2024/ENU/Revit-API/files/Revit_API_Developers_Guide/Basic_Interaction_with_Revit_Elements/Editing_Elements/Revit_API_Revit_API_Developers_Guide_Basic_Interaction_with_Revit_Elements_Editing_Elements_Copying_Elements_html.html)
additionally states that returned IDs include elements created through dependencies.
This reinforces why count equality and zip are not identity verification. The 2024
conceptual guide supplements the installed 2025 contracts; it is not a 2025 host test.

## Proposed independent PLEGTVOS workflow

1. Explicitly select two distinct open project documents. Show identity/path and
   worksharing state, not title alone. Reject closed/invalid/linked/family destinations,
   read-only destinations and unsupported document states. Source may be read-only.
2. Choose source sheets by stable identity with number/name display. Build one deduplicated
   dependency graph across all selected sheets, including every viewport, schedule and
   sheet-owned element. Bound collection and report incomplete preview as blocked.
3. Read-only preview: planned reuse/create actions, mappings, numbers/names, target
   conflicts, unsupported contents, coordinates/levels, template and type differences,
   permissions, warnings and expected counts. Default to blocking conflicts; proposed
   renames require explicit review. A sheet is eligible only when all required content
   has a supported route. Do not silently strip objects to make it transferable.
4. Confirm the concrete source, target, sheets and plan. Revalidate document snapshots,
   identities and dependencies immediately before apply; changes invalidate confirmation.
5. Destination-only TransactionGroup for the approved bounded batch; checked internal
   transactions in dependency order. Cancel/error/verification failure rolls back the
   entire batch. Finish inner transactions before group rollback. If failure handling
   leaves Pending or rollback unconfirmed, stop and report intervention required; do not
   continue to another sheet or claim no changes. Never start a source transaction.
6. Verify created/reused identities, dependency closure, parent links, sheet contents,
   parameters and layout before group assimilation. Report attempted versus durable
   results, warnings and rollback status. Verify source state unchanged. No save, sync,
   coordinate acquisition, active-view or selection changes are part of the design.

Identity keys combine qualified document identity and source UniqueId; target mappings
must resolve and verify target document/UniqueId/category/type. Equal integer IDs or
names do not qualify identity. Creation APIs with direct return objects are preferable;
copy results need object-kind-specific unambiguous matching and full dependency review.
Ambiguous matching rolls back. A persisted operation manifest may support reruns only
when both document snapshots and target mappings still verify; otherwise block. No-op
reruns require equivalence evidence, never a name-only match. Record type reuse and
implicit copied dependencies. Worksharing preflight cannot guarantee later ownership;
apply failures must still exercise rollback, without automatic synchronization.

## Reuse and integration

Recommended future location:
`PLEGTVOS_ModuleEngine.extension/PLEGTVOS_ModuleEngine.tab/Dev.panel/Sheet_Transfer.pushbutton/`.
Display title: Sheet Transfer. No button or executable was created in M0.

Reuse OVT's view/dependent/sheet association approach, target-template candidate index,
source title-block type discovery, target dependent duplication order, number-conflict
checks and viewport-center capture after targeted validation. Repair or replace unsafe
mapping, crop/scope calls, global destination selection, collision loops and transaction
orchestration. No functionality is declared host-proven merely because it existed in OVT.
Keep pure planning/mapping separate from Revit readers and destination apply/verification.
Do not import GC01, extractor, mirror, transform or slope modules; no shared-engine
refactoring is required. See [implementation gates](SHEET_TRANSFER_MILESTONES.md).

## Questions for colleague/Emir

- Which representative source/target RVTs and sheets define acceptance, and who can
  authorize disposable copies? Confirm whether Emin (source author) or Emir owns review.
- Are plans/dependents the initial scope, or are legends, schedules, revisions, drafting,
  sections, tags and dimensions mandatory on the first fixture?
- Does the destination contain equivalent model/linked elements for tag and dimension
  references? What proves correspondence and coordinate/level alignment?
- Which title-block families, shared parameters and templates are authoritative? Should
  differing definitions block, use existing definitions or create reviewed variants?
- Must sheet numbers remain exact? What rename policy, if any, is acceptable? Should a
  previously transferred sheet block or qualify for a verified no-op (no update in MVP)?
- Are workshared/cloud projects required initially? Confirm batch size and whole-batch
  rollback expectations; no save/sync is assumed.

These questions do not block M0 documentation. They gate implementation scope and fixtures.

## Validation and limits

Static source review and installed API contract inspection only; no transfer, Revit
execution, executable import, model creation, compilation or GC01 test rerun. New Markdown
is checked for UTF-8, links/fences and whitespace. Baseline hashes verify all preexisting
repository files except the authorized PROJECT_STATE update remain unchanged; its previous
body is retained verbatim. No reset, clean, stash, commit, push or worktree move occurred.
