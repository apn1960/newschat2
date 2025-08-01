# 📰 Ithaca News Aggregator

A modern news aggregation system that polls RSS feeds from local and regional news sources and provides a beautiful web interface for browsing articles.

## Features

- **RSS Feed Polling**: Automatically fetches articles from multiple local news sources
- **Rich Content Extraction**: Uses newspaper3k to extract full article content and metadata
- **Beautiful Web Interface**: Modern Gradio interface with search and filtering
- **Real-time Updates**: Refresh articles to get the latest news
- **Search & Filter**: Search articles by title, content, or description, filter by publisher

## News Sources

- Ithaca Voice
- 607 News Now
- Ithaca Times
- Cornell Sun
- Ithaca Journal
- Finger Lakes 1
- Tompkins Weekly
- Cornell Chronicle
- Cornell Research
- Ithaca College News

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables**:
   Create a `.env` file with your Supabase credentials:
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   ```

## Usage

### Option 1: Run Everything Together
```bash
python run_app.py
```

This will start both the FastAPI server and Gradio interface.

### Option 2: Run Separately

**Start FastAPI Server**:
```bash
python main.py
```
- FastAPI server runs on http://localhost:8000
- API endpoints available at http://localhost:8000/docs

**Start Gradio Interface**:
```bash
python -c "from main import create_gradio_interface; create_gradio_interface().launch()"
```
- Gradio interface runs on http://localhost:7860

## API Endpoints

- `GET /` - Root endpoint
- `GET /poll` - Poll RSS feeds and insert articles into database
- `GET /list` - Get all articles from database
- `GET /debug-authors` - Debug RSS feed author information
- `GET /test-article/{url}` - Test article extraction from specific URL

## Web Interface Features

- **Search**: Search articles by title, content, or description
- **Filter**: Filter articles by publisher
- **Refresh**: Get the latest articles from the database
- **Article Cards**: Beautiful cards with article previews and direct links
- **Responsive Design**: Works on desktop and mobile devices

## Database Schema

Articles are stored with the following fields:
- `id`: Unique identifier
- `title`: Article title
- `content`: Full article content
- `link`: Original article URL
- `published`: Publication date
- `author`: Article author
- `publisher`: News source
- `description`: Article description
- `summary`: Article summary
- `keywords`: Article keywords

## Development

The system consists of:
- **FastAPI Backend**: Handles RSS polling and database operations
- **Gradio Frontend**: Provides the web interface
- **Supabase Database**: Stores articles and metadata

## Troubleshooting

- If articles aren't showing up, run `/poll` first to fetch articles
- Check the console for any error messages
- Ensure your Supabase credentials are correct
- Make sure all dependencies are installed

## License

MIT License