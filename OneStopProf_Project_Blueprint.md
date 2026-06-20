# OneStopProf — Professor Rating Aggregator
### Complete Solo Developer Blueprint | 4-Day Build Plan

---

## 1. Project Overview

OneStopProf is a Retrieval-Augmented Generation (RAG) system that scrapes professor reviews from Rate My Professor (RMP) and Reddit, embeds them into a vector database, and lets users ask natural language questions about any professor. The AI synthesizes real student reviews into a coherent, cited answer.

**Example queries the system will answer:**
- "Is Professor Smith good for beginners in CS101?"
- "How difficult is Dr. Johnson's grading?"
- "What do students say about her teaching style?"
- "Compare Dr. Lee and Dr. Patel for Linear Algebra."

This is a solo, 4-day MVP build. Complexity is intentionally kept minimal — one university, two data sources, local vector DB, and a Streamlit frontend.

---

## 2. Tech Stack

Every tool in this stack is either free or costs under $5 total. No paid subscriptions required.

| Layer | Tool | Why | Cost |
|---|---|---|---|
| Language | Python 3.11+ | Everything is in Python | Free |
| Scraping (RMP) | httpx + BeautifulSoup4 | RMP has an unofficial GraphQL API | Free |
| Scraping (Reddit) | PRAW | Official Reddit API wrapper | Free |
| Embeddings | sentence-transformers | Local, no API key needed | Free |
| Vector Database | ChromaDB | Local, zero setup, persists to disk | Free |
| LLM | Groq API (Llama 3) | Free tier, very fast inference | Free |
| RAG Framework | LangChain | Wires embeddings + LLM + retrieval | Free |
| Backend | FastAPI | Lightweight REST API (optional) | Free |
| Frontend | Streamlit | Build UI in 1-2 hours, pure Python | Free |
| Database | SQLite | Store structured professor metadata | Free |
| Environment | python-dotenv | Manage API keys cleanly | Free |

> **Alternative:** If you prefer OpenAI's quality, use `text-embedding-3-small` (~$0.02 for all embeddings) and `gpt-4o-mini` (~$0.01/query). Total cost for a few days: under $3.

---

## 3. Project Folder Structure

```
onestopprof/
├── data/                    # Raw scraped data (JSON files)
│   ├── rmp_reviews.json
│   └── reddit_reviews.json
├── ingestion/               # Scraping scripts
│   ├── rmp_scraper.py
│   └── reddit_scraper.py
├── pipeline/                # Embedding + vector DB loading
│   ├── chunker.py
│   ├── embedder.py
│   └── loader.py
├── rag/                     # RAG chain logic
│   ├── retriever.py
│   └── chain.py
├── api/                     # FastAPI backend (optional)
│   └── main.py
├── app/                     # Streamlit frontend
│   └── streamlit_app.py
├── chroma_db/               # ChromaDB persisted storage (auto-created)
├── .env                     # API keys (never commit this)
├── requirements.txt
└── README.md
```

---

## 4. Unified Review Schema

All reviews — regardless of source — are normalized into this schema before embedding:

```json
{
  "professor_id":   "mit_jane_smith",
  "name":           "Dr. Jane Smith",
  "university":     "MIT",
  "department":     "Computer Science",
  "course":         "6.006",
  "source":         "ratemyprofessor",
  "rating":         4.2,
  "difficulty":     3.1,
  "would_retake":   true,
  "tags":           ["helpful", "tough grader"],
  "review_text":    "Great at explaining recursion...",
  "date":           "2024-03-15",
  "upvotes":        12
}
```

---

## 5. Data Ingestion — Day 1

### 5.1 Rate My Professor Scraper

RMP has an unofficial GraphQL endpoint that returns structured JSON. No Playwright needed — just HTTP POST requests.

```python
# ingestion/rmp_scraper.py
import httpx, json, os
from dotenv import load_dotenv
load_dotenv()

RMP_GRAPHQL = "https://www.ratemyprofessors.com/graphql"

def search_professor(name: str, school_id: str):
    query = """
    query TeacherSearchResultsPageQuery($query: TeacherSearchQuery!) {
      search: newSearch {
        teachers(query: $query, first: 8) {
          edges {
            node {
              id
              firstName
              lastName
              avgRating
              avgDifficulty
              wouldTakeAgainPercent
              numRatings
              department
            }
          }
        }
      }
    }"""
    variables = {"query": {"text": name, "schoolID": school_id}}
    resp = httpx.post(
        RMP_GRAPHQL,
        json={"query": query, "variables": variables},
        headers={"Authorization": "Basic dGVzdDp0ZXN0"}
    )
    return resp.json()

def get_professor_reviews(teacher_id: str, count: int = 100):
    query = """
    query RatingsListQuery($id: ID!, $count: Int!) {
      node(id: $id) {
        ... on Teacher {
          ratings(first: $count) {
            edges {
              node {
                comment
                qualityRating
                difficultyRatingRounded
                wouldTakeAgain
                ratingTags
                date
                class
              }
            }
          }
        }
      }
    }"""
    variables = {"id": teacher_id, "count": count}
    resp = httpx.post(
        RMP_GRAPHQL,
        json={"query": query, "variables": variables},
        headers={"Authorization": "Basic dGVzdDp0ZXN0"}
    )
    return resp.json()
```

