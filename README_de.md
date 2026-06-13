<p align="center"><img src="assets/logo.svg" alt="ticket-master" width="160"></p>

# ticket-master

Ein plattformübergreifender, multi-provider **Ticket-Router-Agent** für Softwareprojekte.

ticket-master hält eine Agenten-Session offen und agiert als schlanker, langlebiger
Router: Wenn du einen Bug, einen Änderungswunsch oder ein Projektproblem meldest,
nimmt er das als strukturiertes Ticket auf, bewertet es, wählt den passenden
KI-Provider und delegiert die Aufgabe — oder leitet sie ins projekteigene
Task-Management weiter, wenn Delegation nicht sinnvoll ist.

[![Lizenz: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)](VERSION)

---

🇬🇧 [English documentation → README.md](README.md)

---

## Was es tut

```
Du meldest einen Bug oder Änderungswunsch
        |
        v
[A] Intake — Ticket-Datei anlegen, Projekt zuordnen (GATE1)
        |
        v
[2-5] Charakteristik → Score → Provider-Abgleich → 3 Kandidaten (GATE2)
        |
        v
[B] Delegation an besten verfügbaren Provider (GATE4 + Fallback-Kette)
        |
   oder v
[C] Ins projektspezifische Task-Management einpflegen
        |
        v
Position 0 — Wartet auf das nächste Ticket
```

### Kernprinzipien

- **Lean Router:** Der Master-Agent bleibt schlank. Ausführung wird delegiert;
  Subagenten melden kompakt zurück (Commit-Hash + eine Zeile).
- **Companion-Muster:** Für eine Ticket-Serie im gleichen Bereich wird ein
  Companion-Subagent einmal gespawnt und wiederverwendet.
- **Score-basiertes Routing:** Jedes Ticket wird auf fünf Dimensionen bewertet
  (Klarheit, Komplexität, Kreativität, Kontext, Kritikalität), um den
  benötigten Provider-Tier zu bestimmen.
- **Graceful Fallback:** Wenn der bevorzugte Provider nicht verfügbar ist,
  stellt eine Fallback-Kette sicher, dass kein Ticket verloren geht.
- **Provider-agnostisch:** Funktioniert mit jedem CLI-basierten LLM-Provider.
  Mitgeliefert: Claude, Codex und agy (Gemini). Erweiterbar per Config.

---

## Schnellstart

```bash
# 1. Repository klonen
git clone https://github.com/dev-bricks/ticket-master.git
cd ticket-master

# 2. Config kopieren und anpassen
cp config/ticket-master.config.example.json config/ticket-master.config.json
# -> config/ticket-master.config.json bearbeiten:
#    - Eigene Projektordner in project_roots[] eintragen
#    - Provider-Befehle prüfen (stimmen sie mit den installierten CLIs überein?)

# 3. Starten (Standard: Claude)
./bin/ticket-master.sh               # Unix/macOS
.\bin\ticket-master.bat              # Windows CMD
.\bin\ticket-master.ps1              # Windows PowerShell
```

Der Agent liest die Prompt-Datei der gewählten Sprache
(`prompts/TICKET-MASTER.<lang>.md`, Standard Englisch), orientiert sich an deinen
Projekten und geht auf **Position 0** — wartet still auf dein erstes Ticket.

### Prompt-Sprache

Der Agenten-Prompt liegt in zwei vollwertigen, inhaltsgleichen Versionen vor:

- `prompts/TICKET-MASTER.en.md` (Englisch, Standard)
- `prompts/TICKET-MASTER.de.md` (Deutsch)

Die Sprache wird über die Umgebungsvariable `TM_LANG` gewählt; die Starter laden
`prompts/TICKET-MASTER.${TM_LANG}.md` und fallen mit einer Warnung auf Englisch
zurück, falls die angeforderte Datei fehlt. Das Config-Feld `default_language`
dokumentiert den vorgesehenen Standard.

```bash
TM_LANG=de ./bin/ticket-master.sh        # Deutscher Prompt
TM_LANG=en ./bin/ticket-master.sh        # Englischer Prompt (Standard)
```

```powershell
$env:TM_LANG = "de"; .\bin\ticket-master.ps1
```

---

## Starter-Matrix

