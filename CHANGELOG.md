# Changelog

All notable changes to ticket-master are documented here.

## [1.1.0] — 2026-06-14

### Added

- Bilingual agent prompts: `prompts/TICKET-MASTER.en.md` (English) and
  `prompts/TICKET-MASTER.de.md` (German) — fully equivalent in content.
- `TM_LANG` environment variable for prompt-language selection in all starters
  (`.sh`, `.bat`, `.ps1`); loads `prompts/TICKET-MASTER.${TM_LANG}.md` and falls
  back to English with a stderr warning if the requested file is missing.
- `default_language` field in `config/ticket-master.config.example.json`.
- Logo (`assets/logo.svg`, agy-designed) embedded at the top of both READMEs.
- i18n roadmap entry in `TODO.md`.

### Changed

- Renamed `prompts/TICKET-MASTER.md` → `prompts/TICKET-MASTER.en.md`.
- Smoke test now checks both prompt languages and an extended anonymisation
  pattern list.
- Version badges in both READMEs bumped to 1.1.0.

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
