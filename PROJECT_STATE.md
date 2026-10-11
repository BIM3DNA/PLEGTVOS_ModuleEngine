# PLEGTVOS ModuleEngine project state

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
