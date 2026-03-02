import os
import time
import re
import subprocess
import threading
import keyboard
import shutil
import json
from PIL import Image

# Import nowej biblioteki Google
from google import genai

# Import konfiguracji
from path import LOCATIONS_CONFIG, MONITORS_CONFIG, DOWNLOADS_FOLDER, API
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

client = genai.Client(api_key=API)

# =====================================================================
# WSPÓLNE FUNKCJE LOGICZNE I SCHOWEK
# =====================================================================

def wait_for_file_ready(filepath, max_retries=20, delay=1):
    for _ in range(max_retries):
        if not os.path.exists(filepath):
            return False
        try:
            with open(filepath, 'a'): pass
            return True
        except (IOError, PermissionError):
            time.sleep(delay)
    return False

def wait_for_single_enter():
    """Twardo czeka na jedno fizyczne wciśnięcie klawisza ENTER."""
    time.sleep(0.5)
    while True:
        event = keyboard.read_event()
        if event.event_type == keyboard.KEY_DOWN and event.name == 'enter':
            break
    time.sleep(0.3) # Krótki czas na odpuszczenie klawisza

def set_clipboard(text):
    """Pomocnicza funkcja do wrzucania tekstu do schowka."""
    subprocess.run(["powershell", "-command", f"Set-Clipboard -Value '{text}'"], creationflags=subprocess.CREATE_NO_WINDOW)

# --------------------------
# STANDARDOWY SCHOWEK (Kasy, UPS itp.)
# --------------------------
def wait_for_enter_and_copy_tag(tag):
    print(f" [Oczekiwanie] Nasłuchuję klawisza ENTER dla tagu: {tag}...")
    wait_for_single_enter()
    try:
        set_clipboard(tag)
        print(f" ---> SUKCES! Tag '{tag}' załadowany do schowka!\n")
    except Exception as e:
        print(f"[!] Błąd przy kopiowaniu tagu: {e}")

# --------------------------
# NOWY SCHOWEK DLA AIO (Sekwencja 4 kroków)
# --------------------------
def aio_clipboard_sequence(filepath, nazwa, model, id_prod):
    print("\n--- ROZPOCZYNAM SEKWENCJĘ WYPEŁNIANIA DLA AIO ---")
    try:
        # Krok 1: Ścieżka
        set_clipboard(filepath)
        print(f"[AIO Krok 1/4] Ścieżka zdjęcia skopiowana. Wklej ją w przeglądarce i zatwierdź ENTER.")
        wait_for_single_enter()

        # Krok 2: Nazwa (Tag)
        set_clipboard(nazwa)
        print(f"[AIO Krok 2/4] TAG ({nazwa}) skopiowany. Wklej go i zatwierdź ENTER.")
        wait_for_single_enter()

        # Krok 3: Model
        set_clipboard(model)
        print(f"[AIO Krok 3/4] Model ({model}) skopiowany. Wklej go i zatwierdź ENTER.")
        wait_for_single_enter()

        # Krok 4: ID Produktu
        set_clipboard(id_prod)
        print(f"[AIO Krok 4/4] ID Produktu ({id_prod}) skopiowane. Gotowe! Możesz wkleić.\n")
        print("-------------------------------------------------")
    except Exception as e:
        print(f"[!] Błąd w trakcie sekwencji schowka AIO: {e}")

# =====================================================================
# FUNKCJE PRZENOSZENIA ZDJĘĆ
# =====================================================================

def get_highest_number(folder_path, prefix):
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

def rename_and_process_standard_file(src_path, target_folder, prefix):
    """Obsługa standardowych urządzeń z numeracją prefixową."""
    current_highest = get_highest_number(target_folder, prefix)
    next_number = current_highest + 1
    ext = os.path.splitext(src_path)[1]
    new_name = f"{prefix}{next_number:04d}{ext}"
    new_path = os.path.join(target_folder, new_name)
    
    try:
        shutil.move(src_path, new_path)
        print(f"[{prefix}] Sukces! Plik gotowy -> {new_name}")
        set_clipboard(new_path)
        print(f"[{prefix}] Ścieżka skopiowana! Wklej ją w przeglądarce i wciśnij ENTER.")
        
        tag_sprzetu = os.path.splitext(new_name)[0]
        threading.Thread(target=wait_for_enter_and_copy_tag, args=(tag_sprzetu,), daemon=True).start()
    except Exception as e:
        print(f"[{prefix}] Błąd przy obróbce pliku: {e}")

