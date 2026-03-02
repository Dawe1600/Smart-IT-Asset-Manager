import os
import time
import re
import subprocess
import threading
import keyboard
import shutil
from PIL import Image

# Import nowej biblioteki Google
from google import genai

# Import konfiguracji z pliku path.py
from path import LOCATIONS_CONFIG, DOWNLOADS_FOLDER, API

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# =====================================================================
# INICJALIZACJA KLIENTA AI Z NOWEJ BIBLIOTEKI
# =====================================================================
client = genai.Client(api_key=API)


class DownloadsMonitorHandler(FileSystemEventHandler):
    """
    Klasa monitorująca folder Pobrane, analizująca zdjęcia przez AI
    i przenosząca je do odpowiednich folderów ewidencyjnych.
    """
    def __init__(self, location_config):
        self.location_config = location_config
        print(f"[*] Rozpoczęto monitorowanie folderu: {DOWNLOADS_FOLDER}")
        print("[*] Czekam na pobranie plików rozpoczynających się od 'multimedia'...\n")

    def on_created(self, event):
        # Wyłapuje pliki, które są od razu tworzone z docelową nazwą (np. zrzuty ekranu, kopiuj-wklej)
        if event.is_directory:
            return
        self._process_new_file(event.src_path)

    def on_moved(self, event):
        # Wyłapuje pliki po zakończeniu pobierania przez przeglądarkę (zmiana z .crdownload na .jpg)
        if event.is_directory:
            return
        self._process_new_file(event.dest_path)

    def _process_new_file(self, src_path):
        filename = os.path.basename(src_path).lower()
        
        # Sprawdzamy, czy plik zaczyna się od "multimedia" i jest obrazem
        if not filename.startswith("multimedia") or not filename.endswith(('.jpg', '.jpeg', '.png')):
            return

        print(f"\n[AI] Wykryto nowy plik: {filename}. Czekam na upewnienie się, że plik jest gotowy...")
        if not self._wait_for_file_ready(src_path):
            print(f"[!] Błąd: Plik {filename} jest zablokowany lub pobieranie nie powiodło się.")
            return

        print(f"[AI] Wysyłam {filename} do analizy (może to potrwać kilka sekund)...")
        kategoria = self._classify_image_with_ai(src_path)
        
        if not kategoria:
            print("[!] AI nie rozpoznało urządzenia z listy.")
            return

        print(f"[AI] Wynik analizy: {kategoria}")

        # Sprawdzamy czy AI zwróciło kategorię która istnieje w naszej konfiguracji
        if kategoria not in self.location_config:
            print(f"[!] Błąd: Kategoria '{kategoria}' nie istnieje w słowniku path.py! Upewnij się, że nazwy się pokrywają.")
            return

        target_folder, prefix = self.location_config[kategoria]
        
        # Upewniamy się, że folder docelowy istnieje
        if not os.path.exists(target_folder):
            os.makedirs(target_folder, exist_ok=True)

        self._move_and_rename_file(src_path, target_folder, prefix)

    def _classify_image_with_ai(self, image_path):
        try:
            img = Image.open(image_path)
            prompt = (
                "Jesteś asystentem do inwentaryzacji sprzętu IT. "
                "Na tym zdjęciu znajduje się urządzenie. "
                "Wybierz JEDNĄ, najbardziej pasującą kategorię z poniższej listy i zwróć TYLKO jej dokładną nazwę (bez żadnych innych słów i znaków interpunkcyjnych): "
                "Kasa Fiskalna, Telefon Stacjonarny, UPS, Skaner kodów, Monitor."
            )
            
            # Użycie nowego API Google
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[prompt, img]
            )
            
            wynik = response.text.strip()
            # Czasem AI dopisze kropkę na końcu, czyścimy to
            wynik = wynik.replace(".", "") 
            return wynik
        except Exception as e:
            print(f"[AI Error] Błąd podczas klasyfikacji obrazu: {e}")
            return None

    def _move_and_rename_file(self, src_path, target_folder, prefix):
        current_highest = self._get_highest_number(target_folder, prefix)
        next_number = current_highest + 1
        
        ext = os.path.splitext(src_path)[1]
        new_name = f"{prefix}{next_number:04d}{ext}"
        new_path = os.path.join(target_folder, new_name)
        
        try:
            # Przeniesienie i zmiana nazwy z Downloads do docelowego miejsca
            shutil.move(src_path, new_path)
            print(f"[{prefix}] Sukces! Przeniesiono plik -> {new_name}")
            
            try:
                # 1. Kopiowanie pełnej ŚCIEŻKI do schowka
                subprocess.run(
                    ["powershell", "-command", f"Set-Clipboard -Value '{new_path}'"],
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                print(f"[{prefix}] Ścieżka skopiowana! Wklej ją w oknie przeglądarki i wciśnij ENTER.")
                
                # Wyciągamy Tag Sprzętu (czyli nazwę bez .jpg), np. "S-KAS-0005"
                tag_sprzetu = os.path.splitext(new_name)[0]
                
                # 2. Uruchamiamy "nasłuchiwanie" klawisza ENTER w tle
                threading.Thread(target=self._wait_for_enter_and_copy_tag, args=(tag_sprzetu,), daemon=True).start()
                
            except Exception as clip_err:
                print(f"[{prefix}] Błąd podczas operacji na schowku: {clip_err}")
                
        except Exception as e:
            print(f"[{prefix}] Błąd przy przenoszeniu pliku: {e}")

    def _get_highest_number(self, folder_path, prefix):
        highest = 0
        if not os.path.exists(folder_path):
            return 0
            
        pattern_str = r"^" + re.escape(prefix) + r"(\d{4})\."
        pattern = re.compile(pattern_str)
            
        for filename in os.listdir(folder_path):
            match = pattern.search(filename)
            if match:
                num = int(match.group(1))
                if num > highest:
                    highest = num
        return highest

    def _wait_for_enter_and_copy_tag(self, tag):
        # Skrypt czeka aż naciśniesz Enter w dowolnym programie
        keyboard.wait('enter') 
        time.sleep(0.5) # Zapas dla systemu operacyjnego
        
        try:
            subprocess.run(
                ["powershell", "-command", f"Set-Clipboard -Value '{tag}'"],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            print(f" ---> Tag '{tag}' załadowany do schowka! Możesz wkleić go w formularzu.\n")
        except Exception as e:
            print(f"Błąd przy kopiowaniu tagu: {e}")

    def _wait_for_file_ready(self, filepath, max_retries=20, delay=1):
        # Czeka, aż Chrome/przeglądarka skończy zapisywać plik
        for _ in range(max_retries):
            if not os.path.exists(filepath):
                 return False
            try:
                with open(filepath, 'a'):
                    pass
                return True
            except (IOError, PermissionError):
                time.sleep(delay)
        return False


def show_menu_and_get_location():
    print("=======================================")
    print("   AUTOMATYCZNA EWIDENCJA SPRZĘTU IT")
    print("=======================================")
    print("Wybierz miejscowość, w której się znajdujesz:")
    print("1. SIEDLEC")
    print("2. KARGOWA")
    print("3. WIELICHOWO")
    print("4. PRZEMET")
    print("=======================================")
    
    opcje = {
        "1": "SIEDLEC",
        "2": "KARGOWA",
        "3": "WIELICHOWO",
        "4": "PRZEMET"
    }
    
    while True:
        wybor = input("Wpisz numer (1-4) i zatwierdź ENTER: ").strip()
        if wybor in opcje:
            wybrana_lokalizacja = opcje[wybor]
            print(f"\n=> Wybrano lokalizację: {wybrana_lokalizacja}")
            return wybrana_lokalizacja
        else:
            print("Niepoprawny wybór. Spróbuj ponownie.")

def start_downloads_monitoring(location_name):
    # Pobieramy słownik ścieżek tylko dla wybranej miejscowości
    selected_config = LOCATIONS_CONFIG.get(location_name)
    
    if not selected_config:
        print("Błąd konfiguracji: Nie znaleziono ustawień dla tej lokalizacji.")
        return

    observer = Observer()
    event_handler = DownloadsMonitorHandler(selected_config)
    
    # Monitorujemy JEDYNIE folder Pobrane
    observer.schedule(event_handler, DOWNLOADS_FOLDER, recursive=False)
    observer.start()
    
    print("\n--- Nasłuchiwanie uruchomione ---")
    print("Zminimalizuj to okno. Wciśnij Ctrl+C, aby zamknąć program.\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nZatrzymano program.")
        
    observer.join()

if __name__ == "__main__":
    lokalizacja = show_menu_and_get_location()
    start_downloads_monitoring(lokalizacja)