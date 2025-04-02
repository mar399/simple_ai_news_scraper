from bs4 import BeautifulSoup
from functools import lru_cache
import datetime
import logging
from urllib.parse import urljoin


class ContentExtractor:
    """Class to handle HTML parsing and content extraction"""

    @lru_cache(maxsize=128)
    def extract_article_data(self, url, html_content, fallback_title=None):
        """Extract structured data from article HTML (with LRU caching)"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Extract title with multiple possible selectors
            title_elem = soup.select_one('h1.article-title, h1.headline, div.article-header h1, h1.story-headline')
            title = title_elem.text.strip() if title_elem else fallback_title or "No title found"

            # Try to find the date element with multiple possible selectors
            date_elem = soup.select_one('time, span.date, div.timestamp-latnw-nf,'
                                        'span.timestamp, div.article-info time, div.publish-date')
            published_date = ''

            if date_elem:
                published_date = date_elem.get('datetime', '')
                if not published_date:
                    published_date = date_elem.text.strip()

            if not published_date:
                published_date = datetime.datetime.now().strftime('%Y-%m-%d')

            content_elem = soup.select_one('div.col-lg-9, div.col-md-9, div.col-8 p a')

            content = ""
            if content_elem:
                content = content_elem.text.strip()  # Extract the text from the <a> tag within <p>

            # If no content found, fallback to the first <a> tag text
            if not content:
                link_elem = soup.find('a', href=url)
                if link_elem:
                    content = link_elem.text.strip()  # Fallback to the first <a> tag text
                else:
                    content = ""

            # Extract keywords/tags if available
            keywords = []
            keyword_elems = soup.select('meta[name="keywords"], a.tag, span.tag, div.tags a')
            for elem in keyword_elems:
                if elem.name == 'meta':
                    keywords.extend([k.strip() for k in elem.get('content', '').split(',')])
                else:
                    keywords.append(elem.text.strip())


            return {
                'title': title,
                'content': content,
                'url': url,
                'published_date': published_date,
                'source': 'Khaleej Times',
                'scrape_date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'keywords': ','.join(keywords)
            }

        except Exception as e:
            logging.error(f"Error extracting article data from {url}: {e}")
            return None

    def extract_article_links(self, html_content, base_url='https://www.khaleejtimes.com'):
        """Extract article links from search results page"""
        soup = BeautifulSoup(html_content, 'html.parser')
        articles = []

        # Look for article cards with different possible selectors
        article_elements = soup.select('article.story-card, div.story-card, div.search-result-card, div.card,'
                                       ' article.listing-normal-teasers, article.card-article-list-item,'
                                       'article.list-card-block')

        if not article_elements:
            # If we can't find articles with specific selectors, try to find links within content area
            content_area = soup.select_one('div.main-content, div.search-results, div.content-area')
            if content_area:
                article_elements = content_area.select('a[href*="/article/"], a[href*="/news/"]')

        if not article_elements:
            # Try one more approach - find all <a> tags with href containing certain patterns
            article_elements = soup.select('a[href*="/article/"], a[href*="/news/"], a[href*="/technology/"]')

        for article in article_elements:
            try:
                # Extract article URL based on whether we have a card or direct link
                if article.name == 'a':
                    article_url = article['href']
                    # Check if we can extract a title from the link text
                    title = article.text.strip()
                else:
                    # It's a card element, find the title and link
                    title_elem = article.select_one('h2 a, h3 a, .headline a, .title a')
                    if not title_elem:
                        continue

                    title = title_elem.text.strip()
                    article_url = title_elem['href']

                # Make sure URL is absolute
                if not article_url.startswith('http'):
                    article_url = urljoin(base_url, article_url)

                articles.append({
                    'url': article_url,
                    'title': title
                })

            except Exception as e:
                logging.error(f"Error extracting article link: {e}")
                continue

        return articles

    def get_diagnostic_html(self, html_content, sample_size=10000):
        """Get a sample of HTML for diagnosis"""
        # Return a portion of the HTML for inspection
        return html_content[:sample_size]