> **Finding your school ID:** Search your school on ratemyprofessors.com, then copy the numeric ID from the URL (e.g., `/school/1/professors` → school ID is `1`).

---

### 5.2 Reddit Scraper

Use PRAW — the official Reddit API wrapper. Free for up to 100 requests/minute.

```python
# ingestion/reddit_scraper.py
import praw, os, time
from dotenv import load_dotenv
load_dotenv()

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT")
)

def scrape_professor_mentions(professor_name: str, university_sub: str = None):
    subreddits = ["college", "Professor_Reviews", "RateMyProfessors"]
    if university_sub:
        subreddits.append(university_sub)  # e.g. "mit" or "harvard"

    results = []
    for sub in subreddits:
        try:
            for post in reddit.subreddit(sub).search(professor_name, limit=50):
                results.append({
                    "source": "reddit",
                    "review_text": post.selftext or post.title,
                    "upvotes": post.score,
                    "date": str(post.created_utc),
                    "url": f"https://reddit.com{post.permalink}"
                })
                # Also grab top comments
                post.comments.replace_more(limit=0)
                for comment in post.comments[:5]:
                    if len(comment.body) > 50:
                        results.append({
                            "source": "reddit",
                            "review_text": comment.body,
                            "upvotes": comment.score,
                            "date": str(comment.created_utc),
                        })
            time.sleep(1)  # be polite
        except Exception as e:
            print(f"Error scraping r/{sub}: {e}")
    return results
```

> **Reddit API setup:** Go to reddit.com/prefs/apps → Create App → choose "script" type. You get `client_id` and `client_secret` immediately. Takes 5 minutes, no credit card.

---

## 6. Processing Pipeline — Day 2

### 6.1 Text Chunking

Long reviews are split into overlapping chunks so vector search can match specific parts. Short reviews (under 150 words) are kept as-is.

```python
# pipeline/chunker.py
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=400,      # ~300 tokens
    chunk_overlap=50,    # overlap to preserve context
    separators=["\n\n", "\n", ". ", " "]
)

def chunk_review(review: dict) -> list[dict]:
    text = review["review_text"]
    # Don't chunk short reviews
    if len(text.split()) < 150:
        return [{**review, "chunk_id": 0}]
    chunks = splitter.split_text(text)
    return [
        {**review, "review_text": chunk, "chunk_id": i}
        for i, chunk in enumerate(chunks)
    ]

def chunk_all_reviews(reviews: list[dict]) -> list[dict]:
    all_chunks = []
    for review in reviews:
        all_chunks.extend(chunk_review(review))
    return all_chunks
```

---

### 6.2 Embedding (Local — No API Key)

`sentence-transformers` runs entirely on your CPU. The `all-MiniLM-L6-v2` model is fast, small (80MB), and produces strong semantic embeddings.

```python
# pipeline/embedder.py
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

def embed_texts(texts: list[str]) -> list[list[float]]:
    return model.encode(texts, batch_size=32, show_progress_bar=True).tolist()
```

---

### 6.3 Loading into ChromaDB

ChromaDB is a local vector database that persists to disk. No Docker, no cloud account needed.

```python
# pipeline/loader.py
import chromadb

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(
    name="professor_reviews",
    metadata={"hnsw:space": "cosine"}
)

def load_chunks(chunks: list[dict]):
    texts = [c["review_text"] for c in chunks]
    from pipeline.embedder import embed_texts
    embeddings = embed_texts(texts)

    collection.upsert(  # upsert = safe to re-run
        ids=[f"{c['professor_id']}_{c['source']}_{c['chunk_id']}" for c in chunks],
        documents=texts,
        embeddings=embeddings,
        metadatas=[{k: str(v) for k, v in c.items() if k != "review_text"} for c in chunks]
    )
    print(f"Loaded {len(chunks)} chunks into ChromaDB")
```

---

### 6.4 Full Pipeline Runner

