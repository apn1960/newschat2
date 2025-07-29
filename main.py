# Scaffold FastAPI
from fastapi import FastAPI
import feedparser

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello, World!"}


# Create poll endpoint
@app.get("/poll")
def poll():
    # create dictionary off rss feeds
    rss_feeds = {
        "theguardian": "https://www.theguardian.com/world/rss",
        "nytimes": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "washingtonpost": "https://www.washingtonpost.com/rss",
    }
    # fetch articles from rss feed
    articles = []
    for feed in rss_feeds:
        feed = feedparser.parse(rss_feeds[feed])
        articles.extend(feed.entries)
    # parse articles
    # return articles
    return {"articles": articles}








