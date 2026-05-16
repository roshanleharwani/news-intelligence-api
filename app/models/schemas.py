from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional
from datetime import datetime

# --- Article Models ---

class ArticleBase(BaseModel):
    title: str = Field(..., description="The headline of the article")
    url: HttpUrl = Field(..., description="Original link to the article")
    source: str = Field(..., description="The publisher (e.g., NYT, TechCrunch)")
    published_at: Optional[datetime] = Field(None, description="Publication timestamp")

class ArticleIngested(ArticleBase):
    """Used when the worker first pulls the raw data."""
    raw_content: Optional[str] = None

class ArticleProcessed(ArticleBase):
    """Used after the NLP pipeline has run."""
    id: str
    two_line_summary: str = Field(..., description="Mandatory LLM 2-line summary")
    sentiment: Optional[str] = Field(None, description="Positive, Neutral, or Negative")
    embedding_id: Optional[str] = Field(None, description="Reference to ChromaDB vector")
    cluster_id: Optional[str] = None

# --- Cluster Models ---

class TopicCluster(BaseModel):
    """Represents a grouped story / event."""
    cluster_id: str
    topic_name: str
    cluster_summary: str = Field(..., description="Unified summary of the whole event")
    articles: List[ArticleProcessed] = Field(default_factory=list)