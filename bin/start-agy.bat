@echo off
REM start-agy.bat — launch ticket-master with agy (Gemini)
call "%~dp0ticket-master.bat" --provider agy %*
