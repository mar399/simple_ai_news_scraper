
import logging
import time
import random
from database import Database
from request_handler import RequestHandler
from content_extractor import ContentExtractor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("scraper.log"), logging.StreamHandler()]
)


class AINewsScraper:
    """Main class to coordinate scraping operations"""

    def __init__(self, db_path="ainews.db", cache_dir="cache"):
        self.db = Database(db_path)
        self.request_handler = RequestHandler(self.db, cache_dir)
        self.content_extractor = ContentExtractor()
        # Track visited URLs to avoid duplicate scraping
        self.visited_urls = self.db.get_existing_urls()

    def scrape_article_content(self, url, fallback_title=None):
        """Scrape individual article content"""
        # Get cached or fresh content
        html_content = self.request_handler.get_page_content(url, self.visited_urls)
        if not html_content:
            return None

        # Add to visited URLs
        self.visited_urls.add(url)

        # Extract article data from the HTML
        return self.content_extractor.extract_article_data(url, html_content, fallback_title)

    def scrape_khaleejtimes_ai(self, pages=3, use_ai_term=True, max_articles_per_page=10):
        """Scrape AI articles from Khaleej Times"""
        base_url = "https://www.khaleejtimes.com/search"
        search_term = "AI" if use_ai_term else "artificial intelligence"
        articles_data = []
        total_scraped = 0

        for page in range(1, pages + 1):
            # Build the URL with page parameter
            if page == 1:
                url = f"{base_url}?q={search_term.replace(' ', '%20')}"
            else:
                url = f"{base_url}?q={search_term.replace(' ', '%20')}&page={page}"

            logging.info(f"Scraping page {page}: {url}")

            # Get page content (either from cache or fresh)
            html_content = self.request_handler.get_page_content(url, self.visited_urls)
            if not html_content:
                continue

            try:
                # Extract article links from the page
                articles = self.content_extractor.extract_article_links(html_content)

                if not articles:
                    logging.warning(f"No articles found on page {page}. The selector might need updating.")
                    continue

                processed_count = 0
                for article in articles:
                    if processed_count >= max_articles_per_page:
                        break

                    article_url = article['url']
                    title = article['title']

                    # Skip if already processed
                    if article_url in self.visited_urls:
                        continue

                    # Get full article content
                    article_data = self.scrape_article_content(article_url, title)
                    if article_data:
                        articles_data.append(article_data)
                        total_scraped += 1
                        processed_count += 1
                        logging.info(f"Successfully scraped: {title}")

                # If we didn't find any new articles on this page, it might be the last page
                if processed_count == 0:
                    logging.info(f"No new articles found on page {page}. This might be the last page.")
                    break

                # Respect the site's rate limits between pages
                time.sleep(random.uniform(3, 5))

            except Exception as e:
                logging.error(f"Error processing page {page}: {e}")
                continue

        saved_count = self.db.save_articles(articles_data)
        return saved_count

    def clear_old_cache(self, hours=1):
        """Clear old cache entries"""
        file_cleared = self.request_handler.clear_old_file_cache(hours)
        db_cleared = self.db.clear_old_cache(hours)
        total_cleared = file_cleared + db_cleared
        logging.info(f"Cleared a total of {total_cleared} old cache entries")
        return total_cleared


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Scrape AI news articles')
    parser.add_argument('--reset', action='store_true', help='Reset visited URLs before scraping')
    args = parser.parse_args()

    scraper = AINewsScraper()

    # Clear old cache
    scraper.clear_old_cache(hours=1)

    # Reset visited URLs if requested
    if args.reset:
        scraper.db.reset_visited_urls()
        # Also reset the in-memory set
        scraper.visited_urls = set()
        logging.info("Reset visited URLs - will re-scrape all articles")

    # Log the initial state
    logging.info(f"Starting with {len(scraper.visited_urls)} visited URLs in database")

    # Continue with your regular scraping
    ai_articles = scraper.scrape_khaleejtimes_ai(pages=3, use_ai_term=True, max_articles_per_page=10)
    logging.info(f"Scraped {ai_articles} articles using 'AI' as search term")

    ai_full_articles = scraper.scrape_khaleejtimes_ai(pages=3, use_ai_term=False, max_articles_per_page=10)
    logging.info(f"Scraped {ai_full_articles} articles using 'artificial intelligence' as search term")

    total_articles = ai_articles + ai_full_articles
    logging.info(f"Scraped a total of {total_articles} articles")
