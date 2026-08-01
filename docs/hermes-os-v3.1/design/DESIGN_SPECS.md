# UI Contract, Design Review, Visual QA & Accessibility — HOS-2 Specifications

---

## UI Contract Standard

### When Required
Mandatory for all R2+ visual tasks beginning HOS-3. R1 tasks may use established patterns without formal contract.

### Schema (see `ui-contract.schema.json`)
Required fields: `task_id`, `design_owner`, `required_states`, `required_breakpoints`, `visual_acceptance_criteria`, `required_visual_evidence`.

### Examples

**Low-risk (R1):** Spacing/colour fix → abbreviated contract with existing token references.

**Form flow (R2):** Multi-step quote wizard → full contract with all states, breakpoints, accessibility requirements, visual acceptance criteria.

**Dashboard (R2-R3):** Data-heavy cockpit → contract covering loading, empty, error states; data-density patterns; responsive behaviour.

---

## Design Review Standard

### Workflow
```
Requirement → UX → Wireframe → Visual Design → Approval
→ Implementation → Visual QA → Hermes Review
→ Technical Review → Final → Amjad Approval
```

**R1 shortcut:** Requirement → Implementation → Visual QA → Hermes → Amjad

### Finding Format
```yaml
finding_id: F-DSN-XXX
severity: BLOCKER|HIGH|MEDIUM|LOW|OPTIONAL
category: hierarchy|spacing|typography|alignment|responsive|accessibility|polish|compliance
viewport: mobile|tablet|desktop
description: "..."
recommendation: "..."
```

---

## Visual QA Standard

### Required Screenshots
- Desktop: 1440px
- Tablet: 768px
- Mobile: 375px
- Each required state: default, loading, empty, error, success, disabled

### Review Checklist
Hierarchy, spacing, typography, alignment, white space, consistency, contrast, responsive behaviour, loading/empty/error/success states, interaction feedback, motion, design system compliance, visual polish.

### Status
Visual QA is review-only. Does not modify code. Submits findings to Hermes.

---

## Accessibility Baseline

**Minimum:** WCAG 2.1 AA

| Requirement | Check |
|---|---|
| Keyboard navigation | All interactive elements reachable via Tab |
| Focus visibility | Visible focus ring on all elements |
| Headings | Semantic h1-h6 hierarchy |
| Labels | All inputs have associated labels |
| Colour contrast | 4.5:1 normal, 3:1 large text |
| Forms | Error messages linked via aria-describedby |
| Tables | Headers, captions, row/col scope |
| Dialogs | Focus trap, aria-modal, Escape to close |
| Responsive zoom | Content readable at 200% zoom |
| Reduced motion | Respects prefers-reduced-motion |

**Recommended tooling:** axe-core for CI, eslint-plugin-jsx-a11y for linting.

---

*Part of Hermes Product OS v3.1 — HOS-2.*