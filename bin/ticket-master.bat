@echo off
REM ticket-master.bat — Windows CMD dispatcher for ticket-master
REM Usage: bin\ticket-master.bat [--provider claude|codex|agy]
setlocal

set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%.."

REM Language selection: TM_LANG (default "en"). Falls back to "en" if the file is missing.
if not defined TM_LANG set "TM_LANG=en"
set "PROMPT_FILE=%REPO_ROOT%\prompts\TICKET-MASTER.%TM_LANG%.md"
if not exist "%PROMPT_FILE%" (
    echo WARNING: prompt file for language '%TM_LANG%' not found; falling back to 'en'. 1>&2
    set "TM_LANG=en"
    set "PROMPT_FILE=%REPO_ROOT%\prompts\TICKET-MASTER.en.md"
)

set "BOOTSTRAP=Read and follow the instructions in %PROMPT_FILE% - start at step (a) and work down to Position 0."

set "PROVIDER=claude"
if defined TM_PROVIDER set "PROVIDER=%TM_PROVIDER%"

:parse
if "%~1"=="--provider" (
    set "PROVIDER=%~2"
    shift & shift & goto parse
)
if not "%~1"=="" (
    echo Unknown argument: %~1
    exit /b 1
)

echo [ticket-master] Starting provider: %PROVIDER%
echo [ticket-master] Language: %TM_LANG%
echo [ticket-master] Repo root: %REPO_ROOT%

if "%PROVIDER%"=="claude" (
    where claude >nul 2>&1
    if errorlevel 1 (
        echo ERROR: 'claude' not found in PATH. Install the Claude CLI first.
        exit /b 1
    )
    cd /d "%REPO_ROOT%"
    if "%TM_SKIP_PERMISSIONS%"=="1" (
        claude --dangerously-skip-permissions "%BOOTSTRAP%"
    ) else (
        claude "%BOOTSTRAP%"
    )
    goto :eof
)

if "%PROVIDER%"=="codex" (
    where codex >nul 2>&1
    if errorlevel 1 (
        echo ERROR: 'codex' not found in PATH. Install the Codex CLI first.
        exit /b 1
    )
    cd /d "%REPO_ROOT%"
    codex "%BOOTSTRAP%"
    goto :eof
)

if "%PROVIDER%"=="agy" (
    where agy >nul 2>&1
    if errorlevel 1 (
        echo ERROR: 'agy' not found in PATH. Install the Gemini CLI first.
        exit /b 1
    )
    cd /d "%REPO_ROOT%"
    agy "%BOOTSTRAP%"
    goto :eof
)

echo ERROR: Unknown provider '%PROVIDER%'. Use: claude ^| codex ^| agy
exit /b 1
