import os
import time
import re
import subprocess  # NOWOŚĆ: Moduł pozwalający Pythonowi rozmawiać z Windowsem
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class MultiFolderRenameHandler(FileSystemEventHandler):
    """
    Klasa obsługująca zmianę nazw dla konkretnego folderu i przedrostka.
    Wersja dynamicznie sprawdzająca najwyższy numer przed każdą zmianą nazwy.
    """
    def __init__(self, folder_path, prefix):
        self.folder_path = folder_path
        self.prefix = prefix
        
        # Generujemy wzorzec wyszukiwania dla danego prefiksu (np. S-UPS-0001)
        self.pattern_str = r"^" + re.escape(self.prefix) + r"(\d{4})\."
        self.pattern = re.compile(self.pattern_str)
        
        # Wyświetlamy informację startową
        initial_highest = self._get_highest_number()
        print(f"[{self.prefix}] Monitorowanie aktywne. Aktualnie najwyższy numer to: {initial_highest:04d}")

    def _get_highest_number(self):
        """
        Przeszukuje folder i zwraca najwyższy numer dla zadanego prefiksu.
        Dzięki wywoływaniu tej funkcji na bieżąco, zawsze mamy aktualny stan folderu.
        """
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
        """Reaguje na pojawienie się nowego pliku."""
        if event.is_directory:
            return
        
        src_path = event.src_path
        self._process_new_file(src_path)

    def _process_new_file(self, src_path):
        """Przetwarza nowy plik: czeka na odblokowanie, sprawdza aktualny numer i zmienia nazwę."""
        filename = os.path.basename(src_path)
        
        # Sprawdzamy, czy plik przypadkiem nie ma już dobrej nazwy
        if self.pattern.match(filename):
            return

        # Czekamy, aż plik skończy się kopiować
        if not self._wait_for_file_ready(src_path):
            print(f"[{self.prefix}] Błąd: Plik {filename} jest zablokowany.")
            return

        # Zawsze sprawdzamy aktualny najwyższy numer bezpośrednio przed zmianą nazwy
        current_highest = self._get_highest_number()
        next_number = current_highest + 1
        
        ext = os.path.splitext(src_path)[1]
        
        # Budujemy nową nazwę
        new_name = f"{self.prefix}{next_number:04d}{ext}"
        new_path = os.path.join(self.folder_path, new_name)
        
        try:
            # Zmiana nazwy pliku na dysku
            os.rename(src_path, new_path)
            print(f"[{self.prefix}] Sukces: {filename} -> {new_name}")
            
            # NOWOŚĆ: Ukryte polecenie kopiujące plik do schowka Windows
            try:
                subprocess.run(
                    ["powershell", "-command", f"Set-Clipboard -Value '{new_path}'"],
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                print(f"[{self.prefix}] Plik '{new_name}' gotowy do wklejenia (Ctrl+V)!")
            except Exception as clip_err:
                print(f"[{self.prefix}] Błąd podczas kopiowania do schowka: {clip_err}")
                
        except Exception as e:
            print(f"[{self.prefix}] Błąd zmiany nazwy pliku {filename}: {e}")

    def _wait_for_file_ready(self, filepath, max_retries=15, delay=1):
        """Czeka, aż system zwolni blokadę pliku (zakończy kopiowanie)."""
        for _ in range(max_retries):
            try:
                with open(filepath, 'a'):
                    pass
                return True
            except (IOError, PermissionError):
                time.sleep(delay)
        return False


def start_multi_monitoring(folders_config):
    """
    Uruchamia monitorowanie dla wszystkich folderów przekazanych w słowniku.
    """
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
    # SŁOWNIK KONFIGURACYJNY
    FOLDERS_CONFIG = {
        
        r"C:\Users\DawidBraun\Pictures\Ewidencja\Monitory\P24": "DELL-P24-",
        r"C:\Users\DawidBraun\Pictures\Ewidencja\Monitory\P27": "DELL-P27-",
        
        #Siedlec
        r"C:\Users\DawidBraun\Pictures\Ewidencja\SIEDLEC\Kasy Fiskalne": "S-KAS-",
        r"C:\Users\DawidBraun\Pictures\Ewidencja\SIEDLEC\TELEFONY STACJONARNE": "S-STEL-",
        r"C:\Users\DawidBraun\Pictures\Ewidencja\SIEDLEC\UPSy": "S-UPS-",
        r"C:\Users\DawidBraun\Pictures\Ewidencja\SIEDLEC\Skanery kodów kreskowych": "S-SKAN-",
        #Kargowa
        r"C:\Users\DawidBraun\Pictures\Ewidencja\KARGOWA\Kasy Fiskalne": "K-KAS-",
        r"C:\Users\DawidBraun\Pictures\Ewidencja\KARGOWA\TELEFONY STACJONARNE": "K-STEL-",
        r"C:\Users\DawidBraun\Pictures\Ewidencja\KARGOWA\UPSy": "K-UPS-",
        r"C:\Users\DawidBraun\Pictures\Ewidencja\KARGOWA\Skanery kodów kreskowych": "S-SKAN-",
        
    }
    
    start_multi_monitoring(FOLDERS_CONFIG)