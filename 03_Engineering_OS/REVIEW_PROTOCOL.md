# Claude Code Review Protocol

## Inputs
- original request;
- approved change contract;
- relevant locked decisions;
- base and candidate commits;
- complete diff;
- automated validation evidence.

## First-pass mode
Read-only. Claude reports findings before any code modification.

## Required checks
- objective achieved;
- allowed-file scope respected;
- protected behavior preserved;
- unrelated refactoring absent;
- regressions and edge cases;
- tests and evidence adequate;
- security and data risks;
- builder report matches actual diff.

## Result
- PASS
- PASS WITH REQUIRED FIXES
- FAIL — SCOPE VIOLATION
- FAIL — REGRESSION
- FAIL — INSUFFICIENT EVIDENCE

Findings are Blocker, High, Medium, Low, or Optional. Hermes decides which findings become approved correction work.
