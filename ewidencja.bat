@echo off
echo Uruchamianie monitora plikow...

:: Przejdź do folderu, w którym znajduje się Twój plik monitor.py
:: Zastąp poniższą ścieżkę właściwą lokalizacją pliku monitor.py!
cd /d "C:\\Programowanie\\auto_ewidencja"

:: Uruchom skrypt
python monitor.py

:: Zablokuj zamknięcie okna w przypadku błędu (pozwoli to przeczytać komunikat)
pause