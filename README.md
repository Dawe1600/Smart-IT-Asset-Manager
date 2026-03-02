# Auto Ewidencja IT

Proste narzędzie do automatyzacji procesu ewidencji sprzętu IT, wykorzystujące AI do rozpoznawania urządzeń oraz usprawniające pracę poprzez automatyczne kopiowanie danych do schowka.

## Kluczowe Funkcje

Aplikacja działa w dwóch głównych trybach, aby zapewnić elastyczność i przyspieszyć pracę.

### 1. Tryb Automatyczny (AI)

Ten tryb jest sercem aplikacji i został zaprojektowany do minimalizowania interwencji użytkownika.

- **Monitorowanie Folderu Pobrane**: Skrypt stale obserwuje folder `Pobrane` (skonfigurowany w `path.py`).
- **Wykrywanie Plików AI**: Reaguje na nowe pliki graficzne (`.jpg`, `.png`, `.jpeg`), których nazwa zaczyna się od `multimedia`. Jest to typowy format zapisu zrzutów ekranu lub zdjęć z telefonu w systemie Windows.
- **Analiza Obrazu z Gemini AI**: Wykryty plik jest wysyłany do analizy przez model AI **Google Gemini**. AI ma za zadanie:
    - Zidentyfikować kategorię sprzętu na zdjęciu (np. Kasa Fiskalna, Komputer AIO, UPS, Skaner kodów, Monitor).
    - W przypadku wykrycia **Komputera AIO**, odczytać ze zdjęcia również jego **nazwę**, **model** i **ID produktu**.
- **Automatyczna Organizacja**:
    - **Standardowe urządzenia**: Plik zostaje automatycznie przeniesiony do odpowiedniego folderu (zgodnie z konfiguracją dla danej lokalizacji), a jego nazwa zostaje zmieniona według schematu `PREFIX-NNNN.jpg` (np. `KASA-0015.jpg`).
    - **Komputery AIO**: Plik jest przenoszony do folderu AIO, a jego nazwa jest ustawiana na odczytaną przez AI nazwę komputera.
    - **Monitory**: Jeśli AI rozpozna monitor, plik jest ignorowany i pozostawiany w folderze Pobrane, co pozwala na ręczne przeniesienie go do dedykowanego folderu `P24` lub `P27`.
- **Asystent Schowka**: Po przetworzeniu pliku, skrypt automatycznie inicjuje sekwencję kopiowania kluczowych danych do schowka, aby maksymalnie uprościć wprowadzanie ich do systemu ewidencji. Wystarczy wcisnąć `ENTER`, aby kolejne dane były ładowane do schowka:
    - **Dla urządzeń standardowych**:
        1.  Ścieżka do pliku.
        2.  Tag sprzętu (np. `KASA-0015`).
    - **Dla Komputerów AIO (tryb AI)**:
        1.  Ścieżka do pliku.
        2.  Nazwa komputera (tag).
        3.  Model.
        4.  ID Produktu.

### 2. Tryb Ręczny (Drag-and-Drop)

Ten tryb służy do ewidencji urządzeń z pominięciem analizy AI lub do obsługi wyjątków.

- **Jak to działa?**: Użytkownik przeciąga plik graficzny bezpośrednio do jednego ze skonfigurowanych folderów docelowych (np. do `W:\SIEDLEC\IT\EWIDENCJA\KASY`).
- **Automatyczne Przemianowanie**: Skrypt natychmiast zmienia nazwę pliku na `PREFIX-NNNN.jpg` (zgodnie z konfiguracją folderu) i inicjuje **Asystenta Schowka** (kopiowanie ścieżki i tagu).
- **Obsługa AIO i Monitorów**: Przeciągnięcie pliku do folderu `Komputery_AIO` poprosi użytkownika o ręczne wpisanie nazwy komputera w konsoli. Przeciągnięcie do folderów `P24` lub `P27` automatycznie nada im prefix `P24-` lub `P27-`.

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

## Konfiguracja

Przed pierwszym uruchomieniem należy skonfigurować aplikację.

1.  **Utwórz plik `path.py`**:
    - Znajdź plik `path.py.template`.
    - Skopiuj go i zmień nazwę kopii na `path.py`.

2.  **Uzupełnij `path.py`**:
    - **`API`**: Wklej swój klucz API od Google Gemini. Możesz go uzyskać na stronie [Google AI Studio](https://aistudio.google.com/app/apikey).
    - **`DOWNLOADS_FOLDER`**: Wprowadź pełną ścieżkę do Twojego folderu `Pobrane`.
    - **`LOCATIONS_CONFIG`**: Sprawdź i ewentualnie popraw ścieżki sieciowe dla każdej lokalizacji i kategorii sprzętu.
    - **`MONITORS_CONFIG`**: Sprawdź ścieżki do folderów z monitorami.

    > **Ważne**: Pamiętaj o poprawnym formacie ścieżek w Pythonie (używaj `\\` lub `/`).

## Uruchomienie

Aby uruchomić aplikację, po prostu kliknij dwukrotnie plik `ewidencja.bat`.

- Pojawi się konsola z menu wyboru lokalizacji.
- Wybierz numer odpowiadający Twojej lokalizacji i wciśnij `ENTER`.
- Skrypt rozpocznie nasłuchiwanie w tle. Możesz zminimalizować to okno.

Aby zatrzymać program, wróć do okna konsoli i wciśnij `Ctrl+C`.
