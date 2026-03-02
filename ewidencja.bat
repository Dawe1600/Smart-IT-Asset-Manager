@echo off
echo Uruchamianie monitora plikow...

:: Przejdź do folderu, w którym znajduje się Twój plik monitor.py
cd /d "C:\Programowanie\auto_ewidencja"

:: 1. Aktywuj wirtualne środowisko (.venv)
call .venv\Scripts\activate.bat

:: 2. Uruchom skrypt (teraz użyje Pythona z .venv)
python monitor.py

:: Zablokuj zamknięcie okna w przypadku błędu
pause