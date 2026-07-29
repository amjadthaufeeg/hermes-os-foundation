# Permission Policy

Use least privilege.

- Builders receive write access only to the assigned task workspace and necessary services.
- Reviewers receive read-only access by default.
- Production credentials are not available in preview environments.
- Secrets are stored in approved secret managers, never code or task documents.
- Destructive commands require explicit approval and a rollback plan.
- Permission changes are logged with actor, time, reason, and scope.
- Access is removed when no longer necessary.
