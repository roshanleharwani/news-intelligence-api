import numpy as np
from sklearn.cluster import HDBSCAN
from typing import List, Dict
from app.services.vector_store import collection, semantic_search
from app.models.schemas import ArticleProcessed, TopicCluster
import uuid
import asyncio
from app.services.llm_summarizer import generate_cluster_metadata
# Change the function definition to async:
async def generate_clusters() -> List[TopicCluster]:
    """Pulls all articles from ChromaDB and clusters them semantically."""
    
    # 1. Fetch all documents and embeddings from the DB
    db_data = collection.get(include=["embeddings", "metadatas", "documents"])
    
    if not db_data['ids']:
        return []

    embeddings = np.array(db_data['embeddings'])
    
    # 2. Apply HDBSCAN
    clusterer = HDBSCAN(min_cluster_size=2, metric='euclidean')
    labels = clusterer.fit_predict(embeddings)
    
    # 3. Group the articles by their new cluster labels
    grouped_data: Dict[int, List[ArticleProcessed]] = {}
    
    for idx, label in enumerate(labels):
        if label == -1:
            continue
            
        meta = db_data['metadatas'][idx]
        
        article = ArticleProcessed(
            id=db_data['ids'][idx],
            title=meta['title'],
            url=meta['url'],
            source=meta['source'],
            two_line_summary=db_data['documents'][idx],
            sentiment=meta.get('sentiment', 'Neutral'),
            cluster_id=str(label)
        )
        
        if label not in grouped_data:
            grouped_data[label] = []
        grouped_data[label].append(article)

    # 4. Format into our strict Pydantic Output Model with AI-generated names
    async def process_cluster(label, articles):
        topic_name, cluster_summary = await generate_cluster_metadata(articles)
        return TopicCluster(
            cluster_id=f"cluster_{label}",
            topic_name=topic_name,
            cluster_summary=cluster_summary,
            articles=articles
        )

    # Use native await instead of get_event_loop()
    tasks = [process_cluster(label, articles) for label, articles in grouped_data.items()]
    final_clusters = await asyncio.gather(*tasks)

    return final_clusters

async def generate_search_cluster(query: str) -> TopicCluster:
    """Performs semantic search and dynamically packages the results into a cluster."""
    
    # Get semantically related articles
    articles = await semantic_search(query)
    
    if not articles:
        return None
        
    # Use the LLM to generate a dynamic title and summary explaining WHY these articles match
    topic_name, cluster_summary = await generate_cluster_metadata(articles)
    
    return TopicCluster(
        cluster_id=f"search_{uuid.uuid4().hex[:8]}",
        topic_name=f"🔍 {topic_name}",
        cluster_summary=cluster_summary,
        articles=articles
    )