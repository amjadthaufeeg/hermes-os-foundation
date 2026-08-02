# HOS-3 — Implementation Documentation

**Status:** Implementing | **Release:** HOS-3

This file contains deliverables 3-10 of the HOS-3 package. All content is derived from the approved HOS-3-PLANNING.md specification.

---

## 3. HERMES EXPERIENCE LANGUAGE v1.0

### Core Purpose
Reduce uncertainty in complex operational work. Help Amjad make better decisions with greater confidence.

### Emotional Qualities
Calm, trustworthy, controlled, precise, premium, focused, operational, intelligent without theatre.

### Primary Principle
**Reduce uncertainty before increasing speed.**

### Principles → Rules

| # | Principle | Required Behaviour | Approved Example | Prohibited Example | Validation |
|---|---|---|---|---|---|
| 1 | One obvious next action | Primary action visually dominant; secondary actions subordinate | "Review Decision" gold button; "Defer" muted link | Three equally-weighted buttons | Visual QA: primary action contrast check |
| 2 | Information before controls | Show evidence, then offer actions | Decision card: title → reason → risk → DECIDE button | Button without context | Card must contain ≥2 info fields before action |
| 3 | Progressive disclosure | Summary visible; detail on click | Capability rows: name + badge; expand for full spec | All 17 status fields visible at once | Count expanded vs collapsed rows |
| 4 | Safe decision presentation | Confirm before action; undo path visible | "This decision will lock the record. Continue?" before submit | Instant delete without confirmation | Confirm dialog present for all actions |
| 5 | Quiet confidence | No shouting, no drama, no inflated claims | "3 decisions waiting" — factual, not "URGENT!!!" | "CRITICAL ALERT: 3 DECISIONS OVERDUE" | Language audit: no ALL CAPS, no exclamation marks |
| 6 | Evidence before claims | Every status shows source + freshness | "Source: .hermes/registers/decisions · 1 Aug" | "System is healthy" with no supporting data | Every status badge must have source annotation |
| 7 | Recognition before memory | Don't make users remember previous state | Navigation highlights active section; breadcrumbs present | Flat page with no context indicator | Active nav state visible; page title present |
| 8 | Consistency before cleverness | Reuse patterns; novelty is a cost | All cards use same padding, border, header style | Unique card design per section | Component audit: ≤3 card variants |
| 9 | Errors educate | Explain what happened and what to do next | "GitHub API unavailable. Last known data from 2h ago. Retry?" | "Error 500" | Error states must contain: what, why, next step |
| 10 | Visual silence | Decoration without operational value is noise | 1px borders at 50% opacity; no gradients; no shadows | Decorative gradients, box shadows, coloured backgrounds | No `box-shadow` on static elements |

### Personality Dimensions → Interface Rules

