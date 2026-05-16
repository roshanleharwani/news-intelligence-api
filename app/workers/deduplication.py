import asyncio
from typing import List, Tuple
from app.models.schemas import ArticleProcessed
from app.services.vector_store import process_and_store

async def run_deduplication_pipeline(articles: List[ArticleProcessed]) -> Tuple[int, int]:
    """
    Takes a batch of LLM-processed articles, checks the ChromaDB for semantic duplicates,
    and stores only the unique events.
    
    Returns: (saved_count, duplicate_count)
    """
    print("[3/3] Running semantic deduplication and vector storage...")
    saved_count = 0
    duplicate_count = 0
    
    for article in articles:
        was_saved, message = await process_and_store(article)
        if was_saved:
            saved_count += 1
            print(f" [+] {message}")
        else:
            duplicate_count += 1
            
    return saved_count, duplicate_count