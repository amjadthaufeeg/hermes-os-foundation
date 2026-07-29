# Rollback Protocol

Every material task must state:
- pre-change branch and commit;
- candidate commit;
- database migration status;
- feature flag status;
- exact revert or restore method;
- owner authorized to execute rollback.

Rollback should prefer:
1. disable feature flag;
2. revert merge commit;
3. restore previous release;
4. restore data backup only under approved incident procedure.

A rollback is not complete until application health is checked.
