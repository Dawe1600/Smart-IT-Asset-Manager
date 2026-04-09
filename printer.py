import os
import qrcode
from PIL import Image, ImageDraw, ImageFont
from niimprint import PrinterClient, SerialTransport

# =====================================================================
# KONFIGURACJA DRUKARKI NIIMBOT B3S
# =====================================================================
NIIMBOT_PORT = "COM6"  # <-- Upewnij się, że masz tu swój port

# Przypisanie kategorii do plików z ikonami
ICONS_MAP = {
    "Monitor": "ikony/monitor.png",
    "Monitor P24": "ikony/monitor.png",
    "Monitor P27": "ikony/monitor.png",
    "Kasa Fiskalna": "ikony/kasa.png",
    "Telefon Stacjonarny": "ikony/telefon_stacjonarny.png",
    "UPS": "ikony/ups.png",
    "Skaner kodów": "ikony/skaner.png",
    "Komputer AIO": "ikony/aio.png",
    "Telewizor": "ikony/tv.png",
    "Smartfon": "ikony/smartfon.png",
    "Laptop": "ikony/laptop.png",
    "Drukarka": "ikony/drukarka.png"
}

def generuj_etykiete(tag, sciezka_ikony, plik_wyjsciowy="temp_etykieta.png"):
    szerokosc, wysokosc = 400, 160
    etykieta = Image.new('RGB', (szerokosc, wysokosc), color='white')
    draw = ImageDraw.Draw(etykieta)
    
    margines_lewy = 25   
    margines_prawy = 30  
    
    # 1. Kod QR
    qr = qrcode.QRCode(box_size=4, border=1)
    qr.add_data(tag)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    
    rozmiar_qr = 120 
    qr_img = qr_img.resize((rozmiar_qr, rozmiar_qr))
    pozycja_y_qr = (wysokosc - rozmiar_qr) // 2
    etykieta.paste(qr_img, (margines_lewy, pozycja_y_qr)) 
    
    # 2. Tekst TAG
    obszar_x_start = margines_lewy + rozmiar_qr + 20 
    dostepna_szerokosc = szerokosc - obszar_x_start - margines_prawy
    rozmiar_czcionki = 38 
    
    def pobierz_szerokosc(tekst, czcionka):
        try:
            return draw.textlength(tekst, font=czcionka)
        except AttributeError:
            return draw.textsize(tekst, font=czcionka)[0]

    try:
        font = ImageFont.truetype("arialbd.ttf", rozmiar_czcionki)
    except IOError:
        font = ImageFont.load_default()

    while pobierz_szerokosc(tag, font) > dostepna_szerokosc and rozmiar_czcionki > 10:
        rozmiar_czcionki -= 2
        try:
            font = ImageFont.truetype("arialbd.ttf", rozmiar_czcionki)
        except IOError:
            break

    szerokosc_tekstu = pobierz_szerokosc(tag, font)
    pozycja_x_tekst = obszar_x_start + (dostepna_szerokosc - szerokosc_tekstu) / 2
    pozycja_y_tekst = 20 
    
    draw.text((pozycja_x_tekst, pozycja_y_tekst), tag, font=font, fill="black")
    
    # 3. Ikonka
    if os.path.exists(sciezka_ikony):
        ikona = Image.open(sciezka_ikony).convert('RGBA')
        rozmiar_ikony = 65 
        
        # Skalowanie w wyższej jakości, żeby nie gubić cienkich linii
        try:
            filtr = Image.Resampling.LANCZOS
        except AttributeError:
            filtr = Image.LANCZOS
            
        ikona = ikona.resize((rozmiar_ikony, rozmiar_ikony), resample=filtr)
        
        # Krok 1: Wklejamy ikonę na czyste, białe tło (pozbywamy się przezroczystości)
        tlo = Image.new("RGB", ikona.size, "white")
        tlo.paste(ikona, (0, 0), ikona)
        
        # Krok 2: Agresywne wymuszanie czerni (każdy szary staje się czarny)
        tlo = tlo.convert("L") # Zamiana na skalę szarości
        tlo = tlo.point(lambda p: 0 if p < 230 else 255) # Poniżej 230 (nawet b. jasny szary) -> czarny
        
        pozycja_x_ikona = int(obszar_x_start + (dostepna_szerokosc - rozmiar_ikony) / 2)
        pozycja_y_ikona = 75 
        
        etykieta.paste(tlo, (pozycja_x_ikona, pozycja_y_ikona))
    else:
        print(f" [!] Brak pliku ikony: {sciezka_ikony}")
        
    etykieta.save(plik_wyjsciowy)
    return plik_wyjsciowy

def drukuj_etykiete(sciezka_obrazu, port_com):
    try:
        obraz = Image.open(sciezka_obrazu).convert("1")
        transport = SerialTransport(port=port_com)
        drukarka = PrinterClient(transport)
        drukarka.print_image(obraz, density=3)
        print(f" [+] Wydrukowano etykietę z pliku {sciezka_obrazu}.")
    except Exception as e:
        print(f"\n [!] Błąd drukowania: {e}")
        print(" [!] Upewnij się, że drukarka jest włączona i apka NIIMBOT wyłączona.")

def zapytaj_i_drukuj(tag, kategoria):
    """Pyta użytkownika o zgodę na wydruk po zakończeniu obsługi schowka (tylko T/N)."""
    while True:
        odp = input(f"\n[Wydruk] Czy wydrukować naklejkę dla '{tag}'? (T/N): ").strip().upper()
        
        if odp == 'T':
            print("[Wydruk] Generowanie i wysyłanie do drukarki...")
            sciezka_ikony = ICONS_MAP.get(kategoria, "")
            plik = generuj_etykiete(tag, sciezka_ikony)
            drukuj_etykiete(plik, NIIMBOT_PORT)
            if os.path.exists(plik):
                os.remove(plik)
            break  # Wychodzimy z pętli po udanym wydruku
            
        elif odp == 'N':
            print("[Wydruk] Pominięto.")
            break  # Wychodzimy z pętli, bo użytkownik anulował
            
        else:
            print(" [!] Niepoprawny wybór. Spróbuj ponownie, wpisując 'T' lub 'N'.")
            
    print("-------------------------------------------------\n")