| Betriebssystem | Provider | Befehl |
|----------------|----------|--------|
| Unix / macOS | Claude | `./bin/start-claude.sh` |
| Unix / macOS | Codex | `./bin/start-codex.sh` |
| Unix / macOS | agy (Gemini) | `./bin/start-agy.sh` |
| Windows CMD | Claude | `bin\start-claude.bat` |
| Windows CMD | Codex | `bin\start-codex.bat` |
| Windows CMD | agy (Gemini) | `bin\start-agy.bat` |
| Windows PowerShell | Claude | `.\bin\ticket-master.ps1 -Provider claude` |
| Windows PowerShell | Codex | `.\bin\ticket-master.ps1 -Provider codex` |
| Windows PowerShell | agy (Gemini) | `.\bin\ticket-master.ps1 -Provider agy` |

### Umgebungsvariablen

| Variable | Standard | Wirkung |
|----------|----------|---------|
| `TM_PROVIDER` | `claude` | Provider ohne Flag überschreiben |
| `TM_LANG` | `en` | Prompt-Sprache; lädt `prompts/TICKET-MASTER.${TM_LANG}.md` (Fallback `en`) |
| `TM_SKIP_PERMISSIONS` | `0` | Auf `1` setzen, um `--dangerously-skip-permissions` an Claude zu übergeben |

---

## Konfiguration

`config/ticket-master.config.example.json` nach
`config/ticket-master.config.json` kopieren (die echte Config ist per
`.gitignore` ausgeschlossen).

### Wichtige Felder

| Feld | Beschreibung |
|------|--------------|
| `tickets_dir` | Wo Ticket-Dateien liegen (Standard: `./tickets`) |
| `default_language` | Dokumentierte Standard-Promptsprache (`en`/`de`); Laufzeit-Override via `TM_LANG` |
| `project_roots[]` | **Deine Projekte** — Name, Pfad und Pipeline für jeden Eintrag |
| `providers.claude` | Claude-CLI-Konfiguration |
| `providers.codex` | Codex-CLI-Konfiguration |
| `providers.agy` | Gemini-CLI-Konfiguration |
| `advisor.enabled` | Advisor-Modell für kritische Tickets (Score ≥ 35) aktivieren |

---

## Wie das Routing funktioniert

### Score-Formel

```
SCORE = (10 - KLARHEIT) + KOMPLEXITÄT + KREATIVITÄT + KONTEXT + KRITIKALITÄT
```

Jede Dimension: 0–10. Gesamt: 0–50.

| Score | Tier | Typischer Einsatz |
|-------|------|-------------------|
| 0–8 | Tier 1 | Schnell/günstig — Boilerplate, Formatierung |
| 9–12 | Tier 2 | Standardfähig — Bugs, Dokumentation |
| 13–28 | Tier 3 | Fähiger Coder/Researcher — komplexe Bugs, Code-Review |
| 29–50 | Tier 4 | Architekt/Reviewer — Design, Beweise, kritische Änderungen |

---

## Ticket-Lebenszyklus

```
tickets/               <- offene Tickets (je eine .txt-Datei)
tickets/QUEUED/        <- an Provider übergeben, Ergebnis ausstehend
tickets/PENDING/       <- ins projekteigene Task-Management überführt
tickets/.USER/         <- erfordert manuell gestartetes Modell/User-Aktion
tickets/SOLVED/        <- gelöst und empirisch bestätigt
tickets/INTAKE-TRIAGE-LOG.txt  <- eine Zeile Audit-Trail pro Ticket
```

Triviale Tickets, die sofort erledigt werden, brauchen keine `.txt`-Datei —
eine Zeile im `INTAKE-TRIAGE-LOG.txt` genügt.

---

## Voraussetzungen

- Mindestens ein CLI-basierter LLM-Provider (`claude`, `codex` oder `agy`)
- Python 3.10+ (nur für Tests; der Router selbst läuft in der LLM-Session)

---

## Smoke-Tests ausführen

```bash
python tests/test_smoke.py
```

Prüft: Verzeichnisstruktur vollständig, Config-JSON valide, Prompt enthält
keine verbotenen absoluten Pfade oder systemspezifischen Begriffe.

---

## Lizenz

MIT License — Copyright (c) 2026 Lukas Geiger. Siehe [LICENSE](LICENSE).

## Autor

Lukas Geiger ([github.com/lukisch](https://github.com/lukisch))
