# TASK-BUILDER-BG-E2E-002 — Background Builder End-to-End Smoke Test

Status: APPROVED FOR AUTO SMOKE TEST
Classification: DOCUMENTATION_ONLY
Risk: LOW
Orchestrator: Hermes / ChatGPT project lead
Builder: Kimi K3
Branch: chore/TASK-BUILDER-BG-E2E-002-smoke

## Objective
Prove the governed background builder-dispatch path by creating exactly one harmless documentation artifact while the builder runs as the isolated `hermesbuilder` background service.

## In Scope
Create `docs/hermes-os-v3.1/automation/BACKGROUND-BUILDER-E2E-SMOKE.md` with:
- task id `TASK-BUILDER-BG-E2E-002`;
- the statement `KIMI_K3_BACKGROUND_BUILDER_OK`;
- the current branch name;
- a short statement that no production code was changed.

## Allowed Files
- `docs/hermes-os-v3.1/automation/BACKGROUND-BUILDER-E2E-SMOKE.md`

## Protected Areas
Everything else is protected.

## Must Remain Unchanged
- all production/application code;
- HOS runtime semantics;
- tests;
- schemas;
- policies;
- existing documents;
- main branch.

## Required Validation
- `git status --short` before and after;
- confirm only the allowed file changed;
- commit the change on the assigned task branch.

## Stop Conditions
Stop without making broader changes if the allowed file cannot be created exactly as specified.

## Acceptance Criteria
1. Exactly one allowed file is added.
2. It contains `KIMI_K3_BACKGROUND_BUILDER_OK`.
3. A new candidate commit exists on the assigned branch.
4. No protected file is changed.
5. The worker publishes candidate SHA and HOS gate receipt to `hermes-control`.
