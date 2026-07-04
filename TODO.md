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
- [x] **(Folge, Design — entschieden [U 2026-07-04 „immer verbesserungen
      rückangleichen"], umgesetzt in v1.5.0)** Angleichung an die private
      `_TICKETS`-Instanz: Sammel-Logdatei deprecated, Audit-Trail PRO Ticket
      (Prompts, READMEs, SKILL, llms.txt, Config, Log-Stub). Im Gegenzug die
      v1.4.1-Lib-Fixes (exklusives Anlegen, Lifecycle-IDs, striktes UTF-8)
      in die private laufende Instanz `_scripts/ticket_writer.py` +
      `_scripts/doc_scanner.py` gespiegelt (Lock-Watcher-Tests 8/8 grün).

## Personal-Assistant-Ausbau (entschieden [U 2026-07-04, Decision-Briefing E02/A])

> Ticket-Master wird zum persönlichen Live-Assistenten ausgebaut: er erkennt
> Nutzer-Usecases, bewertet Dringlichkeit (sofort vs. später) und delegiert an
> Skills/Module/Modelle. Umsetzungs-Ticket (privat, mit Systemdetails):
> `_control-center/_TICKETS/T-20260704-02.txt`.

- [x] **Phase 1 — Domänen-Map (generiert):** `lib/domains_generator.py` liest
      die Boss-Agent-Frontmatter (`orchestrates.experts`) und gleicht sie
      gegen eine Skill-Registry-`components.json` (`provenance.origin: bach`,
      `origin_path`) ab → `config/domains.json` (gitignored, generiert;
      Schema/Beispiel in `config/domains.example.json`). Nicht portierte
      Experten werden als `"status": "nicht-portiert"` markiert. Die
      5. Domäne (Versicherung/Finanzen) wird per Namens-/Beschreibungssuche
      gefunden, da ihr Ordnername variieren kann. Zur Laufzeit ist
      `domains.json` BACH-frei — BACH ist nur Generator-Input, kein
      Runtime-Dependency. Tests: `tests/test_domains_generator.py` (12 Fälle).
- [ ] **Phase 2 — Dringlichkeitsachse:** sofort/später entkoppelt vom
      Komplexitäts-Score; Domäne→Frist-Default-Matrix + Nutzer-Präferenzmodell
      (TOM-lm-Hook; niedrige Konfidenz → eskalieren statt raten).
- [ ] **Phase 3 — Delegations-Verdrahtung:** Intake-GATE um DOMAENE/ENDPUNKT
      erweitern; Endpunkte = Standalone-Skills/Module (Lookup via Skill-Registry /
      `controlcenter_find_skill` / skill-finder); Modellwahl an clutch delegieren
      (ersetzt die im Prompt duplizierte Score→Tier-Logik); Rechteprüfung
      (lock-master) vor Delegation; Task-DB (Rinnsal) als „später"-Senke.

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
