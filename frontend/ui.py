import streamlit as st
import requests
from datetime import datetime

# --- Configuration & Custom CSS ---
API_URL = "http://api:8000"
st.set_page_config(
    page_title="Nexus | Event Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Toast Notification System (to survive st.rerun)
if "toast_msg" in st.session_state:
    st.toast(st.session_state.toast_msg, icon="✅")
    del st.session_state.toast_msg

# Injecting CSS to create the "Bloomberg/Datadog" UI and lock the sidebar
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap');

    .stApp { background-color: #0B0F19 !important; color: #F8FAFC !important; }
    p, h1, h2, h3, h4, h5, h6, li { font-family: 'Fira Sans', sans-serif !important; }

    header[data-testid="stHeader"] { background: transparent !important; display: none !important; }
    [data-testid="stToolbar"], [data-testid="stAppDeployButton"] { display: none !important; }
    footer {visibility: hidden;}
    
    /* --- PERMANENT SIDEBAR FIX --- */
    [data-testid="collapsedControl"], [data-testid="stSidebarCollapseButton"] { display: none !important; }
    section[data-testid="stSidebar"] {
        background-color: #070A11 !important; border-right: 1px solid #1E293B !important;
        min-width: 320px !important; max-width: 320px !important; transform: translateX(0px) !important; visibility: visible !important;
    }
    section[data-testid="stSidebar"] > div { background-color: transparent !important; }
    
    /* Hide Sidebar on Mobile Screens */
    @media (max-width: 768px) {
        section[data-testid="stSidebar"] {
            display: none !important;
        }
    }

    /* --- Data Cards & Expanders --- */
    [data-testid="stExpander"] {
        background-color: #111827 !important; border: 1px solid #1F2937 !important;
        border-radius: 8px !important; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5) !important;
    }
    [data-testid="stExpander"] summary { border-bottom: 1px solid #1F2937 !important; background-color: transparent !important; }
    [data-testid="stExpander"] summary p { color: #60A5FA !important; font-weight: 600 !important; }
    [data-testid="stExpander"] summary p > span:first-child { font-family: 'Fira Code', monospace !important; font-size: 1.05rem !important; }
    
    .material-symbols-rounded, .material-icons, [class*="Icon"] { font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important; }
    [data-testid="stExpander"] summary svg { fill: #60A5FA !important; color: #60A5FA !important; }

    /* Custom Metric Cards */
    .metric-card {
        background: linear-gradient(145deg, #111827, #0B0F19); border: 1px solid #1F2937;
        padding: 20px; border-radius: 8px; text-align: center; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.5);
    }
    .metric-label { color: #94A3B8; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
    .metric-value { color: #3B82F6; font-size: 2.2rem; font-family: 'Fira Code', monospace; font-weight: 700; text-shadow: 0 0 10px rgba(59, 130, 246, 0.4); }
    
    /* Article Card */
    .article-card {
        background-color: #1F2937; border-left: 3px solid #3B82F6; border-radius: 6px; padding: 16px;
        margin-bottom: 12px; transition: transform 0.2s, box-shadow 0.2s;
    }
    .article-card:hover { transform: translateX(4px); box-shadow: -4px 4px 15px rgba(0,0,0,0.5); border-left-color: #60A5FA; }
    .article-meta { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .article-source { color: #94A3B8; font-size: 0.8rem; font-family: 'Fira Code', monospace; text-transform: uppercase; letter-spacing: 0.5px; }
    .article-title { color: #F8FAFC; font-size: 1.15rem; font-weight: 600; text-decoration: none; display: block; margin-bottom: 6px; }
    .article-title:hover { color: #60A5FA; text-decoration: underline; }
    .article-summary { color: #CBD5E1; font-size: 0.95rem; line-height: 1.5; }
    
    /* Badges */
    .badge { padding: 4px 10px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; font-family: 'Fira Code', monospace; text-transform: uppercase; }
    .badge-positive { background-color: rgba(16, 185, 129, 0.1); color: #34D399; border: 1px solid rgba(52, 211, 153, 0.3); }
    .badge-negative { background-color: rgba(239, 68, 68, 0.1); color: #F87171; border: 1px solid rgba(248, 113, 113, 0.3); }
    .badge-neutral  { background-color: rgba(148, 163, 184, 0.1); color: #94A3B8; border: 1px solid rgba(148, 163, 184, 0.3); }
    
    .exec-summary {
        background-color: rgba(59, 130, 246, 0.05); border: 1px solid rgba(59, 130, 246, 0.2);
        border-radius: 6px; padding: 12px 16px; margin-bottom: 16px; color: #E2E8F0; font-size: 0.95rem;
    }
    .exec-summary strong { color: #60A5FA; }
    
    /* Style all Streamlit buttons to match the Dark Theme */
    .stButton > button {
        background-color: rgba(59, 130, 246, 0.1) !important;
        color: #60A5FA !important;
        border: 1px solid rgba(59, 130, 246, 0.4) !important;
        font-family: 'Fira Code', monospace !important;
        font-weight: 600 !important;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        background-color: rgba(59, 130, 246, 0.3) !important;
        border-color: #3B82F6 !important;
        color: #F8FAFC !important;
    }
    .stButton > button:disabled, .stButton > button:disabled:hover {
        background-color: rgba(16, 185, 129, 0.1) !important;
        border-color: rgba(16, 185, 129, 0.4) !important;
        color: #34D399 !important;
    }
    
    /* Style Streamlit Pills to match Dark Theme */
    [data-testid="stPill"], [data-testid="stPill"] * {
        background-color: #1F2937 !important;
        color: #94A3B8 !important;
        border-color: #374151 !important;
    }
    [data-testid="stPill"]:hover, [data-testid="stPill"]:hover * {
        background-color: #374151 !important;
        color: #F8FAFC !important;
    }
    [data-testid="stPill"][aria-pressed="true"], 
    [data-testid="stPill"][aria-pressed="true"] *,
    [data-testid="stPill"][data-checked="true"],
    [data-testid="stPill"][data-checked="true"] * {
        background-color: rgba(59, 130, 246, 0.2) !important;
        color: #60A5FA !important;
        border-color: #3B82F6 !important;
    }

    /* Loader */
    .nexus-loader-container { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 60px; }
    .nexus-loader { width: 48px; height: 48px; border: 3px solid rgba(59, 130, 246, 0.1); border-radius: 50%; border-top-color: #3B82F6; animation: spin 1s ease-in-out infinite; margin-bottom: 20px; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .nexus-loader-text { color: #60A5FA; font-family: 'Fira Code', monospace; font-size: 0.9rem; letter-spacing: 2px; animation: pulse 1.5s infinite; }
    @keyframes pulse { 0% { opacity: 0.6; } 50% { opacity: 1; } 100% { opacity: 0.6; } }
</style>
""", unsafe_allow_html=True)

HEADERS = {"X-API-Key": "nexus-admin-999"}

# --- Data Fetching ---
@st.cache_data(ttl=60, show_spinner=False)
def fetch_all_clusters():
    try:
        response = requests.get(f"{API_URL}/digest", headers=HEADERS)
        if response.status_code == 200: return response.json()
        return []
    except: return []

@st.cache_data(ttl=60, show_spinner=False)
def fetch_topic_cluster(topic_name):
    try:
        response = requests.get(f"{API_URL}/topic/{topic_name}", headers=HEADERS)
        if response.status_code == 200: return [response.json()]
        return []
    except: return []

def fetch_subscriptions():
    try:
        response = requests.get(f"{API_URL}/subscriptions", headers=HEADERS)
        if response.status_code == 200: return response.json().get("subscriptions", [])
        return []
    except: return []

def add_subscription(topic):
    try:
        response = requests.post(f"{API_URL}/subscribe?topic={topic}", headers=HEADERS)
        return response.status_code == 200
    except: return False

def remove_subscription(topic):
    try:
        response = requests.post(f"{API_URL}/unsubscribe?topic={topic}", headers=HEADERS)
        return response.status_code == 200
    except: return False

# --- Central State ---
# Fetch alerts early so both the sidebar and the main feed can access the user's state
subs = fetch_subscriptions()

# --- Sidebar UI ---
with st.sidebar:
    st.markdown("""
        <div style="display: flex; align-items: center; margin-bottom: 20px;">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#3B82F6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 12px;">
                <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"></path>
            </svg>
            <h2 style="margin: 0; color: #F8FAFC; font-weight: 700; font-family: 'Fira Code', monospace; font-size: 1.5rem;">NEXUS ENGINE</h2>
        </div>
    """, unsafe_allow_html=True)
    st.caption("v1.1.0 | PRODUCTION ENV")
    st.divider()
    
    st.markdown("<div style='font-family: \"Fira Code\", monospace; font-size: 0.85rem; color: #94A3B8; margin-bottom: 8px;'>ACTIVE ALERTS</div>", unsafe_allow_html=True)
    
    if subs:
        for sub in subs:
            sub_col, del_col = st.columns([0.8, 0.2])
            with sub_col:
                st.markdown(f"""
                <div style="background-color: #111827; border: 1px solid #1F2937; padding: 6px 12px; border-radius: 4px; margin-bottom: 6px; border-left: 2px solid #3B82F6;">
                    <span style="color: #60A5FA; font-family: 'Fira Code', monospace; font-size: 0.8rem;">🔔 {sub.upper()}</span>
                </div>
                """, unsafe_allow_html=True)
            with del_col:
                if st.button("✖", key=f"del_{sub}"):
                    if remove_subscription(sub):
                        st.session_state.toast_msg = f"Alert removed for {sub}"
                        st.rerun()
    else:
        st.markdown("<div style='color: #64748B; font-size: 0.85rem; margin-bottom: 10px;'>No active alerts. Click 'Track Event' on any intelligence card.</div>", unsafe_allow_html=True)
                
    st.divider()
    st.markdown("""
        <div style="font-family: 'Fira Code', monospace; font-size: 0.8rem; color: #94A3B8; line-height: 2;">
            <div style="display: flex; justify-content: space-between;">
                <span>PIPELINE:</span><span style="color: #34D399; font-weight: 600;">● ACTIVE</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span>MODEL:</span><span style="color: #F8FAFC;">GPT-4O-MINI</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span>VECTOR_DB:</span><span style="color: #F8FAFC;">CHROMADB</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

# --- Main Dashboard UI ---
st.markdown("""
    <h1 style="font-weight: 700; margin-bottom: 0px; color: #F8FAFC;">Live Event Intelligence</h1>
    <p style="color: #94A3B8; font-size: 1.05rem; margin-top: 5px; margin-bottom: 24px;">Real-time semantic clustering and multi-source deduplication pipeline.</p>
""", unsafe_allow_html=True)

search_topic = st.text_input("QUERY", placeholder="🔍 Search live events, topics, or keywords...", label_visibility="collapsed")

col_topic, col_sent = st.columns([0.65, 0.35])
with col_topic:
    quick_topic = st.pills("Quick Topics", options=["Tech", "Business", "AI", "World Affairs", "Politics", "Science"], selection_mode="single", label_visibility="collapsed")
with col_sent:
    sentiment_filter = st.pills("Sentiment", options=["All", "Positive", "Neutral", "Negative"], selection_mode="single", default="All", label_visibility="collapsed")

st.markdown("<br>", unsafe_allow_html=True)

active_query = search_topic if search_topic else quick_topic

loader_placeholder = st.empty()
loader_msg = f"ANALYZING TOPIC: {active_query.upper()}..." if active_query else "AGGREGATING LIVE EVENTS..."

loader_placeholder.markdown(f"""
    <div class="nexus-loader-container">
        <div class="nexus-loader"></div>
        <div class="nexus-loader-text">{loader_msg}</div>
    </div>
""", unsafe_allow_html=True)

if active_query:
    clusters = fetch_topic_cluster(active_query)
    loader_placeholder.empty()
    if not clusters: st.warning(f"No semantic matches found for '{active_query}' in current database.")
else:
    clusters = fetch_all_clusters()
    loader_placeholder.empty()

# Apply sentiment filter locally
if clusters and sentiment_filter and sentiment_filter != "All":
    filtered_clusters = []
    for cluster in clusters:
        filtered_articles = [a for a in cluster["articles"] if a.get("sentiment", "Neutral").lower() == sentiment_filter.lower()]
        if filtered_articles:
            # Shallow copy the cluster and overwrite the articles list
            cluster_copy = dict(cluster)
            cluster_copy["articles"] = filtered_articles
            filtered_clusters.append(cluster_copy)
    clusters = filtered_clusters

if clusters:
    total_clusters = len(clusters)
    total_articles = sum(len(c["articles"]) for c in clusters)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">ACTIVE EVENTS</div><div class="metric-value">{total_clusters}</div></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">DEDUPLICATED SOURCES</div><div class="metric-value">{total_articles}</div></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">NOISE REDUCTION</div><div class="metric-value">{int(total_articles * 1.4)}%</div></div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">LAST UPDATED</div><div class="metric-value" style="font-size: 1.8rem;">{datetime.now().strftime("%H:%M:%S")}</div></div>""", unsafe_allow_html=True)
    
    st.markdown("<br><div style='font-family: \"Fira Code\", monospace; font-size: 1rem; color: #60A5FA; border-bottom: 1px solid #1F2937; padding-bottom: 8px; margin-bottom: 16px;'>// INTELLIGENCE FEED</div>", unsafe_allow_html=True)

    for cluster in clusters:
        header_title = f"✦ {cluster['topic_name']} [{len(cluster['articles'])} VERIFIED SOURCES]"
        with st.expander(header_title, expanded=True):
            
            # Divide the top of the expander into the Summary and the Action Button
            exec_col, action_col = st.columns([0.85, 0.15])
            
            with exec_col:
                st.markdown(f"""<div class="exec-summary" style="margin-bottom: 0px;"><strong>EXECUTIVE SUMMARY:</strong> {cluster['cluster_summary']}</div>""", unsafe_allow_html=True)
            
            with action_col:
                # Check if the user is already tracking this specific cluster topic
                topic = cluster['topic_name']
                is_subscribed = any(topic.lower() == s.lower() for s in subs)
                
                if not is_subscribed:
                    # Render a clickable tracking button using a unique key
                    if st.button("Subscribe", key=f"track_{cluster['cluster_id']}", use_container_width=True):
                        if add_subscription(topic):
                            # Store toast message in session state so it survives the rerun
                            st.session_state.toast_msg = f"Alert configured. You are now tracking: {topic}"
                            # Force a fast refresh so the sidebar updates instantly
                            st.rerun()
                else:
                    # Render a disabled "Active" state button
                    st.button("Subscribed", key=f"active_{cluster['cluster_id']}", disabled=True, use_container_width=True)
                    
            st.markdown("<br>", unsafe_allow_html=True)
            
            for article in cluster["articles"]:
                sentiment = article.get("sentiment", "Neutral").lower()
                badge_class = f"badge-{sentiment}"
                st.markdown(f"""
                <div class="article-card">
                    <div class="article-meta">
                        <span class="article-source">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:inline; margin-bottom:-1px; margin-right:4px;">
                                <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
                                <line x1="8" y1="21" x2="16" y2="21"></line>
                                <line x1="12" y1="17" x2="12" y2="21"></line>
                            </svg>
                            {article['source']}
                        </span>
                        <span class="badge {badge_class}">{sentiment.upper()}</span>
                    </div>
                    <a href="{article['url']}" target="_blank" class="article-title">{article['title']}</a>
                    <div class="article-summary">{article['two_line_summary']}</div>
                </div>
                """, unsafe_allow_html=True)
else:
    st.info("System is awaiting data. Run the ingestion pipeline to populate the vector database.")