| Dimension | Score | Means | Designers Should | Designers Should Avoid | Example (Do) | Example (Don't) |
|---|---|---|---|---|---|---|
| Enterprise | 95 | B2B tool, not consumer app | Professional layouts, clear hierarchy, no gamification | Badges, emoji, confetti, casual language | Status badges in muted tones | "Great job! 🎉" after task completion |
| Premium | 80 | Quality through restraint | Refined spacing, intentional typography, gold reserved for authority | Cheap gradients, clip art, excessive decoration | Gold accent on decision items only | Gold used as decorative background |
| Calm | 95 | No surprises, predictable | Low contrast backgrounds, minimal motion, steady indicators | Busy animations, flashing alerts, aggressive red | Steady amber for attention/pending | Pulsing red alert for non-critical item |
| Minimal | 70 | Essential only | Show only what's needed; progressive disclosure | Dashboard sprawl, every metric shown, data dumping | 10 panels on overview; details behind click | 40 KPI cards on one screen |
| Human | 60 | Direct, helpful | Natural language, helpful errors, readable labels | Cold technical jargon in user-facing text | "This decision needs your review" | "Entity DEC-HOS-001 requires state transition approval" |
| Quiet | 90 | Subtle, not loud | Muted indicators, text over icons, restrained language | Loud notifications, aggressive red, shouty text | Muted amber for HOLD, not red | Red "OVERDUE!!!" badge for pending decision |
| Invisible UI | 95 | Content first | Minimal chrome, thin borders, no unnecessary cards | Thick borders, heavy shadows, nested cards, decorative frames | 1px borders at 50% opacity; no shadows | 3px coloured borders, box-shadow cards, gradient headers |

---

## 4. HERMES DESIGN TOKENS

### Colour Tokens (CSS Custom Properties)

```css
:root {
  /* Backgrounds */
  --hermes-bg-primary: #0a0e14;
  --hermes-bg-surface: #11161d;
  --hermes-bg-elevated: #181d26;
  
  /* Borders */
  --hermes-border: #1a2030;
  --hermes-border-dim: rgba(26,32,48,0.5);
  
  /* Text */
  --hermes-text-primary: #cfd4db;
  --hermes-text-secondary: #8899b4;
  --hermes-text-muted: #5c6470;
  
  /* Semantic: Authority */
  --hermes-gold: #c9a03b;
  --hermes-gold-dim: rgba(201,160,59,0.12);
  
  /* Semantic: Execution */
  --hermes-cyan: #26c6da;
  --hermes-cyan-dim: rgba(38,198,218,0.10);
  
  /* Semantic: Verified */
  --hermes-green: #34c97a;
  --hermes-green-dim: rgba(52,201,122,0.12);
  
  /* Semantic: Blocker */
  --hermes-red: #e0556a;
  --hermes-red-dim: rgba(224,85,106,0.10);
  
  /* Semantic: Attention/Pending (L-1 resolved) */
  --hermes-amber: #d4a843;
  --hermes-amber-dim: rgba(212,168,67,0.12);
  
  /* States */
  --hermes-focus: #26c6da;
  --hermes-disabled: #3a3f4a;
  --hermes-stale: #5c6470;
}
```

### Semantic Status Mapping

| Status | Token | Icon | Text Example |
|---|---|---|---|
| ACTIVE, PASSED, CLOSED | `--hermes-green` | ✓ | "CLOSED" |
| DECIDE, LOCKED, AWAITING_AMJAD | `--hermes-gold` | ◆ | "DECIDE" |
| BUILDING, IN_PROGRESS, IN_REVIEW | `--hermes-cyan` | ⬡ | "BUILDING" |
| BLOCKED, FAILED | `--hermes-red` | ✗ | "BLOCKED" |
| HOLD, PENDING, ATTENTION | `--hermes-amber` | ◇ | "AWAITING" |
| INACTIVE, UNKNOWN, NOT_IMPLEMENTED | `--hermes-text-muted` | ◌ | "INACTIVE" |
| STALE, UNAVAILABLE | `--hermes-stale` | ⬒ | "STALE" |

### Typography Tokens

```css
:root {
  - **Font stack:** 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif (Inter preferred when available locally; zero external dependency)
  --hermes-font-mono: 'JetBrains Mono', 'SF Mono', monospace;
  --hermes-text-display: 700 1.5rem/1.3 var(--hermes-font);
  --hermes-text-heading: 600 1.1rem/1.4 var(--hermes-font);
  --hermes-text-card-title: 600 0.72rem/1.4 var(--hermes-font);
  --hermes-text-body: 400 0.78rem/1.5 var(--hermes-font);
  --hermes-text-label: 400 0.72rem/1.4 var(--hermes-font);
  --hermes-text-metadata: 400 0.65rem/1.4 var(--hermes-font);
  --hermes-text-code: 400 0.7rem/1.5 var(--hermes-font-mono);
}
```

### Spacing, Radius, Motion Tokens

```css
:root {
  --hermes-space-1: 4px; --hermes-space-2: 8px; --hermes-space-3: 12px;
  --hermes-space-4: 16px; --hermes-space-5: 20px; --hermes-space-6: 24px;
  --hermes-space-8: 32px; --hermes-space-10: 40px; --hermes-space-12: 48px;
  --hermes-radius-card: 6px; --hermes-radius-badge: 10px; --hermes-radius-button: 6px;
  --hermes-motion-fast: 150ms ease; --hermes-motion-normal: 250ms ease;
}
```

---

## 5. HERMES COMPONENT STANDARD

(AppShell through NotificationIndicator — specifications as per HOS-3-PLANNING §8. Full detail in the component library.)

### Priority Components (Mission Control)

| Component | Purpose | Variants | States |
|---|---|---|---|
| AppShell | Root layout | default | — |
| Sidebar | Navigation | expanded, collapsed | default, active item |
| MetricCard | KPI display | gold, cyan, red | default, no-data |
| StatusBadge | Status label | 17 status values | — |
| DecisionCard | Decision item | default, urgent | review, defer |
| ExecutionCard | Work item | default | building, validating, blocked |
| CapabilityRow | Capability status | complete, placeholder | inactive, unknown |
| Timeline | Chronological list | default | empty |
| EmptyState | No data | default | — |

30 components specified; 9 prioritized for MC. Remaining deferred to future screens.

---

## 6. HERMES INTERACTION STANDARD

### Standard Behaviours

| Interaction | Behaviour | Duration | Reduced Motion |
|---|---|---|---|
| Hover | Background shift: rgba(255,255,255,0.02) | Instant | No effect |
| Focus | Cyan 2px ring, visible on all elements | Instant | Always visible |
| Selection | Left border + background highlight | Instant | Instant |
| Disclosure open | Height transition | 150ms ease | Instant |
| Loading >1s | Skeleton placeholder | — | Static skeleton |
| Keyboard nav | Tab through; Enter selects; Escape closes | — | — |
| Status change | Subtle colour transition | 250ms ease | Instant |

### Keyboard

- Tab order: Sidebar → Main content (top to bottom) → Footer
- Enter: Activate selected nav item or button
- Escape: Close disclosure, modal, or collapse detail
- Arrow keys: Navigate within timelines and lists

---

## 7. HERMES ACCESSIBILITY STANDARD

**Target: WCAG 2.1 AA**

### Requirements

| Requirement | Implementation |
|---|---|
| Semantic landmarks | `<nav>`, `<main>`, `<header>`, `<footer>` with labels |
| Heading hierarchy | h1 (page), h2 (sections), h3 (cards) |
| Keyboard | All interactive: `role="button"` + `tabindex="0"` |
| Focus | Cyan 2px ring, no `outline: none` |
| Contrast | 4.5:1 text, 3:1 large text |
| Status text | Always paired with colour indicator |
| ARIA | `aria-label`, `aria-current`, `aria-hidden` on icons |
| Reduced motion | `@media (prefers-reduced-motion: reduce)` |
| Touch targets | Minimum 44×44px |

---

## 8. MISSION CONTROL REFINEMENT PLAN

### L-1 Resolution: Amber Formalized

Added to token system as `--hermes-amber`. Used for HOLD, PENDING, AWAITING_AMJAD. Applied to HOS-3 timeline badge. Dead CSS (`--amber-dim`) activated.

### L-2 Resolution: Typography

Inter added via Google Fonts with `font-display: swap`. System-ui fallback preserved. Mono stack added for code/commits.

### L-3 Resolution: Badge Noise

Capability rows now collapsed by default for placeholder entries. Full detail behind click/expand. Essential statuses remain visible: first 3 capabilities shown; remaining 5 collapsed with "Show all (5)" toggle.

### Quality Target: 9.5/10

---

## 9. HOS-2.5 LOW FINDINGS DISPOSITION

| ID | Finding | Status | Evidence |
|---|---|---|---|
| L-1 | Amber outside palette | **RESOLVED** | `--hermes-amber` token defined; used for HOLD/PENDING/ATTENTION only |
| L-2 | System font stack | **RESOLVED** | Inter-preferred stack with system-ui fallback; zero external font dependency |
| L-3 | Muted badge noise | **RESOLVED** | Collapse pattern applied to Capability rows; "Show all" toggle |

---

## 10. HOS-3 VISUAL QA PLAN

### Screenshots Required

Desktop (1440), tablet (768), mobile (390). States: default, expanded, collapsed, AWAITING_AMJAD, ATTENTION, STALE, UNAVAILABLE, keyboard-focus.

### Review Criteria

Token consistency, typography, hierarchy, status clarity, reduced noise, responsive quality, decision-first layout, no generic SaaS styling.

### Target: 9.5/10

---

*Part of Hermes Product OS v3.2 — HOS-3 Implementation.*