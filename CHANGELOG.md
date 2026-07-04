# Changelog

All notable changes to ticket-master are documented here.

## [1.6.0] — 2026-07-04

### Added

- **`lib/domains_generator.py` (Phase 1 of the personal-assistant expansion,
  T-20260704-02).** Generates `config/domains.json`, a domains registry that
  maps boss-agent domains to their experts and, where one already exists, the
  matching standalone skill. Reads a boss-agent `SKILL.md` frontmatter
  (`orchestrates.experts`, `description`) and cross-references each expert
  against a skill registry's `components.json`
  (`provenance.origin: bach` / `origin_path`). Experts without a standalone
  counterpart are marked `"status": "nicht-portiert"` (to be closed later via
  a skill-extractor pass). `config/domains.json` is itself BACH-free at
  runtime — the generator only needs BACH access once, at generation time, and
  aborts cleanly (leaving any existing file untouched) if the BACH agents
  directory is not available. Site-specific and gitignored, like
  `config/ticket-master.config.json`; see `config/domains.example.json` for
  the schema. Tests: `tests/test_domains_generator.py`.

## [1.5.0] — 2026-07-04

### Changed

- **Audit trail is now PER TICKET; the shared intake log is deprecated.**
  Back-alignment from the battle-tested private instance of this workflow:
  with several machines appending to one cloud-synced
  `tickets/_logs/INTAKE-TRIAGE-LOG.txt`, sync conflict copies ate log lines.
  The audit/triage trail now lives inside each ticket's own
  `T-….<HOST>.txt` (`STATUS` / `LOG` / `SOLUTION` fields). Trivial,
  immediately verified one-liners get a **minimal** ticket file dropped
  directly into `tickets/SOLVED/` instead of a shared log line.
  Updated: both prompts (decision ladder 3c + LOGGING section), both READMEs,
  `SKILL.md`, `llms.txt`; `logging.intake_log` removed from the config
  example; the `_logs/` file itself is kept as a deprecation stub so legacy
  checkouts and old references do not break.

## [1.4.1] — 2026-07-04

### Fixed

- **`lib/ticket_writer.py`: ticket loss and duplicate IDs prevented.**
  `create()` now opens the target exclusively (`"x"`) and retries with the
  next number on collision — a concurrent creator (second machine, cloud
  sync) can no longer silently overwrite an existing ticket. Ticket numbering
  now scans **all** lifecycle folders (root intake, `QUEUED/`, `PENDING/`,
  `SOLVED/`, `.USER/`) instead of only `QUEUED/`, so a ticket that was moved
  on no longer frees up its ID for reuse.
- **`lib/doc_scanner.py`: `append_entry()` no longer corrupts non-UTF-8
  documents.** Previously a cp1252-encoded `TODO.md` was read with
  `errors="replace"` and written back with U+FFFD replacement characters —
  permanently damaging curated content. Now the read is strict and raises
  `ValueError` with a clear message, leaving the file untouched.
- **`tests/test_smoke.py` had no effect under pytest:** the four checks
  returned booleans, which pytest counts as PASSED regardless of outcome
  (only a `PytestReturnNotNoneWarning`). They are now `check_*` helpers with
  real `test_*` assert wrappers; `python tests/test_smoke.py` still works.
- **Stale references to the pre-1.3.0 log location:** `tests/test_smoke.py`
  (`REQUIRED_PATHS`, gitignore check) and two `.gitignore` lines still
  pointed at `tickets/INTAKE-TRIAGE-LOG.txt`; the file moved to
  `tickets/_logs/` in 1.3.0 — the documented `python tests/test_smoke.py`
  call failed on a correct checkout. Prompt short references (decision
  ladder 3c, EN+DE) now use the full `tickets/_logs/…` path too.
- Version badge (READMEs) and `SECURITY.md` supported-versions table were
  stuck at 1.3.0/1.0.x; `prompts_dir` in the config example is documented
  as reserved (the `bin/` launchers do not read it yet).
- `.gitignore`: ignore local `LOCK*.txt` coordination files.

### Tests

