import sqlite3
from typing import List, Tuple, Optional

DB_NAME = "rss_archive.db"

def get_connection():
    """Veritabanı bağlantısı açar ve foreign key denetimini aktif eder."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Sonuçları sözlük gibi sütun adıyla okumayı sağlar
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Tabloları oluşturur."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. RSS Kaynakları (feeds) Tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feeds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                category TEXT DEFAULT 'Genel'
            )
        """)
        
        # 2. Makaleler/Haberler (articles) Tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feed_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                link TEXT NOT NULL UNIQUE,
                summary TEXT,
                published_at TEXT,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (feed_id) REFERENCES feeds (id) ON DELETE CASCADE
            )
        """)
        conn.commit()

def add_feed(title: str, url: str, category: str = "Genel") -> Optional[int]:
    """Yeni bir RSS kaynağı ekler; URL zaten varsa None döner."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO feeds (title, url, category) VALUES (?, ?, ?)",
                (title, url, category)
            )
            conn.commit()
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None

def insert_articles(articles_data: List[Tuple[int, str, str, str, str]]) -> int:
    """Makaleleri toplu ekler. UNIQUE(link) sayesinde önceden eklenenleri atlar."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT OR IGNORE INTO articles (feed_id, title, link, summary, published_at)
            VALUES (?, ?, ?, ?, ?)
        """, articles_data)
        conn.commit()
        return cursor.rowcount

def get_all_feeds():
    """Kayıtlı tüm akış kaynaklarını döner."""
    with get_connection() as conn:
        return conn.execute("SELECT * FROM feeds").fetchall()

def get_recent_articles(limit: int = 10):
    """En son eklenen haberleri kaynak adıyla birlikte getirir."""
    query = """
        SELECT a.id, a.title, a.link, a.published_at, a.is_read, f.title AS feed_title
        FROM articles a
        JOIN feeds f ON a.feed_id = f.id
        ORDER BY a.id DESC
        LIMIT ?
    """
    with get_connection() as conn:
        return conn.execute(query, (limit,)).fetchall()
def push_article_fifo(feed_id: int, title: str, link: str, summary: str, published_at: str, max_limit: int = 10) -> bool:
    """Belirli bir feed_id için haber ekler ve o kaynağa ait haber sayısını 10'da sabit tutar."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR IGNORE INTO articles (feed_id, title, link, summary, published_at)
            VALUES (?, ?, ?, ?, ?)
        """, (feed_id, title, link, summary, published_at))
        
        if cursor.rowcount == 0:
            return False
        
        # Sadece bu feed_id'ye ait en son 10 haber dışındakileri sil
        cursor.execute(f"""
            DELETE FROM articles
            WHERE feed_id = ? AND id NOT IN (
                SELECT id FROM articles
                WHERE feed_id = ?
                ORDER BY id DESC
                LIMIT {max_limit}
            )
        """, (feed_id, feed_id))
        conn.commit()
        return True

def get_live_10_articles(feed_id: int = 1):
    """Seçili kaynağa ait son 10 haberi getirir."""
    with get_connection() as conn:
        return conn.execute("""
            SELECT id, title, summary, link, published_at
            FROM articles
            WHERE feed_id = ?
            ORDER BY id DESC
            LIMIT 10
        """, (feed_id,)).fetchall()

def seed_default_feeds():
    """Varsayılan 4 RSS kaynağını feeds tablosuna ID'leriyle birlikte kaydeder."""
    defaults = [
        (1, "NTV Gündem", "https://www.ntv.com.tr/gundem.rss", "Haber"),
        (2, "TRT Haber", "https://www.trthaber.com/manset_articles.rss", "Haber"),
        (3, "BBC Türkçe", "https://feeds.bbci.co.uk/turkce/rss.xml", "Haber"),
        (4, "Anadolu Ajansı", "https://www.aa.com.tr/tr/rss/default?cat=guncel", "Haber")
    ]
    with get_connection() as conn:
        cursor = conn.cursor()
        for feed_id, title, url, category in defaults:
            cursor.execute("""
                INSERT OR IGNORE INTO feeds (id, title, url, category)
                VALUES (?, ?, ?, ?)
            """, (feed_id, title, url, category))
        conn.commit()