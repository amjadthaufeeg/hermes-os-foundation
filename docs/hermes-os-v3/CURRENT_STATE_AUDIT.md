# Hermes Engineering OS v3 — Current State Audit

**Audit Date:** 31 July 2026
**Auditor:** Hermes (read-only discovery)
**Target:** Hermes Engineering OS v3 (stored at `03_Engineering_OS/HERMES_ENGINEERING_OS_V3.md`)
**Status: COMPLETE** (partial — see Section J for unverified items)

---

## A. Executive Summary

### Current Maturity

The Hermes system is at **Maturity Level 2.5 out of 5** relative to the v3 target:

- **Level 2 (Prompt-Governed):** Agent roles, routing rules, and workflow constraints are documented in `AGENTS.md` and enforced only through system prompts. There is no automated enforcement of scope, protected zones, or change budgets.
- **Level 3 (Partially Automated):** Task plans exist as markdown documents with scope definitions. Tests exist (78 collected in avoa-connect backend). Hermes has memory, delegation, and session search.

### Strongest Existing Capabilities

1. **Clear governance documentation:** `AGENTS.md` v4.0 (20K+ chars) defines agent roles, workflow states, compliance checklists, and builder routing rules with high precision.
2. **Hermes Agent platform:** Fully configured with OpenRouter (DeepSeek v4 Pro), delegation, cron, memory, session search, and 80+ skills. The underlying agent infrastructure is production-capable.
3. **Founder Decision Register:** 14 decisions recorded and binding. Clear product authority chain.
4. **Comprehensive test suite:** 78 backend tests covering pricing, fixtures, API, models, parity, and cross-engine validation.
5. **OpenCode integration:** Kimi K3 and Claude Opus/Sonnet models available via OpenRouter through OpenCode CLI.

### Most Serious Risks

| # | Risk | Severity | Impact |
|---|---|---|---|
| 1 | Claude Code CLI installed but **not authenticated** — review workflow is non-functional via native Claude Code. Workaround exists via OpenCode but is not the v3 target path. | **HIGH** | Cannot perform independent structured reviews |
| 2 | **No CI/CD pipelines** configured for avoa-connect — no automated build, test, lint, or gate enforcement on push/PR | **HIGH** | All quality gates are manual; no enforcement |
| 3 | **No protected branches** on GitHub — any agent with push access can merge to master | **CRITICAL** | No merge protection; single-point-of-failure |
| 4 | Test suite has **collection error** — 1 test missing fixture file (`kvm_me_packages.json`). Clean pass/fail status unknown. | **MEDIUM** | Test reliability unverified |
| 5 | All scope/protected-zone enforcement is **prompt-based only** — an agent that ignores its instructions has no technical barrier | **HIGH** | v3 requires script/CI enforcement |
| 6 | Hermes writes implementation code directly in current workflow — contradicts v3 orchestrator-only rule | **HIGH** | Hermes authored AGENTS.md, plan files, repair tasks, and configuration directly |

### Migration Feasibility

**Migration can be incremental.** The existing Hermes Agent infrastructure (delegation, memory, cron, skills) provides a strong foundation. The primary gap is moving from prompt-governed to evidence-enforced governance — implementing schemas, automated gates, and structured records. No broad rewrites are needed.

### Immediate Precautions

1. **Do not** deploy to production without protected branches and CI.
2. **Do not** rely on Claude Code CLI for reviews until authenticated.
3. **Do not** assume test suite passes until collection error is fixed.
4. **Do not** implement Mission Control UI before backend records exist.

---

## B. Verified Current Architecture

```
                         AMJAD
              Product Owner (via Hermes chat)
                           │
                           ▼
                        HERMES
         DeepSeek v4 Pro via OpenRouter
         Memory, delegation, cron, session search
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
    AGENTS.md v4.0    Skills (80+)    Memory (persistent)
    (prompt-enforced   (procedural     (project context,
     governance)        knowledge)      decisions)
         │
         ├──────────┬──────────┬──────────┐
         ▼          ▼          ▼          ▼
      OpenCode   Claude CLI  Codex CLI  delegate_task
      (Kimi K3   (v2.1.207,  (v0.144.3, (subagents,
       primary    NOT AUTH)   unknown     DeepSeek)
       builder)              auth)
         │
         ▼
    GitHub.com/amjadthaufeeg/avoa-connect
    Single branch (master) — no protection rules
    No CI/CD workflows configured
```

