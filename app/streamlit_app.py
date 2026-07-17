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

import streamlit as st  # noqa: E402
from pipeline.loader import get_collection  # noqa: E402

try:
    from rag.chain import ask, compare_courses, recommend  # noqa: E402
except ImportError as exc:
    raise ImportError(
        "Failed to import ask/recommend/compare_courses from rag.chain. "
        "Push the latest commit and reboot the Streamlit app. "
        f"Original error: {exc}"
    ) from exc

st.set_page_config(
    page_title="OneStopProf",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Outfit:wght@400;500;600;700&display=swap');

        :root {
            --ink: #0F2C3C;
            --mist: #E8EEF2;
            --paper: #F7F5F1;
            --teal: #1A7A6D;
            --teal-deep: #145E54;
            --line: rgba(15, 44, 60, 0.12);
            --muted: rgba(15, 44, 60, 0.62);
        }

        .stApp {
            background:
                radial-gradient(1200px 500px at 10% -10%, rgba(26, 122, 109, 0.14), transparent 55%),
                radial-gradient(900px 420px at 90% 0%, rgba(15, 44, 60, 0.10), transparent 50%),
                linear-gradient(180deg, #E8EEF2 0%, #F3F1EC 100%);
            color: var(--ink);
            font-family: "Outfit", sans-serif;
        }

        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 3rem;
            max-width: 1120px;
        }

        h1, h2, h3, .osp-brand {
            font-family: "Fraunces", serif !important;
            letter-spacing: -0.02em;
            color: var(--ink) !important;
        }

        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li {
            font-size: 1.02rem;
            line-height: 1.55;
        }

        .osp-hero {
            margin: 0.2rem 0 1.4rem 0;
            padding: 1.35rem 1.5rem 1.45rem;
            border: 1px solid var(--line);
            border-radius: 18px;
            background:
                linear-gradient(135deg, rgba(247, 245, 241, 0.92), rgba(232, 238, 242, 0.75));
            box-shadow: 0 18px 40px rgba(15, 44, 60, 0.06);
            animation: ospFade 0.55s ease-out;
        }

        .osp-brand {
            font-size: 2.35rem;
            font-weight: 700;
            margin: 0 0 0.35rem 0;
            line-height: 1.1;
        }

        .osp-tagline {
            margin: 0;
            color: var(--muted);
            font-size: 1.05rem;
            max-width: 42rem;
        }

        .osp-kicker {
            display: inline-block;
            margin-bottom: 0.55rem;
            font-size: 0.78rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--teal-deep);
        }

        .osp-panel {
            margin: 1rem 0;
            padding: 1.15rem 1.25rem;
            border: 1px solid var(--line);
            border-radius: 16px;
            background: var(--paper);
            box-shadow: 0 10px 28px rgba(15, 44, 60, 0.05);
            animation: ospRise 0.45s ease-out;
        }

        .osp-panel h3 {
            margin-top: 0;
            margin-bottom: 0.75rem;
            font-size: 1.35rem;
        }

        .osp-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin: 0.35rem 0 0.85rem;
        }

        .osp-chip {
            display: inline-flex;
            align-items: center;
            padding: 0.28rem 0.7rem;
            border-radius: 999px;
            border: 1px solid var(--line);
            background: rgba(255, 255, 255, 0.55);
            color: var(--ink);
            font-size: 0.82rem;
            font-weight: 500;
        }

        .osp-meta {
            color: var(--muted);
            font-size: 0.92rem;
            margin: 0.2rem 0 0.8rem;
        }

        .osp-sidebar-card {
            padding: 1rem 1.05rem 1.1rem;
            border-radius: 16px;
            border: 1px solid var(--line);
            background: rgba(247, 245, 241, 0.9);
        }

        div[data-testid="stTabs"] [data-baseweb="tab-list"] {
            gap: 0.35rem;
            background: transparent;
            border-bottom: 1px solid var(--line);
            padding-bottom: 0.35rem;
        }

        div[data-testid="stTabs"] button[data-baseweb="tab"] {
            border-radius: 999px !important;
            padding: 0.45rem 0.95rem !important;
            font-weight: 600 !important;
            color: var(--muted) !important;
            background: transparent !important;
        }

        div[data-testid="stTabs"] button[aria-selected="true"] {
            color: white !important;
            background: var(--ink) !important;
        }

        div[data-testid="stForm"] {
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 1rem 1.1rem 0.85rem;
            background: rgba(247, 245, 241, 0.72);
        }

        .stButton > button {
            border-radius: 12px !important;
            border: 1px solid var(--line) !important;
            background: rgba(255, 255, 255, 0.72) !important;
            color: var(--ink) !important;
            font-weight: 550 !important;
            transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
        }

        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 8px 18px rgba(15, 44, 60, 0.08);
            background: white !important;
            border-color: rgba(26, 122, 109, 0.35) !important;
        }

        div[data-testid="stForm"] .stButton > button[kind="primary"],
        .stButton > button[kind="primary"] {
            background: var(--teal) !important;
            color: white !important;
            border: none !important;
        }

        .stButton > button[kind="primary"]:hover {
            background: var(--teal-deep) !important;
            color: white !important;
        }

        [data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.55);
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: 0.65rem 0.8rem;
        }

        [data-testid="stExpander"] {
            border: 1px solid var(--line);
            border-radius: 14px;
            background: rgba(255, 255, 255, 0.45);
        }

        @keyframes ospFade {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes ospRise {
            from { opacity: 0; transform: translateY(12px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @media (max-width: 768px) {
            .osp-brand { font-size: 1.85rem; }
            .block-container { padding-top: 1rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


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

    review_indices = {
        m.get("review_index") for m in metadatas if m.get("review_index") != ""
    }
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
        "avg_difficulty": (
            sum(difficulties) / len(difficulties) if difficulties else None
        ),
        "university": metadatas[0].get("university", ""),
        "department": metadatas[0].get("department", ""),
    }


def _format_metric(value: float | None, suffix: str = "") -> str:
    if value is None:
        return "N/A"
    return f"{value:.1f}{suffix}"


def _render_sources(sources: list[dict], *, show_professor: bool = False) -> None:
    with st.expander("View source reviews"):
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
                f"Rating: {source.get('rating', 'N/A')} · "
                f"Date: {source.get('date', 'N/A')}"
            )
            if i < len(sources):
                st.divider()


def _example_buttons(examples: list[str], key_prefix: str, state_key: str) -> None:
    cols = st.columns(len(examples))
    for i, (col, example) in enumerate(zip(cols, examples)):
        if col.button(example, use_container_width=True, key=f"{key_prefix}_{i}"):
            st.session_state[state_key] = example
            st.rerun()


def _answer_panel(title: str, body: str) -> None:
    st.markdown(f'<div class="osp-panel"><h3>{title}</h3></div>', unsafe_allow_html=True)
    with st.container():
        st.markdown(body)


inject_styles()

st.markdown(
    """
    <div class="osp-hero">
        <div class="osp-kicker">UMass Amherst · student reviews</div>
        <div class="osp-brand">OneStopProf</div>
        <p class="osp-tagline">
            Find the right professor for your course — recommendations, comparisons,
            and answers grounded in real Rate My Professor reviews.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

professors = get_professors()
if not professors:
    st.error("No professors found. Run the scraper and pipeline first.")
    st.stop()

if "rec_query" not in st.session_state:
    st.session_state.rec_query = ""
if "ask_query" not in st.session_state:
    st.session_state.ask_query = ""
if "cmp_query" not in st.session_state:
    st.session_state.cmp_query = ""

rec_tab, cmp_tab, ask_tab = st.tabs(
    ["Recommend", "Compare courses", "Ask a professor"]
)

with rec_tab:
    st.markdown("#### Who should you take?")
    st.markdown(
        '<p class="osp-meta">Ask about a course, difficulty, grading, or teaching style.</p>',
        unsafe_allow_html=True,
    )

    _example_buttons(
        [
            "Who should I take for CS220 as a beginner?",
            "Easiest professor for CHEM111?",
            "Best for MATH235 if I care about exams?",
        ],
        "rec_example",
        "rec_query",
    )

    with st.form("recommend_form", clear_on_submit=False):
        rec_query = st.text_input(
            "Your question",
            key="rec_query",
            placeholder="e.g. Who should I take for CS220 as a beginner?",
            label_visibility="collapsed",
        )
        rec_submitted = st.form_submit_button("Get recommendations", type="primary")

    if rec_submitted and rec_query.strip():
        with st.spinner("Searching reviews across professors..."):
            result = recommend(rec_query.strip())

        chips = []
        if result.get("course"):
            chips.append(f'<span class="osp-chip">Course · {result["course"]}</span>')
        if result.get("professors"):
            chips.append(
                f'<span class="osp-chip">{len(result["professors"])} professors in evidence</span>'
            )
        if chips:
            st.markdown(
                f'<div class="osp-chip-row">{"".join(chips)}</div>',
                unsafe_allow_html=True,
            )

        if result.get("professors"):
            with st.container():
                st.markdown("**Professors in the evidence set**")
                for prof in result["professors"][:6]:
                    rating = (
                        f"{prof['avg_rating_in_context']:.1f}/5"
                        if prof.get("avg_rating_in_context") is not None
                        else "N/A"
                    )
                    st.markdown(
                        f"- **{prof['name']}** — {rating} "
                        f"({prof['review_count_in_context']} reviews used)"
                    )

        _answer_panel("Recommendation", result["answer"])
        _render_sources(result["sources"], show_professor=True)

with cmp_tab:
    st.markdown("#### Compare courses side by side")
    st.markdown(
        '<p class="osp-meta">Include at least two course codes for pros, cons, '
        "and professor picks for each.</p>",
        unsafe_allow_html=True,
    )

    _example_buttons(
        [
            "Compare CS220 vs MATH235 for a beginner",
            "CS250 vs CS220 — which is harder?",
            "CHEM111 vs BIO152 if I care about exams",
        ],
        "cmp_example",
        "cmp_query",
    )

    with st.form("compare_form", clear_on_submit=False):
        cmp_query = st.text_input(
            "Your comparison",
            key="cmp_query",
            placeholder="e.g. Compare CS220 vs CS250 for a beginner",
            label_visibility="collapsed",
        )
        cmp_submitted = st.form_submit_button("Compare courses", type="primary")

    if cmp_submitted and cmp_query.strip():
        with st.spinner("Gathering reviews for each course..."):
            result = compare_courses(cmp_query.strip())

        if result.get("courses"):
            chip_html = "".join(
                f'<span class="osp-chip">{course}</span>' for course in result["courses"]
            )
            st.markdown(
                f'<div class="osp-chip-row">{chip_html}</div>',
                unsafe_allow_html=True,
            )

        by_course = result.get("by_course") or {}
        if by_course:
            st.markdown("**Evidence snapshot**")
            cols = st.columns(min(len(by_course), 3))
            for col, (course, info) in zip(cols, by_course.items()):
                with col:
                    profs = info.get("professors") or []
                    top_names = ", ".join(p["name"] for p in profs[:2]) or "—"
                    st.markdown(
                        f"""
                        <div class="osp-sidebar-card">
                            <div class="osp-kicker">{course}</div>
                            <div style="font-size:1.4rem;font-weight:700;">{info.get('review_count', 0)}</div>
                            <div class="osp-meta" style="margin:0;">reviews · {top_names}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        _answer_panel("Comparison", result["answer"])
        _render_sources(result["sources"], show_professor=True)

with ask_tab:
    col1, col2 = st.columns([1.05, 2.2], gap="large")

    with col1:
        st.markdown("#### Select professor")
        selected_name = st.selectbox(
            "Professor",
            sorted(professors.values()),
            label_visibility="collapsed",
        )
        professor_id = next(k for k, v in professors.items() if v == selected_name)
        stats = get_professor_stats(professor_id)

        if stats["university"] or stats["department"]:
            meta_bits = " · ".join(
                part
                for part in [stats.get("university"), stats.get("department")]
                if part
            )
            st.caption(meta_bits)

        m1, m2 = st.columns(2)
        m1.metric("Rating", _format_metric(stats["avg_rating"], "/5"))
        m2.metric("Difficulty", _format_metric(stats["avg_difficulty"], "/5"))
        st.metric("Reviews", stats["total_reviews"])

    with col2:
        st.markdown(f"#### Ask about {selected_name}")
        st.markdown(
            '<p class="osp-meta">Grading, exams, teaching style, workload — '
            "answers stay grounded in that professor's reviews.</p>",
            unsafe_allow_html=True,
        )

        _example_buttons(
            [
                "Is this professor good for beginners?",
                "How is the grading style?",
                "What do students say about exams?",
            ],
            "ask_example",
            "ask_query",
        )

        with st.form("ask_form", clear_on_submit=False):
            ask_query = st.text_input(
                "Your question",
                key="ask_query",
                placeholder="e.g. Is this professor good for beginners?",
                label_visibility="collapsed",
            )
            ask_submitted = st.form_submit_button("Ask", type="primary")

        if ask_submitted and ask_query.strip():
            with st.spinner("Searching through student reviews..."):
                result = ask(ask_query.strip(), professor_id)

            _answer_panel("Answer", result["answer"])
            _render_sources(result["sources"], show_professor=False)
