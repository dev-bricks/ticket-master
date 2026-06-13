@echo off
REM start-claude.bat — launch ticket-master with Claude
call "%~dp0ticket-master.bat" --provider claude %*
