# GitHub Workflow

- GitHub is the authoritative code source.
- Every task begins from a named base commit.
- Every task uses a dedicated feature or fix branch.
- Stable branches must not receive direct unreviewed edits.
- Candidate code must be committed before Claude review and Replit preview.
- Pull requests contain the task ID, contract link, evidence, review result, and rollback method.
- Uncommitted unrelated work must never be overwritten.

Recommended names:
- `feature/TASK-0000-short-name`
- `fix/TASK-0000-short-name`
- `docs/TASK-0000-short-name`