- 7 → 11 green (`py -m pytest tests/`): ID uniqueness across lifecycle
  folders, no-overwrite collision retry, strict-UTF-8 append (reject + happy
  path).

## [1.4.0] — 2026-06-27

### Added

- **`lib/ticket_writer.py`:** user-neutral helper for asynchronous ticket creation — drop an
  unclaimed `T-YYYYMMDD-NN.txt` into `<tickets_dir>/QUEUED/` even when no TICKET-MASTER session
  is running (e.g. from a lock-watcher GUI). `tickets_dir` is required or read from
  `TICKET_MASTER_TICKETS_DIR`; the date is injectable for deterministic tests.
- **`lib/doc_scanner.py`:** scan / create / append the four project control documents
  (`TODO.md`, `AUFGABEN.txt`, `DONE.md`, `DECISIONS.md`) without overwriting curated content;
  `DECISIONS.md` is created in ADR format.
- **`tests/test_lib_helpers.py`** covering both helpers.

### Notes

- Mirrored from the running `_scripts/` instance used by the lock-watcher; this module is the
  user-neutral publishable copy.

## [1.3.0] — 2026-06-19

### Added

- **Cloud-Ready / Multi-System Claim Convention:** When the `tickets/` directory is
  shared across multiple machines via a cloud-synced folder (OneDrive, Dropbox, Google
  Drive), claims are signalled via filename rename — `T-YYYYMMDD-NN.txt` (unclaimed)
  → `T-YYYYMMDD-NN.<HOST>.txt` (claimed). Atomic on NTFS; no lock files needed.
  Documented in both prompts (new `MULTI-SYSTEM CLAIM CONVENTION` section), both
  READMEs (new `Cloud-Ready` sections), `SKILL.md`, and `llms.txt`.
- **`tickets/_logs/` sub-directory:** Audit trail (`INTAKE-TRIAGE-LOG.txt`) moved from
  `tickets/` root into `tickets/_logs/` to keep the ticket queue clean.
  Existing `INTAKE-TRIAGE-LOG.txt` migrated; all references updated (prompts, config
  example, `llms.txt`, READMEs).
- Added README/README_de discovery context and `llms.txt` search notes so the
  project is easier to distinguish from Ticketmaster event APIs, support-ticket
  SaaS, ticket bots, and resale marketplaces.

### Changed

- Both agent prompts: log path updated from `tickets/INTAKE-TRIAGE-LOG.txt` to
  `tickets/_logs/INTAKE-TRIAGE-LOG.txt`.
- `config/ticket-master.config.example.json`: `logging.intake_log` updated to
  `_logs/INTAKE-TRIAGE-LOG.txt`.
- Both READMEs: Ticket Lifecycle section replaced by expanded Directory Layout +
  Cloud-Ready section; version badges bumped to 1.3.0.
- `SKILL.md`: description and body updated to mention Cloud-Ready and `_logs/` path.
- `llms.txt`: description updated; audit trail path corrected; last-checked updated
  to 2026-06-19.

## [1.2.1] — 2026-06-14

### Changed

- README banner: replaced the small centered icon with a full-width banner
  (`assets/banner.svg`) — icon motif plus wordmark and tagline, edge-to-edge.

## [1.2.0] — 2026-06-14

### Changed

- Reframed ticket-master as a **workflow / operating mode** for an AI coding agent
  rather than an autonomous tool that acts on its own. Sharpened the framing in both
  READMEs and `llms.txt` using a canonical description; reworded passages that
  presented the program as the acting subject so that the *agent* performs each step
  by following the prompt.
- Version badges in both READMEs bumped to 1.2.0.

### Added

- `SKILL.md` — Claude Code skill manifest. Instructs the agent to read
  `prompts/TICKET-MASTER.${TM_LANG:-en}.md`, load `config/ticket-master.config.json`,
  and follow the workflow through to Position 0.

## [1.1.1] — 2026-06-14

### Changed

- Logo replaced with a refined version genuinely authored by agy (Gemini 3.5 Pro)
  via the Antigravity CLI (workspace granted with the `--add-dir` flag) — ticket
  with perforation and stub detail plus a masked routing hub branching to three
  nodes (amber accent). Works on light and dark backgrounds.

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
