@echo off
rem Lance le serveur nanos world de ce dossier (à copier à côté de NanosWorldServer.exe, avec le Config.toml de la partie).
cd /d "%~dp0"
NanosWorldServer.exe
pause
