# Independent Technical Review — Hermes Product OS v3.2

**Review ID:** REV-HOS-V3.2-001
**Commit:** d5f32ad
**Branch:** feature/HOS-v3.2
**Reviewer:** Independent Technical Reviewer (via Hermes Agent — Claude model)
**Date:** 1 August 2026
**Scope:** Read-only review of 20 deliverables for completeness, consistency, authority clarity, and planning-only compliance
**Status:** COMPLETE

---

## Executive Summary

The v3.2 correction package is a disciplined planning-only refinement. All 20 deliverables are present and materially complete. The earned-authority model (Stage 1), fallback orchestration, human-gate matrix, agent/tool separation, and builder-selection policy are well-structured. No production code or runtime behavior was modified. Planning-only compliance is verified.

**Key risks:** DeepSeek V4 Pro has three different maturity statuses across documents (reconciliation required). The v3.1 organizational model (02_ORGANIZATIONAL_MODEL.md) still classifies Claude Code as a Tertiary Coding Agent, directly contradicting v3.2's reclassification as a review tool. The organizational model lists 5 builder agents where v3.2 only recognizes 2. These must be reconciled before merge.

**Overall: CONDITIONAL PASS — 2 BLOCKERs, 4 HIGHs, 7 MEDIUMs, 5 LOWs, 1 OPTIONAL. All BLOCKERs and HIGHs must be resolved before merge.**

---

## BLOCKER Findings (2)

### BLOCKER-001: DeepSeek V4 Pro Maturity Status Inconsistency (Three-Way)
- **File:** `docs/hermes-os-v3.1/HERMES_OS_V3_2.md` §4, `diagrams/hermes-os-v3.2-current-status.html`, `docs/hermes-os-v3.1/02_ORGANIZATIONAL_MODEL.md` §4
- **Evidence:**
  - HERMES_OS_V3_2.md §4 Tool table: `DeepSeek V4 Pro | Optional research | ACTIVE | PROBATION`
  - Current Status diagram: `DeepSeek V4 Pro (Optional research) | badge-red: RESTRICTED`
  - Organizational model line 58: `DeepSeek V4 Pro | Optional research/challenger | ACTIVE | PILOT`
- **Description:** Three different maturity statuses assigned to the same entity: PROBATION, RESTRICTED, and PILOT. Different maturity values carry different operational implications. Probation implies under review. Restricted implies blocked from use. Pilot implies actively being tested.
- **Recommendation:** Reconcile to a single consistent status across all three files. The §9 builder-selection policy rationale ("Repeated timeouts; zero successful HOS-2 specialist completions") supports RESTRICTED. Apply consistently.

### BLOCKER-002: Claude Code Classification Contradiction — Tool vs Builder Agent
- **File:** `docs/hermes-os-v3.1/HERMES_OS_V3_2.md` §4 vs `docs/hermes-os-v3.1/02_ORGANIZATIONAL_MODEL.md` §4.1.3
- **Evidence:**
  - HERMES_OS_V3_2.md §4: "Claude Code is the **tool** through which the Claude **model** performs the **Independent Technical Reviewer role**. These are distinct concepts."
  - 02_ORGANIZATIONAL_MODEL.md §4.1.3: "Tertiary Coding Agent (Claude Code) — Purpose: Tertiary implementation agent for overflow, experiments, or specialized tasks. Authority: Can WRITE to source directories, Can CREATE branches, Can OPEN pull requests."
- **Description:** v3.2 explicitly reclassifies Claude Code as a review tool with read-only access. The v3.1 organizational model still defines it as a coding agent with source-level write permissions. This is a direct contradiction. If merged as-is, agents would receive ambiguous signals about Claude Code's authority.
- **Recommendation:** Update 02_ORGANIZATIONAL_MODEL.md to remove Claude Code from the builder roster (delete §4.1.3). Replace with the reviewer role description matching v3.2 §4. Audit any other v3.1 docs referencing Claude Code as a builder.

---

## HIGH Findings (4)

### HIGH-001: Unreconciled Builder Roster — 5 Agents in Org Model, 2 in v3.2
- **File:** `docs/hermes-os-v3.1/02_ORGANIZATIONAL_MODEL.md` §§4.1.1–4.1.5
- **Evidence:** Org model lists 5 coding agents: Kimi K3, Codex, Claude Code (Tertiary), Gemini Code (Quaternary), Qwen Coder (Specialty). v3.2 builder-selection policy (§9) and agent table (§4) list only Kimi K3 and Codex.
- **Description:** Three agents (Gemini Code, Qwen Coder, plus the Claude Code issue from BLOCKER-002) exist in the operational model but are absent from all v3.2 artifacts. The builder-selection policy has no entries for them. The stable diagram shows only 2 agents. If they are deprecated or de-scoped for v3.2, this should be explicitly stated.
- **Recommendation:** Either: (a) remove Gemini Code and Qwen Coder from the organizational model, or (b) add them to the v3.2 builder-selection roster with PROVISIONAL status and rationale explaining their deferred/planned status.

