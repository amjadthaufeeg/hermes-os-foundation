# Risk Classification

## R0 — Documentation only
No runtime behavior changes. Builder self-check is normally sufficient.

## R1 — Presentation-only
CSS, spacing, typography, or markup with no interaction, state, API, routing, or logic change. Automated checks, preview, and visual approval required.

## R2 — Interaction or contained bug fix
Changes local UI behavior or a bounded defect. Automated checks, Claude review, preview, and Amjad approval required.

## R3 — Business logic or cross-system behavior
Pricing-adjacent logic, workflows, permissions, integrations, or multi-domain changes. Deterministic tests, Claude review, and explicit Amjad approval required.

## R4 — Data, security, infrastructure, or migration
Database schemas, authentication, secrets, permissions, infrastructure, or production data. Backup, migration validation, security review, rollback rehearsal, and explicit Amjad approval required.

## R5 — Critical commercial or irreversible change
Pricing engine, financial calculations, destructive data operations, major architecture replacement, or high-impact production change. Separate plan, independent challenge, comprehensive evidence, and explicit final approval required.

When uncertain, classify one level higher.
