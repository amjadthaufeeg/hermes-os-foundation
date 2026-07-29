# Example Change Contract — TASK-EXAMPLE

## Request
Make the comparison header less crowded without changing comparison behavior.

## Objective
Improve hierarchy and spacing on mobile and desktop.

## Classification and risk
VISUAL_ONLY / R1

## Allowed files
- `components/compare/ComparisonHeader.tsx`
- `styles/comparison-header.css`

## Protected systems
- comparison state;
- add/remove logic;
- URL state;
- API calls;
- routes;
- pricing;
- database.

## Acceptance criteria
- Header is easier to scan.
- Existing actions remain visible and functional.
- Layout works at agreed mobile, tablet, and desktop widths.
- No protected behavior changes.

## Checks
Build, type-check, relevant UI test, changed-file inspection, Claude scope review, Replit visual review.

## Stop conditions
Any additional file, interaction, state, API, workflow, or logic change is required.
