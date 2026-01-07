# AI Tasks & Decisions Log — PLEGTVOS_ModuleEngine

This document records **important Codex / Copilot-assisted work** for the
PLEGTVOS Module Engine.

It is intentionally curated and **not a full chat log**.

Use this file to capture:

- architectural decisions
- non-obvious fixes
- refactors
- Revit / API constraints
- trade-offs that matter long-term

---

## Project Context

- Project: **PLEGTVOS_ModuleEngine**
- Domain: Revit MEP / Prefab / Modular Systems
- Primary Language: Python (pyRevit / CPython)
- Revit Versions: 2022–2026
- Execution Context:
  - pyRevit
  - External CPython helpers (where applicable)
- Author: BIMCode Solutions

---

## 2026-01-07 — Initial Module Engine Architecture Definition

### Context

- Goal: Define a reusable engine for prefab / modular MEP workflows
- Constraints:
  - Must run safely inside Revit transactions
  - Must support partial regeneration
  - Must survive repeated execution without model corruption

### Prompt (Codex)

Design a modular engine architecture for PLEGTVOS that separates
state serialization, geometry transforms, and fitting reconstruction,
while remaining Revit-API-safe.

### Output Summary

- Identified core subsystems:
  - `state_serializer`
  - `transform_engine`
  - `fitting_rebuilder`
- Recommended strict transaction boundaries per subsystem
- Suggested idempotent operations where possible

### Decision

- Adopt engine-style orchestration instead of script-style execution
- Defer UI concerns to a separate layer
- Treat geometry transforms as deterministic, reversible operations

### Follow-ups

- [ ] Formalize engine interfaces
- [ ] Define minimal state schema (JSON)
- [ ] Decide mirror vs transform precedence

---

## 2026-01-XX — <Task Title>

### Context

- Revit Version:
- Module / Subsystem:
- Problem:

### Prompt (Codex)

<Short, cleaned prompt>

### Output Summary

<Key technical guidance only>

### Decision

<What was chosen and why>

### Follow-ups

- [ ] …

## 2026-01-07 — Task Title

### Context

- Revit Version: 2025.3
- Module / Subsystem: transform_engine
- Goal: copy all elements from scource to target scope box! (ALL!)

### Prompt (Codex)

it had 3650 warnings, then I clicked ok on every, then still we got "copied 293 elements, view-specific copied: 0 |failed/skipped: 12, Invalid/usupported skipped: 378, views skipped: 0. We must copy views also!

### Output Summary

Transform Engine now attempts to copy views and assemblies in addition to all other elements (no whitelist). It also reports view copy results and rolls back/counts failures.
Summary now shows: copied, view-specific copied/failed, views copied/failed, and invalid/unsupported skipped.
Please rerun transform_engine. If some elements still fail, the summary will indicate which buckets failed so we can address them next.

### Decision

### Follow-ups

- [ ]
