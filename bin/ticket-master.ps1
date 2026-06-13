# ticket-master.ps1 — PowerShell dispatcher for ticket-master
# Usage: .\bin\ticket-master.ps1 [-Provider claude|codex|agy]
param(
    [string]$Provider = $(if ($env:TM_PROVIDER) { $env:TM_PROVIDER } else { "claude" })
)

$ScriptDir  = $PSScriptRoot
$RepoRoot   = Resolve-Path (Join-Path $ScriptDir "..")
$PromptFile = Join-Path $RepoRoot "prompts\TICKET-MASTER.md"
$Bootstrap  = "Read and follow the instructions in $PromptFile - start at step (a) and work down to Position 0."

Write-Host "[ticket-master] Starting provider: $Provider"
Write-Host "[ticket-master] Repo root: $RepoRoot"

Set-Location $RepoRoot

switch ($Provider) {
    "claude" {
        if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
            Write-Error "ERROR: 'claude' not found in PATH. Install the Claude CLI first."
            exit 1
        }
        if ($env:TM_SKIP_PERMISSIONS -eq "1") {
            & claude --dangerously-skip-permissions $Bootstrap
        } else {
            & claude $Bootstrap
        }
    }
    "codex" {
        if (-not (Get-Command codex -ErrorAction SilentlyContinue)) {
            Write-Error "ERROR: 'codex' not found in PATH. Install the Codex CLI first."
            exit 1
        }
        & codex $Bootstrap
    }
    "agy" {
        if (-not (Get-Command agy -ErrorAction SilentlyContinue)) {
            Write-Error "ERROR: 'agy' not found in PATH. Install the Gemini CLI first."
            exit 1
        }
        & agy $Bootstrap
    }
    default {
        Write-Error "ERROR: Unknown provider '$Provider'. Use: claude | codex | agy"
        exit 1
    }
}
