"""
Smoke tests for ticket-master.

Checks:
1. Required directory structure exists.
2. config example JSON is valid.
3. Prompt file contains no forbidden terms (absolute Windows paths, system-specific
   infra names that should have been anonymised).
"""
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).parent.parent

REQUIRED_PATHS = [
    "prompts/TICKET-MASTER.en.md",
    "prompts/TICKET-MASTER.de.md",
    "config/ticket-master.config.example.json",
    "tickets/_templates/TICKET.txt",
    "tickets/INTAKE-TRIAGE-LOG.txt",
    "tickets/QUEUED/.gitkeep",
    "tickets/PENDING/.gitkeep",
    "tickets/SOLVED/.gitkeep",
    "tickets/.USER/.gitkeep",
    "bin/ticket-master.sh",
    "bin/ticket-master.bat",
    "bin/ticket-master.ps1",
    "bin/start-claude.sh",
    "bin/start-claude.bat",
    "bin/start-codex.sh",
    "bin/start-codex.bat",
    "bin/start-agy.sh",
    "bin/start-agy.bat",
    "LICENSE",
    "README.md",
    "README_de.md",
    "CHANGELOG.md",
    "VERSION",
    "llms.txt",
    "SECURITY.md",
    ".gitignore",
    ".gitattributes",
]

FORBIDDEN_PATTERNS = [
    r"C:\\Users",
    r"C:/Users",
    "/Users/User/",
    "BACH",
    "Mac Studio",
    "Hetzner",
    ".SYNC",
]

PROMPT_FILES = [
    REPO_ROOT / "prompts" / "TICKET-MASTER.en.md",
    REPO_ROOT / "prompts" / "TICKET-MASTER.de.md",
]


def test_structure():
    missing = []
    for rel in REQUIRED_PATHS:
        p = REPO_ROOT / rel
        if not p.exists():
            missing.append(rel)
    if missing:
        print("FAIL structure — missing files:")
        for m in missing:
            print(f"  {m}")
        return False
    print("OK   structure — all required paths present")
    return True


def test_config_json():
    cfg = REPO_ROOT / "config" / "ticket-master.config.example.json"
    try:
        with open(cfg, encoding="utf-8") as f:
            json.load(f)
        print("OK   config JSON — valid")
        return True
    except json.JSONDecodeError as e:
        print(f"FAIL config JSON — {e}")
        return False


def test_prompt_clean():
    ok = True
    for prompt_file in PROMPT_FILES:
        text = prompt_file.read_text(encoding="utf-8")
        hits = [p for p in FORBIDDEN_PATTERNS if p in text]
        if hits:
            print(f"FAIL anonymisation — forbidden terms in {prompt_file.name}: {hits}")
            ok = False
    if ok:
        print("OK   anonymisation — no forbidden terms in prompt files")
    return ok


def main():
    results = [
        test_structure(),
        test_config_json(),
        test_prompt_clean(),
    ]
    passed = sum(results)
    total = len(results)
    print(f"\n{'PASSED' if passed == total else 'FAILED'}: {passed}/{total} checks")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
