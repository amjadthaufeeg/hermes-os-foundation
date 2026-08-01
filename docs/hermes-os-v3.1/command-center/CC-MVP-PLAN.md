# Hermes Command Center MVP — Implementation Plan

**Status:** HOS-2.5 | **Prototype:** Complete | **Connectivity:** NOT_IMPLEMENTED

---

## Purpose

First operational executive dashboard for Hermes Product OS. Uses existing governance records only. No runtime capability activation. No fabricated data.

## Prototype

`executive-dashboard.html` — 10 panels, dark theme, AVOA navy/gold palette. Self-contained HTML, no build step, no dependencies.

## Information Architecture

```
Command Center
├── Executive Dashboard (MVP)
│   ├── 1. Current Projects
│   ├── 2. Items Awaiting Amjad
│   ├── 3. Active Work
│   ├── 4. Capability Status
│   ├── 5. Hermes Status
│   ├── 6. Recent Releases
│   ├── 7. Current Priorities
│   ├── 8. Recent Decisions
│   ├── 9. Review Queue
│   └── 10. System Health
├── Engineering Dashboard (future)
├── Design Dashboard (future)
└── Operations Dashboard (future)
```

## Data Sources

Every displayed value is sourced from existing governance records:

| Panel | Source |
|---|---|
| Projects | Repository existence + AGENTS.md |
| Awaiting Amjad | v3.2 status doc |
| Active Work | Current Git branches, PRs |
| Capability Status | v3.2 capability definitions |
| Hermes Status | v3.2 maturity classification |
| Recent Releases | Git merge history |
| Priorities | v3.2 closure report |
| Decisions | Decision register (.hermes/registers/decisions/) |
| Review Queue | GitHub PR API |
| System Health | GitHub Actions API, branch protection |

## Connectivity Plan

| Phase | Data Source | Status |
|---|---|---|
| Phase 1 (current) | Static HTML with hardcoded truthful values | ✅ COMPLETE |
| Phase 2 | Read from governance YAML/JSON files | NOT_IMPLEMENTED |
| Phase 3 | GitHub API integration (PRs, CI, branches) | NOT_IMPLEMENTED |
| Phase 4 | Task contract state machine integration | NOT_IMPLEMENTED |
| Phase 5 | Capability Manager health reporting | NOT_IMPLEMENTED |

## Non-Fabrication Guarantees

- Every metric that has no data source shows NO_BASELINE or UNKNOWN.
- No capability shows HEALTHY without runtime evidence.
- No loop is shown as active.
- No delivery metric has an invented value.
- The dashboard displays "NOT_IMPLEMENTED" for any future feature.

## Rollback

Remove `command-center/` directory. Revert commit. No production impact.