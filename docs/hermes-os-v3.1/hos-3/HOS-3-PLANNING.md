# HOS-3 — Hermes Experience Language and Mission Control Refinement

**Status:** Planning | **Release:** HOS-3 | **Requires:** Amjad approval before implementation

---

## 1. Verified HOS-2.5 LOW Findings

Retrieved from final visual review (8.5/10, commit `6a87fe2`):

| # | Finding | Type | HOS-3 Resolution |
|---|---|---|---|
| L-1 | Amber hold color outside approved palette — dead CSS, semantic need | Visual design | **Formalize amber as official "attention/pending" status colour in Experience Language** |
| L-2 | System font stack not premium — functional but generic | Typography | **Specify premium font stack in design tokens (Inter or equivalent)** |
| L-3 | Repetitive muted badge noise — honest but visually static | Information hierarchy | **Collapse repetitive status rows when identical; show summary + expand** |

These are the **only** LOW findings. No findings were invented from memory.

---

## 2. Problem Statement

HOS-2.5 delivered a working, truthful Mission Control MVP (8.5/10 visual score). The MVP proved the design direction: dark graphite, gold authority, cyan execution, green verified, red blockers, decision-first hierarchy, zero fabrication. 

However, the MVP has no formal experience language, no design token system, no component standard, no accessibility baseline, and no scalability rules. Every future screen would require reinvention. 

HOS-3 formalizes what works into a reusable system.

## 3. Scope

- Hermes Experience Language v1.0
- Visual design tokens (colour, typography, spacing, radius, border, elevation, motion)
- Semantic status language (17 states)
- Component standard (30+ components, purpose/anatomy/states)
- Interaction standard (hover, focus, selection, keyboard, motion)
- Accessibility baseline (WCAG 2.1 AA)
- Mission Control refinement (3 LOW findings + quality improvements)
- Placeholder route design plan (7 routes)
- Responsive system specification
- Content and microcopy rules

## 4. Non-Scope

No backend, no loops, no capabilities, no automation, no authentication, no live-data expansion, no AVOA changes, no production deployment, no write actions.

## 5. Hermes Experience Language v1.0

### Core Purpose
Reduce uncertainty in complex operational work. Help Amjad make better decisions with greater confidence.

### Emotional Qualities
Calm, trustworthy, controlled, precise, premium, focused, operational, intelligent without theatre.

### Primary Principle
**Reduce uncertainty before increasing speed.**

### Supporting Principles
1. **One obvious next action.** Every screen has a clear primary path.
2. **Information before controls.** Show evidence, then offer actions.
3. **Progressive disclosure.** Show summary; details on demand.
4. **Important decisions should feel safe.** Confirm, don't surprise.
5. **The interface must not compete with the data.** Minimal chrome, maximal clarity.
6. **Consistency beats cleverness.** Reuse patterns. Novelty is a cost.
7. **Recognition before memory.** Don't make users remember previous state.
8. **Every screen answers:** Where am I? What's happening? What needs attention? What can I do? What happens next?
9. **Quiet confidence.** No shouting, no drama, no inflated claims.
10. **Visual silence.** Decoration that provides no operational value is noise.

### Personality Dimensions → Interface Rules

| Dimension | Rule | Avoid | Example |
|---|---|---|---|
| Enterprise 95 | Professional layouts, no gamification | Consumer-style badges, emoji | status badges, not confetti |
| Premium 80 | Refined spacing, intentional typography | Cheap gradients, clip art | Gold accents on decisions only |
| Calm 95 | Low contrast backgrounds, minimal motion | Busy animations, flashing alerts | Steady amber for attention |
| Minimal 70 | Essential information only | Dashboard sprawl, every metric shown | Progressive disclosure |
| Human 60 | Direct language, helpful errors | Cold technical jargon in user-facing text | "This decision needs your review" |
| Conservative 40 | Tried patterns, predictable layout | Experimental UX that surprises | Familiar card + sidebar layout |
| Quiet 90 | Subtle indicators, text over icons | Loud notifications, aggressive red | Muted amber for HOLD, not red |
| Invisible UI 95 | Content first, chrome minimal | Thick borders, heavy shadows, nested cards | 1px borders at 50% opacity |

## 6. Design Tokens

### Colour Tokens

