# Auto Ewidencja

Prosty, ale potężny skrypt do automatyzacji procesu ewidencjonowania plików (np. zdjęć, dokumentów) w systemach, które wymagają ręcznego dodawania załączników i wpisywania ich identyfikatorów.

## Problem

Podczas ewidencjonowania dużej liczby pozycji (np. sprzętu komputerowego, dokumentów) często wykonujemy powtarzalne czynności:
1.  Zapisujemy plik (np. zrzut ekranu, zdjęcie) w odpowiednim folderze.
2.  Ręcznie zmieniamy jego nazwę na zgodną z systemem (np. `SPRZET-0001.jpg`).
3.  W formularzu klikamy "Dodaj załącznik" i wybieramy świeżo zapisany plik.
4.  Ręcznie przepisujemy lub kopiujemy nową nazwę pliku do pola "Identyfikator" w formularzu.

Ten proces jest monotonny i podatny na błędy.

## Rozwiązanie

`Auto Ewidencja` monitoruje wskazane foldery. Gdy pojawi się w nich nowy plik, skrypt automatycznie:
1.  **Zmienia nazwę pliku**, nadając mu kolejny numer w sekwencji (np. `SPRZET-0001`, `SPRZET-0002` itd.).
2.  **Kopiuje pełną ścieżkę** do nowego pliku do schowka.
3.  Czeka, aż wkleisz ścieżkę w oknie wyboru pliku i naciśniesz **ENTER**.
4.  Po wciśnięciu klawisza ENTER, **kopiuje do schowka samą nazwę pliku** (bez rozszerzenia), gotową do wklejenia w pole formularza.

Dzięki temu cała operacja sprowadza się do kilku prostych kroków: "Zapisz plik -> Wklej -> Enter -> Wklej".

## Instalacja i Konfiguracja

### 1. Wymagania wstępne
- Zainstalowany [Python](https://www.python.org/downloads/) (upewnij się, że podczas instalacji zaznaczyłeś opcję "Add Python to PATH").

### 2. Pobranie projektu
Możesz pobrać pliki ręcznie lub użyć Gita:
```bash
git clone https://github.com/twoj-uzytkownik/auto_ewidencja.git
cd auto_ewidencja
```

### 3. Instalacja zależności
Projekt korzysta z zewnętrznych bibliotek. Otwórz wiersz poleceń (CMD) w folderze projektu i wpisz:
```bash
pip install -r requirements.txt
```

### 4. Konfiguracja folderów
To najważniejszy krok. Musisz powiedzieć skryptowi, które foldery ma monitorować.
1.  W głównym folderze projektu znajdź plik `path.py.template` i zrób jego kopię o nazwie `path.py`.
2.  Otwórz plik `path.py` w edytorze tekstu.
3.  Wypełnij słownik `FOLDERS_CONFIG` według wzoru:

```python
# path.py
# Klucz to pełna ścieżka do folderu, a wartość to prefiks dla plików.


FOLDERS_CONFIG = {
    # Przykład 1:
    'C:\Users\TwojaNazwa\Desktop\Faktury': 'FAKTURA-',
    
    # Przykład 2:
    'D:\Zdjecia_sprzetu\Komputery': 'S-KAS-',
    
    # Tutaj dodaj własne wpisy...
}
```

## Użycie

Aby uruchomić monitorowanie, wystarczy kliknąć dwukrotnie plik `ewidencja.bat`.

Pojawi się czarne okno konsoli z informacją o statusie monitorowania. **Nie zamykaj tego okna!** Możesz je zminimalizować. Skrypt będzie działał w tle i czekał na nowe pliki w skonfigurowanych folderach.

Aby zakończyć działanie skryptu, przejdź do okna konsoli i naciśnij `Ctrl+C`.
