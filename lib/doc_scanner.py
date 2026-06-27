r"""
doc_scanner.py — Scannt/erstellt/ergaenzt Standard-Steuerdateien in Projekten.

Erkennt die vier Standard-Dokumente eines Projekt-/Ticketordners und kann
fehlende anlegen oder Eintraege anhaengen (ohne kuratierten Bestand zu loeschen):

  TODO.md       — aktive, in Arbeit befindliche Aufgaben
  AUFGABEN.txt  — Aufgabenliste (Research/Software-Konvention)
  DONE.md       — erledigte Aufgaben
  DECISIONS.md  — Architektur-/Projektentscheidungen (ADR-Format)

Nutzerneutral: keine festen Pfade; arbeitet auf einem uebergebenen Projektordner.
Vorgesehen fuer den Lock-Watcher (GUI je Raum) und fuer die Rueckspiegelung nach
ticket-master.
"""

from __future__ import annotations

from pathlib import Path

# kind -> (kanonischer Dateiname, akzeptierte Namensvarianten)
DOC_KINDS = {
    "todo": ("TODO.md", ("TODO.md", "todo.md", "Todo.md")),
    "aufgaben": ("AUFGABEN.txt", ("AUFGABEN.txt", "aufgaben.txt", "AUFGABEN.md", "aufgaben.md")),
    "done": ("DONE.md", ("DONE.md", "done.md", "Done.md")),
    "decisions": ("DECISIONS.md", ("DECISIONS.md", "decisions.md", "Decisions.md")),
}

_TEMPLATES = {
    "todo": "# TODO\n\n> Aktive, in Arbeit befindliche Aufgaben.\n\n",
    "aufgaben": "AUFGABEN\n========\n\n",
    "done": "# DONE\n\n> Erledigte Aufgaben.\n\n",
    "decisions": (
        "# DECISIONS (ADR)\n\n"
        "> Architektur-/Projektentscheidungen im ADR-Format.\n"
        "> Pro Eintrag: Kontext, Entscheidung, Konsequenzen.\n\n"
    ),
}


def _find_existing(root: Path, kind: str) -> Path | None:
    # Verzeichnis scannen statt Pfade konstruieren -> liefert den ECHTEN Namen
    # von der Platte (wichtig auf case-insensitiven Dateisystemen wie Windows).
    _canonical, variants = DOC_KINDS[kind]
    variant_lower = {v.lower() for v in variants}
    try:
        for entry in sorted(root.iterdir()):
            if entry.is_file() and entry.name.lower() in variant_lower:
                return entry
    except OSError:
        pass
    return None


def scan_docs(root: Path) -> dict:
    """Liefert je kind {exists, path, lines}. path/lines sind None/0 wenn fehlend."""
    root = Path(root)
    out: dict[str, dict] = {}
    for kind in DOC_KINDS:
        existing = _find_existing(root, kind)
        if existing is None:
            out[kind] = {"exists": False, "path": None, "lines": 0}
        else:
            try:
                lines = len(existing.read_text(encoding="utf-8", errors="replace").splitlines())
            except OSError:
                lines = 0
            out[kind] = {"exists": True, "path": str(existing), "lines": lines}
    return out


def ensure_doc(root: Path, kind: str) -> str:
    """Stellt sicher, dass das Dokument existiert. Legt es bei Bedarf aus Template
    an; vorhandene Dateien werden NICHT ueberschrieben. Returns den Pfad."""
    if kind not in DOC_KINDS:
        raise ValueError(f"Unbekannter kind: {kind}")
    root = Path(root)
    existing = _find_existing(root, kind)
    if existing is not None:
        return str(existing)
    canonical, _variants = DOC_KINDS[kind]
    target = root / canonical
    target.write_text(_TEMPLATES[kind], encoding="utf-8")
    return str(target)


def append_entry(path: Path, text: str) -> None:
    """Haengt einen Eintrag an, ohne bestehenden Inhalt zu veraendern."""
    path = Path(path)
    existing = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    if existing and not existing.endswith("\n"):
        existing += "\n"
    path.write_text(existing + text.rstrip("\n") + "\n", encoding="utf-8")
