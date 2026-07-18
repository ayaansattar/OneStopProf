# OneStopProf

A RAG-powered course-planning assistant for UMass Amherst. OneStopProf
scrapes recent Rate My Professors reviews, embeds them in ChromaDB, and uses
Groq to answer questions with supporting review citations.

## Features

- **Professor recommendations** — describe a course and your preferences to
  get ranked professor suggestions.
- **Course comparisons** — compare two or more course codes and receive pros,
  cons, workload observations, and professor recommendations for each.
- **Professor Q&A** — type or browse for a professor, view their quality,
  difficulty, and review counts, then ask targeted questions.
- **Course-aware retrieval** — course codes such as `CS220` narrow
  recommendation and comparison evidence to matching reviews.
- **Review citations** — generated answers include expandable source reviews.
- **RMP-inspired interface** — searchable professor selection, color-coded
  rating boxes, example prompts, corpus statistics, and responsive layouts.

Example questions:

- *"Who should I take for CS220 as a beginner?"*
- *"Compare CS220 vs MATH235 if I care about exams."*
- *"Easiest professor for CHEM111?"*
- *"How difficult is the grading?"* (after selecting a professor)

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
├── chroma_db/               # Persisted vector store used by the deployed app
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
├── .streamlit/
│   └── config.toml          # Streamlit theme and server settings
├── .devcontainer/           # Optional Codespaces/dev-container setup
├── .env.example             # Environment variable template
└── requirements.txt
```

`data/` and `.env` are intentionally ignored. `chroma_db/` is currently
tracked so Streamlit Community Cloud can start without running the embedding
pipeline during deployment.

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

The default command targets UMass Amherst, keeps professors with more than
five ratings and recent activity, and saves reviews from the last five years
to `data/rmp_reviews.json`. It also writes `data/professors.json` as a scrape
inventory and uses `data/scrape_checkpoint.json` to resume interrupted runs.

Useful options:

```powershell
# Small test scrape
python -m ingestion.scrape_school --limit 10

# Start a fresh scrape instead of resuming a checkpoint
python -m ingestion.scrape_school --no-resume

# Change the recency window
python -m ingestion.scrape_school --max-review-age-years 3
```

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

1. **Recommend** — ask about a course or preference and get ranked
   recommendations with cited reviews. Mentions like `CS220` filter retrieval
   toward that course.
2. **Compare courses** — ask to compare two or more courses (e.g. `CS220 vs MATH235`); get pros/cons for each plus professor recommendations.
3. **Ask a professor** — type a name or browse the dropdown, inspect rating
   summaries, and ask questions grounded in that professor's reviews.

## Deploy (Streamlit Community Cloud)

1. Push this repo to GitHub, including the populated `chroma_db/` directory.
2. At [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Set **Main file path** to `app/streamlit_app.py`.
4. In **Advanced settings**, set **Python version to 3.11** (required for ChromaDB / sentence-transformers).
5. Add secrets:

```toml
GROQ_API_KEY = "gsk_your_key_here"
```

6. Deploy. The first install can take several minutes because it downloads
   CPU PyTorch and the embedding model.

If you see `installer returned a non-zero exit code`, open **Manage app → Logs**, find the first `ERROR:` line, reboot after setting Python to **3.11**, and redeploy.

The `pysqlite3-binary` compatibility shim is used on Streamlit Cloud when the
system SQLite version is too old for ChromaDB.

## Keeping Reviews Up to Date

For a routine refresh, stop the Streamlit app and run:

```powershell
python -m ingestion.scrape_school --no-resume
python -m pipeline.run_pipeline
```

Use the command without `--no-resume` only when continuing an interrupted
scrape that still has `data/scrape_checkpoint.json`.

The pipeline upserts current chunks. For a completely clean rebuild that also
removes reviews no longer present in the source JSON, delete the local
`chroma_db/` directory after stopping the app, then run
`python -m pipeline.run_pipeline`.

After refreshing the database:

1. Restart the local Streamlit app, or let it reload.
2. Commit the updated `chroma_db/` files.
3. Push them to GitHub.
4. Reboot the Streamlit Community Cloud app if it does not redeploy
   automatically.

## How It Works

```
RMP GraphQL API  →  JSON reviews  →  Chunk + Embed  →  ChromaDB
                                                            ↓
Recommend: course filter + multi-professor retrieval → Groq → ranked picks
Compare: multiple course filters + retrieval → Groq → pros, cons, professor picks
Ask: professor filter + semantic retrieval → Groq → cited answer
```

1. **Ingestion** — Reviews are scraped via RMP's GraphQL API and normalized to a unified schema.
2. **Pipeline** — Reviews are chunked, embedded locally with `sentence-transformers`, and stored in ChromaDB.
3. **Retrieval** — User queries are embedded and matched against review chunks
   using cosine similarity. Recommend and Compare apply course metadata
   filters when course codes are detected; Ask filters by professor.
4. **Generation** — Top chunks are passed to Groq (Llama 3.3) with a system prompt that enforces citations and balanced answers.