### HIGH-002: Fallback Restoration Target Undefined
- **File:** `docs/hermes-os-v3.1/HERMES_OS_V3_2.md` §5
- **Evidence:** §5 "Probation Breach" section: "Mark Hermes maturity **SUSPENDED**." §5 "Restoration" section: "Hermes may be restored only after: root-cause review, corrective controls, successful probation task, independent review, Amjad approval."
- **Description:** After suspension, the restoration procedure does not specify what maturity state Hermes returns to. Does it return to UNPROVEN (full reset), back to PROBATION (suspended-probation), or some other state? The maturity path is ambiguous. Additionally, during Stage 1 (STAGE_1_ASSISTED_ORCHESTRATION), Hermes is UNPROVEN — not yet in PROBATION. The probation breach language assumes a future state that doesn't exist yet, which is forward-looking but should be explicit.
- **Recommendation:** Add one line: "Restored to PROBATION or UNPROVEN as determined by root-cause severity." Clarify that probation breach can only occur when Hermes is in PROBATION state, which is a future maturity advancement.

### HIGH-003: Contract Builder Identity — Hermes as Builder for Planning
- **File:** `.hermes/contracts/TASK-HOS-V3-2-CORRECTION.yaml` line 46
- **Evidence:** `builder: hermes`. The HOS-1 reconciliation report (RECONCILIATION_REPORT.md) flagged Hermes writing scripts directly as a "Role-boundary deviation, not authorized" (Section 7). This v3.2 contract assigns Hermes as builder.
- **Description:** Per the Hermes Code Boundary policy (03_AUTHORITY_AND_AGENT_PERMISSIONS.md): Hermes may write "Documentation, plans, task contracts, policies, schemas, templates, decisions, regressions, audits, orchestration config — NOT production features." This contract is planning-only documentation, so Hermes-as-builder is within authorized scope. However, the HOS-1 incident demonstrates that Hermes-as-builder requires explicit authorization and external review. This contract correctly assigns Claude Code as reviewer, but the pattern should be acknowledged as a deliberate, bounded exception rather than precedent for Hermes writing implementation code.
- **Recommendation:** Add a comment or note in the contract confirming this is a planning-only task within Hermes' documented code boundary. No action needed for correctness — this is a process-clarity recommendation.

### HIGH-004: Evaluation Framework Question Count Mismatch
- **File:** `docs/hermes-os-v3.1/HERMES_OS_V3_2.md` §11
- **Evidence:** The v3.2 commit message (8220848) states "§11 OS Evaluation Framework: 10 questions, 5 outcomes." The document §11 lists only 9 review questions.
- **Description:** The spec claims 10 evaluation questions but enumerates only 9. The missing 10th question could be intentional reduction or accidental omission. The 9 present questions cover production value, regressions, rework, cycle time, coordination burden, evidence quality, unsafe changes, governance delay, model assignments, and provider stalls — which is actually 10 distinct topics if "Did regressions decrease? Did rework decrease?" are counted as two separate questions under one bullet.
- **Recommendation:** Count clarification: If "Did regressions decrease?" and "Did rework decrease?" are separate questions (as they logically are), the bullet format merges them. Either split into separate bullets (making 10 explicit) or reduce the claim to 9. Both approaches are acceptable.

---

## MEDIUM Findings (7)

### MEDIUM-001: Organizational Model Duplicated Content — Maturity Model in Two Files
- **File:** `docs/hermes-os-v3.1/HERMES_OS_V3_2.md` §2 vs `docs/hermes-os-v3.1/02_ORGANIZATIONAL_MODEL.md` §3
- **Evidence:** Both files contain identical maturity dimension tables and identical agent/tool tables with minor variation. Organizational model has DeepSeek as PILOT; v3.2 has PROBATION.
- **Description:** Duplication increases maintenance burden and creates the inconsistency seen in BLOCKER-001. The organizational model should reference v3.2 as the authority for maturity status rather than maintaining a parallel copy.
- **Recommendation:** In 02_ORGANIZATIONAL_MODEL.md, replace the duplicated maturity tables with a cross-reference to HERMES_OS_V3_2.md, stating that v3.2 is the authoritative source for current maturity states.

