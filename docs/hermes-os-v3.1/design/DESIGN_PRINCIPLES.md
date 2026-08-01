# AVOA Design Principles

**Status:** HOS-2 Planning | **Version:** 1.0

---

## Principle 1: Every Screen Answers Five Questions

**Purpose:** Users should never feel lost or uncertain.

Every screen must answer:

1. **Where am I?** — Clear page title, breadcrumbs when deep
2. **What can I do?** — Primary action visible and obvious
3. **What changed?** — Status indicators, timestamps, refresh markers
4. **What requires attention?** — Alerts, notifications, overdue items
5. **What happens next?** — Next step, confirmation, or exit path

**Example:** Quote detail screen shows "Quote #1243 — Draft" (where), "Send to Client" button prominent (what), "Last saved 2m ago" (what changed), "Missing arrival date" alert (attention), "After sending, quote moves to Pending" help text (what next).

**Anti-pattern:** Dashboard with no title, no clear primary action, no status indicators.

---

## Principle 2: One Primary Action Per Screen

**Purpose:** Reduce decision fatigue. Make the most important action undeniable.

Every screen has exactly ONE primary action — visually dominant and positioned at the natural scan endpoint. Secondary actions are visually subordinate.

**Example:** Quote wizard — "Next" button is primary. "Save Draft" and "Cancel" are secondary text links.

**Anti-pattern:** Form with three equally-weighted buttons.

---

## Principle 3: Progressive Disclosure

**Purpose:** Show what's needed now. Reveal detail on demand.

Default views show summary. Expanders, tabs, modals, and drill-downs provide depth. Never overwhelm with everything at once.

**Example:** Quote list shows summary cards. Click to expand shows rate breakdown. Collapse returns to summary.

**Anti-pattern:** Quote detail showing every field, every rate component, every offer simultaneously without structure.

---

## Principle 4: Consistency Over Novelty

**Purpose:** Users learn patterns. Break patterns only when the pattern is wrong.

Components, layouts, interactions, and language must be consistent across the product. When a pattern is established, reuse it. When it's broken, fix it everywhere.

**Example:** Every confirmation dialog uses the same pattern. Every table sorts the same way. Every form validates the same way.

**Anti-pattern:** Two different date pickers used in different parts of the same workflow.

---

## Principle 5: Accessibility By Default

**Purpose:** Accessible design is better design for everyone.

Every component must meet WCAG 2.1 AA. Keyboard navigation, screen reader labels, focus visibility, and colour contrast are not optional.

**Example:** Every input has an associated label. Every button has a visible focus ring. Colour alone never conveys critical information.

**Anti-pattern:** "Click here" link text. Grey text on white background failing contrast. Custom checkbox without keyboard support.

---

## Principle 6: Enterprise Clarity Before Decoration

**Purpose:** AVOA is a business tool. Decoration serves clarity, never competes with it.

Visual elements must aid comprehension. Animations must guide attention. Colour must convey meaning. When in doubt, simplify.

**Example:** Table with clear headers, consistent alignment, and zebra striping for readability. No gradient backgrounds, no decorative borders.

**Anti-pattern:** Dashboard with animated charts that distract from the data.

---

## Principle 7: Errors Guide, Don't Blame

**Purpose:** Errors are a normal part of interaction. They must be helpful, not accusatory.

Every error message must explain: what happened, why, and how to fix it. Never use technical jargon. Never blame the user.

**Example:** "The arrival date must be after today. Please select a future date." — Not: "Invalid input. Date validation error E402."

**Anti-pattern:** Red toast "Error. Please try again." with no explanation.

---

## Principle 8: Loading Shows Progress, Not Uncertainty

**Purpose:** Users should never wonder whether the system is working.

Loading states show skeletons, progress bars, or estimated times. Never show a blank screen. Never show an indefinite spinner for more than 3 seconds without explanation.

**Example:** Quote list loading shows skeleton cards matching the expected layout. "Loading quotes…" with estimated time when slow.

**Anti-pattern:** Blank white screen for 8 seconds then sudden content flash.

---

## Principle 9: Nothing Is Irreversible Without Confirmation

**Purpose:** Protect users from accidental destructive actions.

Any action that deletes, cancels, or commits must confirm first. Confirmations must be clear, not ambiguous.

**Example:** "Delete this quote?" with quote reference and "This cannot be undone. Quote #1243 will be permanently removed."

**Anti-pattern:** Trash icon that instantly deletes with no confirmation.

---

## Principle 10: Design For The Data, Not Just The Screen

**Purpose:** Screens are visualizations of data. The data determines the best presentation.

Before designing any screen, ask: what data matters most here? Design the data display first, then the chrome around it.

**Example:** Quote detail — pricing breakdown is the most important data, so it gets the most visual weight and the clearest layout.

**Anti-pattern:** Beautiful card layout with tiny, unreadable pricing numbers.

---

*Part of Hermes Product OS v3.1 — HOS-2.*