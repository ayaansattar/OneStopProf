# OneStopProf

A RAG-powered professor review aggregator. Scrapes student reviews from Rate My Professors, embeds them into a local vector database, and lets you ask natural-language questions — either to **recommend professors for a course**, or to dig into a **specific professor**.

**Example questions:**
- *"Who should I take for CS220 as a beginner?"* (Recommend mode)
- *"Compare CS220 vs MATH235 for a beginner"* (Compare mode)
- *"Easiest professor for CHEM111?"* (Recommend mode)
- *"How difficult is the grading?"* (Ask mode — pick a professor first)

## Tech Stack

| Layer | Tool |
|---|---|
| Scraping | `httpx` |
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
│   ├── rmp_scraper.py       # Rate My Professors scraper
│   └── scrape_school.py     # Scrape all professors at a school (RMP)
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
python -m ingestion.scrape_school
```

Scrapes UMass Amherst professors from Rate My Professors and saves reviews to `data/rmp_reviews.json`.

To scrape a single professor instead, run `python -m ingestion.rmp_scraper` and edit the `__main__` block with the professor name, school ID, and RMP teacher ID.

### Step 2 — Embed and load into ChromaDB

```powershell
python -m pipeline.run_pipeline
```

Chunks reviews, generates embeddings, and loads them into `chroma_db/`. Runs a test retrieval query at the end.

### Step 3 — Test the RAG chain (terminal)

```powershell
python -m rag.chain
```

Runs a sample course recommendation query, then a professor-specific question via Groq.

### Step 4 — Launch the web UI

```powershell
streamlit run app/streamlit_app.py
```

Open [http://localhost:8501](http://localhost:8501). The app has three modes:

1. **Recommend a professor** — ask about a course or preference and get ranked recommendations with cited reviews. Mentions like `CS220` filter retrieval toward that course.
2. **Compare courses** — ask to compare two or more courses (e.g. `CS220 vs MATH235`); get pros/cons for each plus professor recommendations.
3. **Ask about a professor** — pick a professor from the dropdown and ask targeted questions.

## Deploy (Streamlit Community Cloud)

1. Push this repo to GitHub (include `chroma_db/` if you want the app to work without re-embedding).
2. At [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Set **Main file path** to `app/streamlit_app.py`.
4. In **Advanced settings**, set **Python version to 3.11** (required for ChromaDB / sentence-transformers).
5. Add secrets:

```toml
GROQ_API_KEY = "gsk_your_key_here"
```

6. Deploy. First install can take several minutes (downloads torch + the embedding model).

If you see `installer returned a non-zero exit code`, open **Manage app → Logs**, find the first `ERROR:` line, reboot after setting Python to **3.11**, and redeploy.

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
Recommend: course filter + multi-professor retrieve → Groq → ranked recommendations
Ask: professor filter + retrieve → Groq → cited answer
```

1. **Ingestion** — Reviews are scraped via RMP's GraphQL API and normalized to a unified schema.
2. **Pipeline** — Reviews are chunked, embedded locally with `sentence-transformers`, and stored in ChromaDB.
3. **Retrieval** — User queries are embedded and matched against review chunks via cosine similarity. Recommend mode filters by course when a code is detected (with open-search fallback); Ask mode filters by professor.
4. **Generation** — Top chunks are passed to Groq (Llama 3.3) with a system prompt that enforces citations and balanced answers.

