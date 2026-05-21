from fastapi import FastAPI, HTTPException, Depends, Request
from contextlib import asynccontextmanager  # <--- THIS IS THE MISSING PIECE
import asyncio
from typing import List, Dict
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.models.schemas import TopicCluster
from app.services.clustering import generate_clusters, generate_search_cluster
from app.api.dependencies import verify_api_key
from app.workers.ingestion import run_scheduler

# --- Lifecycle Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting background ingestion worker...")
    worker_task = asyncio.create_task(run_scheduler())
    yield
    worker_task.cancel()

# ... (rest of your app code) ...

# --- App Initialization ---
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Real-Time AI News Intelligence API",
    description="Scalable event intelligence platform featuring rate-limiting, auth, and semantic clustering.",
    version="1.1.0",
    lifespan=lifespan

)

# Register the rate limiter middleware to the app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- Mock Database for Subscriptions ---
# Maps an API Key to a list of subscribed topic keywords
USER_SUBSCRIPTIONS: Dict[str, List[str]] = {
    "nexus-user-123": ["AI", "Semiconductors"]
}

# --- Core API Endpoints ---

@app.get("/", tags=["Health"])
@limiter.limit("1000/minute") # Example: Max 10 hits per minute
async def root(request: Request):
    return {"status": "online", "system": "Nexus Engine Active"}

@app.get("/digest", response_model=List[TopicCluster], tags=["News"])
@limiter.limit("500/minute") # Strict rate limit for heavy DB/AI endpoints
async def get_digest(request: Request, api_key: str = Depends(verify_api_key)):
    """Retrieve all clustered news. Requires a valid API Key."""
    clusters = await generate_clusters()
    if not clusters:
        raise HTTPException(status_code=404, detail="No active news clusters found.")
    return clusters

@app.get("/topic/{name}", response_model=TopicCluster, tags=["News"])
@limiter.limit("1500/minute")
async def get_topic(request: Request, name: str, api_key: str = Depends(verify_api_key)):
    """
    Advanced Semantic Search endpoint. 
    Embeds the query and finds contextual matches, even if exact keywords are missing.
    """
    # Hit the new semantic search engine
    cluster = await generate_search_cluster(name)
    
    if not cluster:
        raise HTTPException(status_code=404, detail=f"No semantic matches found for context: '{name}'")
        
    return cluster
# --- Bonus: Topic Subscriptions ---

@app.post("/subscribe", tags=["Subscriptions"])
@limiter.limit("500/minute")
async def subscribe_to_topic(request: Request, topic: str, api_key: str = Depends(verify_api_key)):
    """Allows a user to subscribe to a specific news topic."""
    if api_key not in USER_SUBSCRIPTIONS:
        USER_SUBSCRIPTIONS[api_key] = []
        
    if topic not in USER_SUBSCRIPTIONS[api_key]:
        USER_SUBSCRIPTIONS[api_key].append(topic)
        
    return {
        "status": "success", 
        "message": f"Subscribed to '{topic}'",
        "current_subscriptions": USER_SUBSCRIPTIONS[api_key]
    }

@app.post("/unsubscribe", tags=["Subscriptions"])
@limiter.limit("500/minute")
async def unsubscribe_from_topic(request: Request, topic: str, api_key: str = Depends(verify_api_key)):
    """Allows a user to unsubscribe from a specific news topic."""
    if api_key in USER_SUBSCRIPTIONS and topic in USER_SUBSCRIPTIONS[api_key]:
        USER_SUBSCRIPTIONS[api_key].remove(topic)
        
    return {
        "status": "success", 
        "message": f"Unsubscribed from '{topic}'",
        "current_subscriptions": USER_SUBSCRIPTIONS.get(api_key, [])
    }

@app.get("/subscriptions", tags=["Subscriptions"])
@limiter.limit("1000/minute")
async def get_subscriptions(request: Request, api_key: str = Depends(verify_api_key)):
    """Returns the user's active topic subscriptions."""
    return {"subscriptions": USER_SUBSCRIPTIONS.get(api_key, [])}

@app.get("/my-feed", response_model=List[TopicCluster], tags=["Subscriptions"])
@limiter.limit("500/minute")
async def get_personalized_feed(request: Request, api_key: str = Depends(verify_api_key)):
    """Returns only the clusters that match the user's subscribed topics."""
    user_topics = USER_SUBSCRIPTIONS.get(api_key, [])
    if not user_topics:
        raise HTTPException(status_code=404, detail="You have no active subscriptions.")
        
    all_clusters = await generate_clusters()
    personalized_feed = []
    
    # Filter the massive digest down to only what the user cares about
    for cluster in all_clusters:
        for topic in user_topics:
            if topic.lower() in cluster.topic_name.lower() or topic.lower() in cluster.cluster_summary.lower():
                if cluster not in personalized_feed:
                    personalized_feed.append(cluster)
                    
    return personalized_feed