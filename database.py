import sqlite3
import datetime
import logging
import hashlib


class Database:
    """Class to handle all database operations"""

    def __init__(self, db_path="ainews.db"):
        self.db_path = db_path
        self.setup_database()

    def setup_database(self):
        """Initialize database tables and indexes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create article table with improved schema
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT,
            url TEXT UNIQUE,
            published_date TEXT,
            source TEXT,
            scrape_date TEXT,
            keywords TEXT
        )
        ''')

        # Create a cache table to store HTTP responses
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS request_cache (
            url_hash TEXT PRIMARY KEY,
            url TEXT UNIQUE,
            response TEXT,
            headers TEXT,
            timestamp TEXT
        )
        ''')

        # Create index for faster lookups
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_url ON articles (url)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_source ON articles (source)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_date ON articles (published_date)')

        conn.commit()
        conn.close()
        logging.info("Database setup complete")

    def get_existing_urls(self):
        """Get list of URLs already in the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT url FROM articles')
        urls = { url for (url,) in cursor.fetchall() }
        conn.close()
        logging.info(f"Loaded {len(urls)} existing URLs from database")
        return urls

    def get_cached_response(self, url_hash):
        """Get cached response from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            'SELECT response, timestamp FROM request_cache WHERE url_hash = ?',
            (url_hash,)
        )
        result = cursor.fetchone()
        conn.close()

        return result

    def save_to_cache(self, url_hash, url, content, timestamp):
        """Save response to database cache"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                'INSERT OR REPLACE INTO request_cache (url_hash, url, response, timestamp) VALUES (?, ?, ?, ?)',
                (url_hash, url, content, timestamp)
            )
            conn.commit()
        except Exception as e:
            logging.error(f"Error saving to database cache: {e}")
        finally:
            conn.close()

    def save_articles(self, articles):
        """Save articles to the database, update existing ones"""
        if not articles:
            logging.warning("No articles to save to the database")
            return 0

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        saved_count = 0
        for article in articles:
            try:
                # Ensure 'keywords' defaults to empty string if None
                keywords = article.get('keywords', "")
                if keywords is None:
                    keywords = ""

                cursor.execute('''
                INSERT INTO articles
                (title, content, url, published_date, source, scrape_date, keywords)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    title = excluded.title,
                    content = excluded.content,
                    published_date = excluded.published_date,
                    source = excluded.source,
                    scrape_date = excluded.scrape_date,
                    keywords = excluded.keywords;
                ''', (
                    article['title'],
                    article['content'],
                    article['url'],
                    article['published_date'],
                    article['source'],
                    article['scrape_date'],
                    keywords
                ))

                if cursor.rowcount > 0:
                    saved_count += 1
            except Exception as e:
                logging.error(f"Error saving article to the database: {e}")

        conn.commit()
        conn.close()

        logging.info(f"Saved {saved_count} new articles to the database")
        return saved_count

    def clear_old_cache(self, hours=1):
        """Clear database cache entries older than the specified number of hours"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # Calculate the cutoff time based on the current time minus the given hours
            cutoff_time = (datetime.datetime.now() - datetime.timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')

            # Execute the delete query to remove cache entries older than the cutoff time
            cursor.execute('DELETE FROM request_cache WHERE timestamp < ?', (cutoff_time,))
            cleared_count = cursor.rowcount
            conn.commit()
            conn.close()
            logging.info(f"Cleared {cleared_count} old entries from database cache")
            return cleared_count
        except Exception as e:
            logging.error(f"Error clearing database cache: {e}")
            return 0

    def reset_visited_urls(self):
        """Clear the list of visited URLs in the database"""
        try:
            with self.conn:
                self.conn.execute("DELETE FROM cache WHERE 1=1")
            logging.info("Reset visited URLs in database")
            return True
        except Exception as e:
            logging.error(f"Error resetting visited URLs: {e}")
            return False

    def clear_all_cache(self):
        """Clear all cache entries from the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM request_cache')
            cleared_count = cursor.rowcount
            conn.commit()
            conn.close()
            logging.info(f"Cleared {cleared_count} entries from database cache")
            return cleared_count
        except Exception as e:
            logging.error(f"Error clearing all database cache: {e}")
            return 0

