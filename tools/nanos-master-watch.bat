@echo off
rem Laisse cette fenetre ouverte pendant que tu cuisines depuis Unreal :
rem chaque cook Forge est fusionne dans le master (Documents\nanos-master) puis envoye au serveur nanos.
cd /d "%~dp0"
python -m gmod2nanos.master watch --deploy maps --deploy aksel-animations --deploy scythe --deploy yufu-arme-test --deploy vefects --deploy free-magic --deploy free-spells --deploy sword-trail-vfx --deploy breath-fx
pause