### Verified Flow (Current, Not Target)

```
User request (Hermes chat)
→ Hermes interprets request
→ Hermes writes plan document (docs/tasks/TASK-XXXX.md)
→ Hermes dispatches implementation via OpenCode/delegate_task
   (NOTE: Hermes also writes code directly — violates v3 orchestrator-only rule)
→ Tests run manually (backend/.venv/bin/python -m pytest)
→ Claude review attempted via OpenCode with Claude models
   (NOTE: Not using native Claude Code CLI; not following structured findings format)
→ Hermes reports results to Amjad
→ Amjad approves → Hermes commits to master
   (NOTE: No pull request; no merge gate; no CI)
```

**Key differences from v3 target:**
- No structured task contract YAML
- No risk classification step
- No change budgets
- No automated gates
- No protected zone enforcement (prompt-only)
- Hermes writes code (should not)
- Direct master commits (no PR, no CI)
- No structured review findings
- No decision register (DEC-XXX-NNN format)
- No regression register (template only)
- No builder scorecards
- No rollback packages
- No Mission Control

---

## C. Current-vs-Target Matrix

| # | Capability | Target (v3) | Current State | Status | Evidence | Risk | Action |
|---|---|---|---|---|---|---|---|
| 1 | Sole orchestrator (Hermes) | Hermes routes, approves, never writes code | Hermes routes AND writes code directly | **Partial** | AGENTS.md §0.3 prohibits Hermes code authorship; but Hermes writes AGENTS.md, plans, configs, repairs | HIGH | Enforce programmatically |
| 2 | Structured task contracts (YAML) | YAML with task_id, risk_level, allowed_files, change_budget, etc. | Markdown plan documents with informal scope | **Document-only** | 9 plan files in docs/tasks/; no YAML contracts | MEDIUM | Implement contract schema |
| 3 | 4-tier risk classification (R1-R4) | R1=Low, R2=Moderate, R3=High, R4=Critical | R0-R5 model in v1.0 RISK_CLASSIFICATION.md | **Partial** | v1.0 has 6 tiers; v3 wants 4. Used informally in plans. | LOW | Map and migrate |
| 4 | 18-state task lifecycle | REQUESTED→…→CLOSED + failure states | 13-state model documented; actual flow is 5-7 states | **Document-only** | AGENTS.md §0.5 defines 10 steps; TASK_LIFECYCLE.md defines 13 states; no state machine implementation | MEDIUM | Implement state machine |
| 5 | Protected zones | Folders/files marked protected; CI enforces | Prompt-based only; AGENTS.md §0.3 lists protected areas | **Document-only** | No script or CI enforcement | HIGH | Implement zone checks |
| 6 | Change budgets | max_files, max_lines, max_folders enforced | Not implemented | **Missing** | No budget tracking in any plan file | MEDIUM | Add to contract schema |
| 7 | Automated gates | Build, lint, typecheck, tests, fixtures, scope check | Tests exist (78 collected, 1 error); no CI; no automated gates | **Partial** | 17 test files in backend/tests; no CI config; test collection error | HIGH | Add CI, fix tests, add gates |
| 8 | AVOA-specific fixtures | Pricing, occupancy, offer, tax, commission, cancellation fixtures | Pricing fixtures exist (test_pricing_v4_fixtures.py, test_package_fixtures.py); others unknown | **Partial** | 2 fixture test files verified; others not verified | MEDIUM | Audit fixture coverage |
| 9 | Structured review protocol | YAML findings with BLOCKER/HIGH/MEDIUM/LOW/OPTIONAL | Claude review via OpenCode; findings not structured; no Hermes adjudication record | **Partial** | CLAUDE_REVIEW_SETUP.md documents process; no structured findings observed | HIGH | Implement findings schema |
| 10 | Decision register | DEC-XXX-NNN format with status, owner, applies_to | Founder Decision Register exists (14 decisions, table format); v1.0 DECISION_LEDGER_TEMPLATE exists | **Partial** | FOUNDER_DECISION_REGISTER.md; DECISION_LEDGER_TEMPLATE.md | LOW | Align format with v3 |
| 11 | Regression register | REG-XXX-NNN with symptoms, root_cause, fix, protection | Template only (REGRESSION_REGISTER.md); no actual records | **Missing** | REGRESSION_REGISTER.md is 16-line template | HIGH | Populate from known defects |
| 12 | Builder scorecards | Track per-builder: pass rate, scope violations, cost, corrections | Template only (BUILDER_SCORECARD_TEMPLATE.md); no data collected | **Missing** | Template exists; no populated scorecards | MEDIUM | Start collecting on next task |
| 13 | Rollback packages | Per-task: baseline commit, migration status, rollback steps | Protocol documented (ROLLBACK_PROTOCOL.md); not produced per-task | **Document-only** | No rollback packages found in task directories | MEDIUM | Add to task closure |
| 14 | Mission Control Dashboard | Evidence-backed dashboard with task states, reviews, deployments | Skill exists (mission-control-dashboard); no implementation | **Missing** | Skill installed but not built | LOW | Implement after v3 backend |
| 15 | Two-memory model | Product memory (durable) vs Task memory (temporary) | Hermes memory exists (memory tool) but undifferentiated | **Partial** | Memory has project context and decisions; no task/cleanup lifecycle | LOW | Differentiate with schemas |
| 16 | Evidence-based completion | Checklist: build, tests, fixtures, review, rollback before READY_FOR_AMJAD | AGENTS.md §0.7 defines evidence checklist; manually checked, not automated | **Document-only** | Compliance checklist exists; no automated verification | MEDIUM | Automate evidence collection |
| 17 | Feature flags | Feature flags for high-risk deployment | Policy exists (FEATURE_FLAG_POLICY.md); no implementation | **Missing** | Policy document only | LOW | Implement as needed |
| 18 | Kimi K3 primary builder | Kimi K3 handles new features, vertical slices, multi-file work | Kimi K3 configured in OpenCode; used as primary builder | **Implemented** | moonshotai/kimi-k3 via OpenRouter; verified in opencode.json | — | Maintain |
| 19 | Claude Code reviewer | Independent reviewer, read-only first pass, structured findings | Claude Code CLI installed but NOT authenticated; review via OpenCode workaround | **Partial** | claude v2.1.207; `claude auth status` returns "Not logged in" | HIGH | Authenticate or formalize OpenCode path |
| 20 | Codex fallback builder | Precision builder for narrow fixes, failed Kimi tasks | Codex CLI installed (v0.144.3); auth status unknown; never used in observed workflow | **Unknown** | `codex` binary exists; no `codex auth status` command | MEDIUM | Verify auth and readiness |

