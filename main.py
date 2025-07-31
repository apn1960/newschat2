# Scaffold FastAPI
from fastapi import FastAPI
import feedparser
from supabase import create_client, Client
import os
from dotenv import load_dotenv

import feedparser
import newspaper
from datetime import datetime
from supabase import create_client

app = FastAPI()

load_dotenv()


# Create poll endpoint
@app.get("/poll")
def poll():
    # create dictionary off rss feeds
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
    # fetch articles from rss feed
    articles = []
    for feed in rss_feeds:
        feed = feedparser.parse(rss_feeds[feed])
        articles.extend(feed.entries)
    # parse articles
    # store articles in database
    supabase = create_client(
        os.getenv("https://rzgeagliuqechlaotnrc.supabase.co"),
        os.getenv("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ6Z2VhZ2xpdXFlY2hsYW90bnJjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDM2MzQ2MjcsImV4cCI6MjA1OTIxMDYyN30.wQigFm39bxbf_vl9iY_UKQPL05ifAISkGbNwc9KzCoI"),
    )
    # insert articles into database
    for article in articles:
        supabase.table("articles").insert({"title": article.title, "link": article.link, "description": article.description}).execute()

    # get articles from database
    articles = supabase.table("articles").select("*").execute()
    # return articles
    return {"articles": articles}








