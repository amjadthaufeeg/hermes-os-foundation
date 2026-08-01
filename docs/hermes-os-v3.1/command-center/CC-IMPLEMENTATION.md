# HOS-2.5 — Implementation Planning Package

**Status:** READY_FOR_AMJAD | **Precedes:** Any coding

---

## UI Contract

```yaml
task_id: TASK-HOS-2.5
design_owner: hermes
required_states: [default, no-decisions, blocked, unavailable-data, stale-evidence]
required_breakpoints: [mobile, tablet, desktop]
visual_acceptance_criteria:
  - "Dark graphite background, not pure black"
  - "Gold accents for authority and decisions"
  - "Cyan for live work and execution"
  - "Green only for verified passing states"
  - "Red only for genuine blockers"
  - "Calm, premium, executive feel"
  - "No fake progress rings"
  - "No unnecessary charts"
required_visual_evidence:
  - {type: screenshot, breakpoint: desktop, state: default}
  - {type: screenshot, breakpoint: tablet, state: default}
  - {type: screenshot, breakpoint: mobile, state: default}
  - {type: screenshot, breakpoint: desktop, state: no-decisions}
  - {type: screenshot, breakpoint: desktop, state: blocked}
  - {type: screenshot, breakpoint: desktop, state: unavailable-data}
  - {type: screenshot, breakpoint: desktop, state: stale-evidence}
```

## Architecture Decision

**Framework:** Plain HTML/CSS. No React. No Next.js. No build step.

**Reason:** The dashboard reads static governance records. No server-side rendering needed. Self-contained HTML simplifies deployment and eliminates dependency risk. Can be served from any static host or opened directly. Aligns with "calm, premium, operational" — not a web app, an executive console.

**Location:** `docs/hermes-os-v3.1/command-center/`

## File Manifest

| File | Purpose |
|---|---|
| `executive-dashboard.html` | Production-quality dashboard (replaces prototype) |
| `TASK-HOS-2.5.yaml` | Task contract |
| `CC-IMPLEMENTATION.md` | This planning package |
| `CC-MVP-PLAN.md` | Connectivity plan (existing, updated) |

| # | Component | Type | States |
|---|---|---|---|
| 1 | AppShell | Layout | default |
| 2 | Sidebar | Navigation | collapsed (mobile), expanded (desktop) |
| 3 | Header | Display | default, stale-evidence |
| 4 | SystemStatus | Indicator | healthy, degraded, unknown |
| 5 | MissionSummary | Card | default, no-data |
| 6 | DecisionQueue | List | default, empty |
| 7 | DecisionItem | Row | default, urgent, review, defer |
| 8 | LiveExecution | List | default, empty |
| 9 | ExecutionItem | Row | building, validating, review, awaiting, blocked |
| 10 | MissionStatus | Card | default |
| 11 | CapabilityStatus | List | default |
| 12 | CapabilityRow | Row | inactive, unknown |
| 13 | MissionTimeline | Timeline | default, empty |
| 14 | ReleaseCard | Card | default |
| 15 | DecisionTimeline | Timeline | default, empty |
| 16 | EvidenceFreshness | Indicator | fresh, stale, unavailable |
| 17 | EmptyState | Placeholder | — |
| 18 | UnavailableState | Placeholder | — |
| 19 | LoadingState | Placeholder | — |
| 20 | ErrorState | Placeholder | — |

## Routes

| Route | View | Panel IDs |
|---|---|---|
| `/` | Mission Overview | A-J (all) |
| `/decisions` | Decisions | DecisionQueue, DecisionTimeline |
| `/execution` | Execution | LiveExecution, MissionStatus |
| `/products` | Products | Placeholder |
| `/capabilities` | Capabilities | CapabilityStatus |
| `/releases` | Releases | MissionTimeline |
| `/evidence` | Evidence | EvidenceFreshness, placeholder |
| `/settings` | Settings | Placeholder |

## Data-Source Matrix

| Dashboard Field | Source | Freshness | Fallback | Trust |
|---|---|---|---|---|
| Decisions Waiting | `.hermes/registers/decisions/` | On load | NO DATA | HIGH |
| Blockers | v3.2 current-status | On load | UNKNOWN | MEDIUM |
| Active Deliveries | Git branch + PR API | On load | NO DATA | HIGH |
| Hermes Maturity | v3.2 spec | Manual | UNKNOWN | HIGH |
| Runtime Loops | v3.2 spec | Manual | NOT_IMPLEMENTED | HIGH |
| Capability Status | v3.2 capability defs | Manual | NOT_IMPLEMENTED | HIGH |
| CI Status | GitHub Actions API | API call | UNKNOWN | HIGH |
| Release History | Git log | On load | NO DATA | HIGH |
| Decision Records | `.hermes/registers/decisions/` | On load | NO DATA | HIGH |
| PR Status | GitHub PR API | API call | NO DATA | HIGH |

## Responsive Plan

| Breakpoint | Layout | Navigation | Columns |
|---|---|---|---|
| Desktop (≥1024px) | Full | Left sidebar, always visible | 2-3 column grid |
| Tablet (768-1023px) | Condensed | Collapsible sidebar | 2 column |
| Mobile (<768px) | Single column | Bottom bar or hamburger | Single column, decisions first |

## Accessibility Plan

- Semantic HTML: `<nav>`, `<main>`, `<section>`, `<article>`, `<aside>`
- Keyboard: Tab order logical, all interactive elements reachable
- Focus: Visible focus ring on all interactive elements
- Labels: All status indicators have text alternatives
- Contrast: 4.5:1 minimum for all text
- Headings: h1-h3 hierarchy preserved
- Reduced motion: `prefers-reduced-motion` respected
- Screen reader: ARIA live regions for dynamic status updates

## CI Plan

- Schema validation of TASK-HOS-2.5.yaml
- Scope check against allowed files
- Protected-zone check
- Standard governance workflow

## Independent Review Plan

Reviewer: Claude Code (read-only). Scope: visual fidelity to reference, data truthfulness, no fabrication, responsive behaviour, accessibility, scope compliance, protected-area compliance, code quality.

## Rollback

```bash
git revert <merge-commit>
# Or: delete command-center/ directory
```

## Deferred Functionality

- Decision mutation (approve/reject/defer)
- Real-time data refresh
- Capability Manager health reporting
- Loop Controller status
- Delivery metrics dashboard
- Full Command Center implementation
- Backend API server
- Authentication

---

*Part of Hermes Product OS v3.2 — HOS-2.5 Planning.*