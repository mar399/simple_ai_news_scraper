# AI News Scraper and Search API

A simple web scraper that collects AI-related news from various sources and provides a search API to access the data.

## Features

- Web scraper for AI news articles from a website
- SQLite database for local storage
- FastAPI backend with search functionality
- Simple keyword-based search
- Source filtering and pagination

## Setup and Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/mar399/simple_ai_news_scraper.git
   cd simple_ai_news_scraper
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application

1. Scrape data:

   ```bash
   python scraper.py
   ```

2. Start the FastAPI server:
   ```bash
   python main.py
   ```

3. The API will be available at http://localhost:8000

3. Access the interactive API documentation at http://localhost:8000/docs

## API Endpoints

- `GET /`: Welcome message
- `GET /articles`: List articles with pagination and optional source filtering
- `GET /articles/{article_id}`: Get a specific article by ID
- `GET /sources`: Get a list of all available sources
- `POST /scrape`: Manually trigger the scraper to fetch new articles

## Database

The application uses SQLite for simplicity. The database file (`ainews.db`) will be created in the project root directory when the application is first run.

## How to Use

1. First, make sure the application is running.
2. Trigger a scrape to collect initial data by sending a POST request to `/scrape`.
3. Use the `/search` endpoint to find articles by keyword.
4. Browse articles using the `/articles` endpoint.

## Testing

Run the tests using pytest:
```bash
pytest
```

## Deployment

To deploy to a production environment:

1. Set up a server with Python installed
2. Clone the repository and install dependencies
3. Use a production ASGI server like Gunicorn with Uvicorn workers:
   ```bash
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
   ```

## License

[MIT License](LICENSE)