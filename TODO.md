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
- [x] **Phase 2 — Dringlichkeitsachse:** `config/urgency.json` (Schema:
      `config/urgency.example.json`) — Domäne→Frist-Default-Matrix
      (`sofort|heute|woche|backlog`), entkoppelt vom 5-Dim-Komplexitäts-Score.
      Neues URGENCY-GATE in beiden Prompts (EN/DE) direkt nach GATE 1:
      Domain-Default lesen, Eskalationsregeln prüfen (veröffentlichte Software
      + schwerer Bug → sofort, ggf. nur Diagnose-Subagent zuerst;
      Trigger-Keywords → sofort), optionaler `preference_model_hint.command`
      bei echten Grenzfällen, niedrige Konfidenz → User fragen
      (`low_confidence_policy`). `woche`/`backlog` → optionale
      `task_db_command`-Senke statt Subagent-Spawn.
- [x] **Phase 3 — Delegations-Verdrahtung:** Intake-GATE (GATE 1) um
      DOMAIN/ENDPOINT erweitert (Lookup: `domains.json` →
      `controlcenter_find_skill`/skill-finder → generischer Fallback).
      Modellwahl bevorzugt optionalen `router_command` vor der
      Score→Tier-Formel, die zum expliziten Fallback degradiert (Duplikat
      bewusst NICHT entfernt — bleibt Fallback-Pfad). Neuer
      Rechteprüfungs-Schritt vor jedem Worker-Spawn in Abschnitt (B):
      `LOCK*.txt`/`LOCK.permissions.json`-Konventionen (deny>ask>allow,
      User-Locks absolut). Neue Template-Felder `DOMAIN`/`ENDPOINT`/`URGENCY`,
      neue Config-Felder `router_command`/`task_db_command`. Details:
      CHANGELOG 1.7.0. Rückangleichung an die private `_TICKETS`-Instanz
      (Prompt `_control-center/_prompts/TICKET-MASTER.txt`, Template
      `_control-center/_TICKETS/_templates/TICKET.txt`) erledigt.
- [x] **Phase 3 Follow-up (1.8.0) — Stage-2-Fuzzy-Matching:** Empirischer
      Befund (psycho-berater governs 19x `skill:therapy:*`, ohne
      Provenance-Link; lokale Skills wie `counseling-basics` fehlen in der
      Registry) zeigte: strikte 1:1-Provenance (Stage 1) reicht nicht, ein
      Experte kann eine ganze Skill-FAMILIE regieren. `fuzzy_match_skills()`
      + `KEYWORD_CATEGORY_HINTS` (nur gegen den Expertennamen, NICHT die
      geteilte Boss-Beschreibung — sonst Bleed-Over auf Geschwister-Experten,
      empirisch beobachtet) + optionaler zweiter Skill-Bestand
      (`load_extra_skills()` / `--extra-skills-dir`). Ergebnis:
      `"status": "teilportiert"` + `"match": "fuzzy"` +
      `"matched_skills"`-Liste (Stage-1-Treffer bleiben `"portiert"`/
      `"exact"`). Bereits stage-1-vergebene Skills werden für Geschwister-
      Experten aus dem Fuzzy-Pool ausgeschlossen. Beide Prompts (EN/DE) +
      private Instanz präzisiert: keine Experten-Ebene, GATEs lesen
      `standalone_skill`/`matched_skills` direkt, Worker bekommt bei
      `teilportiert` ALLE gelisteten Skills; optionale (harness-abhängige)
      Worker-Rollen-Wahl generisch im Modul, konkret (Claude-Code-
      Subagenten) in der privaten Instanz. Tests: 9 neue (32/32 gesamt).
- [x] **Phase 4 (1.9.0) — Wissens-Schicht:** User-Leitsatz: Was den
      Ticket-Master zum persönlichen Assistenten macht, ist WISSEN über das
      System (wo was ist, Routing, MCP-Server, Subsysteme) — nicht nur
      Routing-Logik. `config/knowledge.json` (Schema:
      `config/knowledge.example.json`) mit `knowledge_sources` in 4
      Kategorien (`maps`/`state`/`capabilities`/`user_model`, je
      `{id, kind: file|command|mcp_tool, target, when_to_read}`). Neuer
      optionaler Boot-Schritt „(c3) SYSTEM-WISSEN laden" in beiden Prompts
      (EN/DE) direkt vor Position 0: `maps` beim Boot laden, `state` vor
      JEDER Routing-Entscheidung neu prüfen (nicht nur beim Boot),
      `capabilities` bei Endpunkt-/Modell-Lookup, `user_model` nur bei
      echten Grenzfällen. Grundregel: generierten Karten vertrauen, nicht
      dem Gedächtnis — bei Widerspruch Karte neu generieren lassen.
      Feldnamen bewusst englisch (`when_to_read`), konsistent mit den
      anderen Config-Beispielen des Moduls. Rückangleichung: private
      Instanz bekam eine konkrete SYSTEM-WISSEN-Sektion im Prompt (statt
      einer separaten JSON — passend zum bestehenden Muster dieser
      prosa-basierten Instanz) mit realen Pfaden/Kommandos (MANIFEST.md,
      domains.json, releases.json+MASTER-REGISTRY.md, repos.json+
      REPOS-INDEX.md, lock_watcher, _TICKETS, Rinnsal, controlcenter_*,
      clutch, tom-lm).
- [x] **Advisor-Review + Abschluss-Retest-Fixes (weiterhin 1.9.0):**
      Advisor-Auflagen (PFLICHT): `_tokenize()` auf Unicode-fähige Regex
      umgestellt (Umlaute/ß wurden vorher still zerschnitten); Exact-Match-
      Exklusion Stage1→Stage2 GLOBAL statt nur pro Boss geführt (Wahl,
      dokumentiert). Retest-Befunde B2–B6 (frischer Agent, beide
      User-Beispiele "bestanden mit Befunden"): B2 GATE1-Projektanker über
      Repo-/System-Inventar-`maps`-Quelle für Projekte außerhalb
      `project_roots[]`; B3 projekteigene Pflicht-Lektüre-Ketten liest der
      WORKER, nicht der Master (Lean-Router); B4 GATE3-Nutzungslimit auf
      Best-Effort-Selbsteinschätzung abgeschwächt (keine verlässliche
      Quelle); B5 Präzedenzregel für Dringlichkeits-Kollision (Keyword=WANN,
      Diagnose-zuerst=WAS → zusammen: sofort Diagnose-Subagent); B6
      Werkzeug-Hinweis gegen Glob-Timeouts über große/cloud-synchronisierte
      Ordner. B1 kein Fix nötig (erwartetes GAP-Design). Tests: 7 neu
      (39/39 gesamt).

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
