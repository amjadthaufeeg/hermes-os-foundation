# HOS-AUTO-01 — R1 VPS Deployment Package

**PREPARE ONLY. Do NOT deploy without fresh Amjad authorization.**

---

## A. Source Commit

| Field | Value |
|---|---|
| Branch | `hos-auto-01-r1` |
| Short SHA | (record at deploy time via `git rev-parse --short HEAD`) |
| Full SHA | (record at deploy time) |
| Origin | `git ls-remote origin refs/heads/hos-auto-01-r1` must match local |

## B. Artifacts (SHA256 recorded at deploy)

```
deploy/hos_auto_01/bin/bridge.py
deploy/hos_auto_01/bin/preflight.py
deploy/hos_auto_01/bin/broker.py
deploy/hos_auto_01/policy/authority.py
deploy/hos_auto_01/deps/requirements.txt
```

## C. Directories

```
/opt/hermes-auto/
├── bin/               (root:root 755 — bridge + broker + preflight)
├── policy/            (root:root 755 — authority.py, read-only to hermes-auto)
├── contracts/         (root:root 700 — bridge writes via IPC only)
├── evidence/          (hermes-auto:hermes-auto 700)
├── receipts/          (root:root 700 — finalized, append-only)
├── deps/              (root:root 755)
└── logs/              (hermes-auto:hermes-auto 700)
```

## D. Users / Groups

| User | UID | Purpose |
|---|---|---|
| `hermes-auto` | (system, `-r`) | Runs bridge (unprivileged) |
| `root` | 0 | Runs broker (privileged, fixed executable) |

## E. Broker Privilege Mechanism

**Design: systemd service with `sudo`-free, fixed invocation via a root-owned wrapper.**

The bridge (hermes-auto) invokes the broker through a fixed root-owned helper:

```
/usr/local/sbin/hermes-broker-dispatch
```

This helper:
- Is root-owned, mode 755 (readable, not writable by hermes-auto)
- Accepts JSON on stdin (size-limited 64KB)
- Executes `/opt/hermes-auto/bin/broker.py` with fixed env
- Does NOT accept arguments (no caller-controlled executable)

### sudoers rule (narrowest)

```
hermes-auto ALL=(root) NOPASSWD: /usr/local/sbin/hermes-broker-dispatch
```

This grants ONLY the fixed dispatch helper — NOT `docker`, NOT `python`, NOT `bash`.

### Alternative (preferred): systemd socket activation

If sudo is undesirable, use a root systemd service that hermes-auto talks to via a Unix socket. The service runs broker.py as root. hermes-auto has no privilege — it can only send typed JSON over the socket. This is the strongest boundary. **Recommended over sudoers.**

## F. Docker Security Policy (AUTO disposable)

| Property | Enforced |
|---|---|
| privileged | false (never set) |
| network | `none` or `hermes-b5-lab-net` only |
| pid/ipc | default (isolated) |
| cap_drop | ALL (always) |
| no-new-privileges | true (always) |
| Docker socket | NEVER mounted |
| device passthrough | NEVER |
| ports | NEVER published |
| user | `10010:10010` (enforced) |
| pids-limit | 128 |
| memory | 256m |
| cpus | 1.0 |
| read_only | true |
| mounts | only within `/tmp/hermes-b5-lab/`, canonicalized |

## G. Image Policy

- AUTO images: `disposable-*` prefix ONLY.
- Local-only images, no registry pull for R1.
- Production image `hermes-product-os-hpos:*` REJECTED.
- Digest pinning recommended for R1c (post-pilot).

## H. Dependency Installation

```bash
pip install -r deploy/hos_auto_01/deps/requirements.txt
```

## I. Preflight

```bash
sudo -u hermes-auto python3 /opt/hermes-auto/bin/preflight.py
# Must output PREFLIGHT PASSED, else TEST_ENVIRONMENT_INVALID
```

## J. Logging

- Bridge logs: `/opt/hermes-auto/logs/bridge.log`
- Broker logs: systemd journal (if socket-activated) or `/opt/hermes-auto/logs/broker.log`

## K. AC-01 VPS Acceptance Test

After install, Hermes executes:

```json
{"task_id": "AC01-VPS-001", "operations": [
  {"type": "inspect_container", "params": {"container_name": "hermes-product-os-prod"}},
  {"type": "inspect_timer", "params": {"timer_name": "hermes-production-snapshot-refresh.timer"}}
], ...}
```

Expected: preflight → classify AUTO → execute → receipt → Hermes reads receipt → report. **No Amjad SSH/Terminal/screenshot.**

## L. Rollback

```bash
systemctl stop hermes-broker.service (if used)
userdel hermes-auto
rm -rf /opt/hermes-auto
rm -f /etc/sudoers.d/hermes-auto  (if sudoers used)
# Production containers/DB/snapshots untouched
```

## M. Uninstall

Same as rollback, plus `pip uninstall` if isolated venv was used (recommended: venv per-install, so `rm -rf` the venv).

## N. Security Assertions (must hold post-install)

1. hermes-auto cannot write `/opt/hermes-auto/bin/broker.py`
2. hermes-auto cannot write `/opt/hermes-auto/policy/`
3. hermes-auto can only write `/opt/hermes-auto/evidence/` and `/logs/`
4. Broker is root-owned, mode 755, not writable by hermes-auto
5. No `sudo docker`, `sudo python`, `sudo bash` permitted
6. Docker socket not mounted into any disposable container
7. Production resource references hard-blocked by broker

---

**Deployment package prepared. Do NOT deploy without fresh Amjad authorization.**