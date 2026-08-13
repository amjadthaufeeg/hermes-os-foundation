# HOS-AUTO-01 — ChatGPT ↔ Hermes Handoff Reduction

**Design only.**

---

## 1. Current Problem

```
ChatGPT → Amjad → Hermes      (instructions relayed manually)
Hermes   → Amjad → ChatGPT    (results relayed manually)
Amjad    → Terminal           (commands pasted manually)
Terminal → screenshot → ChatGPT (evidence via screenshots)
```

Amjad is the human courier between three systems.

---

## 2. Staged Model (do NOT assume unrestricted integration)

### Stage 0 — TODAY (manual courier)
Everything is manual. This is the current state. Screenshots as evidence.

### Stage 1 — Hermes Execution Bridge (R1)
Hermes talks directly to a controlled executor on the VPS. This eliminates the Hermes → Amjad → Terminal leg for routine work.

**Remaining manual:** ChatGPT → Amjad → Hermes (instructions still relayed).

### Stage 2 — Structured Hermes API
Hermes exposes a controlled task API. Amjad can forward tasks machine-to-machine instead of re-typing.

```
POST /tasks           (submit structured task)
GET  /tasks/{id}      (status)
GET  /tasks/{id}/evidence  (structured evidence, not screenshots)
POST /tasks/{id}/approve   (GATED approval)
POST /tasks/{id}/abort     (abort)
```

**This is the proposed future interface.** But it must be reached carefully.

### Stage 3 — Direct ChatGPT ↔ Hermes (deferred)
Only after Stage 2 proves safe, and ONLY if a trusted, authenticated, scoped integration exists. This is out of R1 scope and may never be needed if Amjad prefers to remain the authority between the two AI systems.

---

## 3. Safest Architecture for the Future Interface

Do NOT blindly expose a public REST API. Recommended:

1. **Authenticated, scoped, local-only API.** Not internet-exposed. Access via SSH tunnel or Unix socket, not public endpoint.

2. **Task submission is a structured contract** (same schema as HOS-AUTO-01), not free-text.

3. **Authority classification server-side.** The API cannot grant authority; it can only submit to the bridge which classifies.

4. **Evidence is receipt-based**, never raw shell dumps as screenshots.

5. **Approval is a signed token**, not a boolean flag.

---

## 4. Proposed Future Interface (conceptual, not R1)

```
POST /api/v1/tasks
  body: {contract}          → 201 + task_id + contract_sha256
  auth: Hermes-or-Amjad token

GET /api/v1/tasks/{id}
  → status, authority_class, verdict

GET /api/v1/tasks/{id}/evidence
  → receipt + artifacts (structured, redacted)

POST /api/v1/tasks/{id}/approve
  body: {authorization_token}   → for GATED tasks

POST /api/v1/tasks/{id}/abort
  → stop execution (if within AUTO timeout window)
```

---

## 5. Trust Boundary

| Actor | Can submit tasks? | Can approve GATED? |
|---|---|---|
| Hermes | YES (AUTO only) | NO |
| Amjad | YES (all) | YES |
| ChatGPT | NO (Stage 2) / YES via Amjad (Stage 3, if ever) | NO |

---

## 6. Key Risks (Stage 2+)

| Risk | Mitigation |
|---|---|
| Public API exposure | Local-only, SSH tunnel, strong auth |
| ChatGPT submitting FORBIDDEN ops | Authority classification is server-side, not client-side |
| Credential exposure via API | No credentials in API responses |
| Replay of approval | Single-use signed tokens |

---

## 7. Recommendation

- **R1 delivers Stage 1** (Hermes → executor bridge). This is the highest-value, lowest-risk step.
- **Stage 2** (structured API) is a follow-on, only after R1 is proven safe.
- **Stage 3** (direct ChatGPT integration) is optional and lowest priority — Amjad may prefer to remain the human authority between AI systems.

---

**Handoff reduction design complete.**