```python
# pipeline/run_pipeline.py
import json
from pipeline.chunker import chunk_all_reviews
from pipeline.loader import load_chunks

def run(source_file: str, professor_meta: dict):
    with open(source_file) as f:
        raw_reviews = json.load(f)

    # Attach professor metadata to each review
    reviews = [{**r, **professor_meta} for r in raw_reviews]

    chunks = chunk_all_reviews(reviews)
    print(f"Created {len(chunks)} chunks from {len(reviews)} reviews")

    load_chunks(chunks)

if __name__ == "__main__":
    run("data/rmp_reviews.json", {
        "professor_id": "mit_jane_smith",
        "name": "Dr. Jane Smith",
        "university": "MIT",
        "department": "Computer Science"
    })
```

---

## 7. RAG Chain — Day 3

### 7.1 Retriever

```python
# rag/retriever.py
import chromadb
from pipeline.embedder import embed_texts

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_collection("professor_reviews")

def retrieve(query: str, professor_id: str, n_results: int = 6) -> list[dict]:
    query_embedding = embed_texts([query])[0]
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where={"professor_id": professor_id},
        include=["documents", "metadatas", "distances"]
    )
    return [
        {
            "text": doc,
            "source": meta.get("source", "unknown"),
            "rating": meta.get("rating"),
            "date": meta.get("date"),
            "distance": dist
        }
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )
    ]
```

---

### 7.2 LLM Chain (Groq — Free)

