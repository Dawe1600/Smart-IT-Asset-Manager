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

# Import konfiguracji oraz naszej nowej funkcji drukarki
from path import LOCATIONS_CONFIG, MONITORS_CONFIG, DOWNLOADS_FOLDER, API
from printer import zapytaj_i_drukuj

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

client = genai.Client(api_key=API)

# =====================================================================
# GLOBALNE ZABEZPIECZENIE PRZED ZAPĘTLENIEM
# =====================================================================
PROCESSED_FILES = set()

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
    time.sleep(0.5)
    while True:
        event = keyboard.read_event()
        if event.event_type == keyboard.KEY_DOWN and event.name == 'enter':
            break
    time.sleep(0.3)

def set_clipboard(text):
    subprocess.run(["powershell", "-command", f"Set-Clipboard -Value '{text}'"], creationflags=subprocess.CREATE_NO_WINDOW)

def wait_for_enter_and_copy_tag(tag, kategoria):
    print(f" [Oczekiwanie] Nasłuchuję klawisza ENTER dla tagu: {tag}...")
    wait_for_single_enter()
    try:
        set_clipboard(tag)
        print(f" ---> SUKCES! Tag '{tag}' załadowany do schowka!\n")
    except Exception as e:
        print(f"[!] Błąd przy kopiowaniu tagu: {e}")
    
    # Po wklejeniu tagu pytamy o wydruk, korzystając z pliku printer.py
    zapytaj_i_drukuj(tag, kategoria)

def aio_clipboard_sequence(filepath, nazwa, model, id_prod, kategoria):
    print("\n--- ROZPOCZYNAM SEKWENCJĘ WYPEŁNIANIA DLA AIO ---")
    try:
        set_clipboard(filepath)
        print(f"[AIO Krok 1/4] Ścieżka skopiowana. Wklej ją w przeglądarce i zatwierdź ENTER.")
        wait_for_single_enter()

        set_clipboard(nazwa)
        print(f"[AIO Krok 2/4] TAG ({nazwa}) skopiowany. Wklej go i zatwierdź ENTER.")
        wait_for_single_enter()

        set_clipboard(model)
        print(f"[AIO Krok 3/4] Model ({model}) skopiowany. Wklej go i zatwierdź ENTER.")
        wait_for_single_enter()

        set_clipboard(id_prod)
        print(f"[AIO Krok 4/4] ID Produktu ({id_prod}) skopiowane. Gotowe! Możesz wkleić.")
    except Exception as e:
        print(f"[!] Błąd w trakcie sekwencji schowka AIO: {e}")
    
    zapytaj_i_drukuj(nazwa, kategoria)

def smartphone_clipboard_sequence(filepath, tag, model, sn, kategoria):
    print("\n--- ROZPOCZYNAM SEKWENCJĘ WYPEŁNIANIA DLA SMARTFONA ---")
    try:
        set_clipboard(filepath)
        print(f"[Smartfon Krok 1/4] Ścieżka skopiowana. Wklej ją w przeglądarce i zatwierdź ENTER.")
        wait_for_single_enter()

        set_clipboard(tag)
        print(f"[Smartfon Krok 2/4] TAG ({tag}) skopiowany. Wklej go i zatwierdź ENTER.")
        wait_for_single_enter()

        set_clipboard(model)
        print(f"[Smartfon Krok 3/4] Model ({model}) skopiowany. Wklej go i zatwierdź ENTER.")
        wait_for_single_enter()

        set_clipboard(sn)
        print(f"[Smartfon Krok 4/4] Numer Seryjny ({sn}) skopiowany. Gotowe! Możesz wkleić.")
    except Exception as e:
        print(f"[!] Błąd w trakcie sekwencji schowka Smartfona: {e}")
    
    # Po wklejeniu pytamy o wydruk etykiety dla telefonu
    zapytaj_i_drukuj(tag, kategoria)

# =====================================================================
# FUNKCJE PRZENOSZENIA I ZMIANY NAZWY
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