```
--hermes-bg-primary: #0a0e14
--hermes-bg-surface: #11161d
--hermes-bg-elevated: #181d26
--hermes-border: #1a2030
--hermes-text-primary: #cfd4db
--hermes-text-secondary: #8899b4
--hermes-text-muted: #5c6470
--hermes-gold: #c9a03b
--hermes-gold-dim: rgba(201,160,59,0.12)
--hermes-cyan: #26c6da
--hermes-cyan-dim: rgba(38,198,218,0.10)
--hermes-green: #34c97a
--hermes-green-dim: rgba(52,201,122,0.12)
--hermes-red: #e0556a
--hermes-red-dim: rgba(224,85,106,0.10)
--hermes-amber: #d4a843
--hermes-amber-dim: rgba(212,168,67,0.12)
--hermes-focus: #26c6da
--hermes-disabled: #3a3f4a
--hermes-stale: #5c6470
```

### Semantic Status Colours

| Status | Colour | Icon |
|---|---|---|
| ACTIVE / PASSED / CLOSED | Green | ✓ |
| DECIDE / LOCKED / ATTENTION | Gold | ◆ |
| BUILDING / IN_PROGRESS | Cyan | ⬡ |
| BLOCKED / FAILED | Red | ✗ |
| HOLD / PENDING / AWAITING | Amber | ◇ |
| INACTIVE / UNKNOWN / NOT_IMPLEMENTED | Muted | ◌ |
| STALE / UNAVAILABLE | Disabled | ⬒ |

### Typography

- **Font stack:** 'Inter', system-ui, -apple-system, sans-serif
- **Display:** 1.5rem / 700 / -0.02em (page titles)
- **Heading:** 1.1rem / 600 / -0.01em (section headers)
- **Card title:** 0.72rem / 600 / 0.06em / uppercase
- **Body:** 0.78rem / 400 / 1.5
- **Label:** 0.72rem / 400
- **Metadata:** 0.65rem / 400 / muted
- **Numbers:** tabular-nums / 500-700 weight
- **Code:** 'JetBrains Mono', monospace / 0.7rem

### Spacing Scale

4px base: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64

### Radius

- Cards: 6px
- Badges: 10px (pill)
- Buttons: 6px
- Overlays: 8px

### Borders

- Default: 1px solid `--hermes-border`
- Row divider: 1px solid, 50% opacity

## 7. Semantic Status Language (17 states)

| Status | Meaning | Colour | When NOT to use |
|---|---|---|---|
| PLANNED | Spec exists, not built | Muted | Don't imply readiness |
| SPECIFIED | Design complete | Muted | Not operational |
| NOT_IMPLEMENTED | Not built | Muted | Don't use for failed builds |
| IMPLEMENTED | Built, not activated | Muted | Not proven |
| INACTIVE | Not running | Muted | Don't use for stopped-by-error |
| ACTIVE | Running | Green | Requires evidence |
| UNKNOWN | Cannot determine | Muted | Be honest |
| NOT_MEASURED | No data collected | Muted | Better than guessing |
| NO_BASELINE | Reference missing | Muted | No targets yet |
| STALE | Evidence outdated | Disabled | Must show last refresh |
| UNAVAILABLE | Source down | Disabled | Show reason |
| BLOCKED | Cannot proceed | Red | Show blocker detail |
| FAILED | Verification failed | Red | Show failure evidence |
| PASSED | Verification passed | Green | Show evidence freshness |
| AWAITING_AMJAD | Human decision needed | Gold | Label the decision |
| IN_REVIEW | Under evaluation | Cyan | Show reviewer |
| CLOSED | Completed | Green | Show close date |

**No HEALTHY status without runtime evidence.**

## 8. Component Standard (30 components)

