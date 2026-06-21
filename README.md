# OneStopProf

A RAG-powered professor review aggregator. Scrapes student reviews from Rate My Professors, embeds them into a local vector database, and lets you ask natural-language questions about any professor — with cited answers grounded in real reviews.

**Example questions:**
- *"Is this professor good for beginners in CS220?"*
- *"How difficult is the grading?"*
- *"What do students say about exams?"*

## Tech Stack

| Layer | Tool |
|---|---|
| Scraping | `httpx`, BeautifulSoup |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`) |
| Vector DB | ChromaDB |
| LLM | Groq API (Llama 3.3) |
| Frontend | Streamlit |

## Project Structure

```
OneStopProf/
├── data/                    # Scraped reviews (JSON, gitignored)
├── chroma_db/               # Vector store (gitignored, auto-created)
├── ingestion/
│   └── rmp_scraper.py       # Rate My Professors scraper
├── pipeline/
│   ├── chunker.py           # Text chunking
│   ├── embedder.py          # Local embeddings
│   ├── loader.py            # ChromaDB loader
│   └── run_pipeline.py      # End-to-end pipeline runner
├── rag/
│   ├── retriever.py         # Semantic search
│   └── chain.py             # LLM answer generation
├── app/
│   └── streamlit_app.py     # Web UI
├── .env                     # API keys (never commit)
└── requirements.txt
```

## Setup

### 1. Clone and create a virtual environment

```powershell
cd OneStopProf
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> **Windows note:** ChromaDB requires Microsoft C++ Build Tools. If `pip install` fails on `chroma-hnswlib`, install [Build Tools for Visual Studio](https://visualstudio.microsoft.com/visual-cpp-build-tools/) with the **Desktop development with C++** workload, then retry.

### 2. Configure environment variables

```powershell
copy .env.example .env
```

Edit `.env` and add your Groq API key (free at [console.groq.com](https://console.groq.com)):

```
GROQ_API_KEY=gsk_your_key_here
```

## Usage

Run all commands from the project root with the virtual environment activated.

### Step 1 — Scrape reviews

```powershell
python -m ingestion.rmp_scraper
```

This scrapes **Marius Minea** (UMass Amherst, Computer Science) and saves ~100 reviews to `data/rmp_reviews.json`.

To scrape a different professor, edit the `__main__` block in `ingestion/rmp_scraper.py` with the professor name, school ID, and RMP teacher ID.

### Step 2 — Embed and load into ChromaDB

```powershell
python -m pipeline.run_pipeline
```

Chunks reviews, generates embeddings, and loads them into `chroma_db/`. Runs a test retrieval query at the end.

### Step 3 — Test the RAG chain (terminal)

```powershell
python -m rag.chain
```

Runs three sample questions against Marius Minea's reviews via Groq.

### Step 4 — Launch the web UI

```powershell
streamlit run app/streamlit_app.py
```

Open [http://localhost:8501](http://localhost:8501), select a professor, ask a question, and view the cited answer with source reviews.

## Adding More Professors

1. Find the professor on [ratemyprofessors.com](https://www.ratemyprofessors.com) and note:
   - **School ID** from the URL (e.g. `/school/1513` → `1513`)
   - **Teacher ID** from the profile URL (e.g. `/professor/2416008` → `2416008`)
2. Update and run `ingestion/rmp_scraper.py`
3. Re-run `python -m pipeline.run_pipeline` — new professors appear in the Streamlit dropdown automatically

## How It Works

```
RMP GraphQL API  →  JSON reviews  →  Chunk + Embed  →  ChromaDB
                                                            ↓
User question  →  Embed query  →  Retrieve top-k chunks  →  Groq LLM  →  Cited answer
```

1. **Ingestion** — Reviews are scraped via RMP's GraphQL API and normalized to a unified schema.
2. **Pipeline** — Reviews are chunked, embedded locally with `sentence-transformers`, and stored in ChromaDB.
3. **Retrieval** — User queries are embedded and matched against review chunks via cosine similarity, filtered by professor.
4. **Generation** — Top chunks are passed to Groq (Llama 3.3) with a system prompt that enforces citations and balanced answers.

