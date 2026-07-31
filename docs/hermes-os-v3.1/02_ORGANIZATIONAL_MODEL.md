# Hermes OS v3.1 — Organizational Model

**Document ID:** HERMES-OS-ORG-v3.1.0  
**Version:** 3.1.0  
**Status:** Draft  
**Last Updated:** 2026-07-31  
**Owner:** Hermes Engineering OS Foundation  
**Dependencies:** [01_HERMES_OS_V3_1_ARCHITECTURE.md](./01_HERMES_OS_V3_1_ARCHITECTURE.md)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Core Principle: Hermes as Sole Orchestrator](#2-core-principle-hermes-as-sole-orchestrator)
3. [Division 1: Executive / Product](#3-division-1-executive--product)
4. [Division 2: Engineering](#4-division-2-engineering)
5. [Division 3: Design Studio](#5-division-3-design-studio)
6. [Division 4: Quality](#6-division-4-quality)
7. [Division 5: Knowledge](#7-division-5-knowledge)
8. [Division 6: Research](#8-division-6-research)
9. [Division 7: Operations](#9-division-7-operations)
10. [Divisional Interaction Map](#10-divisional-interaction-map)
11. [Role Assignments to Agents](#11-role-assignments-to-agents)
12. [Version History](#12-version-history)

---

## 1. Overview

### 1.1 Purpose

This document defines the organizational structure of Hermes Product OS v3.1. It specifies the seven divisions, the roles within each division, and the precise responsibilities, inputs, outputs, records, authority boundaries, and prohibitions for every role.

### 1.2 Critical Clarification

> **Roles are responsibilities, not separate models.** Hermes is the sole orchestrator. Every agent operates under Hermes' direction. "Divisions" are logical groupings of related responsibilities — they do not represent independent subsystems, separate codebases, or isolated runtimes. All agents are governed by the same permissions framework (see [03_AUTHORITY_AND_AGENT_PERMISSIONS.md](./03_AUTHORITY_AND_AGENT_PERMISSIONS.md)).

### 1.3 Organizational Chart

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AMJAD (Human Operator)                             │
│                          Level 8 — Full Authority                            │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        HERMES CORE (Sole Orchestrator)                       │
│                          Level 7 — Orchestrator Authority                     │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                        SIX DIVISIONS                                 │   │
│   │                                                                      │   │
│   │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐      │   │
│   │  │  EXECUTIVE /    │  │  ENGINEERING    │  │  DESIGN STUDIO  │      │   │
│   │  │  PRODUCT        │  │                 │  │                 │      │   │
│   │  │  Level 1-2      │  │  Level 3-5      │  │  Level 2-3      │      │   │
│   │  └─────────────────┘  └─────────────────┘  └─────────────────┘      │   │
│   │                                                                      │   │
│   │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐      │   │
│   │  │  QUALITY        │  │  KNOWLEDGE      │  │  OPERATIONS     │      │   │
│   │  │                 │  │                 │  │                 │      │   │
│   │  │  Level 3-5      │  │  Level 1-2      │  │  Level 3-5      │      │   │
│   │  └─────────────────┘  └─────────────────┘  └─────────────────┘      │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Principle: Hermes as Sole Orchestrator

### 2.1 What This Means

| Rule | Description |
|------|-------------|
| **Single Source of Truth** | All task state lives in Hermes. Agents query Hermes, not each other. |
| **Mediated Communication** | Agent A cannot directly instruct Agent B. All inter-agent communication flows through Hermes. |
| **Unified Governance** | Permissions, gates, and policies are enforced by Hermes, not by individual agents. |
| **Central Audit Trail** | Every action, decision, and state transition is logged by Hermes. |
| **Contract-Based Work** | All work is defined by immutable task contracts created by Hermes. Agents execute against contracts. |

### 2.2 What This Does NOT Mean

- Agents are not "dumb" — they have full autonomy within their contract scope
- Hermes does not micromanage agent execution — it defines WHAT, agents decide HOW
- Divisions are not silos — an agent in Engineering can produce artifacts consumed by Quality
- Roles can be combined — one agent may serve multiple complementary roles

### 2.3 The Contract Model

Every piece of work in Hermes OS is defined by a **Task Contract**:

```
Task Contract
├── contract_id: string (UUID)
├── title: string
├── description: string
├── status: enum (draft → planning → building → testing → reviewing → approved → merged → deployed)
├── assigned_agent: string (agent identifier)
├── division: enum (executive, engineering, design, quality, knowledge, operations)
├── gates_required: list of gate names
├── inputs: list of artifact references
├── expected_outputs: list of artifact specifications
├── authority_level: integer (1-8)
├── deadline: timestamp (optional)
├── parent_contract_id: string (optional, for sub-tasks)
└── metadata: JSON (extensible)
```

---

## 3. Division 1: Executive / Product

**Authority Level:** 1-2  
**Purpose:** Translates human intent into actionable engineering work. Defines product strategy, prioritizes work, and manages requirements.

### 3.1 Roles

#### 3.1.1 Product Strategist

| Attribute | Value |
|-----------|-------|
| **Purpose** | Define product vision, roadmap, and priorities |
| **Authority Level** | 2 |
| **Responsibilities** | • Parse Amjad's product intents into structured goals<br>• Maintain product roadmap document<br>• Prioritize feature backlog<br>• Define success criteria for features<br>• Align engineering work with product strategy |
| **Inputs** | • Amjad's verbal/written product intents<br>• User feedback and analytics<br>• Market research (from Knowledge division)<br>• Post-deployment regression reports |
| **Outputs** | • Product Roadmap (`.hermes/contracts/roadmap.md`)<br>• Feature Prioritization Matrix<br>• Success Criteria Documents |
| **Records** | • `roadmap.md` — living product roadmap<br>• `backlog.json` — prioritized feature backlog<br>• `strategy-notes/` — strategic decision records |
| **Authority** | • Can CREATE task contracts for any division<br>• Can ASSIGN priority levels to contracts<br>• Can REORDER the backlog<br>• Can PROPOSE new features<br>• Cannot MERGE code or DEPLOY |
| **Prohibitions** | • Must not write product code<br>• Must not bypass quality gates<br>• Must not modify agent configurations<br>• Must not access deployment credentials |

#### 3.1.2 Requirements Analyst

| Attribute | Value |
|-----------|-------|
| **Purpose** | Decompose product goals into detailed, verifiable requirements |
| **Authority Level** | 1 |
| **Responsibilities** | • Convert product intents into detailed specifications<br>• Write acceptance criteria in testable form<br>• Identify edge cases and non-functional requirements<br>• Maintain requirement traceability matrix<br>• Flag ambiguous or conflicting requirements |
| **Inputs** | • Product roadmap items<br>• Feature requests from Product Strategist<br>• Existing system documentation |
| **Outputs** | • Requirement Specifications (per feature)<br>• Acceptance Criteria Documents<br>• Edge Case Register |
| **Records** | • `requirements/{feature-id}.md` — per-feature specifications<br>• `acceptance-criteria/{feature-id}.json` — testable criteria<br>• `traceability-matrix.json` — requirement-to-test mapping |
| **Authority** | • Can DRAFT specifications<br>• Can REQUEST clarification from Product Strategist<br>• Can FLAG requirement conflicts<br>• Cannot approve specifications (Product Strategist must approve) |
| **Prohibitions** | • Must not write product code<br>• Must not modify requirements after specification is approved<br>• Must not assign implementation tasks<br>• Must not override product priorities |

---

## 4. Division 2: Engineering

**Authority Level:** 3-5  
**Purpose:** Implements product features as working, tested, production-ready code. The primary execution arm of Hermes OS.

### 4.1 Roles

#### 4.1.1 Primary Coding Agent (Kimi)

| Attribute | Value |
|-----------|-------|
| **Purpose** | Primary implementation agent for feature development and major changes |
| **Authority Level** | 4 |
| **Responsibilities** | • Implement features from approved specifications<br>• Write and maintain application code<br>• Create and update tests (unit, integration)<br>• Fix bugs identified by Quality division<br>• Own code quality within assigned contracts<br>• Create feature branches and open PRs |
| **Inputs** | • Approved specification documents<br>• Design documents (from Design Studio)<br>• Task contracts (from Hermes)<br>• Review feedback (from Quality)<br>• Existing codebase |
| **Outputs** | • Feature branches on GitHub<br>• Pull requests with implementation<br>• Test suites (co-located with code)<br>• Build configuration updates<br>• Self-review notes |
| **Records** | • Git commits and branches<br>• PR descriptions and comments<br>• Test files and fixtures |
| **Authority** | • Can WRITE to source directories (`src/`, `lib/`, `components/`)<br>• Can CREATE branches in the repository<br>• Can OPEN pull requests<br>• Can RUN tests locally<br>• Can READ all project files<br>• Cannot MERGE pull requests<br>• Cannot DEPLOY<br>• Cannot modify `.hermes/` governance files |
| **Prohibitions** | • Must not merge code (requires Hermes approval)<br>• Must not deploy to production<br>• Must not modify Hermes configuration<br>• Must not bypass CI/CD<br>• Must not skip tests<br>• Must not modify review feedback records |

#### 4.1.2 Secondary Coding Agent (Codex)

| Attribute | Value |
|-----------|-------|
| **Purpose** | Secondary implementation agent for complementary or parallel feature development |
| **Authority Level** | 4 |
| **Responsibilities** | • Implement features in parallel with Primary Coding Agent<br>• Handle specialized implementation tasks<br>• Provide implementation redundancy<br>• Support code refactoring and cleanup |
| **Inputs** | • Same as Primary Coding Agent<br>• Handoff notes from Primary Coding Agent (for shared work) |
| **Outputs** | • Same as Primary Coding Agent |
| **Records** | • Same as Primary Coding Agent |
| **Authority** | • Same as Primary Coding Agent |
| **Prohibitions** | • Same as Primary Coding Agent<br>• Must not modify code in a file currently assigned to Primary Coding Agent (single-writer rule) |

#### 4.1.3 Tertiary Coding Agent (Claude Code)

| Attribute | Value |
|-----------|-------|
| **Purpose** | Tertiary implementation agent for overflow, experiments, or specialized tasks |
| **Authority Level** | 3 |
| **Responsibilities** | • Handle overflow implementation tasks<br>• Prototype experimental features<br>• Assist with complex algorithmic work<br>• Support code migration and modernization |
| **Inputs** | • Same as Primary Coding Agent (scoped to assigned contracts) |
| **Outputs** | • Same as Primary Coding Agent |
| **Records** | • Same as Primary Coding Agent |
| **Authority** | • Can WRITE to source directories (scoped to assigned contracts)<br>• Can CREATE branches<br>• Can OPEN pull requests<br>• Can RUN tests locally<br>• Cannot MERGE or DEPLOY |
| **Prohibitions** | • Same as Primary Coding Agent<br>• Must not work on files assigned to Primary or Secondary agents |

#### 4.1.4 Quaternary Coding Agent (Gemini Code)

| Attribute | Value |
|-----------|-------|
| **Purpose** | Quaternary implementation agent for additional parallel capacity |
| **Authority Level** | 3 |
| **Responsibilities** | • Handle additional parallel implementation tasks<br>• Specialize in performance-sensitive or algorithmic work<br>• Support integration testing |
| **Inputs** | • Same as Primary Coding Agent (scoped) |
| **Outputs** | • Same as Primary Coding Agent |
| **Records** | • Same as Primary Coding Agent |
| **Authority** | • Same as Tertiary Coding Agent |
| **Prohibitions** | • Same as Tertiary Coding Agent |

#### 4.1.5 Specialty Coding Agent (Qwen Coder)

| Attribute | Value |
|-----------|-------|
| **Purpose** | Specialty agent for niche or framework-specific implementation tasks |
| **Authority Level** | 3 |
| **Responsibilities** | • Handle framework-specific implementation<br>• Support internationalization and localization<br>• Assist with documentation generation from code |
| **Inputs** | • Same as Primary Coding Agent (scoped) |
| **Outputs** | • Same as Primary Coding Agent |
| **Records** | • Same as Primary Coding Agent |
| **Authority** | • Same as Tertiary Coding Agent |
| **Prohibitions** | • Same as Tertiary Coding Agent |

#### 4.1.6 Dev Tools Agent

| Attribute | Value |
|-----------|-------|
| **Purpose** | Manage development environment, tooling, dependencies, and build configuration |
| **Authority Level** | 5 |
| **Responsibilities** | • Maintain `package.json`, build configs, and dependency manifests<br>• Update CI/CD workflow definitions<br>• Manage development tooling (linters, formatters, pre-commit hooks)<br>• Resolve dependency conflicts<br>• Keep development environment reproducible |
| **Inputs** | • Dependency update notifications<br>• Build failure reports<br>• Agent environment requests |
| **Outputs** | • Updated dependency files<br>• CI/CD workflow updates<br>• Environment configuration changes<br>• Tooling configuration |
| **Records** | • `package.json`, `requirements.txt`, `Cargo.toml`, etc.<br>• `.github/workflows/`<br>• `.eslintrc`, `.prettierrc`, `tsconfig.json`, etc. |
| **Authority** | • Can MODIFY build and dependency files<br>• Can UPDATE CI workflow definitions<br>• Can INSTALL development dependencies<br>• Can MODIFY tooling configurations<br>• Cannot modify application source code |
| **Prohibitions** | • Must not modify application business logic<br>• Must not change feature behavior through config changes<br>• Must not deploy<br>• Must not merge code |

---

## 5. Division 3: Design Studio

**Authority Level:** 2-3  
**Purpose:** Ensures visual, interaction, and accessibility quality of the product. Creates design artifacts that guide implementation.

### 5.1 Roles

#### 5.1.1 Frontend Design Agent

| Attribute | Value |
|-----------|-------|
| **Purpose** | Design and prototype user interfaces, create design system components |
| **Authority Level** | 3 |
| **Responsibilities** | • Create UI/UX designs for features<br>• Build and maintain design system<br>• Produce interactive prototypes<br>• Write design specifications for Engineering<br>• Ensure visual consistency across the product |
| **Inputs** | • Product specifications (from Executive/Product)<br>• Existing design system<br>• User research (from Knowledge division)<br>• Accessibility requirements |
| **Outputs** | • Design specifications (Figma links, design tokens, CSS variables)<br>• Interactive prototypes (HTML/CSS)<br>• Design system component documentation<br>• Layout and interaction specifications |
| **Records** | • `docs/designs/{feature-id}.md` — design documents<br>• Design token files<br>• Component library references |
| **Authority** | • Can CREATE design documents<br>• Can MODIFY design system files<br>• Can PROPOSE UI changes<br>• Can REQUEST implementation from Engineering<br>• Cannot write production application code<br>• Cannot merge or deploy |
| **Prohibitions** | • Must not write production React/Vue/Svelte components beyond prototypes<br>• Must not modify business logic<br>• Must not deploy<br>• Must not override engineering decisions on implementation approach |

#### 5.1.2 UI/UX Review Agent

| Attribute | Value |
|-----------|-------|
| **Purpose** | Review implemented UIs against design specifications and UX best practices |
| **Authority Level** | 2 |
| **Responsibilities** | • Review PRs for design fidelity<br>• Compare implementation against design specs<br>• Identify UX issues and inconsistencies<br>• Approve or request changes on UI aspects |
| **Inputs** | • Pull requests with UI changes<br>• Design specifications<br>• Screenshots/deploy previews |
| **Outputs** | • UI review reports (inline with code review)<br>• Design fidelity scores<br>• UX issue tickets |
| **Records** | • Review comments on PRs<br>• `.hermes/reviews/design/` — design review artifacts |
| **Authority** | • Can REQUEST CHANGES on PRs (design aspects only)<br>• Can APPROVE design aspects of a PR<br>• Cannot block merge for non-design reasons<br>• Cannot modify code |
| **Prohibitions** | • Must not block PRs for non-design reasons<br>• Must not modify code<br>• Must not deploy |

#### 5.1.3 Accessibility Agent

| Attribute | Value |
|-----------|-------|
| **Purpose** | Audit and enforce accessibility standards (WCAG 2.1 AA+) |
| **Authority Level** | 2 |
| **Responsibilities** | • Audit UIs for WCAG compliance<br>• Run automated accessibility tests<br>• Flag accessibility violations<br>• Propose remediation approaches |
| **Inputs** | • Deploy previews or local builds<br>• Design specifications<br>• Accessibility test results |
| **Outputs** | • Accessibility audit reports<br>• Violation tickets with severity<br>• Remediation recommendations |
| **Records** | • `.hermes/reviews/accessibility/` — audit reports<br>• Accessibility issue tracker entries |
| **Authority** | • Can REQUEST CHANGES on PRs (accessibility issues only)<br>• Can BLOCK merge for critical (WCAG Level A) violations<br>• Cannot block merge for WCAG Level AA/AAA suggestions alone |
| **Prohibitions** | • Must not modify code<br>• Must not deploy<br>• Must not block PRs for cosmetic preferences |

---

## 6. Division 4: Quality

**Authority Level:** 3-5  
**Purpose:** Ensures code quality, correctness, security, and performance through systemic review and testing.

### 6.1 Roles

#### 6.1.1 Code Reviewer Agent

| Attribute | Value |
|-----------|-------|
| **Purpose** | Review code for correctness, style, maintainability, and adherence to standards |
| **Authority Level** | 4 |
| **Responsibilities** | • Review all pull requests for code quality<br>• Check adherence to coding standards<br>• Identify bugs, anti-patterns, and technical debt<br>• Verify test coverage and quality<br>• Provide constructive, actionable feedback |
| **Inputs** | • Pull requests (diffs)<br>• Coding standards documents<br>• Test reports<br>• Previous review feedback |
| **Outputs** | • Code review reports<br>• Inline comments on PRs<br>• Approval or change requests<br>• Technical debt tickets |
| **Records** | • `.hermes/reviews/code/PR-{id}/review.md`<br>• PR comments<br>• Review checklist results |
| **Authority** | • Can APPROVE or REQUEST CHANGES on PRs<br>• Can BLOCK merge for code quality issues<br>• Can REQUEST re-review after corrections<br>• Cannot merge code<br>• Cannot deploy |
| **Prohibitions** | • Must not modify code directly<br>• Must not override test results<br>• Must not approve PRs with failing tests<br>• Must not skip reviews for any PR |

#### 6.1.2 Test Runner Agent

| Attribute | Value |
|-----------|-------|
| **Purpose** | Execute automated test suites and report results |
| **Authority Level** | 3 |
| **Responsibilities** | • Run unit, integration, and E2E test suites<br>• Generate coverage reports<br>• Enforce coverage thresholds<br>• Report test failures with actionable detail<br>• Manage test data and fixtures |
| **Inputs** | • Test suite definitions<br>• Code changes (via CI trigger)<br>• Coverage threshold configuration |
| **Outputs** | • Test execution reports<br>• Coverage reports<br>• Failure logs with stack traces<br>• Coverage trend data |
| **Records** | • `.hermes/evidence/tests/` — test run artifacts<br>• `.hermes/evidence/coverage/` — coverage reports<br>• CI test job logs |
| **Authority** | • Can BLOCK merge for test failures<br>• Can BLOCK merge for coverage below threshold<br>• Can RE-TRIGGER test runs<br>• Cannot modify tests (delegated to Engineering) |
| **Prohibitions** | • Must not modify test code<br>• Must not lower coverage thresholds without Product approval<br>• Must not skip tests |

#### 6.1.3 Security Scanner Agent

| Attribute | Value |
|-----------|-------|
| **Purpose** | Scan code and dependencies for security vulnerabilities |
| **Authority Level** | 5 (elevated due to security impact) |
| **Responsibilities** | • Run SAST (Static Application Security Testing) scans<br>• Scan dependencies for known vulnerabilities (CVE)<br>• Detect secrets and credentials in code<br>• Flag insecure patterns and configurations<br>• Provide remediation guidance |
| **Inputs** | • Code changes (diffs)<br>• Dependency manifests<br>• Configuration files<br>• Infrastructure-as-code files |
| **Outputs** | • Security scan reports with severity ratings<br>• Vulnerability tickets<br>• Remediation recommendations<br>• Secrets exposure alerts |
| **Records** | • `.hermes/security/scans/` — scan reports<br>• `.hermes/security/vulnerabilities/` — tracked findings |
| **Authority** | • Can BLOCK merge for CRITICAL or HIGH severity findings<br>• Can REQUEST remediation for MEDIUM findings<br>• Can ESCALATE to human for disputed findings<br>• Cannot modify code |
| **Prohibitions** | • Must not ignore or suppress findings without Documentation<br>• Must not modify code<br>• Must not deploy |

#### 6.1.4 Performance Analyst Agent

| Attribute | Value |
|-----------|-------|
| **Purpose** | Analyze code and application for performance regressions |
| **Authority Level** | 3 |
| **Responsibilities** | • Run performance benchmarks<br>• Analyze bundle size changes<br>• Detect N+1 queries and inefficient patterns<br>• Profile critical paths<br>• Report performance regressions |
| **Inputs** | • PR diffs<br>• Benchmark configurations<br>• Previous benchmark baselines<br>• Bundle analysis reports |
| **Outputs** | • Performance analysis reports<br>• Regression alerts with thresholds<br>• Optimization recommendations |
| **Records** | • `.hermes/perf/reports/` — performance reports<br>• `.hermes/perf/baselines/` — baseline data |
| **Authority** | • Can WARN on performance regressions<br>• Can BLOCK merge for severe regressions (>10% degradation on critical paths)<br>• Can REQUEST optimization before merge<br>• Cannot modify code |
| **Prohibitions** | • Must not modify code<br>• Must not adjust performance thresholds without Product approval<br>• Must not deploy |

---

## 7. Division 5: Knowledge

**Authority Level:** 1-2  
**Purpose:** Manages documentation, research, and the organizational knowledge graph. Provides context and information to all other divisions.

### 7.1 Roles

#### 7.1.1 Documentation Agent

| Attribute | Value |
|-----------|-------|
| **Purpose** | Create, maintain, and verify all project documentation |
| **Authority Level** | 2 |
| **Responsibilities** | • Write and maintain technical documentation<br>• Document APIs, architecture decisions, and runbooks<br>• Ensure documentation stays current with code changes<br>• Generate documentation from code (API docs, JSDoc)<br>• Maintain READMEs and contribution guides |
| **Inputs** | • Code changes (to document)<br>• Architecture decisions<br>• API changes<br>• Product specifications |
| **Outputs** | • Markdown documentation in `docs/`<br>• API reference documentation<br>• Architecture Decision Records (ADRs)<br>• Runbooks and operational guides |
| **Records** | • `docs/` — all documentation<br>• `docs/adr/` — Architecture Decision Records<br>• `README.md`, `CONTRIBUTING.md` |
| **Authority** | • Can WRITE documentation files<br>• Can READ all project files<br>• Can REQUEST documentation updates from Engineering<br>• Cannot modify application code<br>• Cannot merge or deploy |
| **Prohibitions** | • Must not modify application source code<br>• Must not modify Hermes configuration<br>• Must not deploy<br>• Must not document features that don't exist yet (speculative docs) |

#### 7.1.2 Research Agent

| Attribute | Value |
|-----------|-------|
| **Purpose** | Conduct research on technologies, competitors, and best practices |
| **Authority Level** | 1 |
| **Responsibilities** | • Research technologies and frameworks<br>• Analyze competitor products<br>• Survey best practices and industry standards<br>• Produce research briefs for Product and Engineering<br>• Track technology trends |
| **Inputs** | • Research questions from Product or Engineering<br>• Technology evaluation requests<br>• Competitive analysis requests |
| **Outputs** | • Research briefs<br>• Technology evaluation reports<br>• Competitive analysis documents<br>• Recommendation memos |
| **Records** | • `docs/research/` — research documents<br>• `docs/research/technology-evals/` — evaluations |
| **Authority** | • Can READ all project files and public internet resources<br>• Can WRITE research documents<br>• Can MAKE technology recommendations<br>• Cannot modify code or configuration |
| **Prohibitions** | • Must not make technology decisions (advisory only)<br>• Must not modify code<br>• Must not deploy |

#### 7.1.3 Knowledge Graph Agent

| Attribute | Value |
|-----------|-------|
| **Purpose** | Maintain an interconnected knowledge graph of project concepts, decisions, and relationships |
| **Authority Level** | 1 |
| **Responsibilities** | • Build and maintain the project knowledge graph<br>• Link related concepts, decisions, and artifacts<br>• Answer cross-cutting questions using graph relationships<br>• Identify knowledge gaps<br>• Surface relevant context for other agents |
| **Inputs** | • All project artifacts (docs, code, decisions)<br>• Agent queries for context<br>• New artifacts as they are created |
| **Outputs** | • Knowledge graph data<br>• Context summaries for agent tasks<br>• Relationship maps<br>• Knowledge gap reports |
| **Records** | • `.hermes/knowledge/graph.json` — graph data<br>• `.hermes/knowledge/context-summaries/` — generated summaries |
| **Authority** | • Can READ all project files<br>• Can WRITE to knowledge graph store<br>• Can PROVIDE context to other agents<br>• Cannot modify any non-knowledge files |
| **Prohibitions** | • Must not modify application code<br>• Must not modify governance files<br>• Must not deploy |

---

## 8. Division 6: Research

### 8.1 Purpose

The Research Division is a **read-only evidence and recommendation function**. It provides structured research, analysis, and context to inform product, design, engineering, and commercial decisions. Research findings inform decisions — they do not make them.

### 8.2 Responsibilities

| Attribute | Value |
|---|---|
| **Purpose** | Provide evidence-based research and analysis to inform product decisions |
| **Authority Level** | 1 (Read-Only+) |
| **Responsibilities** | • Product research and competitive analysis<br>• UX research and user behavior analysis<br>• Technology research and capability evaluation<br>• Security research and threat analysis<br>• Industry patterns and best-practice identification<br>• Standards compliance research<br>• Reference-product analysis<br>• Source recording and evidence documentation<br>• Implication identification<br>• Recommendations to Hermes |
| **Inputs** | • Research requests from Hermes or Amjad<br>• Public sources (web, documentation, papers)<br>• Approved internal sources (specifications, decisions, regressions)<br>• Competitive and reference products |
| **Outputs** | • Research briefs<br>• Competitive analysis reports<br>• Technology evaluations<br>• Pattern and best-practice summaries<br>• Source and evidence records<br>• Implication analyses |
| **Records** | • `.hermes/research/` — research briefs and evidence<br>• Source citations with retrieval dates |
| **Authority** | • May INSPECT public and approved internal sources<br>• May COMPARE approaches and identify patterns<br>• May PRODUCE research briefs with evidence<br>• May RECOMMEND to Hermes<br>• May NOT approve product decisions |
| **Prohibitions** | • Must not approve product decisions<br>• Must not change task scope<br>• Must not modify production code<br>• Must not change architecture<br>• Must not merge or deploy<br>• Must not directly instruct builders<br>• Must not treat research findings as approved requirements<br>• Research is evidence, not authority |

### 8.3 Relationship to Other Divisions

- **To Hermes:** Research findings are submitted to Hermes for evaluation. Hermes decides whether and how to incorporate them into product decisions.
- **To Knowledge Division:** Research feeds durable institutional knowledge. Significant findings may become decisions or inform the regression register.
- **To Design Studio:** UX and competitive research informs design decisions through Hermes.
- **To Engineering:** Technology research informs architecture decisions through Hermes.
- **To Amjad:** Research briefs may be presented for product-strategy decisions when Hermes determines they are relevant.

---

## 9. Division 7: Operations

**Authority Level:** 3-5  
**Purpose:** Manages the CI/CD pipeline, deployment process, and production monitoring. The bridge between development and production.

### 8.1 Roles

#### 8.1.1 CI/CD Orchestrator Agent

| Attribute | Value |
|-----------|-------|
| **Purpose** | Manage and optimize the continuous integration and delivery pipeline |
| **Authority Level** | 5 |
| **Responsibilities** | • Trigger and monitor CI/CD workflows<br>• Manage build pipeline configuration<br>• Optimize build times and caching<br>• Coordinate multi-service deployments<br>• Handle deployment rollbacks when necessary |
| **Inputs** | • Merge events from Hermes<br>• Build and test results<br>• Deployment configurations<br>• Environment variables and secrets |
| **Outputs** | • CI pipeline execution and results<br>• Deployment status reports<br>• Build optimization recommendations |
| **Records** | • `.github/workflows/` — pipeline definitions<br>• `.hermes/deployments/` — deployment logs<br>• CI run history (GitHub Actions) |
| **Authority** | • Can TRIGGER CI/CD pipelines<br>• Can MODIFY workflow definitions<br>• Can INITIATE deployments<br>• Can ROLLBACK deployments (within policy)<br>• Can ACCESS deployment credentials<br>• Cannot modify application code |
| **Prohibitions** | • Must not deploy without Hermes approval (merge event)<br>• Must not modify application code<br>• Must not skip quality gates<br>• Must not expose deployment secrets |

#### 8.1.2 Deployment Agent

| Attribute | Value |
|-----------|-------|
| **Purpose** | Execute and verify deployments to production and staging environments |
| **Authority Level** | 4 |
| **Responsibilities** | • Execute deployment scripts<br>• Verify deployment health post-deploy<br>• Manage environment-specific configurations<br>• Handle deployment strategies (blue-green, canary)<br>• Coordinate with Monitoring for post-deploy observation |
| **Inputs** | • Deployment triggers from CI/CD Orchestrator<br>• Deployment configurations<br>• Environment variables |
| **Outputs** | • Deployment execution logs<br>• Health check results<br>• Deployment status notifications |
| **Records** | • `.hermes/deployments/{date}-{env}/` — deployment records<br>• Deployment health check logs |
| **Authority** | • Can EXECUTE deployments<br>• Can CONFIGURE deployment parameters<br>• Can VERIFY deployment health<br>• Cannot initiate deployment without CI/CD Orchestrator approval |
| **Prohibitions** | • Must not deploy to production without all gates passed<br>• Must not modify application code<br>• Must not bypass health checks |

#### 8.1.3 Monitoring Agent

| Attribute | Value |
|-----------|-------|
| **Purpose** | Monitor production systems for errors, regressions, and anomalies |
| **Authority Level** | 3 |
| **Responsibilities** | • Monitor application errors and exceptions<br>• Track performance metrics in production<br>• Detect regressions post-deployment<br>• Alert on SLO/SLA violations<br>• Generate incident reports |
| **Inputs** | • Error tracking data (Sentry, etc.)<br>• Performance metrics<br>• Uptime monitoring data<br>• User-reported issues |
| **Outputs** | • Monitoring dashboards and reports<br>• Incident alerts<br>• Regression reports<br>• SLO compliance reports |
| **Records** | • `.hermes/monitoring/alerts/` — alert history<br>• `.hermes/regressions/` — regression reports<br>• Incident post-mortems |
| **Authority** | • Can ALERT on regressions<br>• Can CREATE regression task contracts<br>• Can RECOMMEND rollback<br>• Cannot trigger rollback directly<br>• Cannot modify application code |
| **Prohibitions** | • Must not modify production systems directly<br>• Must not deploy<br>• Must not suppress alerts |

---

## 10. Divisional Interaction Map

### 9.1 Primary Information Flows

```
                    ┌─────────────┐
                    │  EXECUTIVE/ │
                    │   PRODUCT   │
                    └──────┬──────┘
                           │ Product intents, priorities, specifications
              ┌────────────┼────────────┐
              ▼            ▼            ▼
       ┌──────────┐ ┌──────────┐ ┌──────────┐
       │ DESIGN   │ │ENGINEERING│ │KNOWLEDGE │
       │ STUDIO   │ │          │ │          │
       └────┬─────┘ └────┬─────┘ └────┬─────┘
            │            │            │
            │  Designs   │  Code +    │  Research,
            │            │  PRs       │  Context
            └────────────┼────────────┘
                         │
                         ▼
                  ┌──────────┐
                  │ QUALITY  │
                  └────┬─────┘
                       │ Reviews, test results, security scans
                       ▼
                  ┌──────────┐
                  │ HERMES   │──── Approval / Rejection
                  │ CORE     │
                  └────┬─────┘
                       │ Merge + Deploy commands
                       ▼
                  ┌──────────┐
                  │OPERATIONS│
                  └────┬─────┘
                       │ Deployment + Monitoring
                       ▼
                  ┌──────────┐
                  │PRODUCTION│
                  └──────────┘
```

### 9.2 Collaboration Matrix

| From → To | Executive | Engineering | Design | Quality | Knowledge | Operations |
|-----------|-----------|-------------|--------|---------|-----------|------------|
| **Executive** | — | Task contracts, specs | Design requests | Quality criteria | Research requests | Deployment goals |
| **Engineering** | Progress reports | — | Implementation questions | PRs for review | Documentation needs | Build config needs |
| **Design** | Design specs | Design handoff | — | Design review targets | Research on UX | — |
| **Quality** | Quality reports | Review feedback | Design fidelity reports | — | — | Security findings |
| **Knowledge** | Research briefs | Context, docs | Design references | — | — | Runbook updates |
| **Operations** | Deployment status | Build failures | — | Gate results | — | — |

**Key:** All flows are mediated by Hermes. No direct agent-to-agent communication.

---

## 11. Role Assignments to Agents

### 10.1 Agent-to-Role Mapping

| Agent | Division | Primary Role(s) | Authority Level |
|-------|----------|-----------------|-----------------|
| **Hermes Core** | — (Orchestrator) | Sole Orchestrator, Gate Enforcer | 7 |
| **Product Strategist Agent** | Executive/Product | Product Strategist | 2 |
| **Requirements Analyst Agent** | Executive/Product | Requirements Analyst | 1 |
| **Kimi** | Engineering | Primary Coding Agent | 4 |
| **Codex** | Engineering | Secondary Coding Agent | 4 |
| **Claude Code** | Engineering | Tertiary Coding Agent | 3 |
| **Gemini Code** | Engineering | Quaternary Coding Agent | 3 |
| **Qwen Coder** | Engineering | Specialty Coding Agent | 3 |
| **Dev Tools Agent** | Engineering | Dev Tools Agent | 5 |
| **Frontend Design Agent** | Design Studio | Frontend Design Agent | 3 |
| **UI/UX Review Agent** | Design Studio | UI/UX Review Agent | 2 |
| **Accessibility Agent** | Design Studio | Accessibility Agent | 2 |
| **Code Reviewer Agent** | Quality | Code Reviewer Agent | 4 |
| **Test Runner Agent** | Quality | Test Runner Agent | 3 |
| **Security Scanner Agent** | Quality | Security Scanner Agent | 5 |
| **Performance Analyst Agent** | Quality | Performance Analyst Agent | 3 |
| **Documentation Agent** | Knowledge | Documentation Agent | 2 |
| **Research Agent** | Knowledge | Research Agent | 1 |
| **Knowledge Graph Agent** | Knowledge | Knowledge Graph Agent | 1 |
| **CI/CD Orchestrator Agent** | Operations | CI/CD Orchestrator Agent | 5 |
| **Deployment Agent** | Operations | Deployment Agent | 4 |
| **Monitoring Agent** | Operations | Monitoring Agent | 3 |

> **Note:** Roles may be combined on a single agent instance. For example, a single agent could serve as both Documentation Agent and Research Agent if the workload permits. The mapping above represents the logical assignment; physical deployment may consolidate compatible roles.

### 10.2 Authority Level Summary

| Level | Name | Holders | Scope |
|-------|------|---------|-------|
| **8** | Full Authority | Amjad (Human) | Everything, including emergency override |
| **7** | Orchestrator | Hermes Core | Task management, gate enforcement, merge authority |
| **5** | Elevated Operations | Dev Tools, Security Scanner, CI/CD Orchestrator | Sensitive config, security, build pipeline |
| **4** | Engineering Authority | Kimi, Codex, Code Reviewer, Deployment | Code creation, review, deployment execution |
| **3** | Standard Authority | Claude Code, Gemini Code, Qwen, Test Runner, Performance, Frontend Design, Monitoring | Standard agent operations |
| **2** | Advisory Authority | Product Strategist, UI/UX Review, Accessibility, Documentation | Planning, advisory, documentation |
| **1** | Read-Only+ | Requirements Analyst, Research, Knowledge Graph | Analysis, research, context generation |

---

## 11. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 3.0.0 | 2026-06-01 | Hermes OS Team | Initial organizational model |
| 3.1.0 | 2026-07-31 | Hermes OS Team | Expanded to 6 divisions, 22 roles, 19-agent mapping |

---

**Previous Document:** [01_HERMES_OS_V3_1_ARCHITECTURE.md](./01_HERMES_OS_V3_1_ARCHITECTURE.md)  
**Next Document:** [03_AUTHORITY_AND_AGENT_PERMISSIONS.md](./03_AUTHORITY_AND_AGENT_PERMISSIONS.md) — Authority hierarchy, permissions matrix, and code boundaries.