# Auto Ewidencja IT

Narzędzie do automatyzacji procesu ewidencji sprzętu IT, wykorzystujące AI i OCR do rozpoznawania urządzeń, generowania etykiet oraz usprawniania pracy poprzez automatyczne kopiowanie danych do schowka.

## Kluczowe Funkcje

Aplikacja działa w dwóch głównych trybach, aby zapewnić elastyczność i przyspieszyć pracę.

### 1. Tryb Automatyczny (AI)

Ten tryb jest sercem aplikacji i został zaprojektowany do minimalizowania interwencji użytkownika.

- **Monitorowanie Folderu Pobrane**: Skrypt stale obserwuje folder `Pobrane` (skonfigurowany w `path.py`).
- **Wykrywanie Plików AI**: Reaguje na nowe pliki graficzne (`.jpg`, `.png`, `.jpeg`), których nazwa zaczyna się od `multimedia`.
- **Analiza Obrazu z Gemini AI**: Wykryty plik jest wysyłany do analizy przez model AI **`gemma-3-27b-it`**. AI ma za zadanie:
    - Zidentyfikować kategorię sprzętu na zdjęciu (np. Kasa Fiskalna, Komputer AIO, Smartfon, Laptop, Monitor).
    - W przypadku wykrycia **Komputera AIO**, odczytać ze zdjęcia jego **nazwę**, **model** i **ID produktu** dzięki zaawansowanemu systemowi OCR (Optyczne Rozpoznawanie Znaków).
    - W przypadku wykrycia **Smartfona**, odczytać jego **model** oraz **numer seryjny (SN)** dzięki zaawansowanemu systemowi OCR (Optyczne Rozpoznawanie Znaków).
- **Automatyczna Organizacja**:
    - **Standardowe urządzenia**: Plik zostaje automatycznie przeniesiony do odpowiedniego folderu, a jego nazwa zostaje zmieniona według schematu `PREFIX-NNNN.jpg` (np. `KASA-0015.jpg`).
        - **Wyjątek - Laptopy**: Nazwy plików dla laptopów generowane są bez zer wiodących (np. `LAPTOP12.jpg`).
    - **Komputery AIO i Smartfony**: Plik jest przenoszony do dedykowanego folderu, a jego nazwa jest generowana automatycznie, zachowując dane odczytane przez AI.
    - **Monitory**: Gdy AI rozpozna monitor, aplikacja **zapyta użytkownika**, do którego z podfolderów (`P24`, `P27`, `TV`) ma zostać przypisany.
- **Asystent Schowka**: Po przetworzeniu pliku, skrypt automatycznie inicjuje sekwencję kopiowania kluczowych danych do schowka. Wystarczy wciskać `ENTER`, aby kolejne dane były ładowane:
    - **Urządzenia standardowe**: 1. Ścieżka do pliku, 2. Tag sprzętu (np. `KASA-0015`).
    - **Komputery AIO**: 1. Ścieżka, 2. Nazwa komputera (tag), 3. Model, 4. ID Produktu.
    - **Smartfony**: 1. Ścieżka, 2. Tag sprzętu (np. `SMART-0001`), 3. Model, 4. Numer seryjny.
- **Drukowanie Etykiet**: Po każdej operacji aplikacja pyta, czy wydrukować etykietę.

### 2. Tryb Ręczny (Drag-and-Drop)

Tryb służący do ewidencji z pominięciem AI lub do obsługi wyjątków.

- **Jak to działa?**: Użytkownik przeciąga plik graficzny bezpośrednio do jednego ze skonfigurowanych folderów docelowych (np. do `W:\LOKALIZACJA 1\IT\EWIDENCJA\KASY`).
- **Automatyczne Przemianowanie**: Skrypt natychmiast zmienia nazwę pliku, nadając mu kolejny numer (np. `KASA-0016.jpg`) i inicjuje **Asystenta Schowka**.
- **Obsługa AIO**: Przeciągnięcie pliku do folderu `Komputery_AIO` poprosi użytkownika o ręczne wpisanie nazwy komputera w konsoli.

### 3. Drukowanie Etykiet (NIIMBOT B3S)

Po zaksięgowaniu każdego urządzenia (zarówno w trybie AI, jak i ręcznym), aplikacja oferuje wydruk samoprzylepnej etykiety.

- **Generowanie QR Code**: Tag urządzenia (np. `KASA-0015`) jest zamieniany na kod QR.
- **Tworzenie Obrazu Etykiety**: Za pomocą biblioteki `Pillow`, skrypt generuje obraz etykiety zawierający:
    - Kod QR.
    - Czytelny tag tekstowy.
    - Ikonę kategorii sprzętu (np. ikonę kasy fiskalnej).
- **Wysyłka do Drukarki**: Obraz jest drukowany na drukarce **NIIMBOT B3S** za pośrednictwem portu szeregowego.

## Instalacja

1.  **Sklonuj Repozytorium**:
    ```bash
    git clone https://github.com/twoja-nazwa-uzytkownika/auto_ewidencja.git
    cd auto_ewidencja
    ```

2.  **Utwórz i Aktywuj Środowisko Wirtualne**:
    ```bash
    # Utwórz środowisko
    python -m venv .venv

    # Aktywuj środowisko
    .\.venv\Scripts\activate
    ```

3.  **Zainstaluj Zależności**:
    ```bash
    pip install -r requirements.txt
    ```
    Plik `requirements.txt` zawiera: `google-genai`, `Pillow`, `watchdog`, `keyboard`, `qrcode`, `niimprint`.

## Konfiguracja

Przed pierwszym uruchomieniem należy skonfigurować aplikację.

1.  **Utwórz plik `path.py`**:
    - Znajdź plik `path.py.template`.
    - Skopiuj go i zmień nazwę kopii na `path.py`.

2.  **Uzupełnij `path.py`**:
    - **`API`**: Wklej swój klucz API od Google.
    - **`DOWNLOADS_FOLDER`**: Wprowadź pełną ścieżkę do Twojego folderu `Pobrane`.
    - **`LOCATIONS_CONFIG`**: Sprawdź i popraw ścieżki sieciowe dla każdej lokalizacji i kategorii sprzętu.
    - **`MONITORS_CONFIG`**: Sprawdź ścieżki do folderów z monitorami.

3.  **Skonfiguruj Port Drukarki w `printer.py`**:
    - Otwórz plik `printer.py`.
    - Znajdź linię `NIIMBOT_PORT = "COM6"` i zmień `"COM6"` na port COM, do którego podłączona jest Twoja drukarka NIIMBOT B3S.

    > **Ważne**: Pamiętaj o poprawnym formacie ścieżek w Pythonie (używaj `\\` lub `/`).

## Uruchomienie

Aby uruchomić aplikację, kliknij dwukrotnie plik `ewidencja.bat`.

- Pojawi się konsola z menu wyboru lokalizacji.
- Wybierz numer odpowiadający Twojej lokalizacji i wciśnij `ENTER`.
- Skrypt rozpocznie nasłuchiwanie w tle. Możesz zminimalizować to okno.

Aby zatrzymać program, wróć do okna konsoli i wciśnij `Ctrl+C`.
