# Hermes OS Architecture v1.0

## Control flow

```text
Amjad
  ↓
Hermes Control Plane
  ├─ Knowledge OS: what is true
  ├─ Task OS: what should be done
  ├─ Governance OS: what is allowed
  ├─ Intelligence OS: how work is routed
  ├─ Engineering OS: how work is built and verified
  ├─ Operations OS: how releases are operated
  └─ Learning OS: how the system improves
```

## Execution path

```text
Request → Context → Risk → Change Contract → One Builder → Automated Checks
→ GitHub Commit → Claude Review → Replit Preview → Amjad Approval
→ Merge → Deploy Gate → Observe → Learn → Close
```

## Separation rules
- Knowledge documents define truth; task records do not rewrite them.
- The active builder writes; the reviewer initially reads only.
- Replit runs committed candidate code; it does not own unique code.
- Operations begins after merge and continues until health is verified.
- Intelligence recommends routing but cannot override governance.
