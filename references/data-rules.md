# Data Classification Rules

These rules tell Hermes what data can go where. Load as a skill so every session enforces them.

**Source:** Migrated from reefx-hermes-foundation. Now maintained under Hermes OS v1.0 Foundation.

---

## Tiers

### RESTRICTED — never leaves this machine
- Customer PII (names, emails, phone numbers, addresses)
- Partner contracts and agreements
- Live production credentials
- Payment data, pricing agreements, revenue figures
- Opera PMS data and any hotel guest information
- Raw financial records

**Rule:** Hermes must refuse to process RESTRICTED data through any external LLM or web tool. If RESTRICTED data appears in a task, Hermes stops and asks.

### INTERNAL — stays within your tools, never goes to public web
- Product requirements and PRDs
- Source code (before public release)
- Architecture decisions and design docs
- Internal communications
- Work packages and task descriptions

**Rule:** INTERNAL data can be processed by Hermes locally and by your configured LLM provider. It must NOT be sent to public web search, public paste bins, or any unauthenticated endpoint.

### PUBLIC — safe anywhere
- Open-source code, dependencies, documentation
- Public API documentation
- General knowledge and research
- Marketing copy and public-facing content

---

## Daily Rules (memorize these)

1. **Before any task**, ask: "Does this task touch RESTRICTED data?" If yes, the task stays fully local.
2. **Never paste secrets into chat.** Use the terminal tool to read from `.env`.
3. **Before any git push**, run `scripts/no-secrets.sh` and verify the diff contains no credentials.
4. **If unsure, treat it as RESTRICTED.** False positive is safe; false negative is a breach.

---

## Tool Boundaries

| Tool | RESTRICTED | INTERNAL | PUBLIC |
|---|---|---|---|
| terminal (local) | ✓ | ✓ | ✓ |
| file (local) | ✓ | ✓ | ✓ |
| web_search | ✗ | ✗ | ✓ |
| web_extract | ✗ | ✗ | ✓ |
| browser | ✗ | ✗ | ✓ |
| image_gen | ✗ | ✗ | ✓ |

**No exceptions.** If a task needs to search the web but involves INTERNAL data, extract only the PUBLIC parts for the search query.