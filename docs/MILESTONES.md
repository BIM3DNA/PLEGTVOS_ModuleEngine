# Proposed milestone plan

Updated: 2026-10-11. M0 and the separately authorized M0.2 reconciliation/normal push are complete at `97d269ab009cea71528f4532bc1788874f7139ed`. M1.0 documentation-only audit is complete. M1.1 and all model-writing work remain proposals requiring a new instruction. Owners and dates remain unassigned pending Alen/Emir decisions. Historical M0 scope below is retained.

`P` means `PLEGTVOS_ModuleEngine.extension/PLEGTVOS_ModuleEngine.tab/Dev.panel/`. Paths below are expected scopes, not instructions to create every file. The recovered baseline now has seven pushbutton directories and nine plain feature directories. Do not accidentally re-enable archived commands. See [M1.0 architecture inventory](M1_GC01_MIRROR_AUDIT.md#architecture-inventory) for actual paths.

## Shared acceptance rules

Every host record must identify Revit 2025 build, pyRevit engine, loaded extension path and code revision, disposable fixture identity, before/after state and evidence locations. No central-model test writes or production coordinate changes. For writes: Cancel before apply, an intentional failure/rollback case and Undo are required. Preserve connector/host/group/assembly relationships, pinned state, source invariance and architectural reference points as applicable. Offline tests and a success dialog do not substitute for host acceptance.

## M0 — Repository audit and project bootstrap

- **Objective:** establish evidence-backed project state, preserve extraction baseline and document references, risks and delivery gates.
- **Dependencies:** local checkout, supplied requirements, readable remote revisions, local BIM3DNA transfer implementation.
- **Files expected to change:** README.md, PROJECT_STATE.md, AGENTS.md, docs/M0_AUDIT.md, docs/MILESTONES.md, docs/meetings/2026-10-11.md only.
- **Non-goals:** merge/update checkout, refactor code, port references, M1 implementation, model execution, RVT creation, commits/pushes.
- **Acceptance criteria:** branch/HEAD/status and remote delta established; every panel item classified from implementation; engine selection checked; references and feature matrix audited; source defects separated from hypotheses; reported acceptance retained with provenance; docs checked and diff clean.
- **Revit 2025 host-test requirements:** none executed during M0. Inspect installed configuration/API documentation only. Record unavailable live evidence explicitly.

## M1 — GC01 mirror reliability and MEP diagnostics

Current subdivision: M1.0 audit complete; M1.1 independent read-only diagnostics proposed; mirror/slope repairs deferred until host evidence identifies the first failure boundary. The parent milestone's writing/repair goals below are not authorized by audit completion.

- **Objective:** reproduce and locate the first GC01 left/right divergence, then implement the smallest authorized correction with connector and slope evidence.
- **Dependencies:** approved baseline reconciliation preserving M0 docs and extractor bytes; loaded-path/engine verification; disposable GC01 fixture; agreed left/right plane, fixed reference/anchor, flow direction and slope units; historical extraction artifacts requested.
- **Files expected to change:** first docs/host-acceptance/M1-GC01.md and a proposed read-only diagnostic helper under P; only after diagnosis, P/Placement_06.pushbutton/script.py, P/Placement_05.pushbutton/script.py and/or P/Systems_07.pushbutton/script.py as proven necessary; targeted pure-logic tests if added. Update PROJECT_STATE.md. Extractor_14/Test_15 remain unchanged.
- **Non-goals:** broad fitting reconstruction, general engine refactor, new module placement architecture, sheets/register or unexplained automatic network repair.
- **Acceptance criteria:** source-to-output physical inventory and missing/excluded ledger; all expected connections/fittings/hosts accounted for; approved left/right geometry and signed flow/slope; source/pin state unchanged for copies; no unreported partial results; unresolved cases explicitly fail acceptance. Validate fixes against both left/right and non-mirrored baseline.
- **Revit 2025 host-test requirements:** near/distant targets; center/left/right semantics; representative rotated box; loose, grouped, assembled and hosted roof content; relevant levels and VWA/HWA rules; before/after connector graphs, warnings, slope/flow and fixed architectural coordinates; Cancel, failed transaction rollback and Undo. Do not infer group support from loose-pipe success.

## M2 — Drawing register and unique left/right coding

- **Objective:** define and enforce stable module/drawing identity shared by tags, schedules and sheets.
- **Dependencies:** Alen/Emir approval of code scope (project/building/module/hand/revision/variant), sample register, existing Comments semantics and M1 orientation vocabulary. Design can proceed independently; model acceptance waits for approved fixtures.
- **Files expected to change:** proposed docs/DRAWING_REGISTER.md, a register schema/example under docs/examples, a pure code-validation helper under P, relevant Capture_1/Capture_2 or approved documentation integration point; PROJECT_STATE.md. Do not fill examples with invented actual drawing records.
- **Non-goals:** automatic renumbering of existing production sheets, full sheet generation, business-system integration or using mirrored X/Y order as a permanent identity.
- **Acceptance criteria:** unique codes under approved scope; deterministic validation; explicit duplicate/rerun/revision policy; left/right pairs traceable to one module definition; register-to-Comments/tag/schedule mapping documented and checked. Domain approver signs off convention before writes.
- **Revit 2025 host-test requirements:** disposable left/right pair, collisions, missing/read-only parameters, reruns and revision changes; verify Comments/tag values and source document identity; Cancel/rollback/Undo for any apply operation. If delivery is schema-only, record host parameter validation as pending before integration.

## M3 — Plechtvos Sheet Generator

- **Objective:** adapt the audited workflow to Emir-approved Plechtvos sheets, views, tags, schedules and content.
- **Dependencies:** M2 code contract; M1 accepted geometry for test fixtures; review Emir's actual examples; approved title-block/view/tag/schedule and nested-family parameter mapping; choose which reference revision to reuse (installed and GitHub differ).
- **Files expected to change:** approved P/Documentation_09 command entry/bundle, narrowly scoped shared helpers/configuration under P, docs/SHEET_WORKFLOW.md, docs/host-acceptance/M3-SHEETS.md, PROJECT_STATE.md. Resolve plain-folder versus ribbon exposure intentionally. Reference repositories remain unchanged.
- **Non-goals:** wholesale reference import, fitting/reducer model changes merely because reference editor supports them, arbitrary family support, cross-document transfer or new extractor behavior.
- **Acceptance criteria:** one approved left/right sample each; correct unique numbers and Comments; exact schedule membership with no prefix bleed; visible host-correct tags; approved plan/3D crop/template/scale; non-overlapping layout within title block; missing dependencies detected before writes; specified rerun and partial-result policy.
- **Revit 2025 host-test requirements:** representative GC01 hands and required disciplines/fundering; missing title block/tag/master schedule, empty schedule, duplicate number, nested-family parameter and rotated crop cases; verify plan/3D tag visibility, schedule rows/totals and printed layout; Cancel at each phase, rollback and Undo. Reopen saved disposable result only when authorized.

## M4 — OVT Sheet Transfer adaptation

- **Objective:** transfer the approved Plechtvos drawing content with explicit cross-document mapping and predictable failure handling.
- **Dependencies:** M2 collision/code rules; M3 content contract; approved source/target selection, level/type/template mapping, coordinate convention and atomicity policy. BIM3DNA implementation remains a read-only reference.
- **Files expected to change:** a new P/Sheet_Transfer.pushbutton entry/bundle and focused transfer helpers, docs/SHEET_TRANSFER.md, docs/host-acceptance/M4-TRANSFER.md, PROJECT_STATE.md; final command name subject to ribbon convention.
- **Non-goals:** edit BIM3DNA toolbar, unrestricted model cloning, assume source IDs identify target types, automatic coordinate acquisition or silent omission of annotations/schedules.
- **Acceptance criteria:** preflight identifies intended documents and all dependencies; title-block/types mapped by target identity; supported primary/dependent views and scope/crop verified; required templates/tags/schedules and sheet metadata preserved; bounded collision/rerun behavior; output manifest reflects actual committed state; no hidden partial writes. Unsupported content fails or is explicitly deferred.
- **Revit 2025 host-test requirements:** two approved disposable project docs with aligned architecture; different element IDs and missing type/template cases; primary/dependent views, scope boxes, crops, plan tags and schedule instances; duplicate names/numbers, repeated run and shared-sheet selections; coordinate/reference-point comparison; Cancel, failure in each stage, rollback and Undo. Prove plan-copy/recreation API route in host before expanding scope.

## M5 — Extracted module dependency and linking QA

- **Objective:** prove extracted RVTs retain required module dependencies and link at correct architectural coordinates while keeping the validated extraction algorithm intact.
- **Dependencies:** recovered historical acceptance evidence; unchanged extraction baseline; approved source/module models, expected dependencies and link-position convention; drawing/transfer results where required.
- **Files expected to change:** proposed read-only QA helper under P, docs/EXTRACTION_LINKING_QA.md, docs/host-acceptance/M5-LINKING.md, PROJECT_STATE.md. Any later linking writer requires its own authorized scope. Extractor_14/Test_15 changes are not assumed.
- **Non-goals:** reimplement extraction, remove allowed infrastructure indiscriminately, normalize modules to origin, claim zero outside candidates proves connector/dependency completeness.
- **Acceptance criteria:** evidence ledger for GC01/02/04/06/07/08 and GC12 report resolution; required families/types/materials/levels/hosts/groups/assemblies and connectivity accounted for; intentional boundary crossings documented; reopen counts and source invariance retained; link coordinates/orientation match architectural references with an agreed tolerance.
- **Revit 2025 host-test requirements:** authorized disposable extractions and reopen checks across approved module set; workshared-source detach boundary and failure/cancel cases; verify dependencies and source state; link approved outputs into a disposable architectural context using approved coordinates, inspect all relevant levels, reload and Undo where applicable. Record per-module failures, not a blanket pass.

## M6 — Options and building-specific variants

- **Objective:** integrate the selected modification workflow with extracted linked modules using traceable variants.
- **Dependencies:** M5 link/dependency acceptance; M2 identity contract; explicit selection of modification mechanism (not decided in the brief), allowed changes and architectural constraints; approved representative building scenarios.
- **Files expected to change:** proposed docs/VARIANT_CONTRACT.md, scoped configuration/orchestration under P or extension lib after architecture approval, docs/host-acceptance/M6-VARIANTS.md, PROJECT_STATE.md and relevant register integration.
- **Non-goals:** arbitrary building remodeling, editing linked documents implicitly, moving architectural reference systems, unapproved options or redesigning extractor internals.
- **Acceptance criteria:** each variant has provenance, allowed delta and unique code; baseline remains reproducible; only authorized building changes occur; placement/coordinates, connectivity, documentation and dependency gates remain satisfied; rerun/conflict/reversal behavior documented.
- **Revit 2025 host-test requirements:** baseline plus agreed building/hand/option combinations on disposable projects; verify allowed and forbidden deltas, links, coordinates, connectors, schedules and register; Cancel, unsupported option, rollback, repeat run and Undo. No implementation until the workflow contract is approved.

## Immediate next work order

Stop after M1.0 delivery. Reconciliation and push are complete. The next proposed work order is **M1.1: implement and validate only the independent read-only GC01 diagnostic collector** described in [M1_GC01_MIRROR_AUDIT.md](M1_GC01_MIRROR_AUDIT.md). No mirror/slope fix is part of that scope. See [PROJECT_STATE.md](../PROJECT_STATE.md) for domain decisions and unverified host evidence.

## M0.2 checkpoint — completed reconciliation and push

- **Objective:** preserve eight remote implementation commits and replay the six-file M0 documentation commit safely.
- **Dependencies:** verified clean `main`, original `72b68e8a`, remote `f56f0ff`, verified backup branch and complete external Git bundle.
- **Files expected to change:** Git history/checkout only through authorized rebase; documentation content preserved exactly; executable extension equals recovered remote baseline.
- **Non-goals:** new commits beyond replay, code edits, force-push, model writes or host acceptance.
- **Acceptance criteria:** conflict-free rebase to `97d269ab`, one documentation commit above baseline, normal push verified against remote, clean tree, extractors present. Completed in preceding session steps.
- **Revit 2025 host-test requirements:** none performed. Configuration/cache source paths identified repository extension; reload/new host invocation not confirmed. IronPython 2.7.12 syntax compilation was offline only.

## M1.0 — Completed GC01 diagnostic audit

- **Objective:** trace actual mirror/transform/slope/capture/state architecture, identify verified defects separately from hypotheses, define read-only diagnostics and host acceptance.
- **Dependencies:** verified clean `main` at `97d269ab`; source, installed Revit 2025 API documentation and historical meeting requirements. No model fixture required for source audit completion.
- **Files expected to change:** PROJECT_STATE.md, docs/MILESTONES.md and docs/M1_GC01_MIRROR_AUDIT.md only.
- **Non-goals:** code, diagnostic-button implementation, Revit transactions, geometry/connector changes, extractor changes or new host claims.
- **Acceptance criteria:** architecture graph, 13 requirement areas, line-level findings with causes/severity/remedy/test, deterministic report contract, acceptance matrix and explicit team decisions documented; documentation checks pass. Completed as documentation audit.
- **Revit 2025 host-test requirements:** all proposed T01–T14 cases remain NOT RUN. No model manipulation or read-only command execution was needed for M1.0.

## M1.1 — Proposed independent read-only diagnostic collector

- **Objective:** collect GC01 document/source/optional existing target, identity, geometry, dependency, system and connector evidence without modifying the model; serialize deterministic JSON.
- **Dependencies:** new implementation authorization; recovered baseline and loaded path/engine/reload verification; approved GC01 fixture and export location; team input on frames/rules/tolerances for prediction. Unknown approvals allow observation-only reports with unresolved comparison, not guessed transforms.
- **Files expected to change:** proposed new diagnostic pushbutton, minimal pure serialization/comparison helper if needed, focused tests and host acceptance ledger; project documentation. Existing Placement_05/06, Systems_07, module_state, extractors, Sheet Generator and Sheet Transfer remain unchanged.
- **Non-goals:** transactions (even rolled back), regeneration, views/isolation, geometry/parameter/connector writes, slope repair, copying/mirroring, saving/opening RVTs, importing write-command entry points or overwriting historical/latest state.
- **Acceptance criteria:** conform to the proposed schema and deterministic sort/hash rules; explicit missing/unsupported/ambiguous data; stable document/UID and connector matching; physical/logical edge separation; no silent dropped dependencies; no prediction PASS with unresolved identity/frame/policy.
- **Revit 2025 host-test requirements:** T01, T05 and T14 plus read-only observations for T04/T06/T08/T13; prove unchanged model/view/selection/Undo state, safe Cancel/export failure and reproducibility. Commit status remains host-acceptance pending until observed. All write/fault/Undo manipulation tests stay deferred to a separately authorized repair milestone.
