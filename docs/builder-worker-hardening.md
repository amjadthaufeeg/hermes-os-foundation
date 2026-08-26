# Hermes Builder v3 — Security Preconditions

## Status
Founder-authorized hardening after independent Fable 5 review.

## Non-negotiable preconditions

1. Run the builder only from a dedicated macOS user named `hermes-builder` (or an explicitly configured equivalent).
2. The builder account must not be root and must not belong to the macOS `admin` group.
3. Do not sign into personal/work browsers, email, cloud drives, password managers, or unrelated developer tools from the builder account.
4. Kimi Code must be installed separately from Moonshot AI's official documentation. The Hermes installer does not download third-party installers.
5. Create dedicated SSH deploy keys for:
   - `amjadthaufeeg/hermes-control`
   - `amjadthaufeeg/hermes-os-foundation`
   - `amjadthaufeeg/avoa-quote-engine`
   Each private key must be mode `0600`/`0400`. Do not reuse personal GitHub SSH keys.
6. GitHub `main` protection/rulesets must require PRs, block force pushes, and have no builder bypass. Because the current ChatGPT GitHub integration cannot read private-repo branch-protection settings, this must be confirmed in GitHub before activation.
7. Treat write access to `hermes-control:main` as equivalent to the ability to request code execution on the builder account. Restrict writers accordingly.

## Runtime isolation

- One full Git clone per task, not a shared worktree.
- Full clones live below `~/Library/Application Support/HermesBuilder/task-clones/`.
- Each repository uses its own configured SSH deploy key.
- `SSH_AUTH_SOCK` is removed from Git subprocesses.
- Worker pushes use the configured immutable remote URL rather than trusting a builder-modified `origin`.
- Worker Git commands disable hooks using `core.hooksPath=/dev/null`.
- Builder subprocess receives a minimal explicit environment only.
- Builder timeout terminates the entire process group.

## HOS gate

Before execution, the worker requires a completed `PASS` HOS result whose receipt and contract hash match the queued builder job. The gate binds task ID, builder, repository, branch, baseline commit, task contract, allowed files and protected paths.

## Post-build enforcement

Before any push the worker verifies:

- assigned branch is still active;
- working tree is clean;
- candidate SHA differs from baseline;
- candidate descends from baseline;
- every changed path is inside `allowed_files`;
- no changed path intersects `protected_paths`;
- configured remote URL has not changed;
- protected remote branch SHAs did not move during the build;
- final push targets only the assigned task branch.

Builder output and errors are redacted for common token/key patterns before publication.

## Residual risk

This is not a complete operating-system sandbox. Kimi can read files accessible to the dedicated `hermes-builder` macOS user and has network access required for its service. The dedicated-user boundary is therefore mandatory. For materially higher assurance, move the builder to a dedicated VM/remote machine in a later hardening phase.

## Uninstall

```bash
bash "$HOME/Library/Application Support/HermesBuilder/source/deploy/builder_dispatch/uninstall-macos.sh"
```

To delete task clones too:

```bash
bash "$HOME/Library/Application Support/HermesBuilder/source/deploy/builder_dispatch/uninstall-macos.sh" --purge-clones
```

Then revoke all three deploy keys in GitHub and run `kimi logout` if retiring the builder account.
