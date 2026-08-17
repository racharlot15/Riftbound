@echo off
REM Run the game from the project worktree and keep console open on exit
cd /d "%~dp0\Riftbound"
python main.py
echo Exit code %ERRORLEVEL%
pause
