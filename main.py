from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
from typing import List, Optional
import datetime
import uvicorn
import logging
from scraper import AINewsScraper  # Import your scraper class

app = FastAPI(
    title="AI News API",
    description="A simple API for searching AI news articles",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Article(BaseModel):
    id: int
    title: str
    content: Optional[str] = None
    url: str
    published_date: Optional[str] = None
    source: str
    scrape_date: str


class ArticlePreview(BaseModel):
    id: int
    title: str
    content: Optional[str] = None
    url: str
    source: str
    published_date: Optional[str] = None
    snippet: Optional[str] = None
    keywords: Optional[str] = None


class SearchResult(BaseModel):
    count: int
    results: List[ArticlePreview]


class CacheClearResponse(BaseModel):
    status: str
    message: str


def get_db_connection():
    conn = sqlite3.connect("ainews.db")
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/", tags=["Root"])
async def root():
    return {"message": "Welcome to the AI News API"}


@app.get("/articles", response_model=SearchResult, tags=["Articles"])
async def get_articles(
        query: Optional[str] = Query(None, description="Search term"),
        page: int = Query(1, description="Page number", ge=1),
        limit: int = Query(10, description="Number of results per page", ge=1, le=100),
        source: Optional[str] = Query(None, description="Filter by source"),
        start_date: Optional[str] = Query(None, description="Filter by start published date (YYYY-MM-DD)"),
        end_date: Optional[str] = Query(None, description="Filter by end published date (YYYY-MM-DD)")
):
    conn = get_db_connection()
    cursor = conn.cursor()

    offset = (page - 1) * limit

    # Base query
    base_query = "SELECT id, title, url, published_date, source, scrape_date, content, keywords FROM articles"
    count_query = "SELECT COUNT(*) FROM articles"

    where_clauses = []
    params = []

    if query:
        where_clauses.append("(title LIKE ? OR content LIKE ?)")
        search_term = f"%{query}%"
        params.extend([search_term, search_term])

    if source:
        where_clauses.append("source = ?")
        params.append(source)

    if start_date:
        where_clauses.append("published_date >= ?")
        params.append(start_date)

    if end_date:
        where_clauses.append("published_date <= ?")
        params.append(end_date)

    if where_clauses:
        where_statement = " WHERE " + " AND ".join(where_clauses)
        base_query += where_statement
        count_query += where_statement

    # Get total count
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()[0]

    # Get articles with pagination
    cursor.execute(f"{base_query} ORDER BY published_date DESC LIMIT ? OFFSET ?", params + [limit, offset])
    rows = cursor.fetchall()

    results = []
    for row in rows:
        content = row["content"] or ""
        snippet = content[:150] + "..." if content and len(content) > 150 else content

        if query and content and query.lower() in content.lower():
            start_pos = content.lower().find(query.lower())
            start = max(0, start_pos - 75)
            end = min(len(content), start_pos + len(query) + 75)
            snippet = "..." + content[start:end] + "..."

        results.append(
            ArticlePreview(
                id=row["id"],
                title=row["title"],
                content=row["content"],
                url=row["url"],
                source=row["source"],
                published_date=row["published_date"],
                snippet=snippet,
                keywords=row["keywords"]
            )
        )

    conn.close()

    return SearchResult(count=total_count, results=results)


@app.get("/articles/{article_id}", response_model=Article, tags=["Articles"])
async def get_article(article_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM articles WHERE id = ?", (article_id,))
    row = cursor.fetchone()

    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Article not found")

    return Article(
        id=row["id"],
        title=row["title"],
        content=row["content"],
        url=row["url"],
        published_date=row["published_date"],
        source=row["source"],
        scrape_date=row["scrape_date"]
    )


@app.post("/scrape", tags=["Scraping"])
async def trigger_scraping():
    try:
        # Create an instance of the scraper class
        scraper = AINewsScraper()

        # Call the scraper method to fetch articles
        scraped_count = scraper.scrape_khaleejtimes_ai(pages=3, use_ai_term=True, max_articles_per_page=10)

        if scraped_count == 0:
            return {"status": "success", "message": "No new articles to scrape."}

        return {"status": "success", "message": f"Successfully scraped {scraped_count} articles."}

    except Exception as e:
        logging.error(f"Error occurred during scraping: {e}")
        raise HTTPException(status_code=500, detail=f"Error during scraping: {str(e)}")


@app.get("/sources", tags=["Sources"])
async def get_sources():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT source FROM articles")
    sources = [row["source"] for row in cursor.fetchall()]

    conn.close()

    return {"sources": sources}


@app.get("/stats", tags=["Statistics"])
async def get_stats():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get total article count
    cursor.execute("SELECT COUNT(*) FROM articles")
    total_articles = cursor.fetchone()[0]

    # Get count by source
    cursor.execute("SELECT source, COUNT(*) as count FROM articles GROUP BY source")
    source_counts = {row["source"]: row["count"] for row in cursor.fetchall()}

    # Get latest article date
    cursor.execute("SELECT MAX(scrape_date) FROM articles")
    latest_scrape = cursor.fetchone()[0]

    conn.close()

    return {
        "total_articles": total_articles,
        "by_source": source_counts,
        "latest_update": latest_scrape
    }


@app.post("/clear_all_cache", response_model=CacheClearResponse)
async def clear_all_cache():
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect("ainews.db")
        cursor = conn.cursor()

        # Execute the DELETE query to clear all entries in the request_cache table
        cursor.execute('DELETE FROM request_cache')
        cleared_count = cursor.rowcount  # Get the number of deleted rows

        # Commit the transaction and close the connection
        conn.commit()
        conn.close()

        # Log the cleared count
        logging.info(f"Cleared {cleared_count} entries from database cache")

        # Return the success response
        if cleared_count == 0:
            raise HTTPException(status_code=404, detail="No cache entries to clear")

        return CacheClearResponse(
            status="success",
            message=f"Cleared {cleared_count} cache entries."
        )

    except Exception as e:
        # Log the error if any exception occurs
        logging.error(f"Error clearing all database cache: {e}")
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