def rename_and_process_standard_file(src_path, target_folder, prefix, kategoria):
    current_highest = get_highest_number(target_folder, prefix)
    next_number = current_highest + 1
    ext = os.path.splitext(src_path)[1]
    new_name = f"{prefix}{next_number:04d}{ext}"
    new_path = os.path.join(target_folder, new_name)
    
    try:
        PROCESSED_FILES.add(new_path.lower())
        shutil.move(src_path, new_path)
        print(f"[{prefix}] Sukces! Zapisano plik -> {new_name}")
        set_clipboard(new_path)
        print(f"[{prefix}] Ścieżka skopiowana! Wklej ją w przeglądarce i wciśnij ENTER.")
        
        tag_sprzetu = os.path.splitext(new_name)[0]
        threading.Thread(target=wait_for_enter_and_copy_tag, args=(tag_sprzetu, kategoria), daemon=True).start()
    except Exception as e:
        print(f"[{prefix}] Błąd przy obróbce pliku: {e}")

def process_aio_file(src_path, target_folder, data_json, kategoria="Komputer AIO"):
    if not os.path.exists(target_folder):
        os.makedirs(target_folder, exist_ok=True)

    nazwa = str(data_json.get("nazwa_komputera") or "Nieznany_AIO").strip()
    model = str(data_json.get("model") or "").strip()
    id_prod = str(data_json.get("id_produktu") or "").strip()

    safe_name = re.sub(r'[\\/*?:"<>|]', "", nazwa)
    ext = os.path.splitext(src_path)[1]
    
    new_name = f"{safe_name}{ext}"
    counter = 1
    while os.path.exists(os.path.join(target_folder, new_name)):
        new_name = f"{safe_name}_{counter}{ext}"
        counter += 1

    new_path = os.path.join(target_folder, new_name)

    try:
        PROCESSED_FILES.add(new_path.lower())
        shutil.move(src_path, new_path)
        print(f"[AIO AI] Sukces! Zapisano plik jako -> {new_name}")
        
        threading.Thread(target=aio_clipboard_sequence, args=(new_path, nazwa, model, id_prod, kategoria), daemon=True).start()
    except Exception as e:
        print(f"[AIO] Błąd przy przenoszeniu pliku AIO: {e}")

