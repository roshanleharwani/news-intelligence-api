import os
import chromadb
from openai import AsyncOpenAI
from dotenv import load_dotenv
from typing import List, Tuple
from app.models.schemas import ArticleProcessed

load_dotenv(".env.local")

# Initialize OpenAI and local ChromaDB
client = AsyncOpenAI()
chroma_client = chromadb.PersistentClient(path="./data/vector_db")

# Create or load a collection specifically for news articles
# We use cosine similarity (cosine) as the distance metric for semantic search
collection = chroma_client.get_or_create_collection(
    name="news_intelligence",
    metadata={"hnsw:space": "cosine"} 
)

async def generate_embedding(text: str) -> List[float]:
    """Calls OpenAI to convert text into a high-dimensional vector."""
    response = await client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

async def is_duplicate(embedding: List[float], similarity_threshold: float = 0.15) -> bool:
    """
    Checks if an identical story already exists in the database.
    Because we use cosine space, a lower distance means higher similarity.
    0.15 distance means ~85% semantic match.
    """
    if collection.count() == 0:
        return False
        
    results = collection.query(
        query_embeddings=[embedding],
        n_results=1
    )
    
    # If the closest article's distance is below our threshold, it's a duplicate
    if results['distances'] and results['distances'][0]:
        closest_distance = results['distances'][0][0]
        if closest_distance < similarity_threshold:
            return True
            
    return False

async def process_and_store(article: ArticleProcessed) -> Tuple[bool, str]:
    """
    1. Generates an embedding for the article's 2-line summary.
    2. Checks for semantic duplicates.
    3. Saves to ChromaDB if it is a new, unique story.
    Returns: (was_saved, message)
    """
    # We embed the 2-line summary because it represents the dense core of the event
    embedding = await generate_embedding(article.two_line_summary)
    
    if await is_duplicate(embedding):
        return False, f"Duplicate detected: Dropped '{article.title}'"
        
    # If unique, store it in ChromaDB
    collection.add(
        ids=[article.id],
        embeddings=[embedding],
        metadatas=[{
            "title": article.title,
            "url": str(article.url),
            "source": article.source,
            "sentiment": article.sentiment,
            "published_at": article.published_at.isoformat() if article.published_at else ""
        }],
        documents=[article.two_line_summary]
    )
    
    return True, f"Stored new event: '{article.title}'"

# app/services/vector_store.py (Add to the bottom of the file)

async def semantic_search(query: str, top_k: int = 15, max_distance: float = 0.85) -> List[ArticleProcessed]:
    """
    Converts the user query into an embedding and performs a semantic similarity search.
    A lower distance means higher relevance. max_distance prevents returning unrelated garbage.
    """
    if collection.count() == 0:
        return []

    # Embed the search query (e.g., "virus")
    query_embedding = await generate_embedding(query)
    
    # Query ChromaDB for the closest mathematical matches
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )
    
    articles = []
    if results['ids'] and results['ids'][0]:
        for idx, doc_id in enumerate(results['ids'][0]):
            distance = results['distances'][0][idx]
            
            # Filter out results that aren't semantically close enough
            if distance > max_distance:
                continue
                
            meta = results['metadatas'][0][idx]
            articles.append(ArticleProcessed(
                id=doc_id,
                title=meta['title'],
                url=meta['url'],
                source=meta['source'],
                published_at=None, # Skipping parsing here for speed
                two_line_summary=results['documents'][0][idx],
                sentiment=meta.get('sentiment', 'Neutral')
            ))
            
    return articles