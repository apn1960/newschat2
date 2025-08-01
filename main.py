# Scaffold FastAPI
from fastapi import FastAPI
from dotenv import load_dotenv
import os
import feedparser
import newspaper
from datetime import datetime
from supabase import create_client

app = FastAPI()

load_dotenv()

def convert_datetime_to_string(obj):
    """Recursively convert datetime objects to strings in any data structure"""
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    elif hasattr(obj, 'strftime'):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(obj, dict):
        return {key: convert_datetime_to_string(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetime_to_string(item) for item in obj]
    else:
        return obj

def clean_for_json(obj):
    """Clean objects to be JSON serializable"""
    if isinstance(obj, dict):
        cleaned = {}
        for key, value in obj.items():
            # Skip function objects and other non-serializable types
            if callable(value) or hasattr(value, '__dict__') or 'builtin_function_or_method' in str(type(value)):
                continue
            try:
                cleaned[key] = clean_for_json(value)
            except:
                # If we can't process this value, skip it
                continue
        return cleaned
    elif isinstance(obj, list):
        return [clean_for_json(item) for item in obj if not callable(item) and 'builtin_function_or_method' not in str(type(item))]
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    else:
        try:
            return str(obj)
        except:
            return None

def extract_article_metadata(url):
    """Extract article metadata using newspaper3k library"""
    try:
        article = newspaper.Article(url)
        article.download()
        article.parse()
        #print(f"Extracting body from {url} {article.text}")   # Main article text
        metadata = {
            'publisher': article.source_url or article.domain,
            'title': article.title,
            'content': article.text,
            'summary': article.summary,
            'keywords': article.keywords,
            'authors': article.authors,
            'publish_date': article.publish_date,
            'top_image': article.top_image,
            'meta_description': article.meta_description,
            'meta_lang': article.meta_lang,
            'meta_favicon': article.meta_favicon,
            'meta_img': article.meta_img,
            'meta_keywords': article.meta_keywords,
            'meta_data': article.meta_data
        }
        
        # Filter out problematic fields that might contain non-serializable objects
        safe_metadata = {}
        for key, value in metadata.items():
            if key in ['content', 'title', 'summary', 'publisher', 'authors', 'keywords', 'publish_date']:
                safe_metadata[key] = value
        
        # Convert all datetime objects to strings
        return convert_datetime_to_string(safe_metadata)
    except Exception as e:
        print(f"Error extracting metadata from {url}: {e}")
        return None

@app.get("/")
def read_root():
    return {"message": "Hello, World!"}

# Create poll endpoint
@app.get("/poll")
def poll():
    # create dictionary off rss feeds
    rss_feeds = {
        "ithacavoice": "https://ithacavoice.org/feed",
        "607newsnow": "https://607newsnow.com/feed",
        "ithacatimes": "http://www.ithaca.com/search/?q=&t=article&l=100&d=&d1=&d2=&s=start_time&sd=desc&c[]=news*&f=rss",
        "cornellsun": "https://cornellsun.com/feed/",
        "ithacajournal": "https://www.ithacajournal.com/news/feed/",
        "fingerlakes1": "https://fingerlakes1.com/feed/",
        "tompkinsweekly": "https://tompkinsweekly.com/feed/",
        "cornellchronicle": "https://news.cornell.edu/feed",
        "cornellresearch": "https://research.cornell.edu/feed",
        "ithacacollege": "https://www.ithaca.edu/news/feed"
    }
    
    # fetch articles from rss feed
    articles = []
    feed_stats = {}
    for feed_name, feed_url in rss_feeds.items():
        try:
            feed = feedparser.parse(feed_url)
            feed_articles = feed.entries
            articles.extend(feed_articles)
            feed_stats[feed_name] = {
                "url": feed_url,
                "articles_found": len(feed_articles),
                "feed_title": getattr(feed.feed, 'title', 'Unknown'),
                "feed_description": getattr(feed.feed, 'description', 'No description')
            }
            print(f"Feed {feed_name}: {len(feed_articles)} articles found")
        except Exception as e:
            print(f"Error parsing feed {feed_name}: {e}")
            feed_stats[feed_name] = {"error": str(e)}
    
    print(f"Total articles from all feeds: {len(articles)}")
    
    # create supabase client
    supabase = create_client(
        "https://rzgeagliuqechlaotnrc.supabase.co",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ6Z2VhZ2xpdXFlY2hsYW90bnJjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDM2MzQ2MjcsImV4cCI6MjA1OTIxMDYyN30.wQigFm39bxbf_vl9iY_UKQPL05ifAISkGbNwc9KzCoI",
    )
    
    # insert articles into database
    inserted_count = 0
    for article in articles:
        try:
            # Get author information from RSS feed
            author = getattr(article, 'author', None)
            if not author:
                # Try alternative author fields that some RSS feeds use
                author = getattr(article, 'dc_creator', None)  # Dublin Core creator
                if not author:
                    author = getattr(article, 'dc_contributor', None)  # Dublin Core contributor
            
            # Extract rich metadata using newspaper3k
            metadata = extract_article_metadata(article.link)
            
            # Use newspaper3k data if available, fallback to RSS data
            title = metadata['title'] if metadata and metadata['title'] else article.title
            publisher = metadata['publisher'] if metadata else None
            authors = metadata['authors'] if metadata else ([author] if author else [])
            publish_date = metadata['publish_date'] if metadata else article.published
            
            # Convert datetime to string if it's a datetime object
            publish_date = convert_datetime_to_string(publish_date)
            
            text = metadata['content'] if metadata else article.description
            summary = metadata['summary'] if metadata else None
            keywords = metadata['keywords'] if metadata else []
            
            # Get article body content
            article_body = metadata['content'] if metadata and metadata['content'] else article.description
            
            # Convert all data to JSON-serializable format
            article_data = {
                "title": title,
                "published": publish_date, 
                "author": authors[0] if isinstance(authors, list) and authors else authors,
                "publisher": publisher,
                "link": article.link, 
                "description": text,
                "summary": summary,
                "keywords": keywords,
                "content": article_body  # Add article body content
            }
            
            # Convert any remaining datetime objects
            article_data = convert_datetime_to_string(article_data)
            
            # Clean the data for JSON serialization
            article_data = clean_for_json(article_data)
            
            supabase.table("data").insert(article_data).execute()
            inserted_count += 1
        except Exception as e:
            print(f"Error processing article {article.link}: {e}")
    
    print(f"Articles inserted into database: {inserted_count}")
    
    return {
        "message": "Polling completed",
        "articles_processed": len(articles),
        "articles_inserted": inserted_count,
        "feed_statistics": feed_stats
    }

@app.get("/list")
def list_articles():
    """Get recent articles from database"""
    # create supabase client
    supabase = create_client(
        "https://rzgeagliuqechlaotnrc.supabase.co",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ6Z2VhZ2xpdXFlY2hsYW90bnJjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDM2MzQ2MjcsImV4cCI6MjA1OTIxMDYyN30.wQigFm39bxbf_vl9iY_UKQPL05ifAISkGbNwc9KzCoI",
    )
    
    # Get recent articles with explicit content selection
    recent_articles = supabase.table("data").select("id, title, content, link, published, author, publisher, description, summary, keywords").order("created_at", desc=True).execute()
    
    # Process articles to ensure content is included
    processed_articles = []
    for article in recent_articles.data:
        processed_article = {
            "id": article.get("id"),
            "title": article.get("title"),
            "content": article.get("content"),
            "link": article.get("link"),
            "published": article.get("published"),
            "author": article.get("author"),
            "publisher": article.get("publisher"),
            "description": article.get("description"),
            "summary": article.get("summary"),
            "keywords": article.get("keywords"),
            "has_content": article.get("content") is not None,
            "content_length": len(article.get("content", "")) if article.get("content") else 0
        }
        processed_articles.append(processed_article)
    
    return {
        "articles": processed_articles,
        "total_articles": len(processed_articles),
        "articles_with_content": sum(1 for a in processed_articles if a.get("content"))
    }

@app.get("/poll-with-content")
def poll_with_content():
    """Poll endpoint that explicitly includes content field"""
    # create dictionary off rss feeds
    rss_feeds = {
        "ithacavoice": "https://ithacavoice.org/feed",
    }
    
    # fetch articles from rss feed
    articles = []
    for feed_name, feed_url in rss_feeds.items():
        try:
            feed = feedparser.parse(feed_url)
            articles.extend(feed.entries)
        except Exception as e:
            print(f"Error parsing feed {feed_name}: {e}")
    
    # create supabase client
    supabase = create_client(
        "https://rzgeagliuqechlaotnrc.supabase.co",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ6Z2VhZ2xpdXFlY2hsYW90bnJjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDM2MzQ2MjcsImV4cCI6MjA1OTIxMDYyN30.wQigFm39bxbf_vl9iY_UKQPL05ifAISkGbNwc9KzCoI",
    )
    
    # insert articles into database
    for article in articles:
        try:
            # Get author information from RSS feed
            author = getattr(article, 'author', None)
            if not author:
                # Try alternative author fields that some RSS feeds use
                author = getattr(article, 'dc_creator', None)  # Dublin Core creator
                if not author:
                    author = getattr(article, 'dc_contributor', None)  # Dublin Core contributor
            
            # Extract rich metadata using newspaper3k
            metadata = extract_article_metadata(article.link)
            
            # Use newspaper3k data if available, fallback to RSS data
            title = metadata['title'] if metadata and metadata['title'] else article.title
            publisher = metadata['publisher'] if metadata else None
            authors = metadata['authors'] if metadata else ([author] if author else [])
            publish_date = metadata['publish_date'] if metadata else article.published
            
            # Convert datetime to string if it's a datetime object
            publish_date = convert_datetime_to_string(publish_date)
            
            text = metadata['content'] if metadata else article.description
            summary = metadata['summary'] if metadata else None
            keywords = metadata['keywords'] if metadata else []
            
            # Get article body content
            article_body = metadata['content'] if metadata and metadata['content'] else article.description
            
            # Convert all data to JSON-serializable format
            article_data = {
                "title": title,
                "published": publish_date, 
                "author": authors[0] if isinstance(authors, list) and authors else authors,
                "publisher": publisher,
                "link": article.link, 
                "description": text,
                "summary": summary,
                "keywords": keywords,
                "content": article_body  # Add article body content
            }
            
            # Convert any remaining datetime objects
            article_data = convert_datetime_to_string(article_data)
            
            # Clean the data for JSON serialization
            article_data = clean_for_json(article_data)
            
            supabase.table("data").insert(article_data).execute()
        except Exception as e:
            print(f"Error processing article {article.link}: {e}")
    
    print("Articles inserted into database")
    
    # Get recent articles with explicit content selection
    recent_articles = supabase.table("data").select("id, title, content, link, published, author, publisher, description, summary, keywords").order("created_at", desc=True).limit(10).execute()
    
    # Process articles to ensure content is included
    processed_articles = []
    for article in recent_articles.data:
        processed_article = {
            "id": article.get("id"),
            "title": article.get("title"),
            "content": article.get("content"),
            "link": article.get("link"),
            "published": article.get("published"),
            "author": article.get("author"),
            "publisher": article.get("publisher"),
            "description": article.get("description"),
            "summary": article.get("summary"),
            "keywords": article.get("keywords"),
            "has_content": article.get("content") is not None,
            "content_length": len(article.get("content", "")) if article.get("content") else 0
        }
        processed_articles.append(processed_article)
    
    return {
        "articles": processed_articles,
        "total_articles": len(processed_articles),
        "articles_with_content": sum(1 for a in processed_articles if a.get("content"))
    }

@app.get("/debug-authors")
def debug_authors():
    """Debug endpoint to see what author information is available in RSS feeds"""
    rss_feeds = {
        "theguardian": "https://www.theguardian.com/world/rss",
        "nytimes": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "washingtonpost": "http://feeds.washingtonpost.com/rss/world",
        "reuters": "https://www.reuters.com/rss/worldNews",
        "apnews": "https://apnews.com/rss/worldnews",
        "bbc": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "cnn": "https://rss.cnn.com/rss/edition_world.rss",
        "foxnews": "https://feeds.foxnews.com/foxnews/world",
        "aljazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    }
    
    debug_info = {}
    
    for feed_name, feed_url in rss_feeds.items():
        try:
            feed = feedparser.parse(feed_url)
            sample_article = feed.entries[0] if feed.entries else None
            
            if sample_article:
                debug_info[feed_name] = {
                    "has_author": hasattr(sample_article, 'author'),
                    "has_dc_creator": hasattr(sample_article, 'dc_creator'),
                    "has_dc_contributor": hasattr(sample_article, 'dc_contributor'),
                    "author_value": getattr(sample_article, 'author', None),
                    "dc_creator_value": getattr(sample_article, 'dc_creator', None),
                    "dc_contributor_value": getattr(sample_article, 'dc_contributor', None),
                    "available_attributes": [attr for attr in dir(sample_article) if not attr.startswith('_')]
                }
        except Exception as e:
            debug_info[feed_name] = {"error": str(e)}
    
    return debug_info

@app.get("/test-article/{url:path}")
def test_article_extraction(url: str):
    """Test article metadata extraction from a specific URL"""
    metadata = extract_article_metadata(url)
    return {
        "url": url,
        "metadata": metadata
    }

@app.get("/get-articles")
def get_articles():
    """Get articles from database with explicit field selection"""
    supabase = create_client(
        "https://rzgeagliuqechlaotnrc.supabase.co",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ6Z2VhZ2xpdXFlY2hsYW90bnJjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDM2MzQ2MjcsImV4cCI6MjA1OTIxMDYyN30.wQigFm39bxbf_vl9iY_UKQPL05ifAISkGbNwc9KzCoI",
    )
    
    # Explicitly select all fields including content
    articles = supabase.table("data").select("*, content").execute()
    
    # Debug information
    debug_info = {
        "total_articles": len(articles.data) if articles.data else 0,
        "sample_fields": list(articles.data[0].keys()) if articles.data else [],
        "has_content": any('content' in article for article in articles.data) if articles.data else False,
        "content_values": []
    }
    
    # Safely extract content values with null checking
    if articles.data:
        for article in articles.data[:3]:
            content = article.get('content')
            if content is not None:
                debug_info["content_values"].append(content[:100] + '...')
            else:
                debug_info["content_values"].append('NULL_CONTENT')
    
    return {
        "articles": articles.data,
        "debug": debug_info
    }

@app.get("/test-content-retrieval")
def test_content_retrieval():
    """Test content retrieval with different approaches"""
    supabase = create_client(
        "https://rzgeagliuqechlaotnrc.supabase.co",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ6Z2VhZ2xpdXFlY2hsYW90bnJjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDM2MzQ2MjcsImV4cCI6MjA1OTIxMDYyN30.wQigFm39bxbf_vl9iY_UKQPL05ifAISkGbNwc9KzCoI",
    )
    
    # Try different approaches to retrieve content
    results = {}
    
    # Approach 1: Select specific fields
    try:
        articles1 = supabase.table("data").select("id, title, content").limit(1).execute()
        if articles1.data:
            content_value = articles1.data[0].get('content')
            results["approach1"] = {
                "success": True,
                "data": articles1.data[0],
                "content_type": type(content_value),
                "content_value": content_value,
                "content_is_none": content_value is None,
                "content_length": len(content_value) if content_value is not None else 0
            }
        else:
            results["approach1"] = {"success": True, "error": "No data found"}
    except Exception as e:
        results["approach1"] = {"success": False, "error": str(e)}
    
    # Approach 2: Select only content field
    try:
        articles2 = supabase.table("data").select("content").limit(1).execute()
        if articles2.data:
            content_value = articles2.data[0].get('content')
            results["approach2"] = {
                "success": True,
                "data": articles2.data[0],
                "content_type": type(content_value),
                "content_value": content_value,
                "content_is_none": content_value is None,
                "content_length": len(content_value) if content_value is not None else 0
            }
        else:
            results["approach2"] = {"success": True, "error": "No data found"}
    except Exception as e:
        results["approach2"] = {"success": False, "error": str(e)}
    
    # Approach 3: Check raw response
    try:
        articles3 = supabase.table("data").select("*").limit(1).execute()
        if articles3.data:
            sample_article = articles3.data[0]
            content_value = sample_article.get('content')
            # Create a safe version of the sample article for JSON serialization
            safe_article = {}
            for key, value in sample_article.items():
                if isinstance(value, (str, int, float, bool, type(None))):
                    safe_article[key] = value
                else:
                    safe_article[key] = str(value)
            
            results["approach3"] = {
                "success": True,
                "raw_response_keys": list(sample_article.keys()),
                "content_value": content_value,
                "content_is_null": content_value is None,
                "content_is_empty_string": content_value == "",
                "content_type": str(type(content_value)),
                "content_length": len(content_value) if content_value is not None else 0,
                "content_preview": content_value[:200] + "..." if content_value and len(content_value) > 200 else content_value,
                "all_fields": safe_article
            }
        else:
            results["approach3"] = {"success": True, "error": "No data found"}
    except Exception as e:
        results["approach3"] = {"success": False, "error": str(e)}
    
    return results

@app.get("/check-table-schema")
def check_table_schema():
    """Check the schema of the data table"""
    supabase = create_client(
        "https://rzgeagliuqechlaotnrc.supabase.co",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ6Z2VhZ2xpdXFlY2hsYW90bnJjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDM2MzQ2MjcsImV4cCI6MjA1OTIxMDYyN30.wQigFm39bxbf_vl9iY_UKQPL05ifAISkGbNwc9KzCoI",
    )
    
    try:
        # Try to get table information by selecting a single row
        result = supabase.table("data").select("*").limit(1).execute()
        
        if result.data:
            sample_row = result.data[0]
            content_value = sample_row.get("content")
            # Create a safe version of the sample row for JSON serialization
            safe_row = {}
            for key, value in sample_row.items():
                if isinstance(value, (str, int, float, bool, type(None))):
                    safe_row[key] = value
                else:
                    safe_row[key] = str(value)
            
            schema_info = {
                "columns": list(sample_row.keys()),
                "has_content_column": "content" in sample_row,
                "content_column_type": str(type(content_value)),
                "content_column_value": content_value,
                "content_is_null": content_value is None,
                "content_is_empty_string": content_value == "",
                "content_length": len(content_value) if content_value is not None else 0,
                "sample_row": safe_row
            }
        else:
            schema_info = {"error": "No data in table"}
            
        return schema_info
    except Exception as e:
        return {"error": str(e)}

@app.get("/test-insert-content")
def test_insert_content():
    """Test inserting content directly to see if the column exists"""
    supabase = create_client(
        "https://rzgeagliuqechlaotnrc.supabase.co",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ6Z2VhZ2xpdXFlY2hsYW90bnJjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDM2MzQ2MjcsImV4cCI6MjA1OTIxMDYyN30.wQigFm39bxbf_vl9iY_UKQPL05ifAISkGbNwc9KzCoI",
    )
    
    try:
        # Try to insert a test record with content
        test_data = {
            "title": "Test Article",
            "content": "This is a test content to verify the content column exists and works.",
            "link": "https://test.com",
            "published": "2024-01-01"
        }
        
        result = supabase.table("data").insert(test_data).execute()
        
        if result.data:
            return {
                "success": True,
                "inserted_data": result.data[0],
                "has_content": "content" in result.data[0],
                "content_value": result.data[0].get("content")
            }
        else:
            return {"success": False, "error": "No data returned from insert"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/test-convert-function")
def test_convert_function():
    """Test what convert_datetime_to_string does to content"""
    test_data = {
        "title": "Test Article",
        "content": "This is test content with some text.",
        "published": "2024-01-01",
        "keywords": ["test", "content"]
    }
    
    print(f"Original content: {test_data['content']} - Type: {type(test_data['content'])}")
    
    converted_data = convert_datetime_to_string(test_data)
    
    print(f"Converted content: {converted_data['content']} - Type: {type(converted_data['content'])}")
    
    return {
        "original": test_data,
        "converted": converted_data,
        "content_changed": test_data['content'] != converted_data['content']
    }

@app.get("/test-metadata-extraction")
def test_metadata_extraction():
    """Test metadata extraction to see what non-serializable objects are returned"""
    url = "https://ithacavoice.org/2025/07/weather-hazy-hot-and-humid-to-start-the-week-cooler-later/"
    
    try:
        metadata = extract_article_metadata(url)
        
        if metadata:
            # Check for non-serializable objects
            problematic_keys = []
            for key, value in metadata.items():
                if callable(value) or hasattr(value, '__dict__'):
                    problematic_keys.append(key)
            
            return {
                "success": True,
                "metadata_keys": list(metadata.keys()),
                "problematic_keys": problematic_keys,
                "content_type": type(metadata.get('content')),
                "content_length": len(metadata.get('content', '')) if metadata.get('content') else 0,
                "cleaned_metadata": clean_for_json(metadata)
            }
        else:
            return {"success": False, "error": "No metadata returned"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/debug-supabase-response")
def debug_supabase_response():
    """Debug what Supabase is actually returning"""
    supabase = create_client(
        "https://rzgeagliuqechlaotnrc.supabase.co",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ6Z2VhZ2xpdXFlY2hsYW90bnJjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDM2MzQ2MjcsImV4cCI6MjA1OTIxMDYyN30.wQigFm39bxbf_vl9iY_UKQPL05ifAISkGbNwc9KzCoI",
    )
    
    try:
        # Get the most recent article
        result = supabase.table("data").select("*").order("created_at", desc=True).limit(1).execute()
        
        if result.data:
            article = result.data[0]
            
            # Check the raw response
            debug_info = {
                "raw_article": article,
                "has_content_field": "content" in article,
                "content_value": article.get("content"),
                "content_type": str(type(article.get("content"))),
                "content_is_none": article.get("content") is None,
                "content_is_empty": article.get("content") == "",
                "content_length": len(article.get("content", "")) if article.get("content") else 0,
                "all_fields": list(article.keys()),
                "sample_content_preview": article.get("content", "")[:200] + "..." if article.get("content") and len(article.get("content", "")) > 200 else article.get("content", "")
            }
            
            return debug_info
        else:
            return {"error": "No articles found"}
            
    except Exception as e:
        return {"error": str(e)}

@app.get("/get-articles-with-content")
def get_articles_with_content():
    """Get articles with explicit content field selection"""
    supabase = create_client(
        "https://rzgeagliuqechlaotnrc.supabase.co",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ6Z2VhZ2xpdXFlY2hsYW90bnJjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDM2MzQ2MjcsImV4cCI6MjA1OTIxMDYyN30.wQigFm39bxbf_vl9iY_UKQPL05ifAISkGbNwc9KzCoI",
    )
    
    try:
        # Explicitly select content field
        result = supabase.table("data").select("id, title, content, link, published, author").order("created_at", desc=True).limit(5).execute()
        
        articles = []
        for article in result.data:
            # Ensure content is included
            article_with_content = {
                "id": article.get("id"),
                "title": article.get("title"),
                "content": article.get("content"),
                "link": article.get("link"),
                "published": article.get("published"),
                "author": article.get("author"),
                "has_content": article.get("content") is not None,
                "content_length": len(article.get("content", "")) if article.get("content") else 0
            }
            articles.append(article_with_content)
        
        return {
            "articles": articles,
            "total_articles": len(articles),
            "articles_with_content": sum(1 for a in articles if a.get("content"))
        }
        
    except Exception as e:
        return {"error": str(e)}