Sign up at [console.groq.com](https://console.groq.com) — no credit card, free API key in 2 minutes.

```python
# rag/chain.py
import os
from groq import Groq
from rag.retriever import retrieve
from dotenv import load_dotenv
load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """
You are a helpful assistant that answers questions about university professors
based on real student reviews. Follow these rules:
- Always cite which source each claim comes from (Rate My Professor or Reddit)
- Be balanced and acknowledge both positive and negative reviews
- If reviews conflict, present both perspectives
- Never fabricate or infer information not present in the reviews
- Keep answers concise (3-5 paragraphs max)
"""

def ask(query: str, professor_id: str) -> dict:
    chunks = retrieve(query, professor_id)

    if not chunks:
        return {"answer": "No reviews found for this professor.", "sources": []}

    context = "\n---\n".join([
        f"[{c['source'].upper()}] {c['text']}"
        for c in chunks
    ])

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Student reviews:\n{context}\n\nQuestion: {query}"}
    ]

    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=800,
        temperature=0.3
    )

    return {
        "answer": resp.choices[0].message.content,
        "sources": chunks
    }
```

---

## 8. Streamlit Frontend — Day 4

Streamlit lets you build a full interactive web app in pure Python. No HTML, CSS, or JavaScript required.

```python
# app/streamlit_app.py
import streamlit as st
import chromadb
from rag.chain import ask

st.set_page_config(page_title="OneStopProf", page_icon="🎓", layout="wide")

# Load professor list from ChromaDB
@st.cache_resource
def get_client():
    return chromadb.PersistentClient(path="./chroma_db")

@st.cache_data
def get_professors():
    client = get_client()
    collection = client.get_collection("professor_reviews")
    metadatas = collection.get()["metadatas"]
    profs = {}
    for m in metadatas:
        pid = m.get("professor_id")
        if pid and pid not in profs:
            profs[pid] = m.get("name", pid)
    return profs

# UI
st.title("🎓 OneStopProf")
st.caption("Ask anything about your professors — powered by real student reviews")

professors = get_professors()

col1, col2 = st.columns([1, 3])

with col1:
    st.subheader("Select Professor")
    selected_name = st.selectbox("", sorted(professors.values()), label_visibility="collapsed")
    professor_id = [k for k, v in professors.items() if v == selected_name][0]

    # Show basic stats
    st.markdown("---")
    st.metric("Avg Rating", "4.2 / 5.0")
    st.metric("Avg Difficulty", "3.1 / 5.0")
    st.metric("Total Reviews", "142")

with col2:
    st.subheader(f"Ask about {selected_name}")

    # Example questions
    st.markdown("**Try asking:**")
    examples = [
        "Is this professor good for beginners?",
        "How is the grading style?",
        "What do students say about exams?",
    ]
    for ex in examples:
        if st.button(ex, key=ex):
            st.session_state.query = ex

    query = st.text_input(
        "Your question:",
        value=st.session_state.get("query", ""),
        placeholder="e.g. Is this professor good for beginners?"
    )

    if st.button("Ask", type="primary") and query:
        with st.spinner("Searching through student reviews..."):
            result = ask(query, professor_id)

        st.markdown("### Answer")
        st.markdown(result["answer"])

        with st.expander("📚 View Source Reviews"):
            for i, source in enumerate(result["sources"], 1):
                st.markdown(f"**Source {i} — {source['source'].upper()}**")
                st.markdown(f"> {source['text']}")
                st.caption(f"Rating: {source.get('rating', 'N/A')} | Date: {source.get('date', 'N/A')}")
                st.divider()
```

Run with: `streamlit run app/streamlit_app.py`

---

## 9. Environment Setup

### 9.1 .env File

```bash
# .env — DO NOT commit to GitHub
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
REDDIT_CLIENT_ID=xxxxxxxxxxxxxxx
REDDIT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
REDDIT_USER_AGENT=onestopprof/1.0 by u/yourusername
```

### 9.2 requirements.txt

```
httpx==0.27.0
beautifulsoup4==4.12.3
praw==7.7.1
sentence-transformers==3.0.1
chromadb==0.5.3
langchain==0.3.0
langchain-community==0.3.0
groq==0.11.0
streamlit==1.38.0
python-dotenv==1.0.1
fastapi==0.115.0
uvicorn==0.30.6
```

### 9.3 Initial Setup

```bash
# Create project and virtual environment
mkdir onestopprof && cd onestopprof
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

pip install -r requirements.txt

# Copy and fill in your API keys
cp .env.example .env
```

### 9.4 .gitignore

```
venv/
.env
chroma_db/
data/
__pycache__/
*.pyc
```

---

## 10. 4-Day Build Plan

| Day | Goal | Tasks | End State |
|---|---|---|---|
| Day 1 | Data Collection | Set up Reddit API credentials, write RMP GraphQL scraper, write Reddit scraper, run both and save to JSON | 500–2000 reviews in `data/` as JSON |
| Day 2 | Vector Pipeline | Write chunker, set up sentence-transformers, load into ChromaDB, verify similarity search in a notebook | All reviews embedded and queryable |
| Day 3 | RAG Chain | Set up Groq API key, write retriever, write LangChain chain, test 10+ queries in terminal | Terminal chatbot answering professor questions |
| Day 4 | Frontend + Polish | Build Streamlit UI, add professor selector, show stats, test end-to-end, write README | Live web app, demo-ready |

### Bonus (if you have extra time)
- Add a second university's data for breadth
- Scrape Reddit comments (not just post titles)
- Build a professor comparison feature
- Add a "Show Sources" expander so users see raw reviews
- Deploy to Streamlit Cloud (free, one-click from GitHub)

---

## 11. Common Gotchas & Solutions

| Problem | Cause | Solution |
|---|---|---|
| RMP returns empty results | School ID required for search | Find your school's RMP ID from the URL on ratemyprofessors.com |
| Reddit rate limit hit | Too many requests too fast | Add `time.sleep(1)` between requests; PRAW has built-in backoff |
| ChromaDB duplicate errors | Re-running loader on same data | Use `collection.upsert()` instead of `collection.add()` |
| Embeddings are slow | CPU-only, large batch | Use `batch_size=32` and `all-MiniLM-L6-v2` (fastest model) |
| Groq context length error | Too many chunks passed as context | Reduce `n_results` from 6 to 4 in the retriever |
| Streamlit reloads on every keystroke | Default Streamlit behavior | Wrap your query in `with st.form("query_form"):` |
| Same professor, different spellings | RMP vs Reddit naming differences | Normalize names: lowercase, strip titles (Dr., Prof.) |

---

## 12. API Keys You Need

You only need two accounts:

| Service | URL | Free Tier | Setup Time |
|---|---|---|---|
| Groq (LLM) | console.groq.com | Unlimited free tier, fast Llama 3 | 2 min, no credit card |
| Reddit API | reddit.com/prefs/apps | 100 req/min, free forever | 5 minutes |
| OpenAI (optional) | platform.openai.com | $5 free credit on signup | 5 min + credit card |

---

## 13. Future Enhancements (Post-MVP)

- **Hybrid Search** — Combine vector search with BM25 keyword search for better recall on specific course codes or exact professor names
- **Scheduled Re-ingestion** — Use APScheduler or cron to re-scrape monthly and keep reviews fresh
- **Deduplication** — Use fuzzy name matching (`rapidfuzz`) + university to create canonical professor profiles across sources
- **Grade Distribution Data** — Scrape grade data from Koofers or public university reports to add a quantitative difficulty signal
- **Re-ranking** — Use a cross-encoder model to re-rank top-20 retrieved chunks to top-5, improving answer quality
- **Sentiment Analysis** — Pre-compute sentiment scores per review and aggregate by topic (grading, clarity, helpfulness)
- **Multi-University Support** — Abstract the university parameter so any school can be queried
- **Deployment** — Deploy Streamlit to Streamlit Cloud (free). Move ChromaDB to Pinecone for production scale

---

*Built with Python · ChromaDB · sentence-transformers · Groq · Streamlit*
