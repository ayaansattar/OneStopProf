import sys
from pathlib import Path

# ChromaDB on Streamlit Cloud needs a newer SQLite than the system default.
try:
    __import__("pysqlite3")
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from pipeline.loader import get_collection
from rag.chain import ask, recommend

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


def _render_sources(sources: list[dict], *, show_professor: bool = False) -> None:
    with st.expander("📚 View Source Reviews"):
        for i, source in enumerate(sources, 1):
            course = f" · {source['course']}" if source.get("course") else ""
            professor = ""
            if show_professor and source.get("name"):
                professor = f"{source['name']} · "
            st.markdown(
                f"**Source {i} — {professor}{source.get('source', 'unknown').upper()}{course}**"
            )
            st.markdown(f"> {source['text']}")
            st.caption(
                f"Rating: {source.get('rating', 'N/A')} | "
                f"Date: {source.get('date', 'N/A')}"
            )
            st.divider()


st.title("🎓 OneStopProf")
st.caption("Find the right professor for your course — powered by real student reviews")

professors = get_professors()
if not professors:
    st.error("No professors found. Run the scraper and pipeline first.")
    st.stop()

if "rec_query" not in st.session_state:
    st.session_state.rec_query = ""
if "ask_query" not in st.session_state:
    st.session_state.ask_query = ""

rec_tab, ask_tab = st.tabs(["Recommend a professor", "Ask about a professor"])

with rec_tab:
    st.subheader("What course or kind of professor are you looking for?")

    st.markdown("**Try asking:**")
    rec_examples = [
        "Who should I take for CS220 as a beginner?",
        "Easiest professor for CHEM111?",
        "Best for MATH235 if I care about exams?",
    ]
    rec_cols = st.columns(len(rec_examples))
    for i, (col, example) in enumerate(zip(rec_cols, rec_examples)):
        if col.button(example, use_container_width=True, key=f"rec_example_{i}"):
            st.session_state.rec_query = example
            st.rerun()

    with st.form("recommend_form", clear_on_submit=False):
        rec_query = st.text_input(
            "Your question:",
            key="rec_query",
            placeholder="e.g. Who should I take for CS220 as a beginner?",
        )
        rec_submitted = st.form_submit_button("Recommend", type="primary")

    if rec_submitted and rec_query.strip():
        with st.spinner("Searching reviews across professors..."):
            result = recommend(rec_query.strip())

        if result.get("course"):
            st.caption(f"Filtered toward course: **{result['course']}**")

        if result.get("professors"):
            st.markdown("**Professors in the evidence set**")
            for prof in result["professors"][:6]:
                rating = (
                    f"{prof['avg_rating_in_context']:.1f}/5"
                    if prof.get("avg_rating_in_context") is not None
                    else "N/A"
                )
                st.markdown(
                    f"- **{prof['name']}** — context rating {rating} "
                    f"({prof['review_count_in_context']} reviews used)"
                )

        st.markdown("### Recommendation")
        st.markdown(result["answer"])
        _render_sources(result["sources"], show_professor=True)

with ask_tab:
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
        ask_examples = [
            "Is this professor good for beginners?",
            "How is the grading style?",
            "What do students say about exams?",
        ]
        ask_cols = st.columns(len(ask_examples))
        for i, (col, example) in enumerate(zip(ask_cols, ask_examples)):
            if col.button(example, use_container_width=True, key=f"ask_example_{i}"):
                st.session_state.ask_query = example
                st.rerun()

        with st.form("ask_form", clear_on_submit=False):
            ask_query = st.text_input(
                "Your question:",
                key="ask_query",
                placeholder="e.g. Is this professor good for beginners?",
            )
            ask_submitted = st.form_submit_button("Ask", type="primary")

        if ask_submitted and ask_query.strip():
            with st.spinner("Searching through student reviews..."):
                result = ask(ask_query.strip(), professor_id)

            st.markdown("### Answer")
            st.markdown(result["answer"])
            _render_sources(result["sources"], show_professor=False)
