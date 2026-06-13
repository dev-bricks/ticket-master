@echo off
REM start-codex.bat — launch ticket-master with Codex
call "%~dp0ticket-master.bat" --provider codex %*
