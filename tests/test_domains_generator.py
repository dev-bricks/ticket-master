# -*- coding: utf-8 -*-
"""Verifikation von lib/domains_generator.py (Phase 1, T-20260704-02): Parser
fuer BACH-Boss-Frontmatter + Abgleich gegen eine Skill-Registry components.json."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parent.parent / "lib"
sys.path.insert(0, str(LIB_DIR))

import domains_generator as dg  # noqa: E402


FIXTURE_BOSS_A = """---
name: fixture-boss-a
version: 1.0.0
type: boss-agent
status: active

orchestrates:
  experts: [fixture-expert-one, fixture-expert-two]
  services: []

description: >
  Fixture boss agent. Use this skill when: (1) doing thing one is needed,
  (2) doing thing two is needed, (3) doing thing three is needed.
---
# Fixture Boss A
"""

FIXTURE_BOSS_B_NO_LIST = """---
name: fixture-boss-b
version: 1.0.0
type: agent
status: active

orchestrates:
  experts: []
  services: []

description: >
  Fixture boss without a numbered usecase list, just prose.
---
"""


class TestParseFrontmatter(unittest.TestCase):
    def test_parses_experts_and_description(self):
        fm = dg.parse_frontmatter(FIXTURE_BOSS_A)
        self.assertEqual(fm["name"], "fixture-boss-a")
        self.assertEqual(fm["orchestrates"]["experts"], ["fixture-expert-one", "fixture-expert-two"])
        self.assertIn("doing thing one", fm["description"])

    def test_empty_experts_list(self):
        fm = dg.parse_frontmatter(FIXTURE_BOSS_B_NO_LIST)
        self.assertEqual(fm["orchestrates"]["experts"], [])

    def test_no_frontmatter_returns_empty(self):
        self.assertEqual(dg.parse_frontmatter("# just a heading\n"), {})


class TestExtractUsecases(unittest.TestCase):
    def test_splits_numbered_list(self):
        usecases = dg.extract_usecases(
            "Intro text: (1) doing thing one, (2) doing thing two, (3) doing thing three."
        )
        self.assertEqual(len(usecases), 3)
        self.assertIn("doing thing one", usecases[0])

    def test_falls_back_to_whole_description(self):
        usecases = dg.extract_usecases("Just a plain sentence without numbers.")
        self.assertEqual(usecases, ["Just a plain sentence without numbers."])

    def test_empty_description(self):
        self.assertEqual(dg.extract_usecases(""), [])


class TestMatchStandaloneSkill(unittest.TestCase):
    def _component(self, origin_path):
        return {"id": "skill:test:x", "provenance": {"origin": "bach", "origin_path": origin_path}}

    def test_matches_expert_agent_suffix_variant(self):
        # frontmatter lists "steuer-agent", the actual skill folder is "steuer"
        comps = [self._component("system/agents/_experts/steuer/CONCEPT.md")]
        match = dg.match_standalone_skill("steuer-agent", comps)
        self.assertIsNotNone(match)

    def test_matches_filename_stem(self):
        comps = [self._component("system/skills/workflows/foerderplaner.md")]
        match = dg.match_standalone_skill("foerderplaner", comps)
        self.assertIsNotNone(match)

    def test_no_match_returns_none(self):
        comps = [self._component("system/skills/therapie/psychoedukation.md")]
        match = dg.match_standalone_skill("gesundheitsverwalter", comps)
        self.assertIsNone(match)


class TestBuildDomains(unittest.TestCase):
    def test_build_domains_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            agents_dir = Path(tmp) / "agents"
            (agents_dir / "fixture-boss-a").mkdir(parents=True)
            (agents_dir / "fixture-boss-a" / "SKILL.md").write_text(FIXTURE_BOSS_A, encoding="utf-8")

            registry_path = Path(tmp) / "components.json"
            registry_path.write_text(json.dumps({
                "components": [
                    {
                        "id": "skill:test:fixture-expert-one",
                        "provenance": {"origin": "bach", "origin_path": "system/agents/_experts/fixture-expert-one/CONCEPT.md"},
                    }
                ]
            }), encoding="utf-8")

            result = dg.build_domains(agents_dir, registry_path, extra_boss_dirs=["fixture-boss-a"])
            self.assertEqual(result["schema"], "ticket-master-domains-v1")
            self.assertEqual(len(result["domains"]), 1)
            domain = result["domains"][0]
            self.assertEqual(domain["source_boss"], "fixture-boss-a")
            experts_by_name = {e["name"]: e for e in domain["experts"]}
            self.assertEqual(experts_by_name["fixture-expert-one"]["status"], "portiert")
            self.assertEqual(experts_by_name["fixture-expert-two"]["status"], "nicht-portiert")
            self.assertIsNone(experts_by_name["fixture-expert-two"]["standalone_skill"])

    def test_missing_agents_dir_raises(self):
        with self.assertRaises(FileNotFoundError):
            dg.build_domains(Path("/nonexistent/agents/dir/xyz"), None)

    def test_discovers_variable_named_insurance_dir(self):
        """5. Boss-Domaene kann einen abweichenden Ordnernamen haben (z.B.
        'versicherungs-agent' statt 'versicherungen') — wird per Namens-/
        Beschreibungssuche gefunden, nicht per fixem Pfad."""
        with tempfile.TemporaryDirectory() as tmp:
            agents_dir = Path(tmp) / "agents"
            odd_dir = agents_dir / "versicherungs-kram"
            odd_dir.mkdir(parents=True)
            (odd_dir / "SKILL.md").write_text("""---
name: versicherungs-agent
type: agent
orchestrates:
  experts: []
  services: []
description: >
  Dedicated agent for insurance and financial planning.
---
""", encoding="utf-8")
            found = dg.discover_boss_dirs(agents_dir)
            self.assertIn("versicherungs-kram", found)


if __name__ == "__main__":
    unittest.main()
