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

# Import konfiguracji
from path import LOCATIONS_CONFIG, MONITORS_CONFIG, DOWNLOADS_FOLDER, API
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Inicjalizacja klienta nowej biblioteki
client = genai.Client(api_key=API)

# =====================================================================
# WSPÓLNE FUNKCJE LOGICZNE
# =====================================================================

def wait_for_file_ready(filepath, max_retries=20, delay=1):
    """Czeka, aż plik zostanie w pełni zapisany na dysku."""
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

def get_highest_number(folder_path, prefix):
    """Przeszukuje folder i znajduje najwyższy numer dla danego prefixu."""
    highest = 0
    if not os.path.exists(folder_path):
        os.makedirs(folder_path, exist_ok=True)
        return 0
        
    pattern = re.compile(r"^" + re.escape(prefix) + r"(\d{4})\.")
    for filename in os.listdir(folder_path):
        match = pattern.search(filename)
        if match:
            num = int(match.group(1))
            if num > highest:
                highest = num
    return highest

def wait_for_enter_and_copy_tag(tag):
    """Działa w tle: czeka na klawisz ENTER, upewniając się, że nie złapie starych kliknięć."""
    # 1. Dajemy ułamek sekundy na "ostygnięcie" klawiatury po wcześniejszych akcjach
    time.sleep(0.5)
    
    print(f" [Oczekiwanie] Nasłuchuję klawisza ENTER dla tagu: {tag}...")
    
    # 2. Czekamy na wyraźne, fizyczne wciśnięcie klawisza Enter
    while True:
        event = keyboard.read_event()
        if event.event_type == keyboard.KEY_DOWN and event.name == 'enter':
            break

    # 3. Zapas czasu, by przeglądarka zdążyła zatwierdzić formularz
    time.sleep(0.5) 
    
    try:
        subprocess.run(
            ["powershell", "-command", f"Set-Clipboard -Value '{tag}'"],
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        print(f" ---> SUKCES! Tag '{tag}' załadowany do schowka!\n")
    except Exception as e:
        print(f"[!] Błąd przy kopiowaniu tagu: {e}")

def rename_and_process_file(src_path, target_folder, prefix):
    """Zmienia nazwę pliku, przenosi go i odpala operacje na schowku."""
    current_highest = get_highest_number(target_folder, prefix)
    next_number = current_highest + 1
    
    ext = os.path.splitext(src_path)[1]
    new_name = f"{prefix}{next_number:04d}{ext}"
    new_path = os.path.join(target_folder, new_name)
    
    try:
        shutil.move(src_path, new_path)
        print(f"[{prefix}] Sukces! Plik gotowy -> {new_name}")
        
        # 1. Ścieżka do schowka
        subprocess.run(["powershell", "-command", f"Set-Clipboard -Value '{new_path}'"], creationflags=subprocess.CREATE_NO_WINDOW)
        print(f"[{prefix}] Ścieżka skopiowana! Wklej ją w przeglądarce i wciśnij ENTER.")
        
        # 2. Nasłuch na ENTER i sam TAG (nazwa bez rozszerzenia)
        tag_sprzetu = os.path.splitext(new_name)[0]
        threading.Thread(target=wait_for_enter_and_copy_tag, args=(tag_sprzetu,), daemon=True).start()
        
    except Exception as e:
        print(f"[{prefix}] Błąd przy obróbce pliku: {e}")

# =====================================================================
# HANDLERY WATCHDOGA
# =====================================================================

class DownloadsAIHandler(FileSystemEventHandler):
    """Nasłuchuje folderu Pobrane, odpala AI."""
    def __init__(self, location_config):
        self.location_config = location_config

    def on_created(self, event):
        if not event.is_directory: self._process_new_file(event.src_path)

    def on_moved(self, event):
        if not event.is_directory: self._process_new_file(event.dest_path)

    def _process_new_file(self, src_path):
        filename = os.path.basename(src_path).lower()
        if not filename.startswith("multimedia") or not filename.endswith(('.jpg', '.jpeg', '.png')):
            return

        if not wait_for_file_ready(src_path): return

        print(f"\n[AI] Wykryto plik: {filename}. Wysyłam do analizy...")
        
        try:
            img = Image.open(src_path)
            prompt = (
                "Jesteś asystentem do inwentaryzacji sprzętu IT. "
                "Wybierz JEDNĄ kategorię i zwróć TYLKO jej dokładną nazwę (bez kropek): "
                "Kasa Fiskalna, Telefon Stacjonarny, UPS, Skaner kodów, Monitor."
            )
            response = client.models.generate_content(model='gemini-2.5-flash', contents=[prompt, img])
            kategoria = response.text.strip().replace(".", "")
            
            print(f"[AI] Wynik analizy: {kategoria}")

            # Wyjątek dla monitorów
            if kategoria == "Monitor":
                print(f"[AI] Wykryto Monitor! Zostawiam plik '{filename}' w folderze Pobrane.")
                print("[AI] -> Przenieś go ręcznie do folderu P24 lub P27.")
                return

            if kategoria in self.location_config:
                target_folder, prefix = self.location_config[kategoria]
                rename_and_process_file(src_path, target_folder, prefix)
            else:
                print(f"[!] Nieznana kategoria: {kategoria}")
                
        except Exception as e:
            print(f"[AI Error] Błąd AI: {e}")


class ManualMonitorsHandler(FileSystemEventHandler):
    """Nasłuchuje folderów P24 i P27 pod kątem ręcznie przeciągniętych zdjęć."""
    def __init__(self, target_folder, prefix):
        self.target_folder = target_folder
        self.prefix = prefix

    def on_created(self, event):
        if not event.is_directory: self._process_dropped_file(event.src_path)

    def on_moved(self, event):
        if not event.is_directory: self._process_dropped_file(event.dest_path)

    def _process_dropped_file(self, src_path):
        filename = os.path.basename(src_path)
        
        # Ignorujemy pliki, które już mają poprawną nazwę (np. DELL-P24-0010.jpg) 
        # w przeciwnym razie wpadniemy w nieskończoną pętlę!
        if filename.startswith(self.prefix) or not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            return
            
        if not wait_for_file_ready(src_path): return

        print(f"\n[RĘCZNE] Wykryto przeciągnięty monitor: {filename}")
        rename_and_process_file(src_path, self.target_folder, self.prefix)

# =====================================================================
# START APLIKACJI
# =====================================================================

def show_menu_and_get_location():
    print("=======================================")
    print("   AUTOMATYCZNA EWIDENCJA SPRZĘTU IT")
    print("=======================================")
    print("1. SIEDLEC")
    print("2. KARGOWA")
    print("3. WIELICHOWO")
    print("4. PRZEMET")
    print("=======================================")
    
    opcje = {"1": "SIEDLEC", "2": "KARGOWA", "3": "WIELICHOWO", "4": "PRZEMET"}
    
    while True:
        wybor = input("Wpisz numer (1-4) i zatwierdź ENTER: ").strip()
        if wybor in opcje:
            return opcje[wybor]

def start_monitoring(location_name):
    selected_config = LOCATIONS_CONFIG.get(location_name)
    if not selected_config: return

    observer = Observer()
    
    # 1. Nasłuch dla Pobranych (AI)
    ai_handler = DownloadsAIHandler(selected_config)
    observer.schedule(ai_handler, DOWNLOADS_FOLDER, recursive=False)
    
    # 2. Nasłuch dla folderu P24 (Ręczne)
    p24_folder, p24_prefix = MONITORS_CONFIG["P24"]
    os.makedirs(p24_folder, exist_ok=True)
    p24_handler = ManualMonitorsHandler(p24_folder, p24_prefix)
    observer.schedule(p24_handler, p24_folder, recursive=False)
    
    # 3. Nasłuch dla folderu P27 (Ręczne)
    p27_folder, p27_prefix = MONITORS_CONFIG["P27"]
    os.makedirs(p27_folder, exist_ok=True)
    p27_handler = ManualMonitorsHandler(p27_folder, p27_prefix)
    observer.schedule(p27_handler, p27_folder, recursive=False)
    
    observer.start()
    
    print("\n--- Nasłuchiwanie uruchomione ---")
    print("Monitorowane:")
    print(f" - Folder Pobrane: {DOWNLOADS_FOLDER} (AI)")
    print(f" - Foldery ręczne dla monitorów: P24, P27")
    print("Zminimalizuj to okno. Wciśnij Ctrl+C, aby zamknąć.\n")
    
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nZatrzymano program.")
    observer.join()

if __name__ == "__main__":
    lokalizacja = show_menu_and_get_location()
    print(f"\n=> Załadowano ustawienia dla: {lokalizacja}")
    start_monitoring(lokalizacja)