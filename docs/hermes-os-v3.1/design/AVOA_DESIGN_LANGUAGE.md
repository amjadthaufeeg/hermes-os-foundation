# AVOA Design Language

**Status:** HOS-2 Planning | **Version:** 1.0

---

## Brand Personality

AVOA is a premium B2B villa rental platform serving luxury property managers and their clients. The visual language must convey:

- **Confidence** — not loud, but assured
- **Competence** — reliable, precise, trustworthy
- **Warmth** — human, approachable, not cold or institutional
- **Quiet luxury** — premium without ostentation

The product should feel like a well-appointed private office, not a consumer marketplace.

---

## Visual Tone

| Quality | Expression |
|---|---|
| Premium | Subtle gold accents, generous whitespace |
| Trustworthy | Clear hierarchy, predictable patterns, no surprises |
| Professional | Restrained palette, clean typography, precise alignment |
| Modern | Elegant simplicity, thoughtful motion |
| Calm | Low visual noise, breathing room, clear focus |

---

## Emotional Goals

Users should feel:

- **Capable** — the interface enables, not obstructs
- **In control** — every action is deliberate and reversible
- **Confident** — data is accurate, calculations are transparent
- **Valued** — the experience respects their time and attention

---

## Enterprise Characteristics

- Multi-step workflows with clear progression
- Approval and review patterns
- Data density balanced with readability
- Role-appropriate views
- Audit trail visibility
- Bulk operations when appropriate

---

## Luxury Characteristics

- Restrained palette: navy, cream, gold accents
- Generous whitespace — never cramped
- Typography as a differentiator, not an afterthought
- Subtle motion: smooth transitions, no jarring effects
- Thoughtful micro-interactions: hover states, focus rings
- Nothing feels cheap, rushed, or placeholder

---

## Trust Characteristics

- Transparent calculations — no hidden logic
- Clear status indicators
- Confirmation before destructive actions
- Audit trails visible and accessible
- Error messages that explain what happened and how to fix it
- Consistent patterns that build muscle memory

---

## Density Philosophy

Information density varies by context:

- **Dashboards:** higher density, data prioritized
- **Forms:** medium density, focused on single task
- **Detail views:** lower density, breathing room for comprehension
- **Approvals:** focused density, key decision prominent

Never sacrifice readability for density. Never waste space out of laziness.

---

## Whitespace Philosophy

Whitespace is a design element, not wasted space. It:

- Defines hierarchy
- Groups related content
- Separates unrelated content
- Provides visual rest
- Elevates important elements

Default to generous. Reduce only when data density is the primary goal.

---

## Motion Philosophy

Motion serves purpose:

- **Navigation:** smooth transitions (250ms ease-out)
- **Feedback:** micro-interactions (150ms) on hover, focus, click
- **Entrance:** subtle fade-in (400ms) for new content
- **Loading:** skeleton screens preferred over spinners
- **Reduced motion:** always respect `prefers-reduced-motion`

Never use motion for decoration alone. Motion must aid comprehension.

---

## Colour Philosophy

- **Navy:** authority, depth, foundation — primary backgrounds
- **Teal:** action, interaction, clarity — buttons, links, active states
- **Gold:** premium, highlight, distinction — accents, badges, emphasis
- **Coral:** attention, warning, urgency — errors, destructive actions
- **Cream:** warmth, breathing room, contrast — cards, surfaces

Colour never communicates information alone — always pair with text or icons. Accessible contrast is non-negotiable.

---

## Typography Philosophy

Typography is the primary voice of the product. It must be:

- **Readable** at every size and on every device
- **Hierarchical** — scanning the page should reveal structure
- **Consistent** — one type scale, applied everywhere
- **Intentional** — every size, weight, and style has a documented purpose

Body text at 16px minimum. One font family. System stack default; upgrade to premium typeface when justified.

---

## Dashboard Philosophy

Dashboards are decision-support tools, not decoration. Every dashboard must:

1. Answer one primary question at a glance
2. Prioritize actionable data over vanity metrics
3. Show trends, not just snapshots
4. Provide drill-down paths to detail
5. Refresh indicators visible and clear

No dashboard widget without a defined business question it answers.

---

## Data Presentation Philosophy

Data is the product. Every table, chart, and summary must:

- Be accurate and reproducible
- Show context: comparison, trend, threshold
- Respect the user's intelligence: explain outliers
- Never truncate without indication
- Provide export or detail paths

Empty states show opportunity, not absence. Error states show path to resolution. Loading states show progress, not uncertainty.

---

*Part of Hermes Product OS v3.1 — HOS-2.*