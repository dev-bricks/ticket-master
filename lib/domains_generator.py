r"""
domains_generator.py — Generates the ticket-master domains registry.

Phase 1 of the personal-assistant expansion (T-20260704-02): reads the boss-
agent SKILL.md frontmatter of a BACH installation (`orchestrates.experts`,
`description`) and cross-references each expert against a skill registry's
`components.json` (`provenance.origin: bach`, `provenance.origin_path`) to
mark it "portiert" (a standalone skill already exists) or "nicht-portiert"
(still only lives inside BACH).

Stage-2 fuzzy matching (T-20260704-02 follow-up): stage-1 provenance matching
is a strict, exact 1:1 link and misses experts that govern a whole SKILL
FAMILY rather than a single ported skill (e.g. a counseling-style expert
whose skill family has no per-component `provenance` link back to it, only a
shared registry `category`), and skills that were extracted as standalone
but never registered in the main skill registry. `fuzzy_match_skills()` adds
a second pass (keyword/category hints + token overlap, see
`KEYWORD_CATEGORY_HINTS`) that only runs when stage 1 found nothing, marking
the result `"status": "teilportiert"` / `"match": "fuzzy"` with a
`"matched_skills"` list (as opposed to `"portiert"` / `"match": "exact"` /
a single `"standalone_skill"`). `load_extra_skills()` optionally folds a
second skill directory (e.g. a Claude Code `~/.claude/skills/` tree) into
that fuzzy pass via `--extra-skills-dir`. `domains.json`'s per-expert
`experts[]` entries remain provenance/grouping metadata only — the
ticket-master prompt routes directly to the resolved skill(s), it does not
introduce experts as a separate routing hop.

This script is a GENERATOR that runs once on the "origin system" (the machine
that has BACH installed). Its output, `config/domains.json`, is consumed at
ticket-master runtime and is itself BACH-free — no BACH path or BACH code is
read at runtime, only this generated file. If the BACH agents directory is
not available (e.g. a different system, or a fresh checkout), the generator
aborts cleanly without touching any existing `config/domains.json`.

User-neutral module: no hardcoded local paths. Both source directories are
CLI arguments (or environment variables); there is no default that assumes a
particular filesystem layout. `config/domains.json` is itself a generated,
site-specific artifact (like `config/ticket-master.config.json`) and is not
meant to be committed — see `config/domains.example.json` for the schema.

Zero-dep: stdlib only (argparse, json, re, pathlib). Not a general YAML
parser — `parse_frontmatter()` targets the specific frontmatter shape used by
BACH boss-agent SKILL.md files (scalar `key: value`, folded `key: >` block
scalars, and one level of nesting for `orchestrates:`).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Known boss-agent directory names -> (domain id, domain label). Four of the
# five personal-assistant domains have stable folder names; the fifth
# (insurance/finance) is discovered by pattern since its folder name varies
# across BACH installations (e.g. "versicherungen" vs. "versicherungs-agent").
BOSS_DIR_DEFAULTS: dict[str, tuple[str, str]] = {
    "persoenlicher-assistent": ("alltag", "Alltag & Termine"),
    "gesundheitsassistent": ("gesundheit", "Gesundheit"),
    "bueroassistent": ("buero", "Büro, Steuer & Förderung"),
    "production": ("content", "Content & Produktion"),
}
_VERSICHERUNG_PATTERN = re.compile(r"versicher", re.IGNORECASE)

# Stage-2 (fuzzy) matching, T-20260704-02 follow-up: generic role-suffix
# tokens stripped from an expert's own name before token-overlap matching, so
# e.g. "psycho-berater" contributes the meaningful token "psycho" rather than
# the near-universal "berater".
_GENERIC_EXPERT_NAME_TOKENS: set[str] = {
    "agent", "berater", "beraterin", "verwalter", "verwalterin", "planer",
    "planerin", "management", "manager", "assistent", "assistentin",
    "experte", "expertin",
}

# Stage-2 compound-word bridge (T-20260711-01): `_tokenize()` only splits on
# non-letter boundaries, so a German compound written as ONE word (e.g. the
# expert name "haushaltsmanagement") never breaks into {"haushalt",
# "management"} the way a hyphenated skill name ("haushalt-manager") does.
# Plain set-intersection token overlap then finds nothing even though the
# expert and skill clearly refer to the same thing. `_compound_overlap()`
# below bridges this with a length-guarded substring test instead of a real
# compound splitter (stdlib-only, no German morphology dependency available).
# Length threshold avoids short/generic fragments ("in", "der", "test")
# matching almost anything. 4 was tried first and empirically proved too low
# (T-20260711-04 regression, real data): "work" (4 chars) bridged the expert
# "worksheet_generator" to the unrelated therapy skill "genogram-work" purely
# because both contain the substring "work" -- a coincidental fragment, not a
# semantic match. 6 keeps every verified real compound case comfortably clear
# (haushalt=8, gesundheit=10, transkription=13) while excluding short/generic
# English fragments like "work", "team", "plan", "data", "file".
_MIN_COMPOUND_TOKEN_LEN = 6


def _compound_overlap(name_tokens: set[str], comp_tokens: set[str]) -> bool:
    """True if some sufficiently long component token is a substring of some
    expert-name token, or vice versa. Both token sets are expected to already
    have `_GENERIC_EXPERT_NAME_TOKENS` removed by the caller, so a purely
    generic fragment (e.g. "manager") can't bridge two otherwise-unrelated
    compounds on its own."""
    for nt in name_tokens:
        if len(nt) < _MIN_COMPOUND_TOKEN_LEN:
            continue
        for ct in comp_tokens:
            if len(ct) < _MIN_COMPOUND_TOKEN_LEN:
                continue
            if ct in nt or nt in ct:
                return True
    return False


# Optional keyword-stem hints for stage-2 fuzzy matching. Deliberately keyed
# off the EXPERT'S OWN NAME ONLY, never the boss-level description: that
# description is shared verbatim across every expert of the same boss, so
# matching against it would leak one expert's hits onto all of its siblings
# (empirically observed: a "psychological ... counseling" phrase in a shared
# boss description would otherwise also credit a purely medical/
# administrative sibling expert with the whole therapy skill family).
# Each hint maps a stem to (a) the registry `category` this expert's skill
# family likely lives under, and (b) a small set of related term-stems to
# substring-match against a component's own id/name/description — needed for
# sources like an extra skills dir that have no `category` concept at all.
# Generic domain vocabulary, not project-specific; extend for your own
# taxonomy, but keep entries narrow (a few related stems), not broad topic
# words, to avoid turning stage 2 into a noisy full-text search.
KEYWORD_CATEGORY_HINTS: dict[str, dict[str, object]] = {
    "psycho": {"category": "therapy", "terms": {"therap", "counsel", "psycho"}},
    "therap": {"category": "therapy", "terms": {"therap", "counsel"}},
    "berat": {"category": "therapy", "terms": {"therap", "counsel", "berat"}},
    "counsel": {"category": "therapy", "terms": {"therap", "counsel"}},
}


def _tokenize(text: str) -> set[str]:
    """Unicode-aware tokenizer. `[a-zA-Z0-9]+` would silently split German
    umlauts/ß out of a word (verified: "Fördermittelberater" ->
    {"f", "rdermittelberater"}), quietly losing token-overlap matches for
    non-ASCII expert/skill names. `[^\\W\\d_]+` matches Unicode letters
    (Python's `\\w` is Unicode-aware by default), `\\d+` matches digit runs,
    so "Fördermittelberater" stays one token and "gpt4" still splits into
    letters+digits like before."""
    return set(re.findall(r"[^\W\d_]+|\d+", text.lower()))


def _collect_indented(body: list[str], start: int) -> tuple[list[str], int]:
    """Collects consecutive non-blank, indented lines starting at `start`.
    Stops at the first blank line or first line without leading whitespace."""
    j = start
    collected: list[str] = []
    while j < len(body) and body[j].startswith((" ", "\t")) and body[j].strip():
        collected.append(body[j].strip())
        j += 1
    return collected, j


def _parse_bracket_list(value: str) -> list[str]:
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        return [item.strip() for item in inner.split(",") if item.strip()]
    return []


def parse_frontmatter(text: str) -> dict:
    """Targeted extractor for BACH boss-agent SKILL.md frontmatter (between
    the first pair of `---` lines). Returns a dict with whatever top-level
    keys were present; `orchestrates` (if present) is itself a dict whose
    `experts`/`services` values are parsed as lists."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    try:
        end = lines[1:].index("---") + 1
    except ValueError:
        return {}
    body = lines[1:end]

    result: dict = {}
    i = 0
    while i < len(body):
        raw = body[i]
        if not raw.strip() or raw.startswith((" ", "\t")):
            i += 1
            continue
        if ":" not in raw:
            i += 1
            continue
        key, _, rest = raw.partition(":")
        key = key.strip()
        rest = rest.strip()
        if rest == ">":
            collected, i = _collect_indented(body, i + 1)
            result[key] = " ".join(collected)
            continue
        if rest == "":
            collected, i = _collect_indented(body, i + 1)
            nested: dict = {}
            for sub in collected:
                if ":" in sub:
                    sub_key, _, sub_val = sub.partition(":")
                    nested[sub_key.strip()] = _parse_bracket_list(sub_val.strip())
            result[key] = nested
            continue
        result[key] = rest
        i += 1
    return result


def discover_boss_dirs(agents_dir: Path, extra_dirs: list[str] | None = None) -> dict[str, Path]:
    """Finds the boss-agent directories under `agents_dir`. Known directory
    names are used directly; the insurance/finance domain is additionally
    searched for by name/description pattern, since its folder name is not
    guaranteed across BACH installations."""
    found: dict[str, Path] = {}
    for dirname in list(BOSS_DIR_DEFAULTS) + list(extra_dirs or []):
        candidate = agents_dir / dirname
        if (candidate / "SKILL.md").is_file():
            found[dirname] = candidate

    if not any(_VERSICHERUNG_PATTERN.search(name) for name in found):
        for entry in sorted(agents_dir.iterdir()):
            if entry.name in found or not entry.is_dir():
                continue
            skill_file = entry / "SKILL.md"
            if not skill_file.is_file():
                continue
            if _VERSICHERUNG_PATTERN.search(entry.name):
                found[entry.name] = entry
                break
            try:
                text = skill_file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if _VERSICHERUNG_PATTERN.search(text[:2000]):
                found[entry.name] = entry
                break
    return found


def _domain_id_label(dirname: str, frontmatter: dict) -> tuple[str, str]:
    if dirname in BOSS_DIR_DEFAULTS:
        return BOSS_DIR_DEFAULTS[dirname]
    if _VERSICHERUNG_PATTERN.search(dirname) or _VERSICHERUNG_PATTERN.search(str(frontmatter.get("name", ""))):
        return ("versicherung", "Versicherung & Finanzen")
    slug = re.sub(r"[^a-z0-9]+", "-", dirname.lower()).strip("-")
    return (slug or dirname, str(frontmatter.get("name", dirname)))


_USECASE_RE = re.compile(r"\(\d+\)\s*")


def extract_usecases(description: str) -> list[str]:
    """Splits a `(1) ... (2) ...`-style description into individual usecase
    strings. Falls back to the whole description as a single entry when the
    numbered-list pattern is not present."""
    description = description.strip()
    if not description:
        return []
    parts = _USECASE_RE.split(description)
    if len(parts) <= 1:
        return [description]
    return [p.strip().rstrip(",.") for p in parts[1:] if p.strip()]


def load_bach_components(registry_components_path: Path) -> list[dict]:
    """Loads a skill-registry `components.json` and returns only the entries
    with `provenance.origin == "bach"` (candidates for expert-to-skill
    matching)."""
    data = json.loads(Path(registry_components_path).read_text(encoding="utf-8"))
    components = data.get("components", [])
    return [c for c in components if (c.get("provenance") or {}).get("origin") == "bach"]


def _expert_name_variants(name: str) -> set[str]:
    base = name.strip().lower().replace("_", "-")
    variants = {base}
    if base.endswith("-agent"):
        variants.add(base[: -len("-agent")])
    else:
        variants.add(f"{base}-agent")
    return variants


def match_standalone_skill(expert_name: str, bach_components: list[dict]) -> dict | None:
    """Finds a standalone skill in `bach_components` whose `origin_path`
    references this expert (by directory segment or filename stem). Tries
    both `<name>` and `<name>-agent` variants, since BACH expert folder names
    and their `orchestrates.experts` entries do not always match exactly
    (e.g. folder `steuer` vs. frontmatter entry `steuer-agent`)."""
    variants = _expert_name_variants(expert_name)
    for comp in bach_components:
        origin_path = str((comp.get("provenance") or {}).get("origin_path") or "")
        origin_path = origin_path.lower().replace("\\", "/")
        if not origin_path:
            continue
        segments = origin_path.split("/")
        stem = Path(origin_path).stem
        if any(v in segments for v in variants) or stem in variants:
            return comp
    return None


def fuzzy_match_skills(expert_name: str, boss_description: str, components: list[dict]) -> list[dict]:
    """Stage-2 (fuzzy) matching, T-20260704-02 follow-up: an expert governs a
    whole SKILL FAMILY, not necessarily a single 1:1 standalone skill (e.g.
    "psycho-berater" governs an entire "therapy" category of skills). Called
    only when stage-1 exact provenance matching (`match_standalone_skill`)
    finds nothing. `boss_description` is accepted for signature stability
    and possible future per-expert context, but is deliberately NOT used as a
    matching signal here — see the note on `KEYWORD_CATEGORY_HINTS` above for
    why matching against the (boss-shared) description leaks matches across
    sibling experts. Matches a component if either:
      (a) a `KEYWORD_CATEGORY_HINTS` stem is present in the expert's OWN name,
          and the component's `category` equals that stem's hinted category
          (works even when the component has no descriptive text, which is
          common in this registry); or
      (b) same hint, but the component has no `category` (e.g. an
          `load_extra_skills()` entry) — matched instead via a substring hit
          from the hint's `terms` against the component's own id/name/
          description; or
      (c) the expert's name tokens (role-suffix stripped) exactly overlap
          with the component's own id/name tokens (role-suffix stripped);
          or
      (d) a component's own id/name token (role-suffix stripped, length-
          guarded) is a substring of an expert-name token or vice versa —
          bridges German compounds written as one word on the expert side
          against a hyphenated/split skill name (T-20260711-01, see
          `_compound_overlap()`).
    Cases (c) and (d) are deliberately scoped to the component's id/name
    only, NOT its free-text description (T-20260711-05 -- case (c) used to
    run over the full id+name+description haystack, which produced false
    positives whenever an expert's own name happened to be a common English
    word appearing incidentally somewhere in an unrelated component's prose,
    e.g. expert "report_generator" against a component whose description
    merely mentions a "Bug-Report-Template". Empirically verified against
    the real BACH+skill-registry corpus (T-20260711-04/-05 diagnostics):
    no currently-legitimate match relies on a description-only token in
    case (c) -- every real hit already goes through id/name, a category
    hint (a), or a `hinted_terms` substring (b), all of which still
    intentionally read the description). Case (b) is a narrow exception
    that KEEPS reading the description on purpose (see
    `test_token_overlap_on_shared_description_word`): it is gated by a
    `KEYWORD_CATEGORY_HINTS` stem match on the expert's own name first, so
    it cannot fire on an arbitrary shared word the way unguarded case (c)
    could.
    `components` may mix registry entries (with `category`) and entries from
    `load_extra_skills()` (no `category` — matched via (b)/(c)/(d) only).
    Returns every match, since an expert can legitimately govern several
    skills. Deliberately conservative: on a real corpus of 100+ candidate
    skills, a broader token-overlap-on-shared-description heuristic was found
    to match almost anything (verified empirically) — precision over recall
    here."""
    name_tokens = _tokenize(expert_name) - _GENERIC_EXPERT_NAME_TOKENS
    expert_name_lower = expert_name.lower()

    hinted_categories: set[str] = set()
    hinted_terms: set[str] = set()
    for stem, hint in KEYWORD_CATEGORY_HINTS.items():
        if stem in expert_name_lower:
            hinted_categories.add(str(hint["category"]))
            hinted_terms.update(hint["terms"])  # type: ignore[arg-type]

    matches: list[dict] = []
    seen_ids: set[str] = set()
    for comp in components:
        comp_id = comp.get("id")
        if not comp_id or comp_id in seen_ids:
            continue
        category = str(comp.get("category") or "").strip().lower()
        haystack = " ".join([
            str(comp.get("id", "")), str(comp.get("name", "")), str(comp.get("description", "")),
        ]).lower()

        if category and category in hinted_categories:
            matches.append(comp)
            seen_ids.add(comp_id)
            continue
        if not category and hinted_terms and any(term in haystack for term in hinted_terms):
            matches.append(comp)
            seen_ids.add(comp_id)
            continue
        id_name_tokens = _tokenize(
            " ".join([str(comp.get("id", "")), str(comp.get("name", ""))])
        ) - _GENERIC_EXPERT_NAME_TOKENS
        if name_tokens and (name_tokens & id_name_tokens):
            matches.append(comp)
            seen_ids.add(comp_id)
            continue
        if name_tokens and id_name_tokens and _compound_overlap(name_tokens, id_name_tokens):
            matches.append(comp)
            seen_ids.add(comp_id)
    return matches


def load_extra_skills(extra_skills_dir: Path) -> list[dict]:
    """Loads a second, independent skill inventory (e.g. a Claude Code
    `~/.claude/skills/` tree) for stage-2 fuzzy matching — useful when a
    skill has been extracted as standalone but was never (or not yet)
    registered in the main skill registry (observed empirically: skills like
    a job-application helper or a self-management skill existed locally but
    were absent from `components.json`). Reads each
    `<extra_skills_dir>/<name>/SKILL.md` frontmatter (`name`, `description`)
    via `parse_frontmatter()`. These entries never carry a `category`, so in
    `fuzzy_match_skills()` they can only match via token overlap, never via
    `KEYWORD_CATEGORY_HINTS`. Missing directory / unreadable files are
    skipped silently — this is a best-effort secondary source, not a
    required one."""
    extra_skills_dir = Path(extra_skills_dir)
    found: list[dict] = []
    if not extra_skills_dir.is_dir():
        return found
    for entry in sorted(extra_skills_dir.iterdir()):
        if not entry.is_dir():
            continue
        skill_file = entry / "SKILL.md"
        if not skill_file.is_file():
            continue
        try:
            text = skill_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        frontmatter = parse_frontmatter(text)
        found.append({
            "id": f"claude-skill:{entry.name}",
            "name": str(frontmatter.get("name", entry.name)),
            "description": str(frontmatter.get("description", "")),
            "category": None,
        })
    return found


def build_domains(agents_dir: Path, registry_components_path: Path | None,
                   extra_boss_dirs: list[str] | None = None,
                   extra_skills_dir: Path | None = None) -> dict:
    agents_dir = Path(agents_dir)
    if not agents_dir.is_dir():
        raise FileNotFoundError(f"BACH agents dir not found: {agents_dir}")

    bach_components: list[dict] = []
    if registry_components_path is not None and Path(registry_components_path).is_file():
        bach_components = load_bach_components(Path(registry_components_path))

    extra_skills: list[dict] = []
    if extra_skills_dir is not None:
        extra_skills = load_extra_skills(Path(extra_skills_dir))

    fuzzy_pool = bach_components + extra_skills

    boss_dirs = discover_boss_dirs(agents_dir, extra_boss_dirs)

    # Read every boss's frontmatter once, up front, so the exact-match
    # exclusion below can be computed GLOBALLY across all bosses/experts
    # before any fuzzy matching happens -- not just within one boss.
    boss_data: list[tuple[str, str, str, str, list[str], list[str]]] = []
    for dirname, path in sorted(boss_dirs.items()):
        skill_file = path / "SKILL.md"
        text = skill_file.read_text(encoding="utf-8", errors="replace")
        frontmatter = parse_frontmatter(text)
        domain_id, label = _domain_id_label(dirname, frontmatter)
        description = str(frontmatter.get("description", ""))
        orchestrates = frontmatter.get("orchestrates", {})
        expert_names = orchestrates.get("experts", []) if isinstance(orchestrates, dict) else []
        services = orchestrates.get("services", []) if isinstance(orchestrates, dict) else []
        boss_data.append((dirname, domain_id, label, description, expert_names, services))

    # Stage 1 (exact) runs for EVERY expert of EVERY boss first. The
    # resulting matched skill IDs are excluded from the stage-2 fuzzy pool
    # GLOBALLY (across all bosses, not just siblings within the same boss) --
    # otherwise a component could end up "portiert" for one expert here and,
    # via a coincidental keyword/token overlap, "teilportiert" for an
    # unrelated expert in a completely different domain.
    global_exact_matches: dict[tuple[str, str], dict] = {}
    for dirname, _domain_id, _label, _description, expert_names, _services in boss_data:
        for expert_name in expert_names:
            match = match_standalone_skill(expert_name, bach_components)
            if match:
                global_exact_matches[(dirname, expert_name)] = match
    global_exact_matched_ids = {m["id"] for m in global_exact_matches.values()}
    fuzzy_pool_available = [c for c in fuzzy_pool if c.get("id") not in global_exact_matched_ids]

    domains = []
    for dirname, domain_id, label, description, expert_names, services in boss_data:
        experts = []
        for expert_name in expert_names:
            match = global_exact_matches.get((dirname, expert_name))
            if match:
                experts.append({
                    "name": expert_name,
                    "standalone_skill": match["id"],
                    "status": "portiert",
                    "match": "exact",
                    "matched_skills": [match["id"]],
                })
                continue

            # Stage 2 (T-20260704-02 follow-up): keyword/category fuzzy
            # matching against the registry and/or an extra skills dir. An
            # expert governs a skill FAMILY, so this can yield several
            # matches, not just one.
            fuzzy_matches = fuzzy_match_skills(expert_name, description, fuzzy_pool_available) if fuzzy_pool_available else []
            if fuzzy_matches:
                experts.append({
                    "name": expert_name,
                    "standalone_skill": None,
                    "status": "teilportiert",
                    "match": "fuzzy",
                    "matched_skills": sorted(c["id"] for c in fuzzy_matches),
                })
                continue

            experts.append({
                "name": expert_name,
                "standalone_skill": None,
                "status": "nicht-portiert",
                "match": None,
                "matched_skills": [],
            })

        domains.append({
            "id": domain_id,
            "label": label,
            "source_boss": dirname,
            "description": description,
            "usecases": extract_usecases(description),
            "services": services,
            "experts": experts,
        })

    domains.sort(key=lambda d: d["id"])
    return {
        "schema": "ticket-master-domains-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "generator": "lib/domains_generator.py",
            "registry_provided": registry_components_path is not None,
            "bach_components_scanned": len(bach_components),
            "extra_skills_dir_provided": extra_skills_dir is not None,
            "extra_skills_scanned": len(extra_skills),
        },
        "domains": domains,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bach-agents-dir",
        default=os.environ.get("TICKET_MASTER_BACH_AGENTS_DIR"),
        help="Path to the BACH system/agents/ directory (generation-time only, not read at runtime).",
    )
    parser.add_argument(
        "--skills-registry-components",
        default=os.environ.get("TICKET_MASTER_SKILLS_REGISTRY_COMPONENTS"),
        help="Path to a skill registry's components.json (for provenance cross-reference).",
    )
    parser.add_argument(
        "--extra-boss-dir", action="append", default=[],
        help="Additional boss-agent directory name to check (repeatable).",
    )
    parser.add_argument(
        "--extra-skills-dir",
        default=os.environ.get("TICKET_MASTER_EXTRA_SKILLS_DIR"),
        help=(
            "Optional second skill inventory (e.g. a Claude Code ~/.claude/skills/ "
            "tree) for stage-2 fuzzy matching, in case a skill was extracted as "
            "standalone but never registered in the main skill registry. Default: "
            "none (stage 2 then only uses the registry components)."
        ),
    )
    parser.add_argument(
        "--output",
        default=str(Path(__file__).resolve().parent.parent / "config" / "domains.json"),
        help="Output path for the generated domains.json.",
    )
    args = parser.parse_args(argv)

    if not args.bach_agents_dir:
        print(
            "No --bach-agents-dir / TICKET_MASTER_BACH_AGENTS_DIR set — "
            "aborting cleanly, existing domains.json (if any) is left untouched.",
            file=sys.stderr,
        )
        return 2

    agents_dir = Path(args.bach_agents_dir)
    if not agents_dir.is_dir():
        print(f"BACH agents dir not found: {agents_dir} — aborting without changes.", file=sys.stderr)
        return 2

    registry_path = Path(args.skills_registry_components) if args.skills_registry_components else None
    if registry_path is not None and not registry_path.is_file():
        print(f"Skills registry components file not found: {registry_path} — continuing without it.", file=sys.stderr)
        registry_path = None

    extra_skills_dir = Path(args.extra_skills_dir) if args.extra_skills_dir else None
    if extra_skills_dir is not None and not extra_skills_dir.is_dir():
        print(f"Extra skills dir not found: {extra_skills_dir} — continuing without it.", file=sys.stderr)
        extra_skills_dir = None

    result = build_domains(agents_dir, registry_path, args.extra_boss_dir, extra_skills_dir)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"domains.json written: {output_path} ({len(result['domains'])} domains)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
