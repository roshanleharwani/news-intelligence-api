# ⚡ Nexus Engine — Real-Time AI News Intelligence Platform

> A production-grade, event-driven news aggregation and intelligence platform that ingests multi-source RSS feeds, summarizes them with OpenAI, deduplicates events using vector embeddings, and exposes a secure REST API backed by a stunning Bloomberg-style dashboard.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Core Components](#core-components)
  - [Background Ingestion Worker](#1-background-ingestion-worker)
  - [LLM Summarization & Sentiment Analysis](#2-llm-summarization--sentiment-analysis)
  - [Vector Store & Semantic Deduplication](#3-vector-store--semantic-deduplication)
  - [Semantic Clustering Engine](#4-semantic-clustering-engine)
  - [FastAPI REST Gateway](#5-fastapi-rest-gateway)
  - [Streamlit Dashboard (Nexus UI)](#6-streamlit-dashboard-nexus-ui)
- [API Reference](#api-reference)
- [Data Models](#data-models)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Local Development](#local-development)
  - [Docker / Docker Compose](#docker--docker-compose)
- [Configuration](#configuration)
- [News Sources](#news-sources)
- [Security](#security)

---

## Overview

**Nexus Engine** is a full-stack AI news intelligence system that turns the firehose of global news into structured, deduplicated, semantically-clustered intelligence. It runs as three concurrent services:

| Service | Description |
|---|---|
| **API** | FastAPI backend — rate-limited, API-key authenticated REST gateway |
| **Worker** | Async background pipeline — ingests RSS, summarizes with GPT, stores in ChromaDB |
| **Frontend** | Streamlit dashboard — Bloomberg terminal-style intelligence feed |

The system continuously ingests news from 5 curated RSS feeds every 3 minutes, uses OpenAI `gpt-4o-mini` to generate structured 2-line summaries and sentiment labels, then uses vector embeddings to detect and drop near-duplicate stories before clustering the remaining unique events into coherent topic groups.

---

## Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                         NEXUS ENGINE                               │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                  INGESTION PIPELINE (Worker)                │  │
│  │                                                             │  │
│  │  [RSS Feeds] ──► [fetch_feed] ──► [process_batch / OpenAI]  │  │
│  │                                          │                  │  │
│  │                              ┌───────────▼────────────┐     │  │
│  │                              │  Semantic Deduplication │    │  │
│  │                              │  (ChromaDB cosine dist) │    │  │
│  │                              └───────────┬────────────┘     │  │
│  │                                          │                  │  │
│  │                              ┌───────────▼────────────┐     │  │
│  │                              │   ChromaDB Vector Store │    │  │
│  │                              │   (./data/vector_db)    │    │  │
│  │                              └───────────┬────────────┘     │  │
│  └──────────────────────────────────────────│──────────────────┘  │
│                                             │                     │
│  ┌──────────────────────────────────────────▼──────────────────┐  │
│  │                   FastAPI REST Gateway                      │  │
│  │                                                             │  │
│  │   GET /digest   ──► [HDBSCAN Clustering] ──► TopicClusters  │  │
│  │   GET /topic/{name} ──► [Semantic Search] ──► TopicCluster  │  │
│  │   POST /subscribe, /unsubscribe                             |  │
│  │   GET  /subscriptions, /my-feed                             │  │
│  │                                                             │  │
│  │   ● Rate Limiting (SlowAPI)   ● API Key Auth (X-API-Key)    │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                             │                     │
│  ┌──────────────────────────────────────────▼──────────────────┐  │
│  │               Streamlit Dashboard (Nexus UI)                │  │
│  │                                                             │  │
│  │   ● Live Event Feed         ● Semantic Search Bar           │  │
│  │   ● Topic Quick Filters     ● Sentiment Filter Pills        │  │
│  │   ● Subscribe / Unsubscribe ● Metric Cards                  │  │
│  └─────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
RSS Feeds (5 sources)
      │
      ▼
fetch_feed() — async parallel fetch via aiohttp
      │
      ▼  (raw ArticleIngested list)
process_batch() — fan-out to OpenAI gpt-4o-mini
      │  → 2-line summary (structured output)
      │  → sentiment label (Positive / Neutral / Negative)
      ▼  (processed ArticleProcessed list)
run_deduplication_pipeline()
      │  → generate_embedding() via text-embedding-3-small
      │  → is_duplicate() — cosine distance < 0.15 → DROP
      │  → process_and_store() — unique articles stored in ChromaDB
      ▼
ChromaDB (./data/vector_db) — persistent local vector store
      │
      ▼ (on API request)
generate_clusters()
      │  → fetch all embeddings from ChromaDB
      │  → HDBSCAN unsupervised clustering
      │  → generate_cluster_metadata() — LLM generates topic name + summary
      ▼
TopicCluster[] — returned via REST API to the Streamlit UI
```

---

## Project Structure

```
news-intelligence-api/
│
├── app/                            # Core FastAPI application
│   ├── main.py                     # App factory, lifespan manager, all endpoints
│   │
│   ├── api/
│   │   ├── dependencies.py         # API key authentication dependency
│   │   └── endpoints.py            # (reserved for future route extraction)
│   │
│   ├── models/
│   │   ├── schemas.py              # Pydantic data models (Article, Cluster)
│   │   └── domain.py               # (reserved for domain logic models)
│   │
│   ├── services/
│   │   ├── vector_store.py         # ChromaDB client, embedding, dedup, semantic search
│   │   ├── clustering.py           # HDBSCAN clustering, search cluster generation
│   │   └── llm_summarizer.py       # OpenAI structured output: summarize & name clusters
│   │
│   └── workers/
│       ├── ingestion.py            # Master pipeline: fetch → summarize → dedup → store
│       ├── deduplication.py        # Orchestrates the dedup loop over processed batches
│       ├── rss_sources.py          # RSS feed source registry
│       └── parser.py               # (reserved for advanced content parsing)
│
├── frontend/
│   ├── ui.py                       # Streamlit dashboard — full Bloomberg-style UI
│   └── components/                 # (reserved for extracted UI components)
│
├── data/
│   └── vector_db/                  # ChromaDB persistent storage (auto-created)
│
├── .streamlit/                     # Streamlit configuration
├── Dockerfile                      # Single multi-service container image
├── docker-compose.yml              # Orchestrates api + worker + frontend services
├── start.sh                        # Boot script: starts API internally, then UI publicly
├── requirements.txt                # Full pinned Python dependencies
└── .gitignore
```

---

## Core Components

### 1. Background Ingestion Worker

**File:** `app/workers/ingestion.py`

The scheduler runs as an infinite async loop, triggering a full pipeline cycle every **3 minutes**. It is started automatically via FastAPI's `lifespan` context manager when the API boots.

**`run_ingestion_cycle()` — 3-step pipeline:**

| Step | Function | Description |
|------|----------|-------------|
| 1/3 | `fetch_feed()` | Parallel async HTTP fetch of all RSS feeds using `aiohttp`. Parses XML via `feedparser`. Limits to top 15 articles per source. |
| 2/3 | `process_batch()` | Fan-out to OpenAI — runs all articles through `analyze_article()` concurrently using `asyncio.gather`. |
| 3/3 | `run_deduplication_pipeline()` | Iterates processed articles, checks ChromaDB for semantic duplicates, stores unique events. |

**RSS Sources** (`app/workers/rss_sources.py`):

| Source | Category |
|--------|----------|
| The Hindu | National (India) |
| Times of India | General News |
| Mint / LiveMint | Business & Finance |
| TechCrunch | Technology |
| Al Jazeera | Global Affairs |

---

### 2. LLM Summarization & Sentiment Analysis

**File:** `app/services/llm_summarizer.py`

Uses **OpenAI Structured Outputs** (`beta.chat.completions.parse`) to guarantee type-safe, schema-compliant responses — no JSON parsing required.

**`analyze_article()` → `ArticleProcessed`**

- Model: `gpt-4o-mini` (configurable via `LLM_MODEL` env var)
- Timeout: 15 seconds (prevents API hangs from stalling the worker)
- Output schema enforced via Pydantic:
  ```python
  class LLMExtraction(BaseModel):
      summary: str    # Exactly 2-line event summary
      sentiment: str  # "Positive" | "Neutral" | "Negative"
  ```
- Graceful fallback: on API error, uses raw content truncated to 200 chars with `Neutral` sentiment

**`generate_cluster_metadata()` → `(topic_name, cluster_summary)`**

- Called post-clustering to give each event cluster a human-readable name
- Input: list of article titles from the cluster
- Output schema:
  ```python
  class TopicNaming(BaseModel):
      topic_name: str       # 3-5 word event title
      cluster_summary: str  # 1-sentence overarching summary
  ```

---

### 3. Vector Store & Semantic Deduplication

**File:** `app/services/vector_store.py`

The vector store is a **local ChromaDB instance** persisted to `./data/vector_db`. It uses **cosine similarity** as the distance metric.

**Embedding:** OpenAI `text-embedding-3-small` — applied to the 2-line LLM summary (the dense semantic core of the article).

**Deduplication Logic:**

```
New Article Embedding
        │
        ▼
Query ChromaDB for nearest neighbor
        │
        ▼
closest_distance < 0.15?  ──YES──► DROP (duplicate, ~85%+ semantic match)
        │
       NO
        │
        ▼
Store in ChromaDB (unique event)
```

> **Threshold:** `0.15` cosine distance ≈ 85% semantic similarity. Tunable in `is_duplicate()`.

**`semantic_search(query, top_k=15, max_distance=0.85)`**

- Embeds the user query and retrieves the top-k nearest articles
- Filters out results with `distance > 0.85` (too semantically distant)
- Returns `List[ArticleProcessed]` for cluster packaging

---

### 4. Semantic Clustering Engine

**File:** `app/services/clustering.py`

**`generate_clusters()`** — called on every `GET /digest` request:

1. Fetches **all** article embeddings and metadata from ChromaDB
2. Runs **HDBSCAN** (`min_cluster_size=2`, `metric='euclidean'`) — density-based clustering that automatically discovers the number of clusters. Articles labeled `-1` are outliers and dropped.
3. Groups articles by cluster label
4. Calls `generate_cluster_metadata()` concurrently for each cluster using `asyncio.gather` — generates a topic name and unified summary
5. Returns `List[TopicCluster]`

**`generate_search_cluster(query)`** — called on every `GET /topic/{name}` request:

1. Runs `semantic_search(query)` — returns relevant articles
2. Wraps them into a single `TopicCluster` with an LLM-generated name/summary
3. Cluster ID prefixed with `search_` to distinguish from organic clusters

---

### 5. FastAPI REST Gateway

**File:** `app/main.py`

The API is versioned at `v1.1.0` and uses:
- **`SlowAPI`** for IP-based rate limiting
- **`X-API-Key` header** for endpoint authentication
- **`asynccontextmanager` lifespan** to boot and cancel the background worker task

#### Endpoints

| Method | Path | Rate Limit | Auth | Description |
|--------|------|-----------|------|-------------|
| `GET` | `/` | 10/min | ✗ | Health check — system status |
| `GET` | `/digest` | 5/min | ✓ | All semantically clustered news events |
| `GET` | `/topic/{name}` | 15/min | ✓ | Semantic search — find events matching a context query |
| `POST` | `/subscribe` | 5/min | ✓ | Subscribe the authenticated user to a topic keyword |
| `POST` | `/unsubscribe` | 5/min | ✓ | Remove a topic subscription |
| `GET` | `/subscriptions` | 10/min | ✓ | List all active subscriptions for the current API key |
| `GET` | `/my-feed` | 5/min | ✓ | Personalized feed — clusters filtered by subscribed topics |

**Interactive Docs:** Available at `http://localhost:8000/docs` (Swagger UI)

---

### 6. Streamlit Dashboard (Nexus UI)

**File:** `frontend/ui.py`

A full Bloomberg Terminal-style intelligence dashboard with a custom dark theme.

**Design System:**
- Color palette: Deep navy (`#0B0F19`) background, electric blue (`#3B82F6`) accents
- Fonts: `Fira Code` (monospace for data), `Fira Sans` (body text)
- Component style: glassmorphism cards, hover micro-animations, glow effects

**Key UI Features:**

| Feature | Description |
|---------|-------------|
| **Live Feed** | Auto-refreshes clusters every 60 seconds via `@st.cache_data(ttl=60)` |
| **Semantic Search** | Text input triggers `GET /topic/{name}` — returns contextually matched events even without exact keyword matches |
| **Quick Topic Pills** | One-click category filters: Tech, Business, AI, World Affairs, Politics, Science |
| **Sentiment Filter** | Client-side filter pills: All / Positive / Neutral / Negative |
| **Metric Cards** | Active Events, Deduplicated Sources, Noise Reduction %, Last Updated timestamp |
| **Subscribe / Track** | Per-cluster subscribe button calls `POST /subscribe` and updates the sidebar immediately via `st.rerun()` |
| **Alert Sidebar** | Permanent sidebar showing active subscriptions with per-topic delete buttons |
| **System Status Panel** | Live display of pipeline status, active LLM model, and vector DB |

---

## API Reference

### Authentication

All protected endpoints require the `X-API-Key` header:

```http
X-API-Key: nexus-admin-999
```

**Available keys (development):**
- `nexus-admin-999` — admin access
- `nexus-user-123` — standard user (subscribed to AI & Semiconductors by default)

### Example Requests

**Get all clustered events:**
```bash
curl -H "X-API-Key: nexus-admin-999" http://localhost:8000/digest
```

**Semantic search for a topic:**
```bash
curl -H "X-API-Key: nexus-admin-999" http://localhost:8000/topic/artificial%20intelligence
```

**Subscribe to a topic:**
```bash
curl -X POST -H "X-API-Key: nexus-user-123" "http://localhost:8000/subscribe?topic=Climate"
```

**Get personalized feed:**
```bash
curl -H "X-API-Key: nexus-user-123" http://localhost:8000/my-feed
```

---

## Data Models

```python
# Raw article pulled from RSS
class ArticleIngested(BaseModel):
    title: str
    url: HttpUrl
    source: str
    published_at: Optional[datetime]
    raw_content: Optional[str]

# Article after LLM processing
class ArticleProcessed(BaseModel):
    id: str
    title: str
    url: HttpUrl
    source: str
    published_at: Optional[datetime]
    two_line_summary: str       # LLM-generated 2-line summary
    sentiment: Optional[str]    # "Positive" | "Neutral" | "Negative"
    embedding_id: Optional[str] # ChromaDB reference
    cluster_id: Optional[str]   # HDBSCAN cluster label

# Grouped topic event
class TopicCluster(BaseModel):
    cluster_id: str
    topic_name: str             # LLM-generated 3-5 word title
    cluster_summary: str        # LLM-generated 1-sentence overview
    articles: List[ArticleProcessed]
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Web Framework** | FastAPI 0.136 | Async REST API with automatic OpenAPI docs |
| **ASGI Server** | Uvicorn | High-performance async server |
| **LLM** | OpenAI GPT-4o-mini | Structured summarization, sentiment, cluster naming |
| **Embeddings** | OpenAI text-embedding-3-small | Semantic vector representations |
| **Vector DB** | ChromaDB 1.5 (local persistent) | Embedding storage, cosine similarity search |
| **Clustering** | scikit-learn HDBSCAN | Unsupervised density-based topic clustering |
| **RSS Parsing** | feedparser + aiohttp | Async multi-source feed ingestion |
| **Frontend** | Streamlit 1.57 | Bloomberg-style intelligence dashboard |
| **Rate Limiting** | SlowAPI | IP-based request throttling |
| **Data Validation** | Pydantic v2 | Type-safe models and structured OpenAI outputs |
| **Containerization** | Docker + Docker Compose | Multi-service orchestration |
| **Numerical** | NumPy, SciPy | Embedding matrix operations |

---

## Getting Started

### Prerequisites

- Python 3.11+
- An **OpenAI API key** with access to `gpt-4o-mini` and `text-embedding-3-small`

### Local Development

**1. Clone and set up the virtual environment:**
```bash
git clone <repository-url>
cd news-intelligence-api
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

**2. Install dependencies:**
```bash
pip install -r requirements.txt
```

**3. Configure environment variables:**

Create a `.env.local` file in the project root:
```env
OPENAI_API_KEY=sk-your-openai-api-key-here
LLM_MODEL=gpt-4o-mini
```

**4. Run the API (with background worker):**
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The background ingestion worker starts automatically. The first ingestion cycle will begin immediately on boot.

**5. Run the Streamlit dashboard** (in a separate terminal):
```bash
streamlit run frontend/ui.py
```

Access the dashboard at **http://localhost:8501**
Access the API docs at **http://localhost:8000/docs**

---

### Docker / Docker Compose

The full stack can be run with a single command using Docker Compose.

**1. Set your API key:**
```bash
# Create a .env file (Docker Compose picks this up automatically)
echo "OPENAI_API_KEY=sk-your-key-here" > .env
```

**2. Build and launch all three services:**
```bash
docker-compose up --build
```

This starts:
- `nexus_api` — FastAPI on port `8000`
- `nexus_worker` — Background ingestion pipeline
- `nexus_ui` — Streamlit dashboard on port `8501`

**3. Stop the stack:**
```bash
docker-compose down
```

> **Note:** The `./data` directory is mounted as a volume into both the `api` and `worker` containers, so they share the same ChromaDB instance and vector data persists across restarts.

**Single-container mode** (via `start.sh`):
```bash
# Used by Railway and similar PaaS deployments
# Starts the API internally on 127.0.0.1:8000, then Streamlit publicly on $PORT
./start.sh
```

---

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `OPENAI_API_KEY` | *(required)* | Your OpenAI API key |
| `LLM_MODEL` | `gpt-4o-mini` | OpenAI model for summarization and cluster naming |
| `PORT` | `8501` | Port for the Streamlit dashboard (used by PaaS platforms) |

**Tunable parameters (in code):**

| Parameter | Location | Default | Description |
|-----------|----------|---------|-------------|
| Ingestion interval | `ingestion.py` | 180s | How often the pipeline runs |
| Articles per feed | `ingestion.py` | 15 | Max articles fetched per RSS source per cycle |
| Dedup threshold | `vector_store.py` | 0.15 | Cosine distance below which a story is a duplicate |
| Search top-k | `vector_store.py` | 15 | Number of candidate articles for semantic search |
| Search max distance | `vector_store.py` | 0.85 | Maximum cosine distance for search results |
| HDBSCAN min cluster size | `clustering.py` | 2 | Minimum articles required to form a cluster |

---

## News Sources

The system currently ingests from 5 curated RSS feeds:

```python
FEEDS = {
    "The Hindu (National)":  "https://www.thehindu.com/news/national/feeder/default.rss",
    "Times of India":        "http://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    "Mint (Business)":       "https://www.livemint.com/rss/news",
    "TechCrunch":            "https://techcrunch.com/feed/",
    "AlJazeera (Global)":    "https://www.aljazeera.com/xml/rss/all.xml",
}
```

To add more sources, append entries to `app/workers/rss_sources.py`.

---

## Security

- **API Key Authentication:** All data endpoints require a valid `X-API-Key` header. Keys are validated in `app/api/dependencies.py`.
- **Rate Limiting:** IP-based limits enforced via `SlowAPI` on every endpoint.
- **Internal API binding:** In single-container mode (`start.sh`), the FastAPI server binds to `127.0.0.1` only — it is never directly exposed to the public internet. Only the Streamlit dashboard is bound to `0.0.0.0`.
- **No external database:** ChromaDB runs locally with no network exposure. All vector data is stored in `./data/vector_db`.

> **Production Note:** The API key store (`VALID_API_KEYS` in `dependencies.py`) is currently in-memory. For production, migrate this to a database or secrets manager and load keys from environment variables.

---

## License

This project is for educational and personal use. Attribution appreciated.

---

*Built with ⚡ by Nexus Engine — powered by OpenAI, ChromaDB, FastAPI, and Streamlit.*
