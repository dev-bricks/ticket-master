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


class TestTokenize(unittest.TestCase):
    """Advisor-review regression (T-20260704-02): `[a-zA-Z0-9]+` silently
    split German umlauts/ß out of a word ("Fördermittelberater" ->
    {"f", "rdermittelberater"}), quietly losing token-overlap matches for
    any non-ASCII expert/skill name."""

    def test_umlaut_o_stays_one_token(self):
        self.assertEqual(dg._tokenize("Fördermittelberater"), {"fördermittelberater"})

    def test_umlaut_u_stays_one_token(self):
        self.assertEqual(dg._tokenize("Gesundheitsprüfung"), {"gesundheitsprüfung"})

    def test_eszett_stays_one_token(self):
        self.assertEqual(dg._tokenize("Straße"), {"straße"})

    def test_digits_still_tokenize(self):
        self.assertEqual(dg._tokenize("gpt4 test"), {"gpt", "4", "test"})


class TestFuzzyMatchSkills(unittest.TestCase):
    """Stage-2 (fuzzy) matching, T-20260704-02 follow-up: covers the
    empirical case that motivated it -- an expert like "psycho-berater"
    governing a whole "therapy" skill family in the registry, where none of
    the individual components carry a per-component provenance link back to
    that expert (stage 1 finds nothing) and the registry entries have no
    descriptive text to token-match on, only a shared `category`."""

    def test_umlaut_name_token_overlap_match(self):
        """Regression: before the Unicode-aware tokenizer fix, this match
        was silently lost because "Fördermittelberater" tokenized to
        {"f", "rdermittelberater"} instead of one token."""
        components = [{
            "id": "skill:funding:foerdermittelberater-tool",
            "name": "Fördermittelberater-Tool",
            "description": "",
            "category": None,
        }]
        matches = dg.fuzzy_match_skills("Fördermittelberater", "Handles funding.", components)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["id"], "skill:funding:foerdermittelberater-tool")

    def _therapy_components(self):
        # Mirrors the real registry shape: category present, description
        # empty -- stage 1 (provenance) already ruled out for these, and
        # plain token overlap alone would not find them either.
        return [
            {"id": "skill:therapy:act-techniken", "name": "act-techniken", "description": "", "category": "therapy"},
            {"id": "skill:therapy:psychoedukation", "name": "psychoedukation", "description": "", "category": "therapy"},
        ]

    def test_category_hint_matches_whole_family(self):
        matches = dg.fuzzy_match_skills(
            "psycho-berater",
            "Coordinates health management and psychological counseling experts.",
            self._therapy_components(),
        )
        matched_ids = {m["id"] for m in matches}
        self.assertEqual(matched_ids, {"skill:therapy:act-techniken", "skill:therapy:psychoedukation"})

    def test_unrelated_expert_does_not_match_therapy_family(self):
        matches = dg.fuzzy_match_skills(
            "steuer-agent",
            "Handles tax filings and receipts.",
            self._therapy_components(),
        )
        self.assertEqual(matches, [])

    def test_token_overlap_on_shared_description_word(self):
        # No category hint here -- match must come from the shared,
        # sufficiently long token "counseling" between the boss description
        # and the component's own description (mirrors an extra-skills-dir
        # entry, which never carries a `category`).
        components = [{
            "id": "claude-skill:counseling-basics",
            "name": "counseling-basics",
            "description": "Fundamentals of therapeutic communication and counseling.",
            "category": None,
        }]
        matches = dg.fuzzy_match_skills(
            "psycho-berater",
            "Coordinates health management and psychological counseling experts.",
            components,
        )
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["id"], "claude-skill:counseling-basics")

    def test_generic_role_suffix_alone_does_not_cause_false_match(self):
        # "berater" alone (role suffix, stripped from name_tokens) must not
        # match a component just called "berater-tools" via name overlap.
        components = [{"id": "skill:other:berater-tools", "name": "berater-tools", "description": "", "category": "other"}]
        matches = dg.fuzzy_match_skills("foerderplaner", "Plans funding applications.", components)
        self.assertEqual(matches, [])

    # -- T-20260711-01: German compound words don't split on their own -----
    # ("haushaltsmanagement" is one token; the matching skill's name splits
    # on a hyphen into {"haushalt", "manager"}), so plain set-intersection
    # token overlap misses the match. `_compound_overlap()` bridges this via
    # length-guarded substring matching, scoped to the component's id/name
    # (not free-text description, to keep precision high).

    def test_compound_word_matches_hyphenated_skill_name(self):
        """Empirical case (T-20260711-01): expert "haushaltsmanagement" vs.
        real skill "haushalt-manager" -- exact token overlap finds nothing
        ({"haushaltsmanagement"} vs {"haushalt", "manager"}), the compound
        bridge must find it via the substantive "haushalt" fragment."""
        components = [{
            "id": "claude-skill:haushalt-manager",
            "name": "haushalt-manager",
            "description": "Unterstuetzt bei der Organisation von Haushaltsroutinen.",
            "category": None,
        }]
        matches = dg.fuzzy_match_skills("haushaltsmanagement", "Manages household tasks.", components)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["id"], "claude-skill:haushalt-manager")

    def test_compound_word_matches_prefix_skill_name(self):
        """Empirical case (T-20260711-01): expert "gesundheitsverwalter" vs.
        real skill "gesundheit" -- the substantive "gesundheit" is a prefix
        of the compound, "verwalter" is the (generic, stripped) role suffix."""
        components = [{
            "id": "claude-skill:gesundheit",
            "name": "gesundheit",
            "description": "Unterstuetzt bei der Verwaltung von Medikamentenplaenen.",
            "category": None,
        }]
        matches = dg.fuzzy_match_skills("gesundheitsverwalter", "Manages health records.", components)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["id"], "claude-skill:gesundheit")

    def test_compound_bridge_does_not_fire_on_unrelated_clean_token(self):
        """Negative case: "steuer-agent" and "foerderplaner" are already
        clean single tokens (no compound to split) with NO matching skill in
        the real inventory (verified 2026-07-11: absent from both the skill
        registry and the extra-skills-dir). The compound bridge must not
        manufacture a match against an unrelated skill just because it scans
        substrings -- "kein Overfitting, lieber kein Match als ein falscher
        Skill-Endpunkt" (T-20260711-01)."""
        components = [{
            "id": "claude-skill:buero",
            "name": "buero",
            "description": "Unterstuetzt bei Buero-Aufgaben: Bewerbungsmanagement, Berichtsgenerierung.",
            "category": None,
        }]
        matches = dg.fuzzy_match_skills("steuer-agent", "Handles tax filings and receipts.", components)
        self.assertEqual(matches, [])

    def test_compound_bridge_does_not_use_description_text(self):
        """The compound bridge is scoped to id/name only. A component whose
        FREE-TEXT DESCRIPTION happens to contain a compound-overlapping
        fragment, but whose id/name does not, must not match -- otherwise
        the bridge would degrade into the same noisy full-text search the
        existing docstring explicitly rejects for stage 2."""
        components = [{
            "id": "claude-skill:unrelated",
            "name": "unrelated",
            "description": "Verwaltet einen Haushalt nebenbei in der Beschreibung.",
            "category": None,
        }]
        matches = dg.fuzzy_match_skills("haushaltsmanagement", "Manages household tasks.", components)
        self.assertEqual(matches, [])

    def test_compound_bridge_rejects_short_generic_fragment(self):
        """Regression (T-20260711-04, real data): expert "worksheet_generator"
        vs. unrelated component "genogram-work" -- both happen to contain the
        4-char substring "work", but that is a coincidental fragment, not a
        semantic match. MIN_COMPOUND_TOKEN_LEN=6 must reject this; a lower
        threshold (originally 4) let it through, producing a wrong endpoint
        for a real BACH expert once orchestrates.experts was completed."""
        components = [{
            "id": "skill:therapy:genogram-work",
            "name": "genogram-work",
            "description": "",
            "category": "therapy",
        }]
        matches = dg.fuzzy_match_skills("worksheet_generator", "Generates worksheets.", components)
        self.assertEqual(matches, [])

    def test_psycho_berater_category_hint_still_wins_over_compound_bridge(self):
        """Regression: psycho-berater's existing KEYWORD_CATEGORY_HINTS match
        must not be lost or altered by the new compound-overlap path."""
        matches = dg.fuzzy_match_skills(
            "psycho-berater",
            "Coordinates health management and psychological counseling experts.",
            self._therapy_components(),
        )
        matched_ids = {m["id"] for m in matches}
        self.assertEqual(matched_ids, {"skill:therapy:act-techniken", "skill:therapy:psychoedukation"})