def process_smartphone_file(src_path, target_folder, prefix, data_json, kategoria="Smartfon"):
    if not os.path.exists(target_folder):
        os.makedirs(target_folder, exist_ok=True)

    current_highest = get_highest_number(target_folder, prefix)
    next_number = current_highest + 1
    ext = os.path.splitext(src_path)[1]
    
    new_name = f"{prefix}{next_number:04d}{ext}"
    new_path = os.path.join(target_folder, new_name)
    
    model = str(data_json.get("model_smartfona") or "Nieznany_Model").strip()
    sn = str(data_json.get("sn_smartfona") or "Nieznany_SN").strip()
    tag_sprzetu = os.path.splitext(new_name)[0]

    try:
        PROCESSED_FILES.add(new_path.lower())
        shutil.move(src_path, new_path)
        print(f"[{prefix} AI] Sukces! Zapisano plik jako -> {new_name}")
        
        threading.Thread(target=smartphone_clipboard_sequence, args=(new_path, tag_sprzetu, model, sn, kategoria), daemon=True).start()
    except Exception as e:
        print(f"[Smartfon] Błąd przy przenoszeniu pliku: {e}")

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

        if src_path.lower() in PROCESSED_FILES:
            return

        if not wait_for_file_ready(src_path): return

        print(f"\n[AI] Wykryto pobrany plik: {filename}. Czytam dane...")
        
        prompt = """
        Jesteś asystentem do inwentaryzacji sprzętu IT. Przeanalizuj to zdjęcie i zwróć odpowiedź WYŁĄCZNIE w formacie JSON, bez żadnego formatowania markdown (np. bez znaczników ```json) i bez dodatkowego tekstu.
        Zwróć uwagę na wielkie i małe litery oraz nie myl zera z literą O.

        Wymagany format:
        {
          "kategoria": "Kasa Fiskalna" LUB "Telefon Stacjonarny" LUB "UPS" LUB "Skaner kodów" LUB "Monitor" LUB "Komputer AIO" LUB "Telewizor" LUB "Smartfon",
          "nazwa_komputera": "odczytana nazwa urządzenia (tylko w przypadku AIO), np. S-PKar-R4, zostaw puste jeśli to inna kategoria",
          "model": "odczytany model pod nazwą (tylko dla AIO), np. ASUS Vivo AiO V241EA_V241EA, zostaw puste jeśli inna kategoria",
          "id_produktu": "odczytany Identyfikator produktu (tylko dla AIO), zostaw puste jeśli inna kategoria",
          "model_smartfona": "odczytana uproszczona nazwa rynkowa (tylko dla Smartfon), np. Galaxy A16, zostaw puste jeśli inna kategoria",
          "sn_smartfona": "odczytany Numer seryjny (tylko dla Smartfon), np. RFGL11E5WZR, zostaw puste jeśli inna kategoria"
        }
        """

        try:
            img = Image.open(src_path)
        except Exception as e:
            print(f"[!] Błąd przy otwieraniu pliku zdjęcia: {e}")
            return

        max_retries = 3
        
        for attempt in range(1, max_retries + 1):
            try:
                response = client.models.generate_content(model='gemma-3-27b-it', contents=[prompt, img])
                
                match = re.search(r'\{.*\}', response.text, re.DOTALL)
                if not match:
                    print(f"[!] AI zwróciło nierozpoznawalny format: {response.text}")
                    return
                
                dane = json.loads(match.group(0))
                kategoria = dane.get("kategoria", "Nieznana")

                print(f"[AI] Rozpoznana Kategoria: {kategoria}")

                if kategoria == "Monitor":
                    print(f"\n[?] Wykryto Monitor w pliku '{filename}'. Do którego folderu go zapisać?")
                    print("1. P24")
                    print("2. P27")
                    print("3. TV")
                    
                    while True:
                        wybor_mon = input("Wpisz numer (1 lub 2 lub 3) i zatwierdź ENTER: ").strip()
                        if wybor_mon == "1":
                            target_folder, prefix = MONITORS_CONFIG["P24"]
                            kat_do_druku = "Monitor P24"
                            break
                        elif wybor_mon == "2":
                            target_folder, prefix = MONITORS_CONFIG["P27"]
                            kat_do_druku = "Monitor P27"
                            break
                        elif wybor_mon == "3":
                            target_folder, prefix = LOCATIONS_CONFIG["Telewizor"]
                            kat_do_druku = "Telewizor"
                            break
                        else:
                            print("[!] Niepoprawny wybór. Wpisz 1 lub 2 lub 3.")
                    
                    rename_and_process_standard_file(src_path, target_folder, prefix, kat_do_druku)
                    return 
                
                elif kategoria == "Komputer AIO":
                    target_folder = self.location_config["Komputer AIO"][0]
                    process_aio_file(src_path, target_folder, dane, kategoria)
                
                elif kategoria == "Smartfon":
                    target_folder, prefix = self.location_config["Smartfon"]
                    process_smartphone_file(src_path, target_folder, prefix, dane, kategoria)

                elif kategoria in self.location_config:
                    target_folder, prefix = self.location_config[kategoria]
                    rename_and_process_standard_file(src_path, target_folder, prefix, kategoria)
                else:
                    print(f"[!] Nieznana kategoria z AI: {kategoria}")
                    
                break 

            except json.JSONDecodeError as json_err:
                 print(f"[AI Error] Błąd parsowania JSON: {json_err}")
                 break 
                 
            except Exception as e:
                error_msg = str(e).upper()
                if any(err in error_msg for err in ["503", "UNAVAILABLE", "HIGH DEMAND", "429", "TOO MANY REQUESTS", "QUOTA"]):
                    if attempt < max_retries:
                        print(f"[AI] Serwery przeciążone lub osiągnięto limit zapytań (429/503). Czekam 15 sekund i próbuję ponownie (próba {attempt}/{max_retries})...")
                        time.sleep(15)
                    else:
                        print(f"[AI Error] Błąd limitu/przeciążenia. Ostatecznie nie udało się po {max_retries} próbach.")
                else:
                    print(f"[AI Error] Główny Błąd AI: {e}")
                    break

