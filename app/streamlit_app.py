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
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800;900&display=swap');

        :root {
            --black: #000000;
            --white: #FFFFFF;
            --gray-bg: #F6F6F6;
            --gray-line: #E0E0E0;
            --gray-text: #6B6B6B;
            --rmp-green: #7FF6C3;
            --rmp-yellow: #FFF170;
            --rmp-red: #FF9C9C;
            --rmp-blue: #0021FF;
        }

        .stApp {
            background: var(--white);
            color: var(--black);
            font-family: "Poppins", "Helvetica Neue", Arial, sans-serif;
        }

        .block-container {
            padding-top: 1rem;
            padding-bottom: 2.5rem;
            max-width: 1160px;
        }

        h1, h2, h3, h4, .osp-brand {
            font-family: "Poppins", sans-serif !important;
            font-weight: 800 !important;
            letter-spacing: -0.01em;
            color: var(--black) !important;
        }

        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li {
            font-size: 1rem;
            line-height: 1.55;
        }

        /* ── Black hero band, RMP-style ─────────────────────── */
        .osp-hero {
            margin: 0.1rem 0 1.2rem 0;
            padding: 1.8rem 1.9rem 1.7rem;
            border-radius: 12px;
            background: var(--black);
            color: var(--white);
            animation: ospFade 0.5s ease-out;
        }

        .osp-kicker {
            display: inline-block;
            margin-bottom: 0.55rem;
            font-size: 0.74rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: var(--rmp-green);
        }

        .osp-brand {
            font-size: 2.5rem;
            font-weight: 900 !important;
            margin: 0 0 0.4rem 0;
            line-height: 1.05;
            color: var(--white) !important;
        }

        .osp-tagline {
            margin: 0 0 1.2rem 0;
            color: rgba(255, 255, 255, 0.75);
            font-size: 1.05rem;
            max-width: 42rem;
        }

        .osp-stat-row {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.7rem;
        }

        .osp-stat {
            padding: 0.8rem 1rem;
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.14);
        }

        .osp-stat-value {
            font-size: 1.6rem;
            font-weight: 800;
            line-height: 1.1;
            color: var(--white);
        }

        .osp-stat-label {
            margin-top: 0.15rem;
            font-size: 0.8rem;
            color: rgba(255, 255, 255, 0.65);
            font-weight: 500;
        }

        /* ── RMP rating boxes ───────────────────────────────── */
        .osp-rating-row {
            display: flex;
            gap: 0.7rem;
            margin: 0.6rem 0 0.9rem;
            flex-wrap: wrap;
        }

        .osp-rating-box {
            min-width: 5.2rem;
            text-align: center;
            padding: 0.75rem 0.6rem 0.65rem;
            border-radius: 10px;
        }

        .osp-rating-num {
            font-size: 1.9rem;
            font-weight: 900;
            line-height: 1;
            color: var(--black);
        }

        .osp-rating-cap {
            margin-top: 0.3rem;
            font-size: 0.74rem;
            font-weight: 600;
            color: var(--black);
            opacity: 0.75;
        }

        .osp-box-green { background: var(--rmp-green); }
        .osp-box-yellow { background: var(--rmp-yellow); }
        .osp-box-red { background: var(--rmp-red); }
        .osp-box-gray { background: var(--gray-bg); border: 1px solid var(--gray-line); }

        /* ── Panels & cards: white, thin gray borders ───────── */
        .osp-panel {
            margin: 1rem 0;
            padding: 1.15rem 1.25rem 1.25rem;
            border: 1px solid var(--gray-line);
            border-radius: 12px;
            background: var(--white);
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
            animation: ospRise 0.4s ease-out;
        }

        .osp-panel h3 {
            margin-top: 0;
            margin-bottom: 0.65rem;
            font-size: 1.25rem;
        }

        .osp-guide-head {
            margin: 1.4rem 0 0.75rem;
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: 0.11em;
            text-transform: uppercase;
            color: var(--gray-text);
        }

        .osp-guide-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.9rem;
            margin: 0 0 0.4rem;
            animation: ospRise 0.45s ease-out;
        }

        .osp-guide {
            position: relative;
            padding: 1.2rem 1.15rem 1.25rem;
            border-radius: 14px;
            border: 1px solid var(--gray-line);
            background: var(--white);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
            transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
            overflow: hidden;
        }

        .osp-guide::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: var(--rmp-green);
        }

        .osp-guide:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 22px rgba(0, 0, 0, 0.09);
            border-color: var(--black);
        }

        .osp-guide-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 2.1rem;
            height: 2.1rem;
            border-radius: 50%;
            background: var(--black);
            color: var(--white);
            font-weight: 800;
            font-size: 0.95rem;
            margin-bottom: 0.7rem;
        }

        .osp-guide-title {
            font-family: "Poppins", sans-serif;
            font-weight: 800;
            font-size: 1.05rem;
            color: var(--black);
            margin: 0 0 0.4rem 0;
        }

        .osp-guide p {
            margin: 0;
            color: var(--gray-text);
            font-size: 0.9rem;
            line-height: 1.5;
        }

        .osp-topic-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.7rem;
            margin: 0.85rem 0 0.2rem;
        }

        .osp-topic {
            padding: 0.9rem 1rem;
            border-radius: 12px;
            border: 1px solid var(--gray-line);
            background: var(--gray-bg);
        }

        .osp-topic strong {
            display: block;
            margin-bottom: 0.25rem;
            color: var(--black);
            font-size: 0.95rem;
        }

        .osp-topic span {
            color: var(--gray-text);
            font-size: 0.86rem;
            line-height: 1.4;
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
            padding: 0.3rem 0.75rem;
            border-radius: 999px;
            background: var(--black);
            color: var(--white);
            font-size: 0.8rem;
            font-weight: 600;
        }

        .osp-meta {
            color: var(--gray-text);
            font-size: 0.92rem;
            margin: 0.15rem 0 0.75rem;
        }

        .osp-sidebar-card {
            padding: 1rem 1.05rem 1.1rem;
            border-radius: 12px;
            border: 1px solid var(--gray-line);
            background: var(--gray-bg);
        }

        .osp-footer {
            margin-top: 1.8rem;
            padding-top: 1rem;
            border-top: 1px solid var(--gray-line);
            color: var(--gray-text);
            font-size: 0.85rem;
        }

        /* ── Tabs: underline style, black active ────────────── */
        div[data-testid="stTabs"] [data-baseweb="tab-list"] {
            gap: 1.4rem;
            background: transparent;
            border-bottom: 2px solid var(--gray-line);
            padding-bottom: 0;
        }

        div[data-testid="stTabs"] button[data-baseweb="tab"] {
            border-radius: 0 !important;
            padding: 0.55rem 0.15rem !important;
            font-weight: 700 !important;
            font-size: 0.95rem !important;
            color: var(--gray-text) !important;
            background: transparent !important;
            border-bottom: 3px solid transparent !important;
            margin-bottom: -2px;
        }

        div[data-testid="stTabs"] button[aria-selected="true"] {
            color: var(--black) !important;
            background: transparent !important;
            border-bottom: 3px solid var(--black) !important;
        }

        /* ── Forms & buttons: black pills, RMP-style ────────── */
        div[data-testid="stForm"] {
            border: 1px solid var(--gray-line);
            border-radius: 12px;
            padding: 1rem 1.1rem 0.85rem;
            background: var(--white);
        }

        div[data-testid="stForm"] input {
            border-radius: 999px !important;
        }

        .stButton > button {
            border-radius: 999px !important;
            border: 1.5px solid var(--black) !important;
            background: var(--white) !important;
            color: var(--black) !important;
            font-weight: 600 !important;
            transition: background 0.15s ease, color 0.15s ease, transform 0.15s ease;
        }

        .stButton > button:hover {
            background: var(--black) !important;
            color: var(--white) !important;
            transform: translateY(-1px);
        }

        div[data-testid="stForm"] .stButton > button[kind="primary"],
        .stButton > button[kind="primary"] {
            background: var(--black) !important;
            color: var(--white) !important;
            border: 1.5px solid var(--black) !important;
        }

        .stButton > button[kind="primary"]:hover {
            background: #2b2b2b !important;
            color: var(--white) !important;
        }

        [data-testid="stMetric"] {
            background: var(--gray-bg);
            border: 1px solid var(--gray-line);
            border-radius: 10px;
            padding: 0.65rem 0.8rem;
        }

        [data-testid="stExpander"] {
            border: 1px solid var(--gray-line);
            border-radius: 12px;
            background: var(--white);
        }

        @keyframes ospFade {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes ospRise {
            from { opacity: 0; transform: translateY(12px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @media (max-width: 860px) {
            .osp-brand { font-size: 1.9rem; }
            .osp-stat-row,
            .osp-guide-grid,
            .osp-topic-grid {
                grid-template-columns: 1fr;
            }
            .block-container { padding-top: 0.9rem; }
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
def get_corpus_stats() -> dict[str, int]:
    collection = get_collection()
    data = collection.get(include=["metadatas"])
    metadatas = data.get("metadatas") or []
    professors = set()
    courses = set()
    review_keys = set()
    for meta in metadatas:
        pid = meta.get("professor_id")
        if pid:
            professors.add(pid)
        course = (meta.get("course") or "").strip()
        if course:
            courses.add(course.upper())
        review_keys.add((pid, meta.get("review_index")))
    return {
        "professors": len(professors),
        "reviews": len(review_keys) or len(metadatas),
        "courses": len(courses),
        "chunks": len(metadatas),
    }


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


def _html(markup: str) -> None:
    """Render HTML collapsed to one line so Streamlit's markdown parser
    doesn't split indented multi-line HTML into broken fragments."""
    flat = " ".join(line.strip() for line in markup.strip().splitlines() if line.strip())
    st.markdown(flat, unsafe_allow_html=True)


def _format_metric(value: float | None, suffix: str = "") -> str:
    if value is None:
        return "N/A"
    return f"{value:.1f}{suffix}"


def _rating_box_class(value: float | None) -> str:
    """RMP-style color scale: green = good, yellow = okay, red = awful."""
    if value is None:
        return "osp-box-gray"
    if value >= 3.5:
        return "osp-box-green"
    if value >= 2.5:
        return "osp-box-yellow"
    return "osp-box-red"


def _render_rating_boxes(stats: dict) -> None:
    rating = stats.get("avg_rating")
    difficulty = stats.get("avg_difficulty")
    rating_num = f"{rating:.1f}" if rating is not None else "N/A"
    difficulty_num = f"{difficulty:.1f}" if difficulty is not None else "N/A"
    _html(
        f"""
        <div class="osp-rating-row">
            <div class="osp-rating-box {_rating_box_class(rating)}">
                <div class="osp-rating-num">{rating_num}</div>
                <div class="osp-rating-cap">QUALITY</div>
            </div>
            <div class="osp-rating-box osp-box-gray">
                <div class="osp-rating-num">{difficulty_num}</div>
                <div class="osp-rating-cap">DIFFICULTY</div>
            </div>
            <div class="osp-rating-box osp-box-gray">
                <div class="osp-rating-num">{stats.get('total_reviews', 0)}</div>
                <div class="osp-rating-cap">RATINGS</div>
            </div>
        </div>
        """
    )


def _format_count(n: int) -> str:
    if n >= 1000:
        return f"{n / 1000:.1f}k".replace(".0k", "k")
    return str(n)


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
    st.markdown(
        f'<div class="osp-panel"><h3>{title}</h3></div>',
        unsafe_allow_html=True,
    )
    with st.container():
        st.markdown(body)


def _guide_section(items: list[tuple[str, str]]) -> None:
    cards = []
    for i, (title, body) in enumerate(items, 1):
        cards.append(
            f"""
            <div class="osp-guide">
                <div class="osp-guide-badge">{i}</div>
                <div class="osp-guide-title">{title}</div>
                <p>{body}</p>
            </div>
            """
        )
    _html('<div class="osp-guide-head">How it works</div>')
    _html(f'<div class="osp-guide-grid">{"".join(cards)}</div>')


inject_styles()

professors = get_professors()
if not professors:
    st.error("No professors found. Run the scraper and pipeline first.")
    st.stop()

corpus = get_corpus_stats()

_html(
    f"""
    <div class="osp-hero">
        <div class="osp-kicker">UMass Amherst</div>
        <div class="osp-brand">OneStopProf</div>
        <p class="osp-tagline">
            Find the right professor for your course — recommendations, comparisons,
            and answers grounded in real student reviews.
        </p>
        <div class="osp-stat-row">
            <div class="osp-stat">
                <div class="osp-stat-value">{_format_count(corpus['professors'])}</div>
                <div class="osp-stat-label">Professors</div>
            </div>
            <div class="osp-stat">
                <div class="osp-stat-value">{_format_count(corpus['reviews'])}</div>
                <div class="osp-stat-label">Student Reviews</div>
            </div>
            <div class="osp-stat">
                <div class="osp-stat-value">{_format_count(corpus['courses'])}</div>
                <div class="osp-stat-label">courses covered</div>
            </div>
        </div>
    </div>
    """
)

if "rec_query" not in st.session_state:
    st.session_state.rec_query = ""
if "ask_query" not in st.session_state:
    st.session_state.ask_query = ""
if "cmp_query" not in st.session_state:
    st.session_state.cmp_query = ""
if "rec_result" not in st.session_state:
    st.session_state.rec_result = None
if "cmp_result" not in st.session_state:
    st.session_state.cmp_result = None
if "ask_result" not in st.session_state:
    st.session_state.ask_result = None
if "ask_result_for" not in st.session_state:
    st.session_state.ask_result_for = None

rec_tab, cmp_tab, ask_tab = st.tabs(
    ["Recommend", "Compare courses", "Ask a professor"]
)

with rec_tab:
    st.markdown("#### Who should you take?")
    st.markdown(
        '<p class="osp-meta">Ask about a course, difficulty, grading, or teaching style. '
        "Mention a course code like <strong>CS220</strong> for sharper results.</p>",
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
            st.session_state.rec_result = recommend(rec_query.strip())

    result = st.session_state.rec_result
    if result:
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
    else:
        _guide_section(
            [
                (
                    "Name the course",
                    "Include codes like CS220 or CHEM111 to filter reviews matching the course.",
                ),
                (
                    "Add your constraints",
                    "Beginner-friendly, fair grading, lighter workload, strong lectures — be specific.",
                ),
                (
                    "Get ranked picks",
                    "OneStopProf compares review evidence and recommends professors with citations.",
                ),
            ]
        )

with cmp_tab:
    st.markdown("#### Compare courses side by side")
    st.markdown(
        '<p class="osp-meta">Include at least two course codes. You’ll get pros, cons, '
        "and professor recommendations for each.</p>",
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
            st.session_state.cmp_result = compare_courses(cmp_query.strip())

    result = st.session_state.cmp_result
    if result:
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
                    _html(
                        f"""
                        <div class="osp-sidebar-card">
                            <div class="osp-kicker">{course}</div>
                            <div style="font-size:1.4rem;font-weight:800;">{info.get('review_count', 0)}</div>
                            <div class="osp-meta" style="margin:0;">reviews · {top_names}</div>
                        </div>
                        """
                    )

        _answer_panel("Comparison", result["answer"])
        _render_sources(result["sources"], show_professor=True)
    else:
        _guide_section(
            [
                (
                    "Pick two courses",
                    "Try pairs you’d actually choose between — same dept or different requirements.",
                ),
                (
                    "Say what matters",
                    "Exams, curve, workload, or “I’m a first-year” change how the comparison is framed.",
                ),
                (
                    "Read pros & cons",
                    "Each course gets tradeoffs plus professor picks grounded in matching reviews.",
                ),
            ]
        )

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

        _render_rating_boxes(stats)

        _html(
            """
            <div class="osp-sidebar-card" style="margin-top:0.85rem;">
                <div class="osp-kicker">Tip</div>
                <p class="osp-meta" style="margin:0;">
                    Mention the course in your question (e.g. CS383 exams) so answers
                    weight reviews from that class more heavily.
                </p>
            </div>
            """
        )

    with col2:
        st.markdown(f"#### Ask about {selected_name}")
        st.markdown(
            '<p class="osp-meta">Grading, exams, teaching style, workload — '
            "answers stay grounded in that professor’s reviews.</p>",
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
                placeholder="e.g. How are the exams for CS383 under this professor?",
                label_visibility="collapsed",
            )
            ask_submitted = st.form_submit_button("Ask", type="primary")

        if ask_submitted and ask_query.strip():
            with st.spinner("Searching through student reviews..."):
                st.session_state.ask_result = ask(ask_query.strip(), professor_id)
                st.session_state.ask_result_for = selected_name

        result = st.session_state.ask_result
        if result and st.session_state.ask_result_for == selected_name:
            _answer_panel("Answer", result["answer"])
            _render_sources(result["sources"], show_professor=False)
        else:
            st.markdown("**Good questions to try**")
            _html(
                """
                <div class="osp-topic-grid">
                    <div class="osp-topic">
                        <strong>Exams & quizzes</strong>
                        <span>Are tests curved? Multiple choice or proofs? Surprise quizzes?</span>
                    </div>
                    <div class="osp-topic">
                        <strong>Grading & workload</strong>
                        <span>Harsh on homework? Generous with partial credit? Heavy projects?</span>
                    </div>
                    <div class="osp-topic">
                        <strong>Teaching style</strong>
                        <span>Clear lectures, fast pace, lots of slides, or discussion-heavy?</span>
                    </div>
                    <div class="osp-topic">
                        <strong>Fit for you</strong>
                        <span>Beginner-friendly? Good for non-majors? Worth taking again?</span>
                    </div>
                </div>
                """
            )

_html(
    """
    <div class="osp-footer">
        Built for UMass Amherst course planning · Answers cite Rate My Professor reviews ·
        Not affiliated with RMP or the university
    </div>
    """
)
