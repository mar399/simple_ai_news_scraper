import requests
import time
import datetime
import logging
import random
import hashlib
import os
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


class RequestHandler:
    """Class to handle HTTP requests with caching"""

    def __init__(self, db, cache_dir="cache"):
        self.db = db
        self.cache_dir = cache_dir
        self.setup_cache_directory()
        self.session = self.create_session()
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
            'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:88.0) Gecko/20100101 Firefox/88.0'
        ]

    def setup_cache_directory(self):
        """Set up a directory for caching page content"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            logging.info(f"Created cache directory: {self.cache_dir}")

    def create_session(self):
        """Create a requests session with retries and timeouts"""
        session = requests.Session()
        # Configure retries for robustness
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def get_random_headers(self):
        """Get randomized headers for requests"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
            'Upgrade-Insecure-Requests': '1',
        }

    def get_cache_path(self, url):
        """Generate a cache file path for a given URL"""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{url_hash}.html")

    def get_cached_response(self, url):
        """Get a cached response for a URL if it exists and is not too old"""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        cache_path = self.get_cache_path(url)

        # Check if we have a file cache
        if os.path.exists(cache_path):
            # Check if cache is recent (less than 24 hours old)
            cache_age = time.time() - os.path.getmtime(cache_path)
            if cache_age < 86400:  # 24 hours in seconds
                try:
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        logging.info(f"Using file cache for {url}")
                        return f.read()
                except Exception as e:
                    logging.error(f"Error reading cache file: {e}")

        # Check database cache as fallback
        result = self.db.get_cached_response(url_hash)

        if result:
            response_data, timestamp_str = result
            # Check if cache is recent (less than 24 hours old)
            timestamp = datetime.datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            age = datetime.datetime.now() - timestamp

            if age.total_seconds() < 86400:  # 24 hours in seconds
                logging.info(f"Using database cache for {url}")
                return response_data

        return None

    def save_to_cache(self, url, content):
        """Save response to both file and database cache"""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # File cache
        cache_path = self.get_cache_path(url)
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            logging.error(f"Error saving to file cache: {e}")

        # Database cache
        self.db.save_to_cache(url_hash, url, content, timestamp)

    def get_page_content(self, url, visited_urls):
        """Get page content with caching support"""
        # Check if URL is already in our visited set
        if url in visited_urls:
            logging.info(f"Already processed URL: {url}")
            return None

        # Try to get from cache first
        cached_content = self.get_cached_response(url)
        if cached_content:
            return cached_content

        # If not in cache, fetch it
        try:
            logging.info(f"Fetching URL: {url}")
            response = self.session.get(
                url,
                headers=self.get_random_headers(),
                timeout=15
            )
            response.raise_for_status()

            # Save to cache
            self.save_to_cache(url, response.text)

            # Respect robots.txt with a delay
            time.sleep(random.uniform(1.5, 3.5))

            return response.text
        except Exception as e:
            logging.error(f"Error fetching {url}: {e}")
            return None

    def clear_old_file_cache(self, days=7):
        """Clear file cache older than specified days"""
        cutoff_time = time.time() - (days * 86400)
        cleared_count = 0

        try:
            for filename in os.listdir(self.cache_dir):
                filepath = os.path.join(self.cache_dir, filename)
                if os.path.isfile(filepath) and os.path.getmtime(filepath) < cutoff_time:
                    os.remove(filepath)
                    cleared_count += 1
        except Exception as e:
            logging.error(f"Error clearing file cache: {e}")

        logging.info(f"Cleared {cleared_count} old file cache entries")
        return cleared_count