class ManualDropHandler(FileSystemEventHandler):
    def __init__(self, target_folder, prefix, category_name):
        self.target_folder = target_folder
        self.prefix = prefix
        self.category_name = category_name

    def on_created(self, event):
        if not event.is_directory: self._process_dropped_file(event.src_path)

    def on_moved(self, event):
        if not event.is_directory: self._process_dropped_file(event.dest_path)

    def _process_dropped_file(self, src_path):
        filename = os.path.basename(src_path)
        
        if src_path.lower() in PROCESSED_FILES:
            return
            
        if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            return

        if self.prefix and filename.startswith(self.prefix):
            return

        if not wait_for_file_ready(src_path): return

        print(f"\n[RĘCZNE WYMUSZENIE] Wykryto nowy plik w: {self.category_name} -> {filename}")

        if self.category_name == "Komputer AIO":
            nazwa = input(f"Podaj nazwę komputera AIO dla pliku '{filename}' (TAG): ").strip()
            if not nazwa:
                print("[!] Nie podano nazwy. Anulowano ręczne przetwarzanie AIO.")
                return

            ext = os.path.splitext(src_path)[1]
            safe_name = re.sub(r'[\\/*?:"<>|]', "", nazwa)
            new_name = f"{safe_name}{ext}"
            
            counter = 1
            while os.path.exists(os.path.join(self.target_folder, new_name)):
                new_name = f"{safe_name}_{counter}{ext}"
                counter += 1
                
            new_path = os.path.join(self.target_folder, new_name)
            
            try:
                PROCESSED_FILES.add(new_path.lower())
                shutil.move(src_path, new_path)
                print(f"[AIO RĘCZNE] Sukces! Zapisano plik -> {new_name}")
                
                set_clipboard(new_path)
                print(f"[AIO RĘCZNE] Ścieżka skopiowana! Wklej ją i zatwierdź ENTER (tylko Ścieżka -> TAG).")
                threading.Thread(target=wait_for_enter_and_copy_tag, args=(safe_name, "Komputer AIO"), daemon=True).start()
            except Exception as e:
                print(f"[AIO RĘCZNE Błąd] {e}")
                
        else:
            rename_and_process_standard_file(src_path, self.target_folder, self.prefix, self.category_name)

# =====================================================================
# START APLIKACJI
# =====================================================================

def show_menu_and_get_location():
    print("=======================================")
    print("   AUTOMATYCZNA EWIDENCJA SPRZĘTU IT")
    print("=======================================")
    
    locations = list(LOCATIONS_CONFIG.keys())
    for i, location_name in enumerate(locations, 1):
        print(f"{i}. {location_name}")
        
    print("=======================================")
    
    while True:
        try:
            choice = input(f"Wpisz numer (1-{len(locations)}) i zatwierdź ENTER: ").strip()
            choice_index = int(choice) - 1
            if 0 <= choice_index < len(locations):
                return locations[choice_index]
            else:
                print(f"[!] Błędny numer. Podaj liczbę od 1 do {len(locations)}.")
        except ValueError:
            print("[!] To nie jest poprawny numer. Spróbuj ponownie.")

def start_monitoring(location_name):
    selected_config = LOCATIONS_CONFIG.get(location_name)
    if not selected_config: return

    observer = Observer()
    
    ai_handler = DownloadsAIHandler(selected_config)
    observer.schedule(ai_handler, DOWNLOADS_FOLDER, recursive=False)
    
    for kategoria, (folder_path, prefix) in selected_config.items():
        os.makedirs(folder_path, exist_ok=True)
        handler = ManualDropHandler(folder_path, prefix, kategoria)
        observer.schedule(handler, folder_path, recursive=False)

    for kategoria, (folder_path, prefix) in MONITORS_CONFIG.items():
        os.makedirs(folder_path, exist_ok=True)
        handler = ManualDropHandler(folder_path, prefix, f"Monitor {kategoria}")
        observer.schedule(handler, folder_path, recursive=False)
    
    observer.start()
    
    print("\n--- Nasłuchiwanie uruchomione ---")
    print("Monitorowane:")
    print(f" [AI] Folder Pobrane: {DOWNLOADS_FOLDER}")
    print(f" [Ręczne] Foldery dla lokalizacji: {location_name}")
    print(f" [Ręczne] Foldery Monitorów: P24, P27")
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