---

## D. Agent-Permission Matrix

| Agent | Install Status | Auth Status | Write Access | Read Access | Runtime Notes |
|---|---|---|---|---|---|
| **Hermes** | Running (DeepSeek v4 Pro via OpenRouter) | ✅ Authenticated | Full filesystem + git + memory + delegation | All tools enabled | Currently writes code directly despite AGENTS.md prohibiting it |
| **Kimi K3** | Configured in OpenCode (moonshotai/kimi-k3 via OpenRouter) | ✅ Via OpenRouter | Via OpenCode CLI | Via OpenCode CLI | Primary builder; dispatched via `opencode` or `delegate_task` |
| **Claude Code** | Installed v2.1.207 at `~/.local/bin/claude` | ❌ **NOT AUTHENTICATED** | N/A (cannot use) | N/A (cannot use) | `claude auth status` = "Not logged in". Workaround: Claude models via OpenCode/OpenRouter |
| **Codex** | Installed v0.144.3 at `~/.local/bin/codex` | ❓ **UNKNOWN** | Unknown | Unknown | No `auth status` command available; never observed in use |
| **OpenCode** | Installed v1.17.19 | ✅ Via OpenRouter | Via CLI with model selection | Via CLI | Configured with Kimi K3 + Claude Opus/Sonnet in `~/.config/opencode/opencode.json` |
| **GitHub** | Repository access via HTTPS | ❌ `gh` not authenticated | Git push via credential helper | Git pull/fetch | No `gh` CLI auth; git uses credential helper; no protected branches |
| **Replit** | Referenced in docs | ❓ **UNKNOWN** | Unknown | Unknown | Mentioned as preview environment; no verified connection |
| **CI/CD** | N/A | N/A | N/A | N/A | **No CI/CD configured** — no `.github/workflows/` in avoa-connect |

