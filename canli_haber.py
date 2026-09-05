import os
import sys
import time
import html
import msvcrt
import webbrowser
from datetime import datetime
import feedparser
from bs4 import BeautifulSoup
from colorama import init, Fore, Style

# database.py modülünden gerekli fonksiyonlar
from database import init_db, push_article_fifo, get_live_10_articles, seed_default_feeds

# Windows CMD ANSI renk uyumluluğunu başlat
init(autoreset=True)

KAYNAKLAR = {
    "1": {"id": 1, "ad": "NTV Gündem", "url": "https://www.ntv.com.tr/gundem.rss"},
    "2": {"id": 2, "ad": "TRT Haber", "url": "https://www.trthaber.com/manset_articles.rss"},
    "3": {"id": 3, "ad": "BBC Türkçe", "url": "https://feeds.bbci.co.uk/turkce/rss.xml"},
    "4": {"id": 4, "ad": "Anadolu Ajansı", "url": "https://www.aa.com.tr/tr/rss/default?cat=guncel"}
}

YENILEME_SURESI = 300  # 5 dakika (saniye)

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def clean_html(raw_html: str) -> str:
    if not raw_html:
        return "Özet bulunmuyor."
    soup = BeautifulSoup(raw_html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    return html.unescape(text)

def update_feed(feed_key: str) -> int:
    kaynak = KAYNAKLAR[feed_key]
    feed = feedparser.parse(kaynak["url"])
    
    if not feed.entries:
        return 0

    en_guncel_10 = feed.entries[:10]
    yeni_sayac = 0
    
    for entry in reversed(en_guncel_10):
        title = getattr(entry, "title", "Başlıksız")
        link = getattr(entry, "link", "")
        summary = clean_html(getattr(entry, "summary", ""))
        published = getattr(entry, "published", "Bilinmiyor")

        if link:
            if push_article_fifo(kaynak["id"], title, link, summary, published, max_limit=10):
                yeni_sayac += 1

    return yeni_sayac

def render_dashboard(aktif_key: str, yeni_adet: int = 0):
    clear_screen()
    kaynak = KAYNAKLAR[aktif_key]
    articles = get_live_10_articles(kaynak["id"])
    su_an = datetime.now().strftime("%H:%M:%S")

    # Üst Başlık Bloğu
    print(Fore.CYAN + Style.BRIGHT + "=" * 85)
    print(f"       CANLI HABER PANOSU | AKTİF KAYNAK: {Fore.YELLOW + kaynak['ad'].upper() + Fore.CYAN} | SAAT: {su_an}")
    print("=" * 85)
    print(f" {Fore.GREEN}[1] NTV  {Fore.WHITE}|  {Fore.GREEN}[2] TRT  {Fore.WHITE}|  {Fore.GREEN}[3] BBC  {Fore.WHITE}|  {Fore.GREEN}[4] AA  {Fore.WHITE}|  {Fore.MAGENTA}[A] Haberi Aç  {Fore.WHITE}|  {Fore.RED}[0] Çıkış")
    print(Fore.CYAN + "-" * 85)

    if not articles:
        print(Fore.YELLOW + "\n [!] Bu kaynak için henüz haber çekilmedi veya liste boş.\n")
    else:
        for sira, art in enumerate(articles, 1):
            ozet = art["summary"]
            kisa_ozet = (ozet[:115] + "...") if len(ozet) > 115 else ozet

            print(f"{Fore.YELLOW}#{sira:02d}{Style.RESET_ALL} | {Fore.WHITE + Style.BRIGHT}{art['title']}")
            print(f"     {Fore.LIGHTBLACK_EX}Özet : {Style.RESET_ALL}{kisa_ozet}")
            print(f"     {Fore.LIGHTBLACK_EX}Tarih: {Fore.LIGHTBLUE_EX}{art['published_at']}")
            print(f"     {Fore.LIGHTBLACK_EX}Link : {Fore.BLUE + Style.DIM}{art['link']}")
            print(Fore.BLACK + Style.BRIGHT + "-" * 85)

def handle_open_browser(aktif_key: str):
    """Kullanıcıdan sıra numarası alıp tarayıcıda ilgili URL'yi açar."""
    kaynak = KAYNAKLAR[aktif_key]
    articles = get_live_10_articles(kaynak["id"])
    
    if not articles:
        print(Fore.RED + "\n[!] Açılacak haber bulunmuyor.")
        time.sleep(1.5)
        return

    sys.stdout.write(Fore.MAGENTA + Style.BRIGHT + "\nAçmak istediğiniz haberin sıra numarasını girin (1-10) [İptal: Enter]: ")
    sys.stdout.flush()
    secim = input().strip()

    if secim.isdigit() and 1 <= int(secim) <= len(articles):
        secilen_haber = articles[int(secim) - 1]
        print(Fore.GREEN + f"[+] Tarayıcıda açılıyor: {secilen_haber['title']}")
        webbrowser.open(secilen_haber["link"])
        time.sleep(1)
    else:
        print(Fore.YELLOW + "[!] İşlem iptal edildi veya geçersiz sıra numarası.")
        time.sleep(1)

def main():
    init_db()
    seed_default_feeds()
    
    aktif_kanal = "1"
    yeni = update_feed(aktif_kanal)
    render_dashboard(aktif_kanal, yeni)
    
    kalan_sure = YENILEME_SURESI

    while True:
        if msvcrt.kbhit():
            tus = msvcrt.getch().decode("utf-8", errors="ignore").lower()
            
            if tus == "0":
                print(Fore.RED + "\n\n[+] Program kapatılıyor...")
                sys.exit(0)
                
            elif tus in KAYNAKLAR:
                aktif_kanal = tus
                print(Fore.YELLOW + f"\n[+] {KAYNAKLAR[aktif_kanal]['ad']} yükleniyor...")
                yeni = update_feed(aktif_kanal)
                render_dashboard(aktif_kanal, yeni)
                kalan_sure = YENILEME_SURESI

            elif tus == "a":
                handle_open_browser(aktif_kanal)
                render_dashboard(aktif_kanal, 0)

        if kalan_sure <= 0:
            yeni = update_feed(aktif_kanal)
            render_dashboard(aktif_kanal, yeni)
            kalan_sure = YENILEME_SURESI

        dakika, saniye = divmod(kalan_sure, 60)
        sys.stdout.write(
            f"\r{Fore.CYAN}[1-4: Kaynak | A: Haberi Aç | 0: Çıkış]{Style.RESET_ALL} Yenilemeye: {Fore.YELLOW}{dakika:02d}:{saniye:02d} {Style.RESET_ALL}"
        )
        sys.stdout.flush()

        time.sleep(1)
        kalan_sure -= 1

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(Fore.RED + "\n\n[+] Çıkış yapıldı.")
        sys.exit(0)