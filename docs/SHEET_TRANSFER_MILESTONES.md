# Current M1.1 status

M0 complete; M1 integrated and first host preview observed, inventory acceptance pending.
M1.1 name-reader correction and evidence review: [host review](SHEET_TRANSFER_M1_1_HOST_REVIEW.md).
Destination writes disabled. GC01 paused; M2/M3/M4 pending. Earlier plan below is historical.

# Sheet Transfer implementation milestones

Date: 2026-10-14. Only SHEET_TRANSFER_M0 is authorized/completed as an audit.
No implementation or transfer host acceptance is claimed. GC01 stays PAUSED at M1.1h;
FULL disabled; M1.2 not started. This priority supersedes the immediate sequence in the
historical [project milestones](MILESTONES.md), not their historical evidence.

Read the [source audit and API boundaries](SHEET_TRANSFER_M0_AUDIT.md) before implementation.
Retain useful OVT traversal, dependent creation and placement logic after validation;
do not port its entire executable or start a general mirror/extraction engine.

## Small gates

| Milestone | Deliverable | Offline acceptance | Revit 2025 host acceptance |
| --- | --- | --- | --- |
| SHEET_TRANSFER_M0 | Source audit, API contracts, integration plan, paused GC01 state | Documentation/link checks; preexisting files preserved | None authorized or claimed |
| SHEET_TRANSFER_M1 | Independent read-only button: explicit documents/sheets, bounded dependency inventory, deterministic preview and blockers | Pure mapping/deduplication; colliding titles/numbers; missing content/types; Unicode; limits; stale plans; no write entry point | Approved disposable documents: correct source/target/sheets, every viewport/schedule/sheet-owned object accounted for, Cancel at each step, no source/target changes; record exact loaded path/engine |
| SHEET_TRANSFER_M2 | Narrow API feasibility pilot for agreed plan/dependent/title-block/scope/template fixture; identity mapping proof | Mapping ambiguity and wrong-document IDs rejected; bounded name allocation; failure/status state-machine tests; IronPython compilation/probes | Separately authorized disposable target only: mapped levels/types, primary and dependent relationship, scope/crop fidelity, direct target IDs; injected late failure rolls back earlier stages; source unchanged. Unproved content remains blocked |
| SHEET_TRANSFER_M3 | Controlled transfer of the fully supported initial sheet fixture, preview confirmation, destination TransactionGroup, verification ledger | Confirmed plan invalidation; dependency order/dedup; counts; unsupported objects block whole affected batch; Pending/rollback failures never success | Exact sheet names/numbers, title blocks/parameters and viewport layouts; all required fixture contents verified, Cancel before apply, failure between stages, rollback and Undo; no saves/sync/source writes |
| SHEET_TRANSFER_M4 | Incremental supported content and release hardening, one object kind per tested change | Schedule/legend/annotation parameter/reference maps, duplicate types, rerun/no-op identity, deterministic manifests and complete error reports | Approved cases for schedules/segments, legends, tags/dimensions and special crops as required; unresolved references block. Repeated run, ownership denial, workshared local documents, layout comparison, warnings, rollback and Undo. No blanket production acceptance |

Each milestone needs explicit authorization before executable or model-write work.
M2 is a bounded feasibility exercise, not a production apply button. If mandatory fixture
content remains unsupported after M2/M3, release is blocked; do not call an incomplete
sheet successful or silently downgrade the fixture. New view kinds and cloud support
need explicit acceptance cases, not incidental broadening of the MVP.

## Common acceptance contract

- Every host record includes source revision/hash, loaded extension path, Revit build,
  pyRevit/engine/.NET versions, disposable fixture identities, chosen documents/sheets,
  expected and actual behavior, warnings, result ledger and evidence location.
- Offline mocks, syntax checks and API XML establish logic/contracts only. They do not
  establish Revit copy semantics, reference fidelity, transaction cleanup or acceptance.
- Preview has no transactions. Apply stays on the Revit API thread with checked destination
  transactions only. No background API work, source mutations, saves or synchronization.
- Document/element identities must still match the confirmed preview. Do not rely on names
  or matching integer IDs across documents. Copy-result order is not a mapping contract.
- Whole approved batch is atomic. Validate while the group can still roll back. Check
  transaction/group statuses and source state; Pending/unknown cleanup is intervention
  required. Do not assert rollback solely because an exception was caught.
- Test deliberately mismatched source/target IDs, missing/conflicting title blocks and
  templates, repeated sheets via shared dependencies, invalid crop, denied ownership,
  duplicate-type dialogs/policy, forced late failure, Cancel and Undo.
- Preserve all GC01/extractor/mirror/transform/slope implementations and BIM3DNA production
  commands. Keep a separate test fixture and result ledger for Sheet Transfer.

## Safe repository/worktree proposal

M0 uses only three documentation files in the existing checkout. There is no need to
move or isolate the active worktree for an audit. It remains dirty with the preserved
GC01 experiment. No stash, reset, clean, checkout switch, commit or push is authorized.

For separately authorized implementation, first reverify current HEAD and confirm the
proposed branch and sibling path do not already exist. The exact proposal based on the
verified baseline is:

```powershell
git -C C:\00_WORKS\DEVELOPMENT\PLEGTVOS_ModuleEngine worktree add -b feature/sheet-transfer-m1 C:\00_WORKS\DEVELOPMENT\PLEGTVOS_ModuleEngine_sheet_transfer afd71060631faac89559aecf13c2dfeb582f87cd
```

This command has NOT been executed. It creates a separate branch/worktree at the pinned
commit and leaves the current experimental worktree intact. It does not include any
uncommitted GC01 or M0 documentation. After authorization, carry only these three reviewed
documentation files into that worktree explicitly, checking hashes and preserving the
historical status context; do not copy the entire dirty checkout. Reverify AGENTS/state
and the implementation baseline there. No automatic commit/push or merging of paused
GC01 work is implied.

Do not register a second extension or change pyRevit configuration during M0. A future
host test must explicitly verify the intended loaded path and avoid duplicate toolbar
installations; a new worktree alone does not change the loaded Revit command.

## Decisions before M1/M2

Obtain colleague/Emir agreement on representative sheets, required object types, target
model/reference equivalence, levels/coordinates, title-block/template authority, collision
policy, worksharing/cloud scope and whole-batch atomicity. The audit lists the exact
questions. M1 may inventory unsupported content; M2 writes require approved disposable
fixtures and a fixed supported-content contract. No production-transfer acceptance is
inferred from the original button's name or existence.
