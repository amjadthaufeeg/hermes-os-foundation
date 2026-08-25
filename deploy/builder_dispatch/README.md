# Hermes Builder Dispatch Adapter

This adapter closes the runtime gap between Hermes `route_work` and an approved builder process without changing HOS authority semantics.

## Boundary

- Hermes/ChatGPT may submit a declarative builder job to the private control transport.
- The host config, not the job, maps repositories to local working directories and builders to absolute executable paths.
- Only `kimi-k3` and `codex` are accepted builders.
- Protected branches are rejected.
- Only one builder may hold a repository+branch lock at a time.
- Invocation uses fixed argv and `shell=False`.
- HOS remains the verification/control plane after implementation; this adapter does not add HOS operation types.

## Queue

The watcher reuses the existing authenticated `hermes-control` clone and creates these paths as needed:

- `builders/inbox/`
- `builders/claims/<task_id>/claim.json`
- `builders/completed/<task_id>.json`
- `builders/stopped/<task_id>.json`

## Host configuration

Configuration lives outside GitHub, normally at `/etc/hermes-auto/builder-dispatch.json`, must be owned by root or the service user, and must not be group/world writable.

Example shape (executable paths/arguments are installation-specific and must be verified on the host):

```json
{
  "builders": {
    "kimi-k3": {
      "executable": "/ABSOLUTE/PATH/TO/KIMI",
      "args": ["...", "{contract_path}", "..."],
      "pass_env": ["KIMI_API_KEY"]
    },
    "codex": {
      "executable": "/ABSOLUTE/PATH/TO/CODEX",
      "args": ["...", "{contract_path}", "..."],
      "pass_env": ["OPENAI_API_KEY"]
    }
  },
  "repositories": {
    "owner/repo": {
      "working_directory": "/opt/hermes-worktrees/repo",
      "contract_root": "/opt/hermes-worktrees/repo/docs/tasks",
      "allowed_branch_prefixes": ["feature/", "fix/", "chore/"]
    }
  }
}
```

Secrets must remain in the host environment/credential store and never in this repository.