---

## E. Safety-Gap Register

| Gap ID | Description | Affected Area | Severity | Likelihood | Impact | Immediate Mitigation | Long-term Correction |
|---|---|---|---|---|---|---|---|
| GAP-001 | No protected branches on GitHub | Repository safety | **CRITICAL** | High | Any agent can directly push/merge to master | Add branch protection rules manually | Implement v3 automated merge gates |
| GAP-002 | No CI/CD pipelines | Quality assurance | **HIGH** | Certain | No automated test/lint/build enforcement | Add minimal CI (pytest + ruff) | Full v3 gate pipeline |
| GAP-003 | Claude Code not authenticated | Review workflow | **HIGH** | Certain | Cannot perform independent structured reviews | Use OpenCode+Claude models as interim | Authenticate Claude Code or formalize alternative |
| GAP-004 | Hermes writes implementation code | Orchestrator integrity | **HIGH** | Frequent | Violates v3 orchestrator-only rule; no independent implementation review | Enforce via SOUL.md instruction | Programmatic enforcement in task dispatch |
| GAP-005 | No protected-zone enforcement | Commercial safety | **HIGH** | Medium | Builder could modify pricing/occupancy/offers without detection | Add git-diff scope check script | CI-enforced protected zone checks |
| GAP-006 | Test suite has collection error | Quality assurance | **MEDIUM** | Certain | 1 test cannot run; overall reliability unknown | Fix missing fixture file | CI-enforced test gate |
| GAP-007 | Direct master commits | Release safety | **HIGH** | Frequent | No review gate before production code | Require PR for all changes | v3 merge approval workflow |
| GAP-008 | No regression records | Defect management | **MEDIUM** | Certain | Repeated bugs not prevented | Populate register from known fixes | Automated regression detection |
| GAP-009 | No builder scorecards | Agent routing | **LOW** | Certain | Suboptimal builder selection continues | Start tracking on next 3 tasks | Evidence-based routing |
| GAP-010 | No rollback packages | Deployment safety | **MEDIUM** | Medium | Recovery from bad deploy is manual and slow | Document baseline before each deploy | Automated rollback package generation |

---

## F. Reusable Components

The following should be **preserved and reused** during v3 migration:

| Component | Location | Why Reusable |
|---|---|---|
| Hermes Agent platform | `~/.hermes/` (config, skills, memory) | Full delegation, cron, memory, session search, MCP servers already working |
| AGENTS.md v4.0 | `~/projects/avoa-connect/AGENTS.md` | Comprehensive governance document; can be source material for v3 schemas |
| OpenCode + OpenRouter config | `~/.config/opencode/opencode.json` | Kimi K3 and Claude models verified working; keep as builder/reviewer transport |
| Founder Decision Register | `docs/product/FOUNDER_DECISION_REGISTER.md` | 14 binding decisions; migrate to v3 DEC-XXX-NNN format |
| Backend test suite | `backend/tests/` (17 files, 78 tests) | Strong fixture coverage; fix collection error to integrate into v3 gates |
| Pricing fixtures | `test_pricing_v4_fixtures.py`, `test_package_fixtures.py` | Directly reusable for v3 AVOA-specific gates |
| Hermes OS v1.0 Foundation Pack | `~/projects/hermes-os-foundation/` | Modular governance docs; v3 replaces DEVELOPMENT_OPERATING_MODEL, augments others |
| Task plan documents | `docs/tasks/TASK-UI-RESET-*.md` (7 plans) | Reference material for v3 task contract migration |
| Convex MCP server | Connected via MCP | Database inspection capability; reusable for Mission Control data |
| Scrape Creators MCP | Connected via MCP | Social media data; reusable |
| Parallel Search MCP | Connected via MCP | Web search; reusable |
| Cron jobs (4 active) | Spend Audit, Security Audit, Release Watcher, Cost Breakdown | Stable automation; preserve during migration |