### MEDIUM-002: Migrated Organizational Model Has Incomplete Table of Contents
- **File:** `docs/hermes-os-v3.1/02_ORGANIZATIONAL_MODEL.md`
- **Evidence:** The TOC (lines 12-72) references sections 5-9, 10-12 that are mixed with v3.2 new additions. Section numbering jumps from §4 to §6 (skipping §5) in the TOC, and items like "Division 4: Quality" appear between v3.2 maturity sections and the TOC overflow.
- **Description:** The organizational model appears to be in transition — some v3.2 content has been prepended but the original structure wasn't fully reconciled. This creates navigational confusion.
- **Recommendation:** Either fully restructure 02_ORGANIZATIONAL_MODEL.md to integrate v3.2 content, or preserve it as an unmodified v3.1 artifact with v3.2 content only in HERMES_OS_V3_2.md.

### MEDIUM-003: §9 Builder-Selection — PROVISIONAL vs PILOT Criteria Not Explicit
- **File:** `docs/hermes-os-v3.1/HERMES_OS_V3_2.md` §9
- **Evidence:** Claude model is PILOT despite "factual errors requiring human verification." Kimi K3 and Codex are PROVISIONAL despite "observed use" without benchmarks. The distinction between these tiers is implied rather than defined.
- **Description:** The roster statuses (PROVISIONAL/PILOT/APPROVED/RESTRICTED/SUSPENDED) are listed but their definitions and promotion/demotion criteria are not documented. PILOT implies active testing — but what constitutes passing a pilot? How does PROVISIONAL graduate to PILOT?
- **Recommendation:** Add a brief status definition table (one sentence per status) and entry/exit criteria for PROVISIONAL → PILOT → APPROVED transitions.

### MEDIUM-004: Review Process Not Defined for OS Evaluation
- **File:** `docs/hermes-os-v3.1/HERMES_OS_V3_2.md` §11
- **Evidence:** §11 lists 9 review questions, 5 review triggers, and 5 outcomes. It does not specify who performs the review, how the review record is stored, or what format the review takes.
- **Description:** The evaluation framework defines what to review and possible outcomes but omits process: who initiates, who participates, where the record lives, and how outcomes are enacted.
- **Recommendation:** Add: "Review performed by: Independent Technical Reviewer or designated evaluator. Record location: .hermes/reviews/os-evaluation/OS-EVAL-YYYY-MM-DD.md. Outcome must be acknowledged by Amjad."

### MEDIUM-005: Current Status Diagram Blockers Not Cross-Referenced in Spec
- **File:** `diagrams/hermes-os-v3.2-current-status.html`
- **Evidence:** The diagram lists 4 current blockers and 6 next human decisions. These are not referenced or summarized in HERMES_OS_V3_2.md.
- **Description:** Blockers and decisions are critical operational state. If they live only in the diagram and not in any machine-readable or discoverable location, they risk being overlooked during planning.
- **Recommendation:** Add a §19 "Current Operational State" to HERMES_OS_V3_2.md that lists current blockers and next decisions, with a note that the diagram is the visual representation.

### MEDIUM-006: §12 Observability Controls — Budget Values Not Source-Referenced
- **File:** `docs/hermes-os-v3.1/HERMES_OS_V3_2.md` §12 vs `docs/hermes-os-v3.1/loop/LOOP_ENGINEERING.md`
- **Evidence:** §12 default controls yaml matches LOOP_ENGINEERING.md's budget policy values exactly. This is actually cross-document consistency, but neither document cites the other as the source of truth.
- **Description:** When two documents define the same default values independently, future changes risk divergence. One should be the authority; the other should reference it.
- **Recommendation:** Add a note in §12: "Default values derived from Loop Engineering budget policy (LOOP_ENGINEERING.md §Loop Budget Policy)."

### MEDIUM-007: Agent Routing Doc (19) Lists Documentation/Test Agents Not in v3.2 Roster
- **File:** `docs/hermes-os-v3.1/19_AGENT_ROUTING_AND_SCORECARDS.md`
- **Evidence:** Routing table includes "Documentation Agent" and "Test Agent" as routing targets. Neither appears in the v3.2 agent/tool tables or builder-selection policy.
- **Description:** The routing doc references agents not yet defined in the v3.2 agent roster. This is a forward-reference that may cause confusion about which agents are authorized.
- **Recommendation:** Add a note in 19_AGENT_ROUTING_AND_SCORECARDS.md: "Documentation Agent and Test Agent are planned roles not yet activated in v3.2. Routing rules apply when those agents are provisioned."

