import sys
import webbrowser
from database import init_db, add_feed, get_all_feeds, get_recent_articles
from feed_manager import sync_all, sync_feed

def print_menu():
    print("\n" + "=" * 40)
    print("      RSS & HABER ARŞİVLEYİCİ")
    print("=" * 40)
    print("1. Kayıtlı Kaynakları Listele")
    print("2. Yeni RSS Kaynağı Ekle")
    print("3. Tüm Akışları Güncelle (Senkronize Et)")
    print("4. Son Eklenen Haberleri Listele")
    print("5. Haberi Tarayıcıda Aç")
    print("0. Çıkış")
    print("-" * 40)

def handle_list_feeds():
    feeds = get_all_feeds()
    if not feeds:
        print("\n[!] Henüz kayıtlı bir RSS kaynağı yok.")
        return
    
    print("\n--- Kayıtlı RSS Kaynakları ---")
    for f in feeds:
        print(f"ID: {f['id']} | [{f['category']}] {f['title']}")
        print(f"    URL: {f['url']}")

def handle_add_feed():
    print("\n--- Yeni RSS Kaynağı Ekle ---")
    title = input("Kaynak Adı (örn: BBC Teknoloji): ").strip()
    url = input("RSS URL Adresi: ").strip()
    category = input("Kategori (varsayılan 'Genel'): ").strip() or "Genel"

    if not title or not url:
        print("[!] Başlık ve URL boş bırakılamaz.")
        return

    feed_id = add_feed(title=title, url=url, category=category)
    if feed_id:
        print(f"[+] '{title}' başarıyla eklendi (ID: {feed_id}).")
        cevap = input("İçerikleri şimdi çekmek ister misiniz? (e/h): ").strip().lower()
        if cevap == 'e':
            count = sync_feed(feed_id, url)
            print(f"[+] {count} yeni içerik kaydedildi.")
    else:
        print("[!] Bu RSS adresi zaten veritabanında kayıtlı.")

def handle_list_articles():
    try:
        limit = int(input("Kaç adet haber listelensin? (Varsayılan 10): ") or "10")
    except ValueError:
        limit = 10

    articles = get_recent_articles(limit=limit)
    if not articles:
        print("\n[!] Henüz arşivlenmiş haber bulunmuyor.")
        return

    print(f"\n--- Son Eklenen {len(articles)} İçerik ---")
    for art in articles:
        print(f"[{art['id']}] [{art['feed_title']}] {art['title']}")
        print(f"     Tarih: {art['published_at']}")
        print(f"     Link : {art['link']}")

def handle_open_article():
    art_id = input("\nAçmak istediğiniz haberin ID numarasını girin: ").strip()
    if not art_id.isdigit():
        print("[!] Geçerli bir sayı girin.")
        return

    # Veritabanından spesifik haberi çekmek için kısa bir sorgu
    articles = get_recent_articles(limit=100)
    target = next((a for a in articles if a["id"] == int(art_id)), None)

    if target:
        print(f"[+] Tarayıcıda açılıyor: {target['title']}")
        webbrowser.open(target["link"])
    else:
        print("[!] Belirtilen ID'ye sahip haber son arşivlenenler arasında bulunamadı.")

def main():
    init_db()
    while True:
        print_menu()
        secim = input("Seçiminiz (0-5): ").strip()

        if secim == "1":
            handle_list_feeds()
        elif secim == "2":
            handle_add_feed()
        elif secim == "3":
            sync_all()
        elif secim == "4":
            handle_list_articles()
        elif secim == "5":
            handle_open_article()
        elif secim == "0":
            print("\nProgramdan çıkılıyor...")
            sys.exit(0)
        else:
            print("[!] Geçersiz seçim. Lütfen tekrar deneyin.")

if __name__ == "__main__":
    main()