# Installation Guide for Amjad

This guide assumes you are not technical. Your role is to approve decisions and verify the visible result. Hermes and the coding tools should perform the technical work.

## Step 1 — Save a backup

### What this means
A backup gives you a safe return point if the new rules are installed incorrectly.

### Send Hermes

```text
Before changing any files, create a rollback point for the current Hermes repository.

Confirm in plain English:
1. the current GitHub repository;
2. the active branch;
3. whether all current work is committed and pushed;
4. the backup branch or tag you created;
5. how to restore it.

Do not modify product code.
```

### Do not continue until Hermes confirms
- the latest code is on GitHub;
- there are no unexplained uncommitted changes;
- a rollback branch or tag exists.

## Step 2 — Upload this entire pack

### What this means
Place the `Hermes_OS_v1.0_Foundation` folder inside the Hermes repository, preferably under:

```text
docs/hermes-os/
```

### Send Hermes

```text
I am attaching the Hermes OS v1.0 Foundation Pack.

Do not activate or rewrite it yet.
Place the complete pack under docs/hermes-os/ without changing its contents.
Then show me the final folder path and changed-file list.
Do not modify application code.
```

## Step 3 — Run the conflict audit

### What this means
Hermes may already have older instructions in `SOUL.md`, `SHOULD.md`, `AGENTS.md`, routing files, or workflow documents. Conflicting instructions must be identified before activation.

### Send Hermes

```text
Read docs/hermes-os/README_FIRST.md and docs/hermes-os/00_Constitution/HERMES_OS_CHARTER.md.

Audit all active Hermes instruction files for conflicts with Hermes OS v1.0, including SOUL.md, SHOULD.md, AGENTS.md, model-routing rules, development workflows, and deployment rules.

Return a table with:
- file;
- existing rule;
- conflicting Hermes OS rule;
- risk;
- recommendation: keep, update, archive, or decision required.

Do not edit anything yet.
```

## Step 4 — Approve the integration plan

### What this means
Hermes should propose how old rules will be linked, updated, or archived. Nothing should be deleted silently.

### Check only five things
1. Hermes remains the sole orchestrator.
2. Only one builder may write to a task branch at a time.
3. Claude reviews before writing code.
4. GitHub is the source of truth.
5. Replit previews committed code and does not become a separate codebase.

### Send Hermes after you are satisfied

```text
I approve the integration plan.

Apply only the approved instruction-file changes.
Archive superseded rules instead of deleting history.
Do not modify product code.
Afterward, provide:
- files changed;
- files archived;
- rules activated;
- rollback method;
- unresolved conflicts.
```

## Step 5 — Validate tool readiness

### What this means
Before a real task, Hermes must confirm that GitHub, the selected builder, Claude Code, tests, and Replit can perform their assigned roles.

### Send Hermes

```text
Run the Hermes OS tool-readiness check without changing product functionality.

Verify:
1. GitHub repository and feature-branch creation;
2. Kimi K3 can read the repository and follow a change contract;
3. Codex can act as precision fallback;
4. Claude Code can review a diff in read-only mode;
5. existing test, lint, type-check, and build commands;
6. Replit can preview a named committed branch;
7. no preview connects to production data.

Report PASS, PARTIAL, or FAIL for each item, with the exact correction needed.
```

## Step 6 — Choose the first pilot

### What this means
The first pilot tests the workflow, not the intelligence of the models. Choose a small visual issue affecting one page or component.

### Good pilot
- spacing, alignment, hierarchy, or responsive layout;
- no pricing, database, API, state, permissions, or workflow changes;
- two or three files at most;
- easy to inspect in Replit.

### Send Hermes

```text
Prepare the first Hermes OS pilot task.

The pilot must be VISUAL_ONLY, low risk, limited to one page or component area, and easy to verify in Replit.

Do not implement yet.
Create a complete change contract using the Foundation Pack template and explain in plain English:
- the exact visible problem;
- selected builder and reason;
- allowed files;
- protected behavior;
- tests;
- Claude review scope;
- what I must check in Replit;
- rollback method.
```

## Step 7 — Approve the pilot contract

Your job is only to confirm:
- it fixes the issue you care about;
- it clearly says what must not change;
- the allowed file list is small;
- a rollback exists;
- the live preview will be available before merge.

### Approval message

```text
Approved. Execute exactly within this change contract.

Do not expand scope. Stop and return to Hermes if extra files, business logic, workflow, APIs, database, architecture, or permissions need to change.
```

## Step 8 — Review the Replit preview

Open the link and test:
- does it look better;
- do existing buttons and actions still work;
- does mobile work;
- has anything unrelated changed;
- is the preview identified by branch and commit.

Give simple feedback. Hermes must convert any correction into a bounded amendment, not a new redesign.

## Step 9 — Approve merge, not automatic production

### Send Hermes

```text
I approve the final preview and review result.
Proceed with the approved merge process.
Do not deploy to production automatically.

Provide the completion evidence, rollback method, and post-task learning record.
```

## Step 10 — Review the pilot results

Use `Checklists/PILOT_ACCEPTANCE_CHECKLIST.md`.

After one successful pilot, activate the same flow for ordinary UI and bug-fix tasks. Keep production deployment, database changes, pricing changes, and major architecture changes under explicit human approval.