---

## LOW Findings (5)

### LOW-001: Stable Diagram Has CSS Pulse Animation
- **File:** `docs/hermes-os-v3.1/diagrams/hermes-os-v3.2-operating-model.html`
- **Evidence:** Lines 14-15: `.pulse-dot{width:12px;height:12px;background:#C99A3B;border-radius:50%;animation:pulse 2s infinite}`
- **Description:** The feature-frozen "stable" operating model diagram has a pulsing amber dot animation that visually suggests a live/active system. This is cosmetic but semantically confusing for a "feature-frozen" artifact.
- **Recommendation:** Remove the CSS animation. Replace with a static solid dot. The diagram should appear as stable as its label claims.

### LOW-002: Stable Diagram — Replit Shown with Dashed Border Inconsistently
- **File:** `docs/hermes-os-v3.1/diagrams/hermes-os-v3.2-operating-model.html` line 117
- **Evidence:** Replit has `stroke-dasharray="2,2"` while all other tool/agent boxes have solid borders. No key or legend explains the dashed distinction.
- **Description:** The dashed border on Replit is unexplained. It could indicate "planned" vs "active" but other planned items don't use this convention consistently.
- **Recommendation:** Either use a consistent border style or add a legend entry explaining the dashed convention.

### LOW-003: §9 Builder-Selection Criteria — Unranked List
- **File:** `docs/hermes-os-v3.1/HERMES_OS_V3_2.md` §9
- **Evidence:** Selection criteria lists 14 items: "Task type, risk level, golden-task performance, regression fixtures, scope adherence, correctness, review findings, correction rate, timeout rate, execution speed, cost, evidence quality, tool availability." No priority or weighting.
- **Description:** A flat list of 14 criteria without ordering makes builder selection subjective. While formal weighting may be premature (NO_BASELINE), acknowledging which factors dominate would improve decision consistency.
- **Recommendation:** Add grouping: "Primary (task type, risk level, golden-task performance). Secondary (correctness, scope adherence, evidence quality). Tertiary (execution speed, cost, tool availability)."

### LOW-004: §15 Migration Plan — Phases D-F Lack Rollback Specificity
- **File:** `docs/hermes-os-v3.1/HERMES_OS_V3_2.md` §15
- **Evidence:** Phase D rollback: "Unfreeze by Amjad." Phase E: "Pause tasks." Phase F: "Remain at Stage 1." These are lighter than Phases A-C which have concrete rollbacks.
- **Description:** Phases D-F rollback descriptions are procedural ("pause", "remain") rather than state-recovery instructions. Acceptable for planning, but could be more explicit about what state the system is in after rollback.
- **Recommendation:** Expand Phase E rollback: "Pause all active tasks. Return all in-progress work to AWAITING_HUMAN_GATE. No evidence loss."

### LOW-005: §6 Human-Gate Matrix — R1 Delegation Is Minimal
- **File:** `docs/hermes-os-v3.1/HERMES_OS_V3_2.md` §6
- **Evidence:** Out of 14 actions, only "Task-contract approval" and "Correction auth" have Hermes in the R1 column. The other 12 actions require Amjad approval even at R1.
- **Description:** During Stage 1, Hermes has limited delegation (R1 for contract drafting and corrections). This is correct per the Stage 1 definition, but the matrix's granularity draws attention to how little Hermes can approve independently. This is a design observation, not a defect.
- **Recommendation:** No change required. This accurately reflects STAGE_1_ASSISTED_ORCHESTRATION.

---

## OPTIONAL (1)

### OPTIONAL-001: Add Document Revision Table
- **File:** `docs/hermes-os-v3.1/HERMES_OS_V3_2.md`
- **Description:** The document has no revision history table at the bottom. Given it is meant to be feature-frozen, a revision log would help track any allowed changes (bug fixes, security patches) post-merge.
- **Recommendation:** Add a revision table at the document footer: `| Version | Date | Author | Change |`

---

## Compliance Verification

### Planning-Only Compliance
- **Status: PASS** — No production code modified. No runtime behavior changed. Diff is confined to docs/hermes-os-v3.1/, .hermes/contracts/, and diagrams/.
- **Evidence:** `git diff 5fc480c..d5f32ad --stat` shows 4 files: HERMES_OS_V3_2.md, TASK-HOS-V3-2-CORRECTION.yaml, hermes-os-v3.2-current-status.html, hermes-os-v3.2-operating-model.html. Zero files in backend/, frontend/src/, or any runtime directory.

