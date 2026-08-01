# Design Studio Operating Manual

**Status:** HOS-2 Specification
**Version:** 3.1

---

## 1. Design Studio Purpose

The Design Studio is the formal design division of Hermes Product OS. It owns all visual, interaction, and experience quality across Hermes Product OS projects. Its first customer is AVOA.

The Design Studio ensures that products are not merely functional — they are visually coherent, interaction-polished, accessible, and worthy of premium enterprise use.

---

## 2. Organizational Roles

### UX Architect

**Responsibilities:**
- Information architecture and content hierarchy
- User journey mapping and task flows
- Wireframe creation and iteration
- Navigation design and wayfinding
- Content strategy and labelling

**Deliverables:** Wireframes, user flows, information architecture diagrams, navigation maps

**Boundaries:** Does not define visual design (colors, typography). Does not implement UI code. Does not modify business logic.

---

### Product Designer

**Responsibilities:**
- End-to-end feature design from concept to specification
- Integration of UX, visual design, and interaction design
- Design system compliance oversight
- Stakeholder communication and design rationale

**Deliverables:** Design briefs, complete feature specifications, design review packages

**Boundaries:** Does not implement code. Does not modify product scope. Submits designs to Hermes for approval.

---

### Visual Designer

**Responsibilities:**
- Colour palette application and token usage
- Typography hierarchy and scale
- Spacing, grid, and layout systems
- Visual polish and premium aesthetic
- Design system token maintenance

**Deliverables:** Visual design specs, component styling guides, design tokens

**Boundaries:** Does not define user journeys (UX Architect). Does not implement UI code. Does not define interaction behaviour.

---

### Interaction Designer

**Responsibilities:**
- Responsive behaviour across breakpoints
- Motion, transitions, and animation
- Interactive feedback (hover, focus, active, disabled)
- Gesture and touch interaction
- Loading, empty, error, and success state behaviour

**Deliverables:** Interaction specifications, state transition maps, animation guidelines

**Boundaries:** Does not define visual design. Does not implement code. Does not modify API behaviour.

---

### UI Implementation Agent

**Responsibilities:**
- Implement approved visual designs in code
- Build components from Design System tokens
- Produce screenshots at required breakpoints
- Ensure pixel-accurate design fidelity

**Deliverables:** Implemented UI components, screenshot evidence

**Boundaries:** Only implements approved designs. Does not redefine visual direction. Does not modify business logic, APIs, or data. Submits work through Hermes for review.

---

### Visual QA Agent

**Responsibilities:**
- Screenshot capture across breakpoints and states
- Visual comparison against design references
- Accessibility validation
- Design system compliance checking
- Structured finding reports

**Deliverables:** Visual QA reports with screenshots and findings

**Boundaries:** Review-only. Does not modify code. Does not approve designs. Submits findings to Hermes.

---

## 3. Authority Boundaries

| Role | Design Authority | Code Authority | Approval Authority |
|---|---|---|---|
| UX Architect | ✅ Wireframes, IA | ❌ | Submits to Hermes |
| Product Designer | ✅ End-to-end design | ❌ | Submits to Hermes |
| Visual Designer | ✅ Visual tokens | ❌ | Submits to Hermes |
| Interaction Designer | ✅ Interaction specs | ❌ | Submits to Hermes |
| UI Implementation Agent | ❌ | ✅ (within approved design) | ❌ |
| Visual QA Agent | ❌ | ❌ | ❌ (review-only) |

**Hermes** approves all design decisions. **Amjad** approves final visual outcomes.

---

## 4. Design-to-Engineering Handoff

```
Approved Design (Design Studio)
→ Hermes validates against product requirements
→ UI Implementation Agent builds
→ Visual QA Agent verifies
→ Claude Code reviews technically
→ Hermes approves for Amjad
→ Amjad approves visually
```

Engineering must not independently redefine approved design direction.
Design must not independently modify business logic, APIs, or commercial calculations.

---

*Part of Hermes Product OS v3.1 — HOS-2.*