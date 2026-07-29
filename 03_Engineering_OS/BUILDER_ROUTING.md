# Builder Routing

## Default
- Kimi K3: substantial features, vertical slices, broad context, coordinated multi-file implementation.
- Codex: surgical fixes, sensitive behavior preservation, small allowed-file lists, recovery after uncontrolled scope expansion.
- Claude Code: independent review and architectural challenge; no initial write access.

## Routing gates
- Only one active builder per task branch.
- A handoff requires the first builder to stop, commit or discard its work, and document state.
- Kimi failing verification twice triggers stop and re-plan; Codex may then receive a new approved repair contract.
- High-risk work may use an independent alternative implementation, but never simultaneous writes to the same branch.
- Routing should later use project scorecards, not general reputation alone.
