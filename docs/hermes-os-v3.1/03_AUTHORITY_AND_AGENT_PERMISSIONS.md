# 03 — Authority and Agent Permissions

**Status:** SPECIFICATION  
**Version:** 3.1

## Authority Hierarchy

1. **Explicit current instruction from Amjad** — overrides everything below
2. **Locked approved decisions** — DEC-XXX-NNN records; require Amjad to change
3. **Approved parent task contract** — defines scope, risk, allowed files
4. **Approved subtask and UI contracts** — within parent contract boundaries
5. **Product and architecture specifications** — what the system IS
6. **Risk, permission and protected-zone policies** — automated enforcement rules
7. **Design-system standards** — visual and interaction rules
8. **Agent recommendations** — advisory only; never override higher authority

No lower-level source may override a higher-authority source. When two sources at the same level conflict, Hermes stops and requests or records a resolution.

---

## Permission Matrix

| Permission | Hermes | Kimi K3 | Codex | Claude Code | Sub-agents |
|---|---|---|---|---|---|
| Create task contracts | ✓ | ✗ | ✗ | ✗ | ✗ |
| Approve task contracts | ✓ | ✗ | ✗ | ✗ | ✗ |
| Define/change scope | ✓ | ✗ | ✗ | ✗ | ✗ |
| Classify risk | ✓ | ✗ | ✗ | ✗ | ✗ |
| Unlock protected zones | ✓ | ✗ | ✗ | ✗ | ✗ |
| Accept/reject review findings | ✓ | ✗ | ✗ | ✗ | ✗ |
| Route work between agents | ✓ | ✗ | ✗ | ✗ | ✗ |
| Declare READY_FOR_AMJAD | ✓ | ✗ | ✗ | ✗ | ✗ |
| Merge to protected branch | ✓* | ✗ | ✗ | ✗ | ✗ |
| Deploy to production | ✓* | ✗ | ✗ | ✗ | ✗ |
| Write production code | Limited† | ✓‡ | ✓‡ | ✗ | Limited¶ |
| Read codebase | ✓ | ✓ | ✓ | ✓ | ✓ |
| Write tests | ✗ | ✓ | ✓ | ✗ | Test Agent |
| Edit documentation | ✓ | ✓ | ✓ | ✗ | Doc Agent |
| Modify CI configuration | ✓ | ✗ | ✗ | ✗ | ✗ |
| Modify branch protection | ✓§ | ✗ | ✗ | ✗ | ✗ |
| Capture screenshots | ✓ | ✗ | ✗ | ✗ | Visual QA |

**Legend:**
- ✓ = Allowed
- ✗ = Prohibited
- ✓* = After all required gates AND Amjad approval
- ✓‡ = Within approved task contract boundaries only
- ✓§ = Amjad may also authorize
- Limited† = Docs, plans, contracts, policies, schemas, templates, decisions, regressions, audits, orchestration config. NOT production features.
- Limited¶ = Within specific restricted domain and approved contract

---

## Hermes Code Boundary

**Hermes may directly write:**
- Documentation, plans, task contracts, UI contracts
- Policies, schemas, templates
- Decision records, regression records
- Audit records, evidence records
- Orchestration configuration (CI workflows, policies, .hermes/ structure)
- Non-production operational metadata

**Hermes should NOT normally write:**
- Production application features
- Business logic or pricing code
- API implementation or database models
- UI components
- Tests (delegated to Test Agent or builder)

**Exception:** Small orchestration-layer configuration changes when Hermes itself is the system being implemented, provided explicitly authorized and reviewed.

---

## Agent Authority Boundaries

### Kimi K3
- May: implement within contract scope, read entire codebase, commit to feature branches
- Must not: redefine objectives, expand scope, change architecture, edit protected zones without unlock, treat reviewer findings as direct instructions, mark own work approved, merge to master, deploy

### Codex
- May: implement within contract scope (narrow, precise changes), read codebase, commit to feature branches
- Must not: same as Kimi K3

### Claude Code
- May: inspect repository, read diffs, review against contract, report structured findings to Hermes
- Must not: directly instruct builders, change scope, rewrite implementation, merge, deploy, act as orchestrator
- First pass: read-only

### Sub-agents (Scout, Test Agent, Doc Agent, UI Agent, Visual QA)
- May: operate within named restricted domain and approved contract
- Must not: merge, deploy, expand scope, unlock zones, route work, approve anything

---

## Communication Path

```
Builder submits implementation
→ Hermes sends evidence package to reviewer
→ Reviewer submits findings to Hermes
→ Hermes accepts or rejects findings
→ Hermes sends ONLY approved corrections to builder
```

Claude Code must not directly instruct Kimi.  
Builders must not independently implement every reviewer suggestion.  
Agents must not directly control one another.

---

*Part of Hermes OS v3.1 — Specification.*