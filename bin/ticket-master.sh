#!/usr/bin/env bash
# ticket-master.sh — Unix dispatcher for ticket-master
# Usage: ./bin/ticket-master.sh [--provider claude|codex|agy]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Language selection: TM_LANG (default "en"). Falls back to "en" if the file is missing.
TM_LANG="${TM_LANG:-en}"
PROMPT_FILE="${REPO_ROOT}/prompts/TICKET-MASTER.${TM_LANG}.md"
if [[ ! -f "${PROMPT_FILE}" ]]; then
    echo "WARNING: prompt file for language '${TM_LANG}' not found; falling back to 'en'." >&2
    TM_LANG="en"
    PROMPT_FILE="${REPO_ROOT}/prompts/TICKET-MASTER.en.md"
fi

BOOTSTRAP="Read and follow the instructions in ${PROMPT_FILE} - start at step (a) and work down to Position 0."

PROVIDER="claude"
if [[ "${TM_PROVIDER:-}" != "" ]]; then
    PROVIDER="${TM_PROVIDER}"
fi

while [[ $# -gt 0 ]]; do
    case "$1" in
        --provider) PROVIDER="$2"; shift 2 ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

echo "[ticket-master] Starting provider: ${PROVIDER}"
echo "[ticket-master] Language: ${TM_LANG}"
echo "[ticket-master] Repo root: ${REPO_ROOT}"

case "${PROVIDER}" in
    claude)
        if ! command -v claude &>/dev/null; then
            echo "ERROR: 'claude' not found in PATH. Install the Claude CLI first." >&2
            exit 1
        fi
        EXTRA_ARGS=()
        if [[ "${TM_SKIP_PERMISSIONS:-0}" == "1" ]]; then
            EXTRA_ARGS+=("--dangerously-skip-permissions")
        fi
        cd "${REPO_ROOT}"
        exec claude "${EXTRA_ARGS[@]}" "${BOOTSTRAP}"
        ;;
    codex)
        if ! command -v codex &>/dev/null; then
            echo "ERROR: 'codex' not found in PATH. Install the Codex CLI first." >&2
            exit 1
        fi
        cd "${REPO_ROOT}"
        exec codex "${BOOTSTRAP}"
        ;;
    agy)
        if ! command -v agy &>/dev/null; then
            echo "ERROR: 'agy' not found in PATH. Install the Gemini CLI first." >&2
            exit 1
        fi
        cd "${REPO_ROOT}"
        exec agy "${BOOTSTRAP}"
        ;;
    *)
        echo "ERROR: Unknown provider '${PROVIDER}'. Use: claude | codex | agy" >&2
        exit 1
        ;;
esac