---

## G. Migration Constraints

### Dependencies
- Migration requires `gh` CLI authentication for branch protection and CI setup.
- Claude Code authentication needed for native review path (or decision to formalize OpenCode alternative).
- Test suite must be fixed (missing fixture file) before CI gates work.

### Operational Risks
- Current workflow has no safety nets — migration should add gates before removing any existing practice.
- Hermes currently writes code directly; stopping this requires an alternative builder path that is verified working.

### Compatibility Concerns
- v1.0 R0-R5 risk model is used in AGENTS.md and plans; v3 R1-R4 requires mapping.
- Task state machine change (13→18 states) should not break in-flight tasks.

### Areas Where Broad Rewrites Must Be Avoided
- The AVOA quote engine backend code — this is the product. Migration touches governance, not product logic.
- Existing test files — preserve and add to them, don't replace.
- Active cron jobs — migration should not interrupt them.

---

## H. Decisions Required from Amjad

Only decisions that cannot be resolved from existing context:

1. **Claude Code authentication:** Claude Code CLI requires direct Anthropic API key or OAuth. Currently we use OpenRouter for all LLM access. Should we:
   - (a) Get an Anthropic API key and authenticate Claude Code natively?
   - (b) Formalize the OpenCode+Claude-via-OpenRouter path as the official review method and update v3 docs accordingly?

2. **Hermes code authorship boundary:** The current workflow has Hermes writing AGENTS.md, plan files, configuration, and direct repairs. v3 says "Hermes must not write production code." Should:
   - (a) Hermes be allowed to write governance docs, plans, and config (but not product code)?
   - (b) All Hermes writing be delegated — even plan documents go through Kimi K3?

3. **GitHub CI setup:** Setting up GitHub Actions requires initial workflow configuration. Should Hermes:
   - (a) Set up CI/CD workflows now (as part of v3 migration)?
   - (b) Wait until after the audit is fully approved?

4. **Branch protection:** Adding protected branch rules to `master` on `avoa-connect` would immediately change the current workflow (all changes would need PRs). Should this be:
   - (a) Implemented now as a safety measure?
   - (b) Deferred until CI gates are operational?

5. **Replit integration status:** Is Replit currently connected and functional for AVOA previews, or is it aspirational?

---

## I. Recommended Next Step

**Smallest safe implementation package:** Implement v3 items 4-6 from Section 17 of the target model:

```
Package P0 — Governance Foundation (est. 1-2 sessions):
  1. Define task contract YAML schema
  2. Implement risk classification (R1-R4 mapping)
  3. Implement state machine definitions
  4. Create decision register (DEC-XXX-NNN) with 2 locked decisions
  5. Create first regression record from recent defect

Package P1 — Safety Gates (est. 2-3 sessions):
  6. Set up GitHub branch protection on master
  7. Add minimal CI workflow (pytest, ruff)
  8. Fix test collection error
  9. Implement protected-zone diff check script

Package P2 — Review Path (est. 1 session):
  10. Resolve Claude Code auth OR formalize OpenCode path
  11. Implement structured findings schema
  12. Implement Hermes findings adjudication record
```

**Do NOT start Mission Control UI until P0-P2 are complete.**

---

## J. Unverified / Incomplete Items

The following could not be fully verified during this audit:

| Item | Reason | Impact |
|---|---|---|
| Replit integration status | No connection or configuration found | Low — not critical to v3 foundation |
| Codex authentication status | No `codex auth status` command available | Medium — fallback builder readiness unknown |
| Test suite pass/fail rate | Collection error prevented full run | High — need to fix and re-run |
| Frontend test coverage | Only backend tests inspected | Low — frontend is UI prototype stage |
| Convex deployment state | MCP connected but deployment selector not probed | Low |
| Production deployment status | No deployment config found | Low — AVOA appears pre-production |
| Telegram gateway operational status | Config shows Telegram configured but gateway state not verified | Low |

