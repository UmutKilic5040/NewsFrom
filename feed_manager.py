import feedparser
from database import init_db, add_feed, get_all_feeds, insert_articles, get_recent_articles

def sync_feed(feed_id: int, feed_url: str) -> int:
    """Belirli bir RSS kaynağını internetten çeker ve veritabanına ekler."""
    parsed = feedparser.parse(feed_url)
    
    if parsed.bozo:
        print(f"[!] Uyarı: Akış ayrıştırılırken bir sorun yaşandı ({feed_url})")
        
    articles_to_insert = []
    
    for entry in parsed.entries:
        # RSS kaynakları standart dışı olabileceği için getattr ile güvenli okuma yapıyoruz
        title = getattr(entry, "title", "Başlıksız")
        link = getattr(entry, "link", "")
        summary = getattr(entry, "summary", "")
        published = getattr(entry, "published", getattr(entry, "updated", "Bilinmiyor"))
        
        if link:
            articles_to_insert.append((feed_id, title, link, summary, published))
            
    # database.py içindeki toplu ekleme fonksiyonunu çağırıyoruz
    added_count = insert_articles(articles_to_insert)
    return added_count

def sync_all():
    """Veritabanındaki tüm kayıtlı akışları sırayla günceller."""
    feeds = get_all_feeds()
    if not feeds:
        print("[i] Henüz kayıtlı bir RSS kaynağı bulunamadı.")
        return

    print(f"Toplam {len(feeds)} kaynak taranıyor...\n")
    for feed in feeds:
        print(f"-> Taranıyor: {feed['title']}...")
        count = sync_feed(feed["id"], feed["url"])
        print(f"   Sonuç: {count} yeni haber veritabanına eklendi.")

def display_recent_articles(limit: int = 5):
    """Veritabanındaki en son haberleri ekrana şık bir şekilde yazdırır."""
    articles = get_recent_articles(limit=limit)
    print(f"\n--- Son Eklenen {len(articles)} Haber ---")
    for idx, art in enumerate(articles, 1):
        print(f"{idx}. [{art['feed_title']}] {art['title']}")
        print(f"   Tarih: {art['published_at']}")
        print(f"   Link : {art['link']}\n")

if __name__ == "__main__":
    # 1. Tabloların var olduğundan emin olalım
    init_db()
    
    # 2. Test amaçlı iki popüler RSS kaynağı ekleyelim (zaten varsa atlayacaktır)
    add_feed(
        title="Python Software Foundation", 
        url="https://blog.python.org/feeds/posts/default?alt=rss", 
        category="Python"
    )
    add_feed(
        title="Hacker News", 
        url="https://news.ycombinator.com/rss", 
        category="Teknoloji"
    )
    
    # 3. Akışları çekip veritabanına kaydedelim
    sync_all()
    
    # 4. Kaydedilen haberleri ekranda görelim
    display_recent_articles(limit=5)