class TestLoadExtraSkills(unittest.TestCase):
    def test_loads_frontmatter_from_extra_skills_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "bewerbungsexperte"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("""---
name: bewerbungsexperte
description: >
  Specialist for the whole job-application process.
---
""", encoding="utf-8")
            found = dg.load_extra_skills(Path(tmp))
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0]["id"], "claude-skill:bewerbungsexperte")
            self.assertEqual(found[0]["name"], "bewerbungsexperte")
            self.assertIn("job-application", found[0]["description"])
            self.assertIsNone(found[0]["category"])

    def test_skips_entries_without_skill_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "not-a-skill").mkdir()
            self.assertEqual(dg.load_extra_skills(Path(tmp)), [])

    def test_missing_dir_returns_empty_list(self):
        self.assertEqual(dg.load_extra_skills(Path("/nonexistent/extra/skills/dir")), [])


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
            self.assertEqual(experts_by_name["fixture-expert-one"]["match"], "exact")
            self.assertEqual(experts_by_name["fixture-expert-one"]["matched_skills"], ["skill:test:fixture-expert-one"])
            self.assertEqual(experts_by_name["fixture-expert-two"]["status"], "nicht-portiert")
            self.assertIsNone(experts_by_name["fixture-expert-two"]["standalone_skill"])
            self.assertIsNone(experts_by_name["fixture-expert-two"]["match"])
            self.assertEqual(experts_by_name["fixture-expert-two"]["matched_skills"], [])
            self.assertFalse(result["source"]["extra_skills_dir_provided"])
            self.assertEqual(result["source"]["extra_skills_scanned"], 0)

    def test_stage_2_fuzzy_match_via_category_hint(self):
        """End-to-end version of the empirical psycho-berater/therapy case:
        stage 1 finds nothing (no provenance link at all), stage 2 finds the
        whole category via KEYWORD_CATEGORY_HINTS."""
        with tempfile.TemporaryDirectory() as tmp:
            agents_dir = Path(tmp) / "agents"
            boss_dir = agents_dir / "fixture-boss-c"
            boss_dir.mkdir(parents=True)
            boss_dir.joinpath("SKILL.md").write_text("""---
name: fixture-boss-c
orchestrates:
  experts: [psycho-berater]
  services: []
description: >
  Coordinates health management and psychological counseling experts.
---
""", encoding="utf-8")

            registry_path = Path(tmp) / "components.json"
            registry_path.write_text(json.dumps({
                "components": [
                    {"id": "skill:therapy:psychoedukation", "name": "psychoedukation", "category": "therapy",
                     "provenance": {"origin": "bach", "origin_path": "system/skills/therapie/psychoedukation.md"}},
                ]
            }), encoding="utf-8")

            result = dg.build_domains(agents_dir, registry_path, extra_boss_dirs=["fixture-boss-c"])
            expert = result["domains"][0]["experts"][0]
            self.assertEqual(expert["name"], "psycho-berater")
            self.assertEqual(expert["status"], "teilportiert")
            self.assertEqual(expert["match"], "fuzzy")
            self.assertEqual(expert["matched_skills"], ["skill:therapy:psychoedukation"])
            self.assertIsNone(expert["standalone_skill"])

    def test_extra_skills_dir_feeds_stage_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            agents_dir = Path(tmp) / "agents"
            boss_dir = agents_dir / "fixture-boss-d"
            boss_dir.mkdir(parents=True)
            boss_dir.joinpath("SKILL.md").write_text("""---
name: fixture-boss-d
orchestrates:
  experts: [psycho-berater]
  services: []
description: >
  Coordinates health management and psychological counseling experts.
---
""", encoding="utf-8")

            extra_skills_dir = Path(tmp) / "extra-skills"
            skill_dir = extra_skills_dir / "counseling-basics"
            skill_dir.mkdir(parents=True)
            skill_dir.joinpath("SKILL.md").write_text("""---
name: counseling-basics
description: >
  Fundamentals of therapeutic communication and counseling.
---
""", encoding="utf-8")

            result = dg.build_domains(
                agents_dir, None, extra_boss_dirs=["fixture-boss-d"], extra_skills_dir=extra_skills_dir,
            )
            expert = result["domains"][0]["experts"][0]
            self.assertEqual(expert["status"], "teilportiert")
            self.assertEqual(expert["matched_skills"], ["claude-skill:counseling-basics"])
            self.assertTrue(result["source"]["extra_skills_dir_provided"])
            self.assertEqual(result["source"]["extra_skills_scanned"], 1)

    def test_exact_match_excluded_from_sibling_experts_fuzzy_pool(self):
        """Advisor-review regression test: a skill exact-matched (stage 1) to
        one expert must not ALSO be fuzzy-matched (stage 2) to a sibling
        expert of the same boss, even if a KEYWORD_CATEGORY_HINTS stem would
        otherwise match it."""
        with tempfile.TemporaryDirectory() as tmp:
            agents_dir = Path(tmp) / "agents"
            boss_dir = agents_dir / "fixture-boss-e"
            boss_dir.mkdir(parents=True)
            boss_dir.joinpath("SKILL.md").write_text("""---
name: fixture-boss-e
orchestrates:
  experts: [foerderplaner, psycho-berater]
  services: []
description: >
  Coordinates funding planning and psychological counseling experts.
---
""", encoding="utf-8")

            registry_path = Path(tmp) / "components.json"
            registry_path.write_text(json.dumps({
                "components": [
                    {"id": "skill:test:shared-skill", "name": "shared-skill", "category": "therapy",
                     "provenance": {"origin": "bach", "origin_path": "system/agents/_experts/foerderplaner/CONCEPT.md"}},
                ]
            }), encoding="utf-8")

            result = dg.build_domains(agents_dir, registry_path, extra_boss_dirs=["fixture-boss-e"])
            experts_by_name = {e["name"]: e for e in result["domains"][0]["experts"]}
            self.assertEqual(experts_by_name["foerderplaner"]["status"], "portiert")
            self.assertEqual(experts_by_name["foerderplaner"]["standalone_skill"], "skill:test:shared-skill")
            # psycho-berater's KEYWORD_CATEGORY_HINTS stem would match
            # category "therapy", but the skill is already claimed exactly
            # by its sibling foerderplaner -- must not show up here too.
            self.assertEqual(experts_by_name["psycho-berater"]["status"], "nicht-portiert")
            self.assertNotIn("skill:test:shared-skill", experts_by_name["psycho-berater"]["matched_skills"])

    def test_exact_match_exclusion_is_global_across_bosses(self):
        """The exclusion above is deliberately GLOBAL, not just per-boss: a
        skill exact-matched to an expert in one boss must not be
        fuzzy-matched to an unrelated expert in a DIFFERENT boss either."""
        with tempfile.TemporaryDirectory() as tmp:
            agents_dir = Path(tmp) / "agents"
            boss_buero = agents_dir / "fixture-boss-buero"
            boss_buero.mkdir(parents=True)
            boss_buero.joinpath("SKILL.md").write_text("""---
name: fixture-boss-buero
orchestrates:
  experts: [foerderplaner]
  services: []
description: >
  Coordinates funding planning.
---
""", encoding="utf-8")
            boss_gesundheit = agents_dir / "fixture-boss-gesundheit"
            boss_gesundheit.mkdir(parents=True)
            boss_gesundheit.joinpath("SKILL.md").write_text("""---
name: fixture-boss-gesundheit
orchestrates:
  experts: [psycho-berater]
  services: []
description: >
  Coordinates psychological counseling.
---
""", encoding="utf-8")

            registry_path = Path(tmp) / "components.json"
            registry_path.write_text(json.dumps({
                "components": [
                    {"id": "skill:test:shared-skill", "name": "shared-skill", "category": "therapy",
                     "provenance": {"origin": "bach", "origin_path": "system/agents/_experts/foerderplaner/CONCEPT.md"}},
                ]
            }), encoding="utf-8")

            result = dg.build_domains(
                agents_dir, registry_path,
                extra_boss_dirs=["fixture-boss-buero", "fixture-boss-gesundheit"],
            )
            all_experts = [e for dom in result["domains"] for e in dom["experts"]]
            experts_by_name = {e["name"]: e for e in all_experts}
            self.assertEqual(experts_by_name["foerderplaner"]["status"], "portiert")
            self.assertEqual(experts_by_name["psycho-berater"]["status"], "nicht-portiert")
            self.assertNotIn("skill:test:shared-skill", experts_by_name["psycho-berater"]["matched_skills"])

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
