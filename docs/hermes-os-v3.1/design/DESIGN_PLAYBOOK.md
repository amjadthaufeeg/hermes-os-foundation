# Design Studio Playbook

**Status:** HOS-2 Specification
**Version:** 3.1

---

## 1. How UX Is Created

1. Product Designer receives requirement from Hermes (with context, user goal, business outcome).
2. UX Architect maps information architecture and user journey.
3. Wireframes created at appropriate fidelity for the task risk level.
4. UX Architect submits wireframes to Product Designer for integration review.
5. Product Designer presents to Hermes for approval.

**R1 tasks** may skip full wireframing if using established patterns.

---

## 2. How Wireframes Are Approved

1. Wireframes submitted as design artifacts with annotations.
2. Product Designer verifies alignment with requirements.
3. Hermes evaluates against task contract and business goals.
4. Amjad reviews for R2+ tasks where visual impact is significant.
5. Approved wireframes become the binding reference for visual design and implementation.

---

## 3. How Design Reviews Work

1. Implementation completed with screenshot evidence.
2. Visual QA Agent captures screenshots at all required breakpoints and states.
3. Visual QA Agent compares against approved design reference.
4. Findings submitted to Hermes with severity classification.
5. Hermes accepts, rejects, or defers each finding.
6. Accepted findings become approved corrections for UI Implementation Agent.
7. Cycle repeats until Visual QA passes.

---

## 4. How Visual QA Works

1. Receive approved design reference and UI contract.
2. Capture screenshots: desktop (1440px), tablet (768px), mobile (375px).
3. Capture every required state: default, loading, empty, error, success, disabled.
4. Check: hierarchy, spacing, typography, alignment, white space, consistency, accessibility, responsive behaviour, loading/empty/error/success states, polish, design system compliance.
5. Report structured findings with evidence (screenshots, annotations).
6. Visual QA is review-only — does not modify code.

---

## 5. How Accessibility Is Reviewed

1. Accessibility Baseline defines minimum requirements (WCAG 2.1 AA).
2. Visual QA Agent runs automated checks (axe-core).
3. Manual keyboard navigation test.
4. Colour contrast verification.
5. Focus order check.
6. Screen reader label verification.
7. Findings reported to Hermes.

---

## 6. How Design Regressions Are Prevented

1. Approved designs stored in `docs/design/approved/` as frozen references.
2. Design system tokens version-controlled in the repository.
3. Visual QA compares every implementation against the frozen reference.
4. Regression tests flag any visual deviation.
5. Design decisions recorded as decision records (DES-XXX).

---

## 7. How Design Decisions Are Stored

1. Major design decisions → Decision Register (`DES-NNN`).
2. Design system token changes → Version-controlled in design system documentation.
3. Component specifications → Component Library specification.
4. Approved design references → `docs/design/approved/` directory.

---

## 8. How Design System Evolves

1. Any designer or developer may propose a change via Hermes.
2. Product Designer evaluates against existing patterns and consistency.
3. Hermes approves or rejects.
4. If approved: update design system documentation, update tokens, update component library.
5. Version the change.
6. Retroactively apply to existing components only if warranted.

---

## 9. How Components Become Official

1. Component proposed with purpose, variants, states, accessibility, and usage constraints.
2. Product Designer reviews against existing component library.
3. Visual Designer creates design tokens.
4. UX Architect validates interaction patterns.
5. Hermes approves.
6. Component added to Component Library specification.
7. UI Implementation Agent builds reference implementation.
8. Visual QA Agent validates.
9. Component available for use in HOS-3+.

---

## 10. Design Workflow Summary

```
Requirement → UX → Wireframe → Visual Design → Approval → Implementation → Visual QA → Hermes Review → Technical Review → Final Validation → Amjad Approval
```

Shortened for R1 tasks using established patterns.

---

*Part of Hermes Product OS v3.1 — HOS-2.*