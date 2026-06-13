<p align="center"><img src="assets/logo.svg" alt="ticket-master" width="160"></p>

# ticket-master

A cross-platform, multi-provider **ticket router agent** for software projects.

ticket-master keeps a session open and acts as a lean, long-lived router: when
you report a bug, a change request, or any project problem, it captures the item
as a structured ticket, scores it, picks the right AI provider for the job, and
delegates accordingly — or routes it to the project's own task management when
delegation is not appropriate.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)](VERSION)

---

🇩🇪 [Deutsche Dokumentation → README_de.md](README_de.md)

---

## What It Does

```
You report a bug or change request
        |
        v
[A] Intake — ticket file created, project assigned (GATE1)
        |
        v
[2-5] Characterise → Score → Match provider → Rank 3 candidates (GATE2)
        |
        v
[B] Delegate to best available provider (GATE4 success check + fallback chain)
        |
   or   v
[C] Write to project task management (usage limit / all unavailable)
        |
        v
Position 0 — waiting for next ticket
```

Key design principles:

- **Lean Router:** The master agent stays lean. Execution is delegated; sub-agents
  report back compactly (commit hash + one line).
- **Companion Pattern:** For a series of tickets in the same domain, one companion
  sub-agent is spawned and reused — paying orientation cost once, not per ticket.
- **Score-Based Routing:** Every ticket is scored on five dimensions (Clarity,
  Complexity, Creativity, Context, Criticality) to determine the required provider
  tier.
- **Graceful Fallback:** If the preferred provider is unavailable, a fallback chain
  and checkpoint ensure tickets are never dropped.
- **Provider-Agnostic:** Works with any CLI-based LLM provider. Ships with support
  for Claude, Codex, and agy (Gemini). Extend via config.

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/dev-bricks/ticket-master.git
cd ticket-master

# 2. Copy and edit the config
cp config/ticket-master.config.example.json config/ticket-master.config.json
# -> Edit config/ticket-master.config.json:
#    - Add your project directories to project_roots[]
#    - Verify provider commands match your installed CLIs

