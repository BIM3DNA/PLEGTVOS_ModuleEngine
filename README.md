# PLEGTVOS ModuleEngine

pyRevit prototypes for capturing, extracting and documenting standardized MEP modules for repetitive housing projects. The intended longer-term workflow combines reusable modules with controlled placement and building-specific variants while preserving architectural coordinates.

## Current status

M0 audit dated 2026-10-11. This checkout is `main` at `a10c8575e8c4e196a7734e7031d616bfa33ce9b1`, eight commits behind the inspected GitHub `main` at `f56f0ffe530032e78b3571f2b2637093d2686058`. No merge was performed. Read [PROJECT_STATE.md](PROJECT_STATE.md) before development and verify Git again; these hashes are an audit snapshot.

The detached-copy extraction prototype is reported host-tested for GC01, GC02, GC04, GC06, GC07 and GC08; GC12 is also reported successful. Its code is present in the inspected remote revision, **not in this working checkout**. M0 did not rerun Revit or independently verify those model results.

Mirror, transform, slope and documentation commands are experimental. There is no production-readiness claim, general fitting auto-repair, or implemented preflight/postflight framework. Earlier README descriptions of reliable placement, automatic fitting repair and production-grade UI described the ambition, not demonstrated capability.

## Repository layout

- `PLEGTVOS_ModuleEngine.extension/PLEGTVOS_ModuleEngine.tab/Dev.panel/`: command scripts and shared `module_state.py`; see the complete [inventory](docs/M0_AUDIT.md#command-inventory).
- `PLEGTVOS_ModuleEngine.extension/lib/`: sample Revit API scripts and a print helper, not an implemented engine library.
- `PLEGTVOS_ModuleEngine.extension/hooks/`: import-command hook with its blocking behavior commented out.
- [AGENTS.md](AGENTS.md): operating and acceptance rules.
- [PROJECT_STATE.md](PROJECT_STATE.md): verified state, evidence boundaries, blockers and next action.
- [docs/M0_AUDIT.md](docs/M0_AUDIT.md): local/remote comparison, reference audits and feature gap matrix.
- [docs/MILESTONES.md](docs/MILESTONES.md): proposed M0–M6 delivery gates.
- [docs/meetings/2026-10-11.md](docs/meetings/2026-10-11.md): supplied meeting requirements and unresolved decisions.
- [docs/AI_TASKS.md](docs/AI_TASKS.md): preserved historical architecture and host-observation notes; not current acceptance authority.

## Development environment

Target acceptance environment: Windows, Revit 2025 and pyRevit. The installed Revit 2025 add-in points to `IPY2712PR` (IronPython 2.7.12). Audited commands have no `#! python3` selector and use the default IronPython route. The configured CPython 3.12 engine does not make these scripts CPython commands. A live command invocation was not observed during M0. Existing references to Revit 2022–2026 are historical intentions, not a tested support matrix.

Most commands use `__revit__.ActiveUIDocument`, Autodesk Revit API assemblies and .NET collections; editors use Windows Forms. `UI_11` contains XAML only. Some scaffold imports require `RevitServices`; optional Pillow imports do not establish a supported external Python execution path. A local ignored `venv/` exists but is not the pyRevit command engine. No project test suite or CI configuration was found.

## Workflows and limitations

1. **Existing capture prototype:** `Capture_01` selects a scope box or closed detail-line region and writes a state snapshot. It also changes view isolation by default and has a hide-elements fallback; it is not a model-read-only audit command. `Capture_02` resolves saved element IDs and writes collection buckets.
2. **Existing region documentation prototype:** `Documentation_10` duplicates/crops a floor plan from state; `Capture_1` stages review data; `Capture_2` applies Comments, text and pipe tags. State is document-local and IDs must not be reused across models. The full sheet workflow is not implemented in local `Documentation_09`.
3. **Reported extraction workflow, remote revision only:** `Module_Extractor_14` classifies scope-box candidates and writes JSON without a Revit transaction. `Module_Extract_Test_15` copies a saved local RVT, opens the copy detached where workshared, deletes outside candidates only in the copy, saves, closes and reopens the output for verification. Preserve this implementation. See the audit for exact acceptance limits and path dependencies.
4. **Experimental placement and systems:** `Placement_05` copies between scope-box frames; `Placement_06` mirrors; `Systems_07` attempts system-specific slopes. Use only a separately authorized disposable-model host test. They do not guarantee connector integrity or full dependency coverage.

State files are written near the RVT/central file or under `%APPDATA%/pyRevit/PLEGTVOS_ModuleEngine/state/<document title>`. Model-adjacent filesystem writes can reach shared locations. JSON existence and successful transaction counts do not prove model correctness.

During M0, no button was run, no RVT was created, and no executable code was changed. M1 or later work requires a new instruction. Read the milestone host-test requirements before using write commands on any model; do not use central or production models as test fixtures.