---

*Audit completed 31 July 2026. Next: Amjad review of decisions in Section H.*

---

# Hermes OS v3.1 Impact Addendum

**Date:** 31 July 2026
**Status:** Appended to v3 audit per Amjad direction
**Target:** Hermes Engineering OS v3.1

## Addendum A — Decisions from Audit Resolved

### DECISION A — Claude Code Authentication

**Resolved:** Preferred target is native Claude Code access. Temporary fallback is OpenCode using Claude models via OpenRouter.

**Current state:** Claude Code CLI v2.1.207 installed but NOT authenticated (`claude auth status` returns "Not logged in"). OpenCode workaround documented in `CLAUDE_REVIEW_SETUP.md`.

**Documentation needed in implementation package:**
- Authentication method (Anthropic API key required)
- Permissions (read-only review mode)
- Review invocation command
- Evidence retained (structured findings)
- Fallback limitations (no interactive TUI, no `/review` command, no hooks)
- Transition path to native Claude Code

### DECISION B — Hermes Code Boundary

**Resolved:** Hermes may write documentation, plans, task contracts, policies, schemas, templates, decision records, regression records, orchestration config, and audit records. Hermes should delegate production application feature code to Kimi K3 or Codex.

**Current state:** Hermes currently writes code for AGENTS.md, plan files, and has authored repairs. This aligns with the approved boundary.

**Clarification:** Small orchestration-layer configuration changes (e.g., CI config, branch protection setup) are permitted when Hermes itself is the system being implemented, provided explicitly authorized and reviewed.

### DECISION C — CI Timing

**Resolved:** Minimum CI is part of the first foundation release. Not deferred.

**First CI package target:** Build, type check, lint, existing tests, changed-file reporting, protected-zone check proof-of-concept.

### DECISION D — Branch Protection

**Resolved:** Implement after CI checks are validated. Interim no-direct-push rule applies.

**Current state:** `master` has no protection rules. Repository is `amjadthaufeeg/avoa-connect`. Branch: `master` (not `main`). One stale feature branch (`feature/TASK-0001-login-visual-polish`).

**Implementation sequence:** 1) Create CI checks, 2) Enable branch protection, 3) Confirm rollback procedure, 4) Test with pilot branch.

### DECISION E — Replit

**Resolved:** Optional preview capability. Not a prerequisite for v3.1 foundation.

**Current state:** 
- `avoa-quote-engine/` has `.replit` config file — Replit was used for initial prototyping
- `REPLIT_PROTOTYPE_WORKFLOW_LOCK.md` (454 lines) is the authoritative workflow reference extracted from the Replit prototype ZIP
- Current Replit connection status: **UNVERIFIED** — no live Replit deployment confirmed
- Prototype was captured as a ZIP, not a running Replit

**v3.1 verification needed:**
- Is Replit currently connected? → UNKNOWN
- Which repository does it use? → UNKNOWN (likely avoa-quote-engine)
- Does it track the correct branch? → UNKNOWN
- Are previews automatic? → UNKNOWN
- Does runtime config match AVOA? → UNKNOWN
- Are secrets handled safely? → UNKNOWN

**Recommendation:** If Replit is unsuitable, use GitHub-connected staging or PR-preview (e.g., Vercel, Railway, or GitHub Pages for static previews).

---

## Addendum B — Design Studio Assessment

### Design System Maturity: EARLY STAGE

**What exists:**
- `tailwind.config.ts` with color tokens: navy, teal, gold, coral, cream palettes with 50-900 scales
- 3 approved design HTML prototypes in `docs/design/approved/`: `cockpit.html` (44KB), `request-form.html` (12KB), `inbox.html` (7KB)
- Replit prototype workflow lock (454 lines) defining 15+ screens and routes
- Basic component library: `AvailabilityBadge`, `Navbar`, `OccupancyGate`, `OfferBuilder`

**What is missing:**
- No formal design system documentation (color tokens exist in Tailwind config but no usage guide)
- No typography scale documented
- No spacing/grid system documented
- No component library documentation
- No icon system
- No motion/interaction guidelines
- No accessibility guidelines or checks
- No visual regression testing
- No Figma or design-tool integration
- No responsive breakpoint documentation (though Tailwind defaults apply)