# 3. Launch (default: Claude)
./bin/ticket-master.sh               # Unix/macOS
.\bin\ticket-master.bat              # Windows CMD
.\bin\ticket-master.ps1              # Windows PowerShell
```

The agent reads the prompt file for the selected language
(`prompts/TICKET-MASTER.<lang>.md`, default English), orients itself on your
projects, and goes to **Position 0** — waiting silently for your first ticket.

### Prompt Language

The agent prompt ships in two fully equivalent versions:

- `prompts/TICKET-MASTER.en.md` (English, default)
- `prompts/TICKET-MASTER.de.md` (German)

Select the language with the `TM_LANG` environment variable; the starters load
`prompts/TICKET-MASTER.${TM_LANG}.md` and fall back to English with a warning if
the requested file is missing. The config field `default_language` documents the
intended default.

```bash
TM_LANG=de ./bin/ticket-master.sh        # German prompt
TM_LANG=en ./bin/ticket-master.sh        # English prompt (default)
```

```powershell
$env:TM_LANG = "de"; .\bin\ticket-master.ps1
```

---

## Starter Matrix

| OS | Provider | Command |
|----|----------|---------|
| Unix / macOS | Claude | `./bin/start-claude.sh` or `./bin/ticket-master.sh --provider claude` |
| Unix / macOS | Codex | `./bin/start-codex.sh` or `./bin/ticket-master.sh --provider codex` |
| Unix / macOS | agy (Gemini) | `./bin/start-agy.sh` or `./bin/ticket-master.sh --provider agy` |
| Windows CMD | Claude | `bin\start-claude.bat` or `bin\ticket-master.bat --provider claude` |
| Windows CMD | Codex | `bin\start-codex.bat` or `bin\ticket-master.bat --provider codex` |
| Windows CMD | agy (Gemini) | `bin\start-agy.bat` or `bin\ticket-master.bat --provider agy` |
| Windows PowerShell | Claude | `.\bin\ticket-master.ps1 -Provider claude` |
| Windows PowerShell | Codex | `.\bin\ticket-master.ps1 -Provider codex` |
| Windows PowerShell | agy (Gemini) | `.\bin\ticket-master.ps1 -Provider agy` |

### Environment Variables

| Variable | Default | Effect |
|----------|---------|--------|
| `TM_PROVIDER` | `claude` | Override provider without a flag |
| `TM_LANG` | `en` | Prompt language; loads `prompts/TICKET-MASTER.${TM_LANG}.md` (falls back to `en`) |
| `TM_SKIP_PERMISSIONS` | `0` | Set to `1` to pass `--dangerously-skip-permissions` to Claude |

---

## Configuration

Copy `config/ticket-master.config.example.json` to
`config/ticket-master.config.json` (the real config is gitignored).

### Key Fields

| Field | Description |
|-------|-------------|
| `tickets_dir` | Where ticket files live (default: `./tickets`) |
| `prompts_dir` | Where prompt files live (default: `./prompts`) |
| `default_language` | Documented default prompt language (`en`/`de`); runtime override via `TM_LANG` |
| `project_roots[]` | **Your projects** — add name, path, pipeline for each |
| `providers.claude` | Claude CLI config (`command`, `default_model`, `args`) |
| `providers.codex` | Codex CLI config |
| `providers.agy` | Gemini CLI config |
| `default_provider` | Provider used when none is specified |
| `advisor.enabled` | Enable advisor model for high-stakes tickets (score ≥ 35) |
| `advisor.threshold_score` | Score at which advisor is recommended |
| `score_thresholds` | Tier boundary scores (tier1\_max, tier2\_max, etc.) |

### Example `project_roots` Entry

```json
{
  "name": "my-app",
  "path": "/home/user/projects/my-app",
  "pipeline": "software"
}
```

---

## How Routing Works

### Score Formula

```
SCORE = (10 - CLARITY) + COMPLEXITY + CREATIVITY + CONTEXT + CRITICALITY
```

Each dimension is 0–10. Total range: 0–50.

| Score Range | Tier | Typical Use |
|-------------|------|-------------|
| 0–8 | Tier 1 | Fast / cheap — boilerplate, formatting, trivial fixes |
| 9–12 | Tier 2 | Capable chat — standard bugs, documentation |
| 13–28 | Tier 3 | Capable coder / researcher — complex bugs, code review |
| 29–50 | Tier 4 | Architect / reviewer — design, proofs, high-stakes changes |

At score ≥ 35, an advisor model is recommended.

### Ticket Lifecycle

```
tickets/               <- open tickets (one .txt file each)
tickets/QUEUED/        <- handed to a provider, awaiting result
tickets/PENDING/       <- moved to project task management
tickets/.USER/         <- requires user-launched model / manual step
tickets/SOLVED/        <- resolved and empirically confirmed
tickets/INTAKE-TRIAGE-LOG.txt  <- one-line audit trail for every ticket
```

Trivial tickets that are resolved immediately do not need a `.txt` file — a
single line in `INTAKE-TRIAGE-LOG.txt` suffices.

### Companion Pattern

For a series of related tickets, the master spawns one **companion sub-agent**
and reuses it via `SendMessage`. The companion orients itself once (reads
project files, learns conventions) and then processes subsequent tickets without
re-paying that cost. The master rotates the companion when the domain changes
significantly or when its context grows large.

### Fallback Chain

```
Candidate 1
    | fail
    v
Candidate 2
    | fail
    v
Candidate 3
    | fail
    v
CHECKPOINT ALPHA:
    1. Async delegation (sync folder / cron)
    2. Project task management (-> PENDING)
    3. User handoff (-> .USER)
```

---

## Requirements

- A CLI-based LLM provider (at least one of: `claude`, `codex`, `agy`)
- Python 3.10+ (for tests only; the router itself runs inside the LLM session)
- No additional Python dependencies

### Provider Installation

| Provider | Install |
|----------|---------|
| Claude CLI | `npm install -g @anthropic-ai/claude-code` |
| Codex CLI | `npm install -g @openai/codex` |
| agy (Gemini) | See [antigravity docs](https://github.com/google-labs-git/agy) |

---

## Running the Smoke Tests

```bash
python tests/test_smoke.py
```

Checks: directory structure complete, config JSON valid, prompt contains no
forbidden absolute paths or system-specific terms.

---

## License

MIT License — Copyright (c) 2026 Lukas Geiger. See [LICENSE](LICENSE).

## Author

Lukas Geiger ([github.com/lukisch](https://github.com/lukisch))
