# TODO — ticket-master

## Review 2026-07-04 (Modul-Review-Loop, frischer Subagent — Funde gefixt in v1.4.1)

- [x] **(hoch)** `ticket_writer.create()` konnte Tickets still überschreiben
      (nicht-exklusives `write_text`) → exklusives Anlegen + Retry.
- [x] **(hoch)** ID-Vergabe scannte nur `QUEUED/` → doppelte IDs bei
      verschobenen Tickets; jetzt alle Lebenszyklus-Ordner.
- [x] **(hoch)** `doc_scanner.append_entry()` korrumpierte nicht-UTF-8-Bestand
      (errors="replace" + Rückschreiben) → strikt lesen, ValueError.
- [x] **(hoch)** `test_smoke.py` unter pytest wirkungslos (return statt assert)
      + verwaiste Pfade auf vor-1.3.0-Log-Speicherort (Test schlug bei
      `python tests/test_smoke.py` real fehl).
- [x] **(mittel/niedrig)** `prompts_dir` als reserved dokumentiert;
      SECURITY-Versionsmatrix, Badges, `.gitignore` (`_logs/`-Pfade, LOCK*.txt).
- [ ] **(Folge)** `prompts_dir` in den `bin/`-Launchern tatsächlich auswerten
      (oder Feld aus dem Config-Beispiel entfernen).
- [ ] **(Folge, Design)** Angleichung an die private `_TICKETS`-Instanz prüfen:
      dort ist die Sammel-Logdatei INTAKE-TRIAGE-LOG deprecated (Multi-System-
      OneDrive-Kollisionen) zugunsten Audit-Trail PRO Ticket — entscheiden, ob
      das public Modul dieselbe Konvention übernehmen soll.

## Roadmap

- [ ] **i18n:** Standardsprachen über DE/EN hinaus erweitern — dem Muster der
      ellmos-MCP-Server folgen (`set_language`-Mechanik, `README_de` + weitere
      Sprachdateien). Geplant: weitere `prompts/TICKET-MASTER.<lang>.md`
      (z.B. `es`, `fr`) + Sprachauswahl bereits vorbereitet
      (`TM_LANG`/`default_language`).

## Near-term

- [ ] Python helper script (`bin/ticket_master.py`) as a thin wrapper that reads
      `config/ticket-master.config.json` and dispatches to the correct provider
      without shell-specific scripts — easier cross-platform maintenance.
- [ ] `--list` mode: print open tickets from `tickets/` to stdout.
- [ ] `--intake "description"` flag: pre-create a ticket file from the command line
      before launching the agent session.
- [ ] Config validation on startup: warn if `project_roots` is empty or provider
      commands are not found in PATH.

## Medium-term

- [ ] Optional TUI dashboard (curses or textual) showing ticket counts per
      lifecycle state.
- [ ] GitHub Issues bridge: pull open issues from a repo into `tickets/` as `.txt`
      files automatically.
- [ ] Webhook receiver: accept tickets via HTTP POST (e.g. from n8n or a CI system).
- [ ] pytest integration: convert `tests/test_smoke.py` to proper pytest suite.

## Long-term / Ideas

- [ ] Multi-repo support: manage tickets across several Git repositories from one
      ticket-master instance.
- [ ] Automatic companion rotation based on context-token watermarks.
- [ ] Web UI for ticket overview and manual routing overrides.