def process_aio_file(src_path, target_folder, data_json):
    """Specjalna obsługa komputerów AIO - własna nazwa i zabezpieczenie przed nadpisaniem."""
    if not os.path.exists(target_folder):
        os.makedirs(target_folder, exist_ok=True)

    nazwa = data_json.get("nazwa_komputera", "Nieznany_AIO").strip()
    model = data_json.get("model", "").strip()
    id_prod = data_json.get("id_produktu", "").strip()

    # Usuwamy znaki niedozwolone w nazwach plików w Windowsie
    safe_name = re.sub(r'[\\/*?:"<>|]', "", nazwa)
    ext = os.path.splitext(src_path)[1]
    
    # Zabezpieczenie przed duplikatami
    new_name = f"{safe_name}{ext}"
    counter = 1
    while os.path.exists(os.path.join(target_folder, new_name)):
        new_name = f"{safe_name}_{counter}{ext}"
        counter += 1

    new_path = os.path.join(target_folder, new_name)

    try:
        shutil.move(src_path, new_path)
        print(f"[AIO] Sukces! Zapisano plik jako -> {new_name}")
        
        # Uruchamiamy sekwencję w tle
        threading.Thread(
            target=aio_clipboard_sequence, 
            args=(new_path, nazwa, model, id_prod), 
            daemon=True
        ).start()
    except Exception as e:
        print(f"[AIO] Błąd przy przenoszeniu pliku AIO: {e}")

# =====================================================================
# HANDLERY WATCHDOGA
# =====================================================================

class DownloadsAIHandler(FileSystemEventHandler):
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

        print(f"\n[AI] Wykryto plik: {filename}. Czytam dane i układam JSON-a...")
        
        prompt = """
        Jesteś asystentem do inwentaryzacji sprzętu IT. Przeanalizuj to zdjęcie i zwróć odpowiedź WYŁĄCZNIE w formacie JSON, bez żadnego formatowania markdown (np. bez znaczników ```json) i bez dodatkowego tekstu.
        Zwróć uwagę na wielkie i małe litery oraz nie myl zera z literą O.

        Wymagany format:
        {
          "kategoria": "Kasa Fiskalna" LUB "Telefon Stacjonarny" LUB "UPS" LUB "Skaner kodów" LUB "Monitor" LUB "Komputer AIO",
          "nazwa_komputera": "odczytana nazwa urządzenia (tylko w przypadku AIO), np. S-PKar-R4, zostaw puste jeśli to inna kategoria",
          "model": "odczytany model pod nazwą (tylko dla AIO), np. ASUS Vivo AiO V241EA_V241EA, zostaw puste jeśli inna kategoria",
          "id_produktu": "odczytany Identyfikator produktu (tylko dla AIO), zostaw puste jeśli inna kategoria"
        }
        """

        try:
            img = Image.open(src_path)
            response = client.models.generate_content(model='gemini-2.5-flash', contents=[prompt, img])
            
            # Próbujemy odszukać JSON-a w odpowiedzi (na wypadek, gdyby AI mimo wszystko dodało jakieś słowa)
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if not match:
                print(f"[!] AI zwróciło nierozpoznawalny format: {response.text}")
                return
            
            dane = json.loads(match.group(0))
            kategoria = dane.get("kategoria", "Nieznana")

            print(f"[AI] Rozpoznana Kategoria: {kategoria}")

            if kategoria == "Monitor":
                print(f"[AI] Wykryto Monitor! Zostawiam plik '{filename}' w folderze Pobrane (przenieś do P24 lub P27).")
                return
            elif kategoria == "Komputer AIO":
                print(f"[AI OCR] Zczytano AIO - Nazwa: {dane.get('nazwa_komputera')} | Model: {dane.get('model')}")
                target_folder = self.location_config["Komputer AIO"][0]
                process_aio_file(src_path, target_folder, dane)
            elif kategoria in self.location_config:
                target_folder, prefix = self.location_config[kategoria]
                rename_and_process_standard_file(src_path, target_folder, prefix)
            else:
                print(f"[!] Nieznana kategoria zwrócona z AI: {kategoria}")
                
        except json.JSONDecodeError as json_err:
             print(f"[AI Error] Błąd podczas parsowania JSON: {json_err}")
             print(f"Surowa odpowiedź modelu: {response.text}")
        except Exception as e:
            print(f"[AI Error] Główny Błąd AI: {e}")

class ManualMonitorsHandler(FileSystemEventHandler):
    def __init__(self, target_folder, prefix):
        self.target_folder = target_folder
        self.prefix = prefix

    def on_created(self, event):
        if not event.is_directory: self._process_dropped_file(event.src_path)

    def on_moved(self, event):
        if not event.is_directory: self._process_dropped_file(event.dest_path)

    def _process_dropped_file(self, src_path):
        filename = os.path.basename(src_path)
        if filename.startswith(self.prefix) or not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            return
        if not wait_for_file_ready(src_path): return

        print(f"\n[RĘCZNE] Wykryto przeciągnięty monitor: {filename}")
        rename_and_process_standard_file(src_path, self.target_folder, self.prefix)

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
    print(f" - Folder Pobrane: {DOWNLOADS_FOLDER} (AI + OCR AIO)")
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