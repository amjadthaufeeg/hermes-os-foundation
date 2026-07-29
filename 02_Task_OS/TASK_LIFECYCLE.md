# Task Lifecycle

```text
REQUESTED
→ CONTEXT_RETRIEVED
→ CLASSIFIED
→ CONTRACT_DRAFTED
→ APPROVED
→ READY
→ IN_PROGRESS
→ BUILT
→ AUTOMATED_CHECKED
→ COMMITTED
→ REVIEWED
→ PREVIEW_READY
→ HUMAN_APPROVED
→ MERGED
→ DEPLOYED_OR_HELD
→ OBSERVED
→ LEARNED
→ CLOSED
```

## Gate rules
- A material task cannot enter `IN_PROGRESS` without an approved contract.
- Code cannot enter review without a commit and validation evidence.
- Replit must identify branch and commit.
- Merge requires all mandatory gates for the risk level.
- Deployment is a separate approval from merge unless governance explicitly allows otherwise.
- `CLOSED` requires learning and rollback information.