### UI Consistency: PARTIAL

**Evidence:**
- 3 approved HTML prototypes serve as design reference
- AGENTS.md §2 enforces a "Design Freeze" rule requiring approved reference comparison before frontend changes
- 4 React components exist but no systematic component library
- Frontend routes: `/cockpit`, `/inbox`, `/login`, `/quote`, `/request` — in various stages of implementation

### UX Governance: DOCUMENT-ONLY

**Evidence:**
- AGENTS.md §2-3 define design freeze and mobile-first requirements
- No UX review workflow beyond Amjad visual approval
- No structured UX contracts (v3.1 introduces UI contract requirement)
- No accessibility review process

### Visual Review Workflow: MANUAL

**Evidence:**
- Current flow: Build → Amjad reviews visually → approve
- No screenshot automation
- No visual regression detection
- No multi-breakpoint screenshot evidence in task records

### Screenshot Capability: TOOL AVAILABLE, NOT USED FOR EVIDENCE

Hermes has `vision_analyze` and `macos-computer-use` skills. Screenshots can be captured but are not systematically collected as task evidence.

### Accessibility: NONE

No accessibility testing tools, no axe-core integration, no WCAG checks, no screen-reader testing found.

---

## Addendum C — Parallel Execution Readiness

### Sub-Agent Support: INFRASTRUCTURE EXISTS, NOT CONFIGURED FOR V3.1 ROLES

**What exists:**
- `delegate_task` tool — functional, used in current workflow
- 8 Hermes profiles: `avoa`, `dev`, `orchestrator`, `reach`, `reefxlab`, `scout`, `scribe`
- Profiles for proposed v3.1 roles (`scout`, `scribe`, `orchestrator`) exist but are NOT active
- `--worktree/-w` flag supported for isolated git worktrees
- Kanban system available but not initialized

**Gaps:**
- No profile configured as Codebase Scout (read-only)
- No profile configured as Test/Fixture Agent
- No profile configured as Documentation Agent
- No profile configured as Visual QA Agent
- No worktree isolation enforced in current workflow
- Kanban board not initialized — no task dispatch automation

### Worktree Support: AVAILABLE BUT UNUSED

Hermes Agent supports `--worktree/-w` flag for isolated parallel work. Current worktree list shows only the master checkout. No parallel worktree has been tested.

### File-Ownership Enforcement: NONE

No mechanism exists to prevent two agents from editing the same file. Current enforcement is procedural only (single-writer rule in AGENTS.md §0.2).

### Collision Detection: NONE

No automated detection of overlapping file changes across parallel worktrees or branches.

### Parallel Task Support: NOT READY

Current workflow is strictly serial: one task at a time, one builder at a time. Parallel execution would require kanban initialization, profile configuration, worktree isolation, and collision detection — none of which exist.

---

## Addendum D — CI and Branch Protection Readiness

### CI Readiness: NOT READY

**Repository:** `amjadthaufeeg/avoa-connect`
**Branch to protect:** `master`
**Current state:** No `.github/workflows/` directory. No CI configuration of any kind.

**Blockers:**
1. Test suite has collection error (`kvm_me_packages.json` missing)
2. No `gh` CLI authentication
3. No CI workflow files exist
4. Python version mismatch (system 3.9 vs backend venv 3.11) — CI must use correct Python

**What needs to happen before CI:**
1. Fix test collection error
2. Authenticate `gh` CLI (or use GITHUB_TOKEN from .env)
3. Create `.github/workflows/ci.yml` with pytest + ruff
4. Verify workflow runs on push/PR
5. Document check names for branch protection rules

### Branch Protection Readiness: NOT READY

**Prerequisites not met:**
- No CI checks to require
- No verified check names
- `gh` CLI not authenticated
- Emergency access procedure not defined

---

## Addendum E — Command Center Data Availability

### Data Sources That Exist and Could Power Command Center:

