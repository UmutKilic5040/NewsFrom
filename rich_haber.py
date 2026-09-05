import os
import sys
import time
import html
import msvcrt
import webbrowser
from datetime import datetime
import feedparser
from bs4 import BeautifulSoup

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from database import init_db, push_article_fifo, get_live_10_articles, seed_default_feeds

console = Console()

KAYNAKLAR = {
    "1": {"id": 1, "ad": "NTV Gündem", "url": "https://www.ntv.com.tr/gundem.rss"},
    "2": {"id": 2, "ad": "TRT Haber", "url": "https://www.trthaber.com/manset_articles.rss"},
    "3": {"id": 3, "ad": "BBC Türkçe", "url": "https://feeds.bbci.co.uk/turkce/rss.xml"},
    "4": {"id": 4, "ad": "Anadolu Ajansı", "url": "https://www.aa.com.tr/tr/rss/default?cat=guncel"}
}

YENILEME_SURESI = 300

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

def build_dashboard(aktif_key: str):
    kaynak = KAYNAKLAR[aktif_key]
    articles = get_live_10_articles(kaynak["id"])
    su_an = datetime.now().strftime("%H:%M:%S")

    # 1. Üst Bilgi Paneli
    ust_bilgi = Text()
    ust_bilgi.append(f"KAYNAK: {kaynak['ad']}  |  SAAT: {su_an}\n", style="bold cyan")
    ust_bilgi.append("[1] NTV   [2] TRT   [3] BBC   [4] AA   |   [A] Haberi Aç   |   [0] Çıkış", style="dim white")
    
    panel = Panel(
        ust_bilgi, 
        title="[bold yellow]CANLI HABER PANOSU[/bold yellow]", 
        box=box.ROUNDED,
        border_style="cyan"
    )

    # 2. Şık Haber Tablosu
    tablo = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold magenta", expand=True)
    tablo.add_column("#", justify="center", style="bold yellow", width=4)
    tablo.add_column("Başlık & Özet", style="white", ratio=3)
    tablo.add_column("Yayın Tarihi", justify="center", style="cyan", width=18)

    for sira, art in enumerate(articles, 1):
        ozet = art["summary"]
        kisa_ozet = (ozet[:110] + "...") if len(ozet) > 110 else ozet
        
        icerik = Text()
        icerik.append(f"{art['title']}\n", style="bold white")
        icerik.append(f"{kisa_ozet}\n", style="dim")
        icerik.append(art['link'], style="underline blue")

        tablo.add_row(f"{sira:02d}", icerik, art['published_at'][:17] if art['published_at'] else "-")

    return panel, tablo

def handle_open_browser(aktif_key: str):
    kaynak = KAYNAKLAR[aktif_key]
    articles = get_live_10_articles(kaynak["id"])
    
    console.print("\n[bold magenta]Açmak istediğiniz sıra numarası (1-10) [İptal: Enter]: [/bold magenta]", end="")
    secim = input().strip()

    if secim.isdigit() and 1 <= int(secim) <= len(articles):
        secilen = articles[int(secim) - 1]
        console.print(f"[green]Tarayıcıda açılıyor: {secilen['title']}[/green]")
        webbrowser.open(secilen["link"])
        time.sleep(1)

def main():
    init_db()
    seed_default_feeds()
    
    aktif_kanal = "1"
    update_feed(aktif_kanal)
    kalan_sure = YENILEME_SURESI

    while True:
        os.system("cls" if os.name == "nt" else "clear")
        panel, tablo = build_dashboard(aktif_kanal)
        console.print(panel)
        console.print(tablo)

        # 1 saniyelik adımlarla tuş kontrolü ve sayaç
        for _ in range(kalan_sure):
            if msvcrt.kbhit():
                tus = msvcrt.getch().decode("utf-8", errors="ignore").lower()
                if tus == "0":
                    console.print("\n[bold red]Program kapatıldı.[/bold red]")
                    sys.exit(0)
                elif tus in KAYNAKLAR:
                    aktif_kanal = tus
                    update_feed(aktif_kanal)
                    kalan_sure = YENILEME_SURESI
                    break
                elif tus == "a":
                    handle_open_browser(aktif_kanal)
                    break

            dakika, saniye = divmod(kalan_sure, 60)
            sys.stdout.write(f"\r \x1b[36mOtomatik yenilemeye:\x1b[0m \x1b[33m{dakika:02d}:{saniye:02d}\x1b[0m ")
            sys.stdout.flush()
            time.sleep(1)
            kalan_sure -= 1

        if kalan_sure <= 0:
            update_feed(aktif_kanal)
            kalan_sure = YENILEME_SURESI

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold red]Çıkış yapıldı.[/bold red]")
        sys.exit(0)