### Role / Model / Tool / Platform Separation
- **Status: PASS with reconciliation needed** — §4 properly separates categories and states "Claude Code is the tool through which the Claude model performs the Independent Technical Reviewer role." However, 02_ORGANIZATIONAL_MODEL.md still conflates these (see BLOCKER-002).

### Hermes Not Portrayed as Builder
- **Status: PASS** — Hermes is consistently portrayed as orchestrator throughout v3.2. The contract's `builder: hermes` field is for planning-only documentation, within Hermes' authorized scope.

### Claude Code Is Tool Not Role
- **Status: PASS in v3.2, FAIL in v3.1 org model** — v3.2 §4 is explicit and correct. The v3.1 organizational model contradicts this (see BLOCKER-002).

### Diagram Accuracy
- **Status: PASS with one inconsistency** — Stable diagram correctly represents the architecture. Current Status diagram has DeepSeek as RESTRICTED while the spec has PROBATION (see BLOCKER-001).

### No Invented Baselines
- **Status: PASS** — All 8 delivery metrics correctly show NO_BASELINE, NOT_MEASURED, or INSUFFICIENT_DATA. No fabricated data.

### Human Gates Absolute
- **Status: PASS** — §6 states: "Human gates have no timeout override. Silence is not approval." §5 suspension triggers include "Bypassed human gate." P2 principle: "Human Gate Is Absolute: No timeout override. No silent escalation."

---

## Deliverable Completeness Matrix

| # | Deliverable | § | Status | Notes |
|---|---|---|---|---|
| 1 | Earned Authority (Stage 1) | §3 | PASS | STAGE_1_ASSISTED_ORCHESTRATION with rationale, stage definitions, promotion criteria |
| 2 | Fallback Orchestration | §5 | PASS | Normal path, probation breach, direct fallback, 10 triggers, restoration |
| 3 | Human-Gate Matrix (14 actions) | §6 | PASS | All 14 actions with R1-R4, approver, entry/exit evidence |
| 4 | Product & Architecture Responsibility | §7 | PASS | Amjad accountable, Hermes advisory |
| 5 | Division Clarification | §8 | PASS | 7 domains, planned vs active distinction |
| 6 | Builder-Selection Policy | §9 | PASS | Roster, criteria, current status, change rule |
| 7 | Model-Roster Rationale | §9 | PASS | Rationale for all 4 models, RESTRICTED for DeepSeek |
| 8 | Delivery Metrics (8) | §10 | PASS | 8 metrics, all NO_BASELINE/NOT_MEASURED |
| 9 | Evaluation Framework | §11 | MEDIUM | 5 outcomes present; question count 9 vs claimed 10 (HIGH-004) |
| 10 | Observability Specification | §12 | PASS | COMPLETE spec, NOT_IMPLEMENTED, default controls |
| 11 | Capability Status (8) | §13 | PASS | All INACTIVE/UNPROVEN, no HEALTHY claims |
| 12 | Loop Status (4) | §14 | PASS | All INACTIVE/UNPROVEN |
| 13 | Stable Diagram | diagram | PASS | Architecture, layers, roles, no dynamic status |
| 14 | Current Status Diagram | diagram | MEDIUM | Accurate snapshot; DeepSeek status mismatch (BLOCKER-001) |
| 15 | Migration Plan (6 phases) | §15 | PASS | Entry/rollback for each phase |
| 16 | Independent Review Plan | §16 | PASS | Scope, criteria, method defined |
| 17 | Operating Principles (7) | §17 | PASS | P1-P7 principles |
| 18 | Feature-Freeze Policy | §18 | PASS | Scope, exclusions, activation conditions |
| 19 | Maturity Model | §2 | PASS | 4 dimensions defined |
| 20 | Agents vs Tools Separation | §4 | PASS | Clear separation; org model needs reconciliation |

---

## Summary

| Severity | Count |
|---|---|
| BLOCKER | 2 |
| HIGH | 4 |
| MEDIUM | 7 |
| LOW | 5 |
| OPTIONAL | 1 |
| **Total** | **19** |

**Resolution required before merge:** BLOCKER-001 (DeepSeek three-way inconsistency), BLOCKER-002 (Claude Code classification contradiction). All HIGH findings should be addressed. MEDIUM and LOW findings are advisory.

**Overall assessment:** The v3.2 correction package meets planning-only compliance requirements and materially fulfills all 20 deliverable commitments. The architecture, authority model, and governance framework are internally consistent within the v3.2 document. The primary risk is incomplete reconciliation with the v3.1 organizational model, which retains outdated agent classifications that directly contradict v3.2 decisions.
