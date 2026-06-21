import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from pipeline.loader import get_collection
from rag.chain import ask

st.set_page_config(page_title="OneStopProf", page_icon="🎓", layout="wide")


@st.cache_data
def get_professors() -> dict[str, str]:
    collection = get_collection()
    metadatas = collection.get()["metadatas"]
    profs: dict[str, str] = {}
    for meta in metadatas:
        pid = meta.get("professor_id")
        if pid and pid not in profs:
            profs[pid] = meta.get("name", pid)
    return profs


@st.cache_data
def get_professor_stats(professor_id: str) -> dict:
    collection = get_collection()
    metadatas = collection.get(where={"professor_id": professor_id})["metadatas"]

    if not metadatas:
        return {
            "total_reviews": 0,
            "avg_rating": None,
            "avg_difficulty": None,
            "university": "",
            "department": "",
        }

    review_indices = {m.get("review_index") for m in metadatas if m.get("review_index") != ""}
    ratings = []
    difficulties = []
    for meta in metadatas:
        if meta.get("chunk_id") not in (0, "0"):
            continue
        try:
            if meta.get("rating") not in (None, ""):
                ratings.append(float(meta["rating"]))
            if meta.get("difficulty") not in (None, ""):
                difficulties.append(float(meta["difficulty"]))
        except ValueError:
            pass

    if not ratings:
        seen = set()
        for meta in metadatas:
            idx = meta.get("review_index")
            if idx in seen:
                continue
            seen.add(idx)
            try:
                if meta.get("rating") not in (None, ""):
                    ratings.append(float(meta["rating"]))
                if meta.get("difficulty") not in (None, ""):
                    difficulties.append(float(meta["difficulty"]))
            except ValueError:
                pass

    return {
        "total_reviews": len(review_indices) or len(metadatas),
        "avg_rating": sum(ratings) / len(ratings) if ratings else None,
        "avg_difficulty": sum(difficulties) / len(difficulties) if difficulties else None,
        "university": metadatas[0].get("university", ""),
        "department": metadatas[0].get("department", ""),
    }


def _format_metric(value: float | None, suffix: str = "") -> str:
    if value is None:
        return "N/A"
    return f"{value:.1f}{suffix}"


st.title("🎓 OneStopProf")
st.caption("Ask anything about your professors — powered by real student reviews")

professors = get_professors()
if not professors:
    st.error("No professors found. Run the scraper and pipeline first.")
    st.stop()

if "query" not in st.session_state:
    st.session_state.query = ""

col1, col2 = st.columns([1, 3])

with col1:
    st.subheader("Select Professor")
    selected_name = st.selectbox(
        "Professor",
        sorted(professors.values()),
        label_visibility="collapsed",
    )
    professor_id = next(k for k, v in professors.items() if v == selected_name)
    stats = get_professor_stats(professor_id)

    st.markdown("---")
    if stats["university"]:
        st.caption(stats["university"])
    if stats["department"]:
        st.caption(stats["department"])

    st.metric("Avg Rating", _format_metric(stats["avg_rating"], " / 5.0"))
    st.metric("Avg Difficulty", _format_metric(stats["avg_difficulty"], " / 5.0"))
    st.metric("Total Reviews", stats["total_reviews"])

with col2:
    st.subheader(f"Ask about {selected_name}")

    st.markdown("**Try asking:**")
    examples = [
        "Is this professor good for beginners?",
        "How is the grading style?",
        "What do students say about exams?",
    ]
    example_cols = st.columns(len(examples))
    for col, example in zip(example_cols, examples):
        if col.button(example, use_container_width=True):
            st.session_state.query = example

    with st.form("query_form", clear_on_submit=False):
        query = st.text_input(
            "Your question:",
            value=st.session_state.query,
            placeholder="e.g. Is this professor good for beginners?",
        )
        submitted = st.form_submit_button("Ask", type="primary")

    if submitted and query.strip():
        st.session_state.query = query.strip()
        with st.spinner("Searching through student reviews..."):
            result = ask(query.strip(), professor_id)

        st.markdown("### Answer")
        st.markdown(result["answer"])

        with st.expander("📚 View Source Reviews"):
            for i, source in enumerate(result["sources"], 1):
                course = f" · {source['course']}" if source.get("course") else ""
                st.markdown(f"**Source {i} — {source['source'].upper()}{course}**")
                st.markdown(f"> {source['text']}")
                st.caption(
                    f"Rating: {source.get('rating', 'N/A')} | "
                    f"Date: {source.get('date', 'N/A')}"
                )
                st.divider()
