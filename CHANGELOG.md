# Changelog

All notable changes to ticket-master are documented here.

## [1.0.0] — 2026-06-14

### Initial Release

- Cross-platform starters: Unix shell (`.sh`), Windows CMD (`.bat`), PowerShell (`.ps1`)
- Provider support: Claude CLI, Codex CLI, agy (Gemini CLI)
- `TM_PROVIDER` and `TM_SKIP_PERMISSIONS` environment variables
- `prompts/TICKET-MASTER.md` — fully anonymised, provider-agnostic agent prompt
  - Lean Router principle and three-bucket context model
  - Companion Pattern for ticket series
  - Decision Ladder (feature/user-only/actionable/bulk)
  - Score formula: `(10 - CLARITY) + COMPLEXITY + CREATIVITY + CONTEXT + CRITICALITY`
  - Processing chain: Intake → GATE1 → Characterise → Score → Candidates (GATE2/3) → Delegate (GATE4 + fallback) → Position 0
  - CHECKPOINT ALPHA (async / project task / user handoff)
- `config/ticket-master.config.example.json` — all fields documented
- `tickets/` — lifecycle directories: `QUEUED/`, `PENDING/`, `SOLVED/`, `.USER/`
- `tickets/_templates/TICKET.txt` — structured ticket template
- `tickets/INTAKE-TRIAGE-LOG.txt` — one-line-per-ticket audit trail
- `tests/test_smoke.py` — structure, JSON validity, anonymisation checks
- English and German documentation (`README.md`, `README_de.md`)
