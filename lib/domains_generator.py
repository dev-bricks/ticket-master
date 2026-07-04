r"""
domains_generator.py — Generates the ticket-master domains registry.

Phase 1 of the personal-assistant expansion (T-20260704-02): reads the boss-
agent SKILL.md frontmatter of a BACH installation (`orchestrates.experts`,
`description`) and cross-references each expert against a skill registry's
`components.json` (`provenance.origin: bach`, `provenance.origin_path`) to
mark it "portiert" (a standalone skill already exists) or "nicht-portiert"
(still only lives inside BACH).

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


def build_domains(agents_dir: Path, registry_components_path: Path | None,
                   extra_boss_dirs: list[str] | None = None) -> dict:
    agents_dir = Path(agents_dir)
    if not agents_dir.is_dir():
        raise FileNotFoundError(f"BACH agents dir not found: {agents_dir}")

    bach_components: list[dict] = []
    if registry_components_path is not None and Path(registry_components_path).is_file():
        bach_components = load_bach_components(Path(registry_components_path))

    boss_dirs = discover_boss_dirs(agents_dir, extra_boss_dirs)
    domains = []
    for dirname, path in sorted(boss_dirs.items()):
        skill_file = path / "SKILL.md"
        text = skill_file.read_text(encoding="utf-8", errors="replace")
        frontmatter = parse_frontmatter(text)
        domain_id, label = _domain_id_label(dirname, frontmatter)
        description = str(frontmatter.get("description", ""))
        orchestrates = frontmatter.get("orchestrates", {})
        expert_names = orchestrates.get("experts", []) if isinstance(orchestrates, dict) else []
        services = orchestrates.get("services", []) if isinstance(orchestrates, dict) else []

        experts = []
        for expert_name in expert_names:
            match = match_standalone_skill(expert_name, bach_components)
            experts.append({
                "name": expert_name,
                "standalone_skill": match["id"] if match else None,
                "status": "portiert" if match else "nicht-portiert",
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

    result = build_domains(agents_dir, registry_path, args.extra_boss_dir)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"domains.json written: {output_path} ({len(result['domains'])} domains)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
