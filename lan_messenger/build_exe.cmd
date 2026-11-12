@echo off
REM Build do LANMessenger.exe - rodar a partir da RAIZ do projeto:
REM   lan_messenger\build_exe.cmd
REM Requer: pip install pyinstaller lan_messenger\requirements.txt
cd /d "%~dp0.."
pip install pyinstaller
pyinstaller --noconfirm lan_messenger\LANMessenger.spec
echo.
echo EXE em dist\LANMessenger.exe
pause