| Component | Purpose | Variants | States |
|---|---|---|---|
| AppShell | Root layout container | default | — |
| Sidebar | Primary navigation | expanded, collapsed | default, active item |
| TopHeader | Page header + status | default | default, stale |
| PageHeader | Screen title area | default | — |
| MetricCard | KPI display | gold, cyan, red | default, no-data |
| StatusCard | Status display | default | default |
| DecisionCard | Decision item | default, urgent | review, defer |
| BlockerCard | Blocker display | default, critical | default |
| ExecutionCard | Work item | default | building, validating, review, blocked |
| CapabilityRow | Capability status | complete, placeholder | inactive, unknown |
| EvidenceBadge | Trust indicator | fresh, stale, unavailable | — |
| FreshnessIndicator | Data age | fresh, stale, unknown | — |
| StatusBadge | Status label | all 17 statuses | — |
| Timeline | Chronological list | default | empty |
| ReleaseCard | Release entry | closed, pending | — |
| DecisionRecord | Decision entry | locked, proposed | — |
| EmptyState | No data | default | — |
| UnknownState | Cannot determine | default | — |
| UnavailableState | Source down | default | — |
| StaleState | Old data | default | — |
| ErrorState | Error occurred | default | — |
| LoadingState | Loading | skeleton, spinner | — |
| Button | Action trigger | primary(gold), secondary, danger | default, hover, focus, disabled |
| NavigationItem | Nav link | default, active | default, active |
| Tabs | Content switching | default | active tab |
| DataTable | Structured data | default, compact | loading, empty, error |
| DetailPanel | Expandable info | default | open, closed |
| Modal | Focused action | confirmation, detail | open, closed |
| Tooltip | Context help | default | visible, hidden |
| NotificationIndicator | Alert count | default | count, none |

## 9. Interaction Standard

- **Hover:** Subtle background shift (rgba white 2%)
- **Focus:** Visible cyan ring, 2px
- **Selection:** Active state via left border + background
- **Opening details:** Smooth height transition, 150ms
- **Returning:** Back button or breadcrumb
- **Progressive disclosure:** Click to expand, collapse to summary
- **Stale data:** Show last-refresh timestamp + stale badge
- **Unavailable:** Show reason + retry state (read-only)
- **Loading:** Skeleton preferred over spinner for >1s
- **Keyboard:** Tab through nav, Enter to select, Escape to close
- **Reduced motion:** Respect `prefers-reduced-motion`

## 10. Accessibility Baseline

**Target: WCAG 2.1 AA**

- Semantic landmarks: `<nav>`, `<main>`, `<header>`, `<footer>`
- Logical heading hierarchy: h1 → h2 → h3
- Keyboard: All interactive elements reachable via Tab
- Visible focus: Cyan 2px ring on all elements
- Contrast: 4.5:1 minimum for text, 3:1 for large text
- Status independent of colour: text label + colour badge
- Screen reader: ARIA labels on all status indicators
- Reduced motion: Respects system preference
- Touch targets: Minimum 44x44px

## 11. Mission Control Refinement Plan

### Resolve LOW Findings

| Finding | Resolution | Target |
|---|---|---|
| L-1 Amber colour | Add `--hermes-amber` and `--hermes-amber-dim` to token system. Use for HOLD, PENDING, AWAITING states. Remove dead CSS. | HOS-3 |
| L-2 System fonts | Add Inter via Google Fonts with `font-display: swap`. Fallback to system-ui. | HOS-3 |
| L-3 Badge noise | Collapse repetitive INACTIVE/UNKNOWN rows into summary. Add "Show all" expander. | HOS-3 |

### Quality Target: 9.5/10 in next visual review.

## 12. Placeholder Route Design Plan

| Route | Purpose | Implementation | HOS-3? |
|---|---|---|---|
| Decisions | Decision register browser | Read-only list + detail | Placeholder |
| Execution | Active tasks, branches, agents | Task state reader | Placeholder |
| Products | Connected product list | Static product cards | Placeholder |
| Capabilities | Capability health dashboard | Full implementation-ready design | Placeholder |
| Releases | Release history + upcoming | Timeline + detail | Placeholder |
| Evidence | Evidence package browser | Read-only list | Placeholder |
| Settings | User preferences | Static, no writes | Placeholder |

All remain placeholder in HOS-3. Each gets a designed empty/planned state using the component system.

## 13. File Manifest

| # | File | Purpose |
|---|---|---|
| 1 | `TASK-HOS-3.yaml` | Task contract |
| 2 | `HOS-3-PLANNING.md` | This document (all specifications) |

## 14. Change Budget

| Budget | Value | Actual |
|---|---|---|
| max_files | 12 | 2 |
| max_lines | 3,000 | ~500 |
| max_folders | 2 | 1 |

## 15. Rollback

```bash
git revert <future-merge-commit>
```

---

*Planning only. Awaiting Amjad approval before implementation.*