| Data Source | Location | Status |
|---|---|---|
| Task plans | `docs/tasks/` (9 files) | Manual markdown; no structured schema |
| Task state | Git commits + plan files | Informal; no state machine |
| Agent runs | Session history (`state.db`) | Exists but not tagged by task |
| Changed files | Git diffs | Available but not aggregated |
| Test results | `backend/tests/` | Manual runs only; no history |
| Review findings | Conversation history | Not structured; no persistence |
| Founder decisions | `FOUNDER_DECISION_REGISTER.md` | 14 decisions in table format |
| Deployments | N/A | No production deployments |
| Rollback packages | N/A | None created |
| Builder performance | N/A | No scorecards populated |

### Data Sources That Do NOT Exist:

| Data Source | Status |
|---|---|
| Structured task state history | Missing |
| Automated gate results | Missing |
| Structured review findings database | Missing |
| Builder scorecard data | Missing |
| Regression records | Missing (template only) |
| Deployment history | Missing |
| Cost tracking per task | Missing (Hermes tracks total usage only) |

---

## Addendum F — New v3.1 Capability Gaps

| # | Capability | v3.1 Target | Current State | Status | Risk |
|---|---|---|---|---|---|
| C1 | Design Studio | UX, visual, interaction, accessibility ownership | No formal design function; Amjad does visual review | Missing | MEDIUM |
| C2 | UI Contracts | YAML UI contract per visual task | Not implemented | Missing | MEDIUM |
| C3 | Design System Documentation | Color, typography, spacing, grid, components | Tailwind config colors only | Missing | MEDIUM |
| C4 | Parallel Execution Controller | Sub-agent dispatch with safeguards | Kanban available; no profiles active | Missing | LOW |
| C5 | Codebase Scout | Read-only codebase analysis agent | `scout` profile exists; not configured | Partial | LOW |
| C6 | Documentation Agent | Documentation-only writing agent | `scribe` profile exists; not configured | Partial | LOW |
| C7 | Visual QA Agent | Screenshot capture and comparison | `vision_analyze` tool exists; no automation | Partial | MEDIUM |
| C8 | Screenshot Evidence | Desktop/tablet/mobile per task | Tool available; never used for tasks | Missing | MEDIUM |
| C9 | Accessibility Validation | WCAG checks, screen-reader testing | None | Missing | LOW |
| C10 | Worktree Isolation | Isolated worktrees per parallel sub-agent | Supported; never tested with multiple agents | Partial | MEDIUM |
| C11 | Collision Detection | Detect overlapping file changes | None | Missing | MEDIUM |
| C12 | Hermes Command Center | Evidence-backed operational dashboard | No implementation; no backend data | Missing | LOW |
| C13 | Replit Connection Verified | Confirm or replace preview environment | Unverified | Unknown | LOW |

---

## Addendum G — Updated Implementation Priority

The original v3 audit recommended P0 (Governance) → P1 (Safety) → P2 (Review).

v3.1 expands P0 to include CI and adds design-system planning. Revised sequence:

```
P0 — Foundation + Safety (v3.1 expanded):
  1. Task-contract YAML schema
  2. UI-contract schema
  3. Risk classification R1-R4
  4. Task-state definitions
  5. Role and permission model
  6. Review-report schema
  7. Evidence-package schema
  8. Protected-zone policy
  9. Decision register (DEC-HOS-001, DEC-AVOA-PRICING-001)
  10. Regression-register structure + first 3 records
  11. Minimum CI workflow (build + lint + test)
  12. Changed-file reporting script
  13. Minimal scope checker
  14. Branch-protection preparation
  15. Interim no-direct-push rule

P1 — Review Path:
  16. Resolve Claude Code auth or formalize OpenCode path
  17. Structured findings schema implementation
  18. Hermes adjudication record
  19. Builder scorecard for Kimi K3

P2 — Design Foundation:
  20. Design-system audit and documentation
  21. Accessibility baseline
  22. Visual QA automation (screenshot capture)

P3 — Parallel Execution (deferred):
  23. Configure sub-agent profiles
  24. Initialize Kanban board
  25. Worktree isolation testing
  26. Collision detection

P4 — Command Center (deferred):
  27. Backend data APIs
  28. Dashboard UI
```

---

*Addendum complete 31 July 2026. Awaiting v3.1 implementation-package instruction.*