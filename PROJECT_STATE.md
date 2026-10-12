# PLEGTVOS ModuleEngine project state

## Current checkpoint - M1.1a instrumentation, 2026-10-11

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

## Historical M0 record — preserved, superseded for current state

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
