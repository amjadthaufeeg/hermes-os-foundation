# Staging and Production Policy

## Staging
- Mirrors production architecture where practical.
- Uses isolated or sanitized data.
- Receives merged, validated candidates.
- Supports final integration and operational checks.

## Production
- Requires the risk-level approval gate.
- Uses versioned releases and a rollback path.
- Deployment must be traceable to a commit.
- Post-deployment health checks are mandatory.
- Automatic production deployment remains disabled until explicitly approved by governance.
