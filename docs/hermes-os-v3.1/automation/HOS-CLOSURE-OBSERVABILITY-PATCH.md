# HOS Closure Observability Patch

Purpose: ensure HOS-AUTO failures are diagnosable through the automated ChatGPT↔Hermes transport without asking Amjad to inspect Terminal.

Acceptance:
- bridge CLI emits a compact final DETAIL line on non-PASS verdicts;
- DETAIL includes execution id plus operation type/exit code and output tail, or preflight failure reason;
- evidence receipt retains preflight failure details;
- R2's existing 200-character summary tail therefore carries actionable failure evidence.
