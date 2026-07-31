# Hermes OS v3.1 — Architecture Specification

**Document ID:** HERMES-OS-ARCH-v3.1.0  
**Version:** 3.1.0  
**Status:** Draft  
**Last Updated:** 2026-07-31  
**Owner:** Hermes Engineering OS Foundation  
**Dependencies:** None (foundational document)

---

## Table of Contents

1. [Overview](#1-overview)
2. [System Architecture Diagram](#2-system-architecture-diagram)
3. [Data Flow Architecture](#3-data-flow-architecture)
4. [Component Map](#4-component-map)
5. [Technology Stack](#5-technology-stack)
6. [Storage Layout](#6-storage-layout)
7. [Message Flow: The Development Lifecycle](#7-message-flow-the-development-lifecycle)
8. [Network Topology & Security Boundaries](#8-network-topology--security-boundaries)
9. [Scaling & Resilience Design](#9-scaling--resilience-design)
10. [Version History](#10-version-history)

---

## 1. Overview

### 1.1 Purpose

Hermes OS v3.1 is an AI-native engineering operating system that orchestrates a fleet of specialized AI agents to build, review, test, and deploy software. Hermes itself acts as the **sole orchestrator** — a central coordination layer that routes tasks, enforces governance, manages state, and ensures quality gates are met before any code reaches production.

### 1.2 Core Design Principles

| Principle | Description |
|-----------|-------------|
| **Single Orchestrator** | Hermes is the only entity that can create, assign, and track tasks across divisions. No agent communicates directly with another agent without Hermes mediation. |
| **Immutable Evidence Chain** | Every decision, review, test result, and approval is recorded as an immutable artifact. Nothing enters production without a verifiable trail. |
| **Division of Responsibility** | Six specialized divisions handle distinct concerns. Agents within divisions have narrowly scoped authority. |
| **Hermes Code Boundary** | Hermes may write docs, plans, schemas, and policies. All product code changes are delegated to specialized coding agents (Kimi, Codex). |
| **Gate-Enforced Delivery** | No code reaches production without passing through mandatory quality gates. Gates are enforced programmatically, not by convention. |

### 1.3 System Context

Hermes OS sits between the human operator (Amjad) and the software delivery pipeline. It translates high-level product intents into structured task contracts, dispatches them to specialized agents, aggregates results, enforces quality standards, and orchestrates the merge/deploy pipeline through GitHub integration.

```
┌─────────┐     ┌──────────────────────────────────────────────────────────────┐
│  Amjad  │────▶│                     Hermes OS v3.1                            │
│ (Human) │     │  ┌──────────┬──────────┬──────────┬──────────┬──────────┐    │
└─────────┘     │  │Executive │Engineering│ Design   │ Quality  │Knowledge │    │
                │  │/Product  │          │ Studio   │          │          │    │
                │  ├──────────┴──────────┴──────────┴──────────┴──────────┤    │
                │  │                    Operations                         │    │
                │  └──────────────────────────────────────────────────────┘    │
                │                              │                                │
                │                              ▼                                │
                │  ┌──────────────────────────────────────────────────────┐    │
                │  │    GitHub Integration (PRs, CI, Merge, Deploy)        │    │
                │  └──────────────────────────────────────────────────────┘    │
                └──────────────────────────────────────────────────────────────┘
```

---

## 2. System Architecture Diagram

### 2.1 High-Level Architecture

```
                                    ┌─────────────────────────┐
                                    │        Amjad            │
                                    │   (Human Operator)      │
                                    └───────────┬─────────────┘
                                                │ Intent / Goals
                                                ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                              HERMES OS v3.1 CORE                                    │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                         Orchestration Engine                                  │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │   │
│  │  │ Task     │  │ Contract │  │ State    │  │ Routing  │  │ Event    │       │   │
│  │  │ Parser   │  │ Manager  │  │ Machine  │  │ Engine   │  │ Bus      │       │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │                          DIVISION LAYER                                        │  │
│  │                                                                                │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │  │
│  │  │  Executive/  │ │ Engineering  │ │   Design     │ │   Quality    │          │  │
│  │  │   Product    │ │              │ │   Studio     │ │              │          │  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘          │  │
│  │                                                                                │  │
│  │  ┌──────────────┐ ┌──────────────────────────────────────────────┐            │  │
│  │  │  Knowledge   │ │              Operations                      │            │  │
│  │  └──────────────┘ └──────────────────────────────────────────────┘            │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │                         AGENT FLEET (19 Agents)                                │  │
│  │                                                                                │  │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐     │  │
│  │  │Hermes│ │ Kimi │ │Codex │ │Claude│ │Gemini│ │  Qwen│ │  Cursor│ │  …   │     │  │
│  │  │Core  │ │      │ │      │ │ Code │ │      │ │      │ │       │ │      │     │  │
│  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘     │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │                    GOVERNANCE & POLICY LAYER                                    │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │  │
│  │  │ Auth     │  │ Single   │  │ Quality  │  │ Audit    │  │ Emergency│       │  │
│  │  │ Matrix   │  │ Writer   │  │ Gates    │  │ Trail    │  │ Override │       │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                     │
└───────────────────────────────────────────────────────────────────────────────────┘
                                                │
                    ┌───────────────────────────┼───────────────────────────┐
                    ▼                           ▼                           ▼
            ┌──────────────┐           ┌──────────────┐           ┌──────────────┐
            │   GitHub     │           │   CI/CD      │           │  Deployment  │
            │   (PRs,      │           │   Pipeline   │           │  Targets     │
            │   Branches)  │           │   (Tests,    │           │  (Vercel,    │
            │              │           │    Builds)   │           │   Cloudflare)│
            └──────────────┘           └──────────────┘           └──────────────┘
```

### 2.2 Agent Topology

Hermes OS v3.1 manages 19 agents organized under six divisions:

```
Hermes OS v3.1 Agent Topology
═══════════════════════════════

DIVISION 1: EXECUTIVE / PRODUCT (Level 1-2)
├── Hermes Core (Orchestrator, Level 8)
├── Product Strategist Agent
└── Requirements Analyst Agent

DIVISION 2: ENGINEERING (Level 3-5)
├── Kimi (Primary Coding Agent)
├── Codex (Secondary Coding Agent)
├── Claude Code (Tertiary Coding Agent)
├── Gemini Code (Quaternary Coding Agent)
├── Qwen Coder (Specialty Coding Agent)
└── Dev Tools Agent (Environment, Config)

DIVISION 3: DESIGN STUDIO (Level 2-3)
├── Frontend Design Agent
├── UI/UX Review Agent
└── Accessibility Agent

DIVISION 4: QUALITY (Level 3-5)
├── Code Reviewer Agent
├── Test Runner Agent
├── Security Scanner Agent
└── Performance Analyst Agent

DIVISION 5: KNOWLEDGE (Level 1-2)
├── Documentation Agent
├── Research Agent
└── Knowledge Graph Agent

DIVISION 6: OPERATIONS (Level 3-5)
├── CI/CD Orchestrator Agent
├── Deployment Agent
└── Monitoring Agent
```

---

## 3. Data Flow Architecture

### 3.1 End-to-End Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DATA FLOW PIPELINE                                  │
│                                                                              │
│  AMJAD                                                                       │
│    │                                                                         │
│    │  Product Intent / Feature Request                                       │
│    ▼                                                                         │
│  ┌──────────────────────┐                                                    │
│  │  TASK CONTRACT (TC)  │  ◀── Hermes parses intent into structured contract │
│  │  - Objective         │                                                    │
│  │  - Scope             │                                                    │
│  │  - Acceptance Criteria│                                                   │
│  │  - Agent Assignments │                                                    │
│  │  - Gate Requirements │                                                    │
│  └──────────┬───────────┘                                                    │
│             │                                                                │
│             ├────────────────────────────────────────────┐                   │
│             ▼                                            ▼                   │
│  ┌──────────────────┐                        ┌──────────────────┐            │
│  │  SPECIFICATION   │                        │  DESIGN DOCS     │            │
│  │  (Hermes writes) │                        │  (Design Studio) │            │
│  └────────┬─────────┘                        └────────┬─────────┘            │
│           │                                           │                      │
│           └───────────────┬───────────────────────────┘                      │
│                           ▼                                                  │
│                  ┌──────────────────┐                                        │
│                  │ IMPLEMENTATION   │  ◀── Kimi / Codex / Claude Code        │
│                  │ (Coding Agents)  │                                        │
│                  └────────┬─────────┘                                        │
│                           │                                                  │
│                           ▼                                                  │
│                  ┌──────────────────┐                                        │
│                  │  EVIDENCE PACK   │  ◀── Test results, coverage, lint      │
│                  │  - Unit Tests    │                                        │
│                  │  - Integration   │                                        │
│                  │  - Coverage Rpt  │                                        │
│                  │  - Lint Results  │                                        │
│                  │  - Build Status  │                                        │
│                  └────────┬─────────┘                                        │
│                           │                                                  │
│                           ▼                                                  │
│                  ┌──────────────────┐                                        │
│                  │  CODE REVIEW     │  ◀── Reviewer Agent(s)                 │
│                  │  - Diff Analysis │                                        │
│                  │  - Standards Chk │                                        │
│                  │  - Security Scan │                                        │
│                  │  - Perf Analysis │                                        │
│                  └────────┬─────────┘                                        │
│                           │                                                  │
│                    ┌──────┴──────┐                                           │
│                    ▼             ▼                                           │
│              ┌──────────┐  ┌──────────┐                                      │
│              │ APPROVED  │  │ REJECTED │  ◀── Back to implementation         │
│              │  (Pass)   │  │ (Cycle)  │                                      │
│              └─────┬─────┘  └──────────┘                                      │
│                    │                                                          │
│                    ▼                                                          │
│              ┌──────────┐                                                     │
│              │  MERGE   │  ◀── Hermes executes merge (if authorized)          │
│              │  TO MAIN │                                                     │
│              └─────┬────┘                                                     │
│                    │                                                          │
│                    ▼                                                          │
│              ┌──────────┐                                                     │
│              │  DEPLOY  │  ◀── CI/CD triggers deployment                     │
│              └─────┬────┘                                                     │
│                    │                                                          │
│                    ▼                                                          │
│              ┌──────────┐                                                     │
│              │REGRESSION│  ◀── Post-deploy monitoring & alerts               │
│              │ MONITOR  │                                                     │
│              └──────────┘                                                     │
│                                                                              │
│  FEEDBACK LOOP: Any regression → new Task Contract → repeat cycle            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Data Artifacts Catalog

| Artifact | Producer | Consumer | Persistence | Immutable |
|----------|----------|----------|-------------|-----------|
| Task Contract | Hermes Core | All agents | Project repo `.hermes/contracts/` | Yes |
| Specification | Hermes Core | Coding agents | Project repo `docs/specs/` | Yes (versioned) |
| Design Document | Design Studio | Coding agents, Reviewers | Project repo `docs/designs/` | Yes (versioned) |
| Implementation PR | Kimi/Codex/Claude | Reviewers, CI | GitHub | Version-controlled |
| Test Evidence | Test Runner | Quality agents | CI artifacts, `.hermes/evidence/` | Yes |
| Code Review Report | Reviewer Agent | Hermes, Coding agents | `.hermes/reviews/` | Yes |
| Security Scan | Security Scanner | Quality agents | `.hermes/security/` | Yes |
| Performance Profile | Performance Analyst | Engineering agents | `.hermes/perf/` | Yes (per-run) |
| Approval Record | Hermes Core | Audit trail | `.hermes/approvals/` | Yes |
| Deployment Log | Deployment Agent | Operations, Monitoring | `.hermes/deployments/` | Yes |
| Regression Report | Monitoring Agent | All divisions | `.hermes/regressions/` | Yes |

### 3.3 State Machine

```
                    ┌──────────┐
                    │  DRAFT   │
                    └────┬─────┘
                         │ Hermes publishes contract
                         ▼
                    ┌──────────┐
                    │ PLANNING │
                    └────┬─────┘
                         │ Specs & designs complete
                         ▼
                    ┌──────────┐
                    │ BUILDING │◄──────────────────────┐
                    └────┬─────┘                       │
                         │ Code committed               │
                         ▼                              │
                    ┌──────────┐                       │
                    │ TESTING  │                       │
                    └────┬─────┘                       │
                         │                              │
                    ┌────┴────┐                        │
                    ▼         ▼                        │
              ┌──────────┐  ┌──────────┐              │
              │ REVIEWING│  │  FAILED  │──────────────┘
              └────┬─────┘  └──────────┘   (retry)
                   │
              ┌────┴────┐
              ▼         ▼
        ┌──────────┐  ┌──────────┐
        │ APPROVED │  │ REJECTED │──────────────┐
        └────┬─────┘  └──────────┘              │
             │                          (back to BUILDING)
             ▼
        ┌──────────┐
        │ MERGING  │
        └────┬─────┘
             │
             ▼
        ┌──────────┐
        │DEPLOYING │
        └────┬─────┘
             │
             ▼
        ┌──────────┐
        │ MONITOR  │──── regression detected ────▶ DRAFT (new contract)
        └──────────┘
```

---

## 4. Component Map

### 4.1 Core Components

| Component | Responsibility | Technology | Internal/External |
|-----------|---------------|------------|-------------------|
| **Orchestration Engine** | Task parsing, contract management, state machine, routing, event bus | Python 3.11+ (FastAPI + asyncio) | Internal |
| **Agent Runtime** | Agent lifecycle, sandboxing, tool provisioning, context injection | Python + Docker | Internal |
| **Governance Layer** | Auth matrix, single-writer enforcement, quality gates, audit trail | Python + SQLite/Postgres | Internal |
| **GitHub Integration** | PR creation, branch management, merge execution, CI trigger | GitHub REST API + GraphQL | External (SaaS) |
| **CI/CD Pipeline** | Build, test, lint, coverage, deploy | GitHub Actions / custom runners | External (SaaS) |
| **Deployment Targets** | Production hosting, CDN, serverless functions | Vercel, Cloudflare Workers | External (SaaS) |
| **Monitoring & Observability** | Error tracking, performance monitoring, uptime | Sentry, custom telemetry | External (SaaS) |
| **Knowledge Store** | Documentation, research artifacts, knowledge graph | Markdown files in repo + vector DB | Internal |
| **Audit Trail DB** | Immutable record of all actions, decisions, and approvals | SQLite (embedded) or Postgres | Internal |
| **Configuration Store** | Agent configs, division policies, gate rules | YAML/TOML in `.hermes/` | Internal |

### 4.2 Interface Boundaries

```
┌────────────────────────────────────────────────────────────────┐
│                     EXTERNAL BOUNDARIES                         │
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ GitHub   │    │ CI/CD    │    │ Deploy   │    │ Monitor  │  │
│  │ API      │    │ Runners  │    │ Targets  │    │ Services │  │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘  │
│       │               │               │               │         │
│  ─────┼───────────────┼───────────────┼───────────────┼─────    │
│       │     TRUST BOUNDARY (Hermes authenticates to all)  │     │
│  ─────┼───────────────┼───────────────┼───────────────┼─────    │
│       │               │               │               │         │
│  ┌────┴───────────────┴───────────────┴───────────────┴────┐   │
│  │                  HERMES OS v3.1 CORE                     │   │
│  │                                                          │   │
│  │  ┌──────────────────────────────────────────────────┐   │   │
│  │  │             INTERNAL API GATEWAY                  │   │   │
│  │  │  (All agent-to-agent comms go through this)      │   │   │
│  │  └──────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

---

## 5. Technology Stack

### 5.1 Core Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Runtime** | Python | 3.11+ | Orchestration engine, governance, CLI |
| **Web Framework** | FastAPI | 0.100+ | Internal API, agent communication |
| **Async Runtime** | asyncio + uvloop | stdlib | High-concurrency task management |
| **Database (Embedded)** | SQLite | 3.40+ | Local state, audit trail, session storage |
| **Database (Server)** | PostgreSQL | 15+ | Shared state (multi-instance deployments) |
| **Message Queue** | Redis / NATS | 7+ / 2.9+ | Event bus, agent task queues |
| **Container Runtime** | Docker | 24+ | Agent sandboxing, reproducible environments |
| **Version Control** | Git + GitHub | - | Source control, PR workflow |
| **CI/CD** | GitHub Actions | - | Automated testing, building, deployment |
| **Hosting** | Vercel / Cloudflare | - | Production deployment targets |

### 5.2 Agent-Specific Technologies

| Agent | Runtime | Primary Language | Toolchain |
|-------|---------|-----------------|-----------|
| Hermes Core | Python | Python 3.11 | FastAPI, Pydantic, Rich |
| Kimi | Cloud API | Multi | Moonshot API, filesystem tools |
| Codex | Cloud API | Multi | OpenAI API, shell access |
| Claude Code | Cloud API | Multi | Anthropic API, shell access |
| Gemini Code | Cloud API | Multi | Google AI API, shell access |
| Qwen Coder | Cloud API | Multi | Alibaba Cloud API |
| Cursor Agent | Local/Cloud | Multi | Cursor IDE integration |

### 5.3 Storage & Persistence

| Data Type | Storage Backend | Location | Retention |
|-----------|----------------|----------|-----------|
| Task Contracts | Git (Markdown) | `.hermes/contracts/` | Forever |
| Specifications | Git (Markdown) | `docs/specs/` | Forever |
| Design Documents | Git (Markdown) | `docs/designs/` | Forever |
| Evidence (Tests) | Git + CI Artifacts | `.hermes/evidence/` | 90 days (CI) / Forever (Git) |
| Code Reviews | Git (Markdown) | `.hermes/reviews/` | Forever |
| Security Scans | Git (Markdown) | `.hermes/security/` | Forever |
| Approval Records | Git (Markdown) + DB | `.hermes/approvals/` | Forever |
| Audit Trail | SQLite / Postgres | Local or shared DB | Forever |
| Agent Session Logs | Filesystem | `.hermes/logs/` | 30 days |
| Configuration | Git (YAML/TOML) | `.hermes/config/` | Forever |

---

## 6. Storage Layout

### 6.1 Repository Structure

```
project-root/
│
├── .hermes/                          # Hermes OS operational directory
│   ├── config/
│   │   ├── divisions.yaml            # Division definitions & policies
│   │   ├── agents.yaml               # Agent registry & capabilities
│   │   ├── gates.yaml                # Quality gate definitions
│   │   ├── permissions.yaml          # Authority & permissions matrix
│   │   └── routing.yaml              # Task routing rules
│   │
│   ├── contracts/                    # Immutable task contracts
│   │   ├── active/                   # Contracts in progress
│   │   └── archive/                  # Completed contracts
│   │
│   ├── evidence/                     # Test/validation evidence
│   │   ├── tests/                    # Test run outputs
│   │   ├── coverage/                 # Coverage reports
│   │   └── lint/                     # Lint results
│   │
│   ├── reviews/                      # Code review artifacts
│   │   └── PR-{id}/
│   │       ├── review.md             # Review report
│   │       └── checklist.json        # Gate checklist results
│   │
│   ├── security/                     # Security scan reports
│   │
│   ├── approvals/                    # Approval records (immutable)
│   │
│   ├── deployments/                  # Deployment logs
│   │
│   ├── regressions/                  # Post-deploy regression reports
│   │
│   ├── logs/                         # Agent session logs
│   │
│   └── state.db                      # SQLite state database (local only)
│
├── docs/                             # Human-readable documentation
│   ├── specs/                        # Generated specifications
│   └── designs/                      # Design documents
│
├── src/                              # Application source code
│   └── ...                           # (managed by coding agents)
│
├── tests/                            # Test suite
│   └── ...                           # (managed by coding agents)
│
└── .github/                          # GitHub Actions workflows
    └── workflows/
        ├── hermes-ci.yaml            # CI pipeline definition
        └── hermes-deploy.yaml        # Deployment pipeline
```

### 6.2 Database Schema (SQLite)

```sql
-- Core tables for Hermes OS state management

CREATE TABLE contracts (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL,           -- draft, planning, building, testing, reviewing, approved, rejected, merged, deployed
    title TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_agent TEXT,
    parent_contract_id TEXT,
    metadata JSON
);

CREATE TABLE artifacts (
    id TEXT PRIMARY KEY,
    contract_id TEXT NOT NULL,
    artifact_type TEXT NOT NULL,    -- spec, design, evidence, review, approval, deployment
    file_path TEXT NOT NULL,
    content_hash TEXT NOT NULL,     -- SHA-256 for immutability verification
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    producer_agent TEXT NOT NULL,
    FOREIGN KEY (contract_id) REFERENCES contracts(id)
);

CREATE TABLE approvals (
    id TEXT PRIMARY KEY,
    contract_id TEXT NOT NULL,
    gate_name TEXT NOT NULL,
    status TEXT NOT NULL,           -- pending, passed, failed
    reviewer_agent TEXT,
    evidence_artifact_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contract_id) REFERENCES contracts(id),
    FOREIGN KEY (evidence_artifact_id) REFERENCES artifacts(id)
);

CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    agent_id TEXT NOT NULL,
    action TEXT NOT NULL,           -- create, update, delete, approve, reject, deploy
    target_type TEXT,               -- contract, artifact, approval
    target_id TEXT,
    details JSON,
    previous_state JSON,            -- For state change tracking
    new_state JSON
);

CREATE TABLE agent_sessions (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    contract_id TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    status TEXT,                    -- active, completed, failed
    token_usage INTEGER,
    cost_cents INTEGER
);
```

---

## 7. Message Flow: The Development Lifecycle

### 7.1 Complete Message Sequence

The following sequence diagram traces a feature from inception to deployment:

```
Amjad          Hermes        Builder       Reviewer      CI/CD         GitHub
  │              │              │              │            │             │
  │  "Build X"   │              │              │            │             │
  │─────────────▶│              │              │            │             │
  │              │              │              │            │             │
  │              │  Parse intent, create contract                         │
  │              │──────────────│              │            │             │
  │              │              │              │            │             │
  │              │  Write specification (Hermes code boundary)            │
  │              │──────────────│              │            │             │
  │              │              │              │            │             │
  │              │  Dispatch build task ──────▶│            │             │
  │              │              │              │            │             │
  │              │              │  Clone repo, create branch              │
  │              │              │──────────────────────────────────────▶  │
  │              │              │              │            │             │
  │              │              │  Implement feature                      │
  │              │              │  Write tests                            │
  │              │              │  Run lint                               │
  │              │              │              │            │             │
  │              │              │  Commit & push ──────────────────────▶  │
  │              │              │              │            │             │
  │              │              │  Open PR ────────────────────────────▶  │
  │              │              │              │            │             │
  │              │  Receive PR event ◀─────────────────────────────────  │
  │              │              │              │            │             │
  │              │  Trigger CI ───────────────────────────▶│             │
  │              │              │              │            │             │
  │              │              │              │   Tests run              │
  │              │  CI results ◀───────────────────────────│             │
  │              │              │              │            │             │
  │              │  Dispatch review ───────────▶│           │             │
  │              │              │              │            │             │
  │              │              │              │  Analyze diff            │
  │              │              │              │  Check standards         │
  │              │              │              │  Run security scan       │
  │              │              │              │            │             │
  │              │  Review complete ◀──────────│            │             │
  │              │              │              │            │             │
  │              │  ┌── Corrections Gate ──┐  │            │             │
  │              │  │ If issues found:     │  │            │             │
  │              │  │  Notify Builder ─────▶│  │            │             │
  │              │  │  Builder fixes ──────▶│  │            │             │
  │              │  │  Re-review ──────────▶│  │            │             │
  │              │  └──────────────────────┘  │            │             │
  │              │              │              │            │             │
  │              │  All gates passed           │            │             │
  │              │  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│            │             │
  │              │              │              │            │             │
  │              │  Execute merge ────────────────────────────────────▶  │
  │              │              │              │            │             │
  │              │  Merge confirmed ◀─────────────────────────────────  │
  │              │              │              │            │             │
  │              │  Trigger deploy ───────────────────────▶│             │
  │              │              │              │            │             │
  │              │              │              │   Deploy to production   │
  │              │  Deploy complete ◀──────────────────────│             │
  │              │              │              │            │             │
  │              │  Start monitoring (regression detection)               │
  │              │              │              │            │             │
  │  Done! ◀─────│              │              │            │             │
  │              │              │              │            │             │
```

### 7.2 Gate Definitions

| Gate | Order | Required | Description |
|------|-------|----------|-------------|
| **Specification Gate** | 1 | Yes | Task contract must have a complete, reviewed specification |
| **Build Gate** | 2 | Yes | Code must compile/build successfully |
| **Test Gate** | 3 | Yes | All tests must pass; coverage must meet threshold |
| **Lint Gate** | 4 | Yes | Code must pass linting with zero errors |
| **Review Gate** | 5 | Yes | At least one reviewer agent must approve |
| **Security Gate** | 6 | Yes | Security scan must return zero critical/high findings |
| **Performance Gate** | 7 | Conditional | Required for performance-sensitive changes |
| **Approval Gate** | 8 | Yes | Hermes must issue final approval (orchestrator sign-off) |
| **Merge Gate** | 9 | Yes | All prior gates must pass before merge is allowed |

### 7.3 Contract Lifecycle Events

```
Event                Producer          Consumer           Action
─────────────────────────────────────────────────────────────────────
contract.created      Hermes Core       All                Initialize tracking
contract.assigned     Hermes Core       Builder Agent      Start implementation
contract.built        Builder Agent     Hermes Core        Trigger CI
contract.tested       CI/CD             Hermes Core        Evaluate gate
contract.reviewed     Reviewer Agent    Hermes Core        Evaluate gate
contract.corrected    Builder Agent     Reviewer Agent     Re-review cycle
contract.approved     Hermes Core       CI/CD              Allow merge
contract.rejected     Hermes Core       Builder Agent      Return for fixes
contract.merged       Hermes Core       CI/CD              Trigger deploy
contract.deployed     CI/CD             Hermes Core        Start monitoring
contract.regressed    Monitoring Agent  Hermes Core        Create new contract
```

---

## 8. Network Topology & Security Boundaries

### 8.1 Trust Zones

```
┌────────────────────────────────────────────────────────────────────┐
│  ZONE 0: HUMAN OPERATOR                                             │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Amjad's workstation                                          │  │
│  │  - Full authority (Level 8)                                   │  │
│  │  - Emergency override capability                              │  │
│  │  - Manual merge/deploy access                                 │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│  ZONE 1: HERMES CORE     │    │  ZONE 2: EXTERNAL APIs   │
│  ┌────────────────────┐  │    │  ┌────────────────────┐  │
│  │  Hermes Runtime     │  │    │  │  GitHub API        │  │
│  │  - Orchestration    │  │    │  │  Vercel API        │  │
│  │  - Governance       │  │    │  │  Cloudflare API    │  │
│  │  - State Management │  │    │  │  Agent APIs        │  │
│  │  - Audit Logging    │  │    │  │  (Kimi, Codex,     │  │
│  └────────────────────┘  │    │  │   Claude, Gemini)   │  │
│                          │    │  └────────────────────┘  │
│  Hermes-only access:     │    │                          │
│  - Write to .hermes/     │    │  Authenticated via:      │
│  - Merge to main         │    │  - API keys              │
│  - Trigger deploy        │    │  - OAuth tokens           │
│  - Modify config         │    │  - SSH keys              │
└──────────────────────────┘    └──────────────────────────┘
              │                               │
              ▼                               ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│  ZONE 3: AGENT RUNTIME   │    │  ZONE 4: CI/CD            │
│  ┌────────────────────┐  │    │  ┌────────────────────┐  │
│  │  Agent Sandboxes    │  │    │  │  GitHub Actions    │  │
│  │  - Isolated env     │  │    │  │  Test Runners      │  │
│  │  - Limited fs access │  │    │  │  Build Pipelines   │  │
│  │  - No network egress│  │    │  │  Deploy Scripts    │  │
│  │   (except API calls)│  │    │  └────────────────────┘  │
│  └────────────────────┘  │    │                          │
└──────────────────────────┘    └──────────────────────────┘
```

### 8.2 Network Communication Rules

| Source | Destination | Protocol | Authentication | Allowed |
|--------|-------------|----------|----------------|---------|
| Amjad | Hermes Core | HTTPS / CLI | User session | Yes |
| Hermes Core | Agent APIs | HTTPS | API keys | Yes |
| Hermes Core | GitHub API | HTTPS | OAuth / PAT | Yes |
| Hermes Core | CI/CD | Webhook / API | Shared secret | Yes |
| Hermes Core | Deployment Targets | HTTPS | API tokens | Yes |
| Agent Runtime | External (arbitrary) | Any | N/A | **No** (blocked) |
| Agent A | Agent B (direct) | Any | N/A | **No** (must route via Hermes) |
| CI/CD | GitHub | HTTPS | GITHUB_TOKEN | Yes |
| CI/CD | Deployment Targets | HTTPS | Deploy tokens | Yes |

---

## 9. Scaling & Resilience Design

### 9.1 Scaling Model

| Component | Scaling Strategy | Failure Mode |
|-----------|-----------------|--------------|
| Hermes Core | Single instance (by design — orchestrator) | Fail-stop: human operator notified immediately |
| Agent Fleet | Stateless, horizontally scalable (N concurrent agents) | Individual agent failure → task reassignment |
| CI/CD | GitHub-managed, auto-scaling | Queue delay on heavy load |
| Database (SQLite) | Single-writer by design | WAL mode for concurrent reads |
| Database (Postgres) | Connection pooling, read replicas | Automatic failover |

### 9.2 Resilience Patterns

1. **Idempotent Contracts**: Task contracts are idempotent — replaying a contract produces the same result
2. **Immutable Evidence**: All artifacts are content-addressed (SHA-256); tampering is detectable
3. **Graceful Degradation**: If a specialty agent (e.g., Security Scanner) is unavailable, the gate is blocked (fail-closed), not bypassed
4. **Retry with Backoff**: Agent API calls use exponential backoff with jitter
5. **Circuit Breaker**: After N consecutive failures from an agent, that agent is marked unhealthy and excluded from routing

### 9.3 Emergency Override

The human operator (Amjad) retains an **emergency override** capability that can:
- Bypass any gate
- Force-merge any PR
- Reassign or kill any contract
- Modify any configuration

All emergency overrides are **logged immutably** with a mandatory reason field. Emergency overrides are not routable through agents — they require direct human action.

---

## 10. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 3.0.0 | 2026-06-01 | Hermes OS Team | Initial v3 architecture |
| 3.1.0 | 2026-07-31 | Hermes OS Team | Added 19-agent fleet, 6-division model, gate enforcement, permissions matrix |

---

**Next Document:** [02_ORGANIZATIONAL_MODEL.md](./02_ORGANIZATIONAL_MODEL.md) — Division structure, role definitions, and responsibility matrix.