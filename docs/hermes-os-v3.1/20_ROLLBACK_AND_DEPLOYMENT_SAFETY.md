# 20 — Rollback and Deployment Safety

**Status:** SPECIFICATION
**Version:** 3.1

---

## Purpose

Every material task must be reversible. High-risk features require documented rollback packages, feature flags, and controlled deployment. No agent may deploy to production without all required gates and Amjad approval.

---

## Rollback Package Schema

```yaml
rollback_package:
  task_id:
  timestamp:
  
  baseline:
    branch:
    commit:
    tag:
  
  candidate:
    branch:
    commit:
  
  changes:
    files_changed: N
    files:
      - path:
    dependencies_changed: N
    dependencies:
      - name:
        from_version:
        to_version:
  
  database:
    migrations: true|false
    migration_files:
      - path:
    migration_rollback: >
      Exact steps to reverse the migration.
  
  feature_flags:
    uses_feature_flags: true|false
    flag_name:
    disable_steps:
  
  rollback_steps:
    1. "Step description with exact command"
    2. "Step description with exact command"
  
  post_rollback_checks:
    - "Check description"
    - "Check description"
  
  deployment:
    identifier:
    environment:
    timestamp:
    deployed_by:
```

---

## Deployment Gate Requirements

| Gate | R1 | R2 | R3 | R4 |
|---|---|---|---|---|
| All automated gates pass | ✓ | ✓ | ✓ | ✓ |
| Independent review complete | ✓ | ✓ | ✓ | ✓ |
| Accepted findings resolved | ✓ | ✓ | ✓ | ✓ |
| Rollback package available | — | ✓ | ✓ | ✓ |
| Feature flags (if applicable) | — | — | ✓ | ✓ |
| Staging deployment validated | — | — | ✓ | ✓ |
| Amjad approval | ✓ | ✓ | ✓ | ✓ |

---

## Feature Flag Policy

High-risk features (R3-R4) should use feature flags where practical:

```yaml
feature_flag:
  name: "feature_name"
  description:
  default: off
  environments:
    development: on
    staging: on
    production: off
  rollback: "Disable flag → feature is invisible → no data loss"
  cleanup: "Remove flag code after N days of stable production use"
```

---

## Rollback Preference Order

1. **Disable feature flag** — fastest, no code change, no data impact
2. **Revert merge commit** — `git revert <sha>`; preserves history
3. **Restore previous release** — redeploy previous tagged version
4. **Restore data backup** — last resort; requires approved incident procedure

---

## Who Can Deploy

| Agent | Deploy Authority |
|---|---|
| Amjad | Full authority |
| Hermes | After all gates + Amjad approval |
| Kimi K3 | **Prohibited** |
| Codex | **Prohibited** |
| Claude Code | **Prohibited** |
| Any sub-agent | **Prohibited** |
| CI/CD | Automated after merge if all gates pass **and** deployment is explicitly approved |

---

## Direct Push Prohibition

Routine direct pushes to `master` are prohibited for agent-driven development.

Until branch protection is technically enforced, this is an interim operating rule. Every exception must be recorded.

---

## Emergency Procedure

Only in documented emergencies, with Amjad explicit authorization:

1. Amjad authorizes emergency access
2. Hermes records the authorization and reason
3. Change is made
4. Post-emergency review is scheduled
5. Permanent fix follows normal workflow

---

*Part of Hermes OS v3.1 — Specification. Awaiting implementation.*