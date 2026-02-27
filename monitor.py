import os
import time
import re
import subprocess
import threading  # NOWOŚĆ: Pozwala na wykonywanie zadań "w tle"
import keyboard   # NOWOŚĆ: Pozwala skryptowi reagować na klawisze

from path import FOLDERS_CONFIG

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class MultiFolderRenameHandler(FileSystemEventHandler):
    """
    Klasa obsługująca zmianę nazw dla konkretnego folderu i przedrostka.
    """
    def __init__(self, folder_path, prefix):
        self.folder_path = folder_path
        self.prefix = prefix
        
        self.pattern_str = r"^" + re.escape(self.prefix) + r"(\d{4})\."
        self.pattern = re.compile(self.pattern_str)
        
        initial_highest = self._get_highest_number()
        print(f"[{self.prefix}] Monitorowanie aktywne. Aktualnie najwyższy numer to: {initial_highest:04d}")

    def _get_highest_number(self):
        highest = 0
        if not os.path.exists(self.folder_path):
            return 0
            
        for filename in os.listdir(self.folder_path):
            match = self.pattern.search(filename)
            if match:
                num = int(match.group(1))
                if num > highest:
                    highest = num
        return highest

    def on_created(self, event):
        if event.is_directory:
            return
        src_path = event.src_path
        self._process_new_file(src_path)

    def _process_new_file(self, src_path):
        filename = os.path.basename(src_path)
        
        if self.pattern.match(filename):
            return

        if not self._wait_for_file_ready(src_path):
            print(f"[{self.prefix}] Błąd: Plik {filename} jest zablokowany.")
            return

        current_highest = self._get_highest_number()
        next_number = current_highest + 1
        
        ext = os.path.splitext(src_path)[1]
        
        new_name = f"{self.prefix}{next_number:04d}{ext}"
        new_path = os.path.join(self.folder_path, new_name)
        
        try:
            # Zmiana nazwy pliku
            os.rename(src_path, new_path)
            print(f"[{self.prefix}] Sukces: {filename} -> {new_name}")
            
            try:
                # 1. Kopiowanie pełnej ŚCIEŻKI do schowka
                subprocess.run(
                    ["powershell", "-command", f"Set-Clipboard -Value '{new_path}'"],
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                print(f"[{self.prefix}] Ścieżka skopiowana! Wklej ją w oknie przeglądarki i wciśnij ENTER.")
                
                # Wyciągamy Tag Sprzętu (czyli nazwę bez .jpg), np. "S-KAS-0005"
                tag_sprzetu = os.path.splitext(new_name)[0]
                
                # 2. Uruchamiamy "nasłuchiwanie" klawisza ENTER w tle
                # Aby nie blokować skryptu, robimy to w osobnym wątku
                threading.Thread(target=self._wait_for_enter_and_copy_tag, args=(tag_sprzetu,)).start()
                
            except Exception as clip_err:
                print(f"[{self.prefix}] Błąd podczas operacji na schowku: {clip_err}")
                
        except Exception as e:
            print(f"[{self.prefix}] Błąd zmiany nazwy pliku {filename}: {e}")

    def _wait_for_enter_and_copy_tag(self, tag):
        """
        Czeka na wciśnięcie klawisza ENTER przez użytkownika,
        a następnie ładuje do schowka Tag Sprzętu.
        """
        # Skrypt w tym miejscu czeka, aż naciśniesz Enter
        keyboard.wait('enter') 
        
        # Dajemy systemowi ułamek sekundy na zamknięcie okienka wyboru pliku
        time.sleep(0.5) 
        
        try:
            # Nadpisujemy schowek samym Tagiem
            subprocess.run(
                ["powershell", "-command", f"Set-Clipboard -Value '{tag}'"],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            print(f" ---> Tag '{tag}' załadowany do schowka! Możesz wkleić go w formularzu.")
        except Exception as e:
            print(f"Błąd przy kopiowaniu tagu: {e}")

    def _wait_for_file_ready(self, filepath, max_retries=15, delay=1):
        for _ in range(max_retries):
            try:
                with open(filepath, 'a'):
                    pass
                return True
            except (IOError, PermissionError):
                time.sleep(delay)
        return False


def start_multi_monitoring(folders_config):
    observer = Observer()
    active_watches = 0
    
    for folder_path, prefix in folders_config.items():
        if not os.path.exists(folder_path):
            print(f"OSTRZEŻENIE: Folder nie istnieje i zostanie pominięty: {folder_path}")
            continue
            
        event_handler = MultiFolderRenameHandler(folder_path, prefix)
        observer.schedule(event_handler, folder_path, recursive=False)
        active_watches += 1

    if active_watches == 0:
        print("Błąd: Nie znaleziono żadnego z podanych folderów. Sprawdź ścieżki.")
        return

    observer.start()
    print("\n--- Monitorowanie rozpoczęte pomyślnie! ---")
    print("Naciśnij Ctrl+C, aby zatrzymać.\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nZatrzymano monitorowanie.")
        
    observer.join()


if __name__ == "__main__":
    # SŁOWNIK KONFIGURACY w pliku path.py
    
    start_multi_monitoring(FOLDERS_CONFIG)