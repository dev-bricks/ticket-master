# -*- coding: utf-8 -*-
"""Verifikation der zurueckgespiegelten Python-Helfer im ticket-master-Modul:
ticket_writer (asynchrone Ticket-Erzeugung) + doc_scanner (TODO/AUFGABEN/DONE/DECISIONS)."""
import sys
import tempfile
import unittest
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parent.parent / "lib"
sys.path.insert(0, str(LIB_DIR))

import ticket_writer  # noqa: E402
import doc_scanner  # noqa: E402


class TestTicketWriter(unittest.TestCase):
    def test_requires_tickets_dir(self):
        with self.assertRaises(ValueError):
            ticket_writer.create("t", "b", today="2026-06-27")  # kein tickets_dir/env

    def test_creates_unclaimed_ticket(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = ticket_writer.create("Titel", "Body", project="proj",
                                        tickets_dir=Path(tmp), today="2026-06-27")
            p = Path(path)
            self.assertEqual(p.name, "T-20260627-01.txt")
            self.assertEqual(p.parent.name, "QUEUED")
            self.assertIn("Titel", p.read_text(encoding="utf-8"))


class TestDocScanner(unittest.TestCase):
    def test_scan_and_ensure(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "TODO.md").write_text("# TODO\n", encoding="utf-8")
            res = doc_scanner.scan_docs(d)
            self.assertTrue(res["todo"]["exists"])
            self.assertFalse(res["decisions"]["exists"])
            path = doc_scanner.ensure_doc(d, "decisions")
            self.assertIn("ADR", Path(path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
