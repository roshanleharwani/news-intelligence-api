import asyncio
import aiohttp
import feedparser
from datetime import datetime
from typing import List
from app.models.schemas import ArticleIngested
from app.services.llm_summarizer import process_batch
from app.workers.deduplication import run_deduplication_pipeline 
from app.workers.rss_sources import FEEDS
async def fetch_feed(session: aiohttp.ClientSession, source_name: str, url: str) -> List[ArticleIngested]:
    """Fetches and parses a single RSS feed asynchronously."""
    articles = []
    try:
        # A 10-second timeout prevents a hanging feed from stalling the worker
        async with session.get(url, timeout=10) as response:
            response.raise_for_status()
            content = await response.text()
            
            # Parse the XML payload
            parsed_feed = feedparser.parse(content)
            
            # Limit to top 15 recent articles per feed to keep the DB clean during testing
            for entry in parsed_feed.entries[:15]: 
                
                # Safely handle published dates (RSS feeds format these inconsistently)
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                    
                article = ArticleIngested(
                    title=entry.title,
                    url=entry.link,
                    source=source_name,
                    published_at=pub_date,
                    raw_content=entry.get('summary', '') 
                )
                articles.append(article)
                
    except Exception as e:
        # If one feed goes down, the worker logs it but keeps running the others
        print(f"Error fetching {source_name}: {e}")
        
    return articles

from app.services.llm_summarizer import process_batch
from app.services.vector_store import process_and_store

async def run_ingestion_cycle():
    """Main entry point: Ingest -> Summarize -> Deduplicate -> Store."""
    print("Initiating Master Pipeline...")
    
    headers = {"User-Agent": "NewsIntelligencePlatform/1.0"}
    
    async with aiohttp.ClientSession(headers=headers) as session:
        # STEP 1: Parallel Ingestion
        print("[1/3] Fetching raw RSS feeds...")
        tasks = [fetch_feed(session, name, url) for name, url in FEEDS.items()]
        results = await asyncio.gather(*tasks)
        raw_articles = [article for sublist in results for article in sublist]
        print(f"Fetched {len(raw_articles)} raw articles.")

    # STEP 2: Parallel LLM Summarization & Sentiment Extraction
    print("[2/3] Extracting summaries and sentiment via OpenAI...")
    processed_articles = await process_batch(raw_articles)
    
    # STEP 3: Semantic Deduplication & Storage
    # STEP 3: Semantic Deduplication & Storage
    saved_count, duplicate_count = await run_deduplication_pipeline(processed_articles)
            
    print("-" * 40)
    print(f"Pipeline Complete: {saved_count} new events stored. {duplicate_count} duplicates dropped.")
if __name__ == "__main__":
    # Wrap the ingestion cycle in a continuous interval loop
    async def run_scheduler():
        while True:
            await run_ingestion_cycle()
            print("Sleeping for 60 minutes before next ingestion...")
            await asyncio.sleep(3600) # Runs every hour

    asyncio.run(run_scheduler())

