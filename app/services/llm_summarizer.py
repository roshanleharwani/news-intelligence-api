import os
import asyncio
from typing import List
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from openai import AsyncOpenAI
from app.models.schemas import ArticleIngested, ArticleProcessed

load_dotenv(".env.local")

# The AsyncOpenAI client automatically looks for the OPENAI_API_KEY environment variable.
client = AsyncOpenAI()
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# --- Native OpenAI Structured Output Schema ---
class LLMExtraction(BaseModel):
    """We define a temporary schema just for OpenAI to guarantee strict adherence."""
    summary: str = Field(..., description="Exactly a 2-line summary of the core event.")
    sentiment: str = Field(..., description="Classify exactly as 'Positive', 'Neutral', or 'Negative'.")

async def analyze_article(article: ArticleIngested) -> ArticleProcessed:
    """Asynchronously calls OpenAI to generate a summary and extract sentiment."""
    
    prompt = f"Title: {article.title}\nContent: {article.raw_content}"
    
    try:
        # Using OpenAI's beta parse method natively binds the LLM response to your Pydantic model
        completion = await client.beta.chat.completions.parse(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert news analyst. Extract the required event summary and sentiment."},
                {"role": "user", "content": prompt}
            ],
            response_format=LLMExtraction,
            timeout=15.0 # Prevents API hangs from stalling the worker
        )
        
        # The response is now a guaranteed, type-safe Python object, not a raw string
        result = completion.choices[0].message.parsed
        
        return ArticleProcessed(
            id=str(hash(article.url)), 
            title=article.title,
            url=article.url,
            source=article.source,
            published_at=article.published_at,
            two_line_summary=result.summary,
            sentiment=result.sentiment
        )
            
    except Exception as e:
        print(f"OpenAI API Error for '{article.title}': {e}")
        # Graceful fallback to keep the ingestion pipeline alive during API rate limits
        return ArticleProcessed(
            id=str(hash(article.url)),
            title=article.title,
            url=article.url,
            source=article.source,
            published_at=article.published_at,
            two_line_summary=article.raw_content[:200] + "..." if article.raw_content else "Content unavailable.",
            sentiment="Neutral"
        )

async def process_batch(articles: List[ArticleIngested]) -> List[ArticleProcessed]:
    """Fans out the OpenAI tasks to process a batch of articles concurrently."""
    print(f"Sending {len(articles)} articles to OpenAI ({LLM_MODEL})...")
    
    # AsyncOpenAI manages its own connection pooling, eliminating the need for aiohttp ClientSessions here
    tasks = [analyze_article(article) for article in articles]
    processed_articles = await asyncio.gather(*tasks)
    
    return processed_articles

class TopicNaming(BaseModel):
    topic_name: str = Field(..., description="A short, 3-to-5 word title for this news event.")
    cluster_summary: str = Field(..., description="A 1-sentence overarching summary of the combined articles.")

async def generate_cluster_metadata(articles: List[ArticleProcessed]) -> tuple[str, str]:
    """Reads a group of articles and generates a unified topic name and summary."""
    
    # Give the LLM the titles of the articles in this cluster
    titles = "\n".join([f"- {a.title}" for a in articles])
    prompt = f"Analyze these related news headlines and generate a single event title and summary:\n{titles}"
    
    try:
        completion = await client.beta.chat.completions.parse(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a senior editor for a financial and global news terminal."},
                {"role": "user", "content": prompt}
            ],
            response_format=TopicNaming
        )
        
        result = completion.choices[0].message.parsed
        return result.topic_name, result.cluster_summary
        
    except Exception as e:
        print(f"Failed to generate cluster metadata: {e}")
        return "Breaking News Event", "Multiple sources are reporting on this developing story."