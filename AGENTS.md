# Repository operating rules

## Establish scope and evidence

Read `PROJECT_STATE.md`, this file and the relevant milestone before work. Verify branch, HEAD, worktree and remote state; Git takes precedence over recorded snapshots. Distinguish checked-out code, fetched remote code, installed toolbar copies, commit-message reports and observed host results. Never infer functionality from filenames or imports.

Work only in the authorized repository. Reference repositories and the BIM3DNA toolbar are read-only unless separately authorized. Preserve user changes and untracked files. Do not automatically commit, push, reset, merge, rebase, delete files or synchronize this checkout to the remote. Keep changes scoped to the requested milestone and report exact files changed and validation performed.

M0 authorizes documentation only after inspection. No M1 implementation, executable changes, model writes, generated RVTs or extractor refactoring are authorized by M0. A future explicit user instruction can authorize the next scope.

## Revit API and engine safety

- Revit API work must execute in a valid Revit API context on its supported thread. Do not import executable pyRevit buttons into offline tests: many execute UI/model work at module level.
- Confirm the command's selected engine and installed attachment. These scripts currently use default IronPython; do not introduce Python 3-only syntax on that path. Do not claim installed configuration proves the engine of an already-running session.
- Separate read-only diagnostics from apply commands. Existing `Capture_01` performs isolation/hide transactions and is not a read-only probe.
- Verify document identity, element validity, group/assembly membership, host relationships, pinned state and editability before authorized writes. Integer IDs are document-local. Do not treat equal titles or stale `latest.json` as sufficient cross-document identity.
- Use document-scoped transactions and check commit status. Isolate fallbacks; an exception does not prove earlier writes were undone. Restore pinning inside a valid transaction. Define whether a multi-step operation is atomic or partial and report durable results honestly.
- Capture warnings and errors as evidence. Do not silently suppress MEP failures or count a matching slope as connectivity acceptance. Cancellation, rollback and Undo must be tested in the host for write workflows.

## Worksharing and extractor preservation

Preserve `Module_Extractor_14` and `Module_Extract_Test_15` from the inspected extraction baseline. Do not redesign, normalize or refactor them as incidental cleanup. M0 found them only in remote `f56f0ff`; do not claim they are installed here until the checkout is reconciled and the loaded path verified.

The extraction source must remain unchanged and open. Preserve filesystem-copy, detached-open, copied-document deletion, SaveAs and reopened-output verification boundaries. Never synchronize test changes to a central model. Do not enable preserve-worksets fallback or mixed-assembly disassembly incidentally. A saved local file is required by the current prototype; unsaved edits and cloud paths need explicit handling decisions before extending support.

Document state-directory writes and output path selection. Do not overwrite production outputs or existing evidence. Do not run extraction just to validate documentation.

## Coordinates and dependencies

Preserve architectural internal/project/shared-coordinate relationships, project location, levels and link alignment. Do not move project bases, acquire/publish coordinates or normalize geometry to the origin as a convenience. Record source/target frames and known reference points before an authorized transform. Verify orientation, elevations and architectural/link alignment afterward. Scope-box centers alone are insufficient acceptance for rotated or mirrored geometry.

Connector graphs, hosted/nested content, groups, assemblies, systems and view dependencies must be accounted for. Missing or ambiguous objects are unresolved, not successful skips. Cross-document copying requires explicit type, view, template, level and element mapping; never pass a source-document element ID as a target-document identity.

## Testing and acceptance

Use offline checks for pure logic and documentation; they do not prove Revit behavior. There is currently no repository test suite. Add focused tests when implementation warrants them. Run `git diff --check` and relevant documentation/link checks for documentation changes.

Revit 2025 host acceptance must record code revision and loaded path, Revit/pyRevit engine/build, fixture identity, source/target context, action, expected result, actual result and evidence location. Use approved disposable models, with before/after counts, connector state, slope/direction, host/pin membership, warnings and coordinates as relevant. Test Cancel before apply, intentional failure/rollback and Undo. Record failures and untested cases explicitly.

GC01/02/04/06/07/08 and GC12 extraction successes are user-reported historical host evidence until the original reports are attached to an acceptance ledger. Preserve those reports without upgrading them to newly observed results. Reopening and classifier acceptance do not establish full MEP, drawing, linking or production readiness.
