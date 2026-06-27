r"""
ticket_writer.py — Asynchronous ticket creation for the ticket-master queue.

Lets any tool (e.g. a lock watcher GUI) drop a ticket into the queue even when
no TICKET-MASTER session is running. Writes an unclaimed ticket file
T-YYYYMMDD-NN.txt (no <HOST> suffix) into <tickets_dir>/QUEUED/ using the
canonical TICKET format (fields ID/TITLE/STATUS/.../LOG/SOLUTION).

User-neutral module: `tickets_dir` is required (or taken from the
TICKET_MASTER_TICKETS_DIR environment variable / config). The current date is
injectable (today=) for deterministic tests/automation. This is the canonical
home of the helper; the running instance lives in the user's _scripts/ mirror.
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path


def _default_tickets_dir() -> Path | None:
    env = os.environ.get("TICKET_MASTER_TICKETS_DIR")
    return Path(env) if env else None

_TICKET_TEMPLATE = """\
==============================================================
TICKET
==============================================================
ID:            {ticket_id}
TITEL:         {title}
ERSTELLT:      {date}
STATUS:        QUEUED
PRIORITAET:    {priority}

--------------------------------------------------------------
PROJEKT-ZUORDNUNG
--------------------------------------------------------------
PIPELINE:      {pipeline}
PROJEKTORDNER: {project}
FUEHRUNGSDATEI:<noch offen — beim Triage bestaetigen>

--------------------------------------------------------------
PROBLEMBESCHREIBUNG
--------------------------------------------------------------
{body}

--------------------------------------------------------------
AUFGABENCHARAKTERISTIK  (Bearbeitungskette Schritt 2-3)
--------------------------------------------------------------
TYP:           <Bug / Feature / Doku / Recherche / Review / Refactor>
ANFORDERUNGEN: <Klarheit, Komplexitaet, Kreativitaet, Kontext, Kritikalitaet>
SCORE:         <0-50>

--------------------------------------------------------------
MODELL-ROUTING  (Bearbeitungskette Schritt 4-5)
--------------------------------------------------------------
KANDIDAT 1:    <Modell + Aufrufweg>     [LLM-startbar: ja/nein]
KANDIDAT 2:    <Modell + Aufrufweg>     [LLM-startbar: ja/nein]
KANDIDAT 3:    <Modell + Aufrufweg>     [LLM-startbar: ja/nein]
GEWAEHLT:      <Kandidat + Begruendung>

--------------------------------------------------------------
AUFTRAG / PROMPT
--------------------------------------------------------------
<Konkreter Arbeitsauftrag inkl. Projekt-Routing + zu lesende Root-Doks.>

--------------------------------------------------------------
VERLAUF / LOG
--------------------------------------------------------------
{date}  Aufgenommen (asynchron via Lock-Watcher-GUI / ticket_writer).

--------------------------------------------------------------
LOESUNG / ERGEBNIS
--------------------------------------------------------------
<Vor Verschieben nach SOLVED ausfuellen.>
==============================================================
"""


def _next_number(queued_dir: Path, datestr: str) -> int:
    """Naechste freie laufende Nummer fuer ein Datum (beruecksichtigt claimed
    Tickets T-DATE-NN.<HOST>.txt und unclaimed T-DATE-NN.txt)."""
    pattern = re.compile(rf"^T-{datestr}-(\d+)(?:\.[A-Za-z0-9_-]+)?\.txt$")
    highest = 0
    if queued_dir.is_dir():
        for entry in queued_dir.iterdir():
            m = pattern.match(entry.name)
            if m:
                highest = max(highest, int(m.group(1)))
    return highest + 1


def create(title: str, body: str, project: str | None = None, priority: str = "mittel",
           pipeline: str = "<offen>", tickets_dir: Path | None = None,
           today: str | None = None) -> str:
    """Erzeugt ein unclaimed Ticket in <tickets_dir>/QUEUED/. Returns den Pfad.

    tickets_dir ist erforderlich (oder via TICKET_MASTER_TICKETS_DIR gesetzt)."""
    base = Path(tickets_dir) if tickets_dir else _default_tickets_dir()
    if base is None:
        raise ValueError(
            "tickets_dir required (pass it or set TICKET_MASTER_TICKETS_DIR).")
    queued = base / "QUEUED"
    queued.mkdir(parents=True, exist_ok=True)

    date_iso = today or datetime.now().strftime("%Y-%m-%d")
    datestr = date_iso.replace("-", "")
    number = _next_number(queued, datestr)
    ticket_id = f"T-{datestr}-{number:02d}"
    target = queued / f"{ticket_id}.txt"

    content = _TICKET_TEMPLATE.format(
        ticket_id=ticket_id, title=title.strip() or "<ohne Titel>", date=date_iso,
        priority=priority, pipeline=pipeline, project=project or "<offen>",
        body=body.strip() or "<keine Beschreibung>",
    )
    target.write_text(content, encoding="utf-8")
    return str(target)
