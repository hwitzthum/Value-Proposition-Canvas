"""
Value Proposition Canvas — Streamlit UI.
Spatial canvas (default) with optional guided mode.
"""

import os
import html
import hashlib
import logging
from pathlib import Path
from typing import Optional

import httpx
import streamlit as st

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── Auth & Canvas API imports ──
from auth_ui import (  # noqa: E402
    check_auth, render_login_page, render_pending_page, render_blocked_page,
    logout, change_password_request, _render_password_strength,
)
from canvas_api import CanvasAPIClient  # noqa: E402
from admin_api import AdminAPIClient  # noqa: E402
from admin_ui import render_admin_dashboard, render_admin_user_management  # noqa: E402

# ── Page Configuration ──
st.set_page_config(
    page_title="Value Proposition Canvas",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load external CSS ──
_css_parts = []
_CSS_PATH = Path(__file__).parent / "assets" / "style.css"
if _CSS_PATH.exists():
    _css_parts.append(_CSS_PATH.read_text())
_ADMIN_CSS_PATH = Path(__file__).parent / "assets" / "admin.css"
if _ADMIN_CSS_PATH.exists():
    _css_parts.append(_ADMIN_CSS_PATH.read_text())
if _css_parts:
    st.markdown(f"<style>{''.join(_css_parts)}</style>", unsafe_allow_html=True)

# ── API Configuration ──
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "")

# ── Theme Configuration (Light + Dark only) ──
DEFAULT_THEME = "Light"
THEME_CONFIGS = {
    "Light": {},  # Uses CSS :root defaults
    "Dark": {"attr": "dark"},
}


# ═══════════════════════════════════════════════════════════════════════════
# Session State
# ═══════════════════════════════════════════════════════════════════════════

INITIAL_STATE = {
    "step": 0,
    "job_description": "",
    "pain_points": [],
    "gain_points": [],
    "job_validated": False,
    "pains_validated": False,
    "gains_validated": False,
    "editing_pain_index": None,
    "editing_gain_index": None,
    "session_loaded": False,
    "canvas_mode": "spatial",  # "spatial" or "guided"
}


def init_session_state():
    for key, default in INITIAL_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = list(default) if isinstance(default, list) else default
    if "theme_mode" not in st.session_state:
        st.session_state.theme_mode = DEFAULT_THEME
    if "pref_high_contrast" not in st.session_state:
        st.session_state.pref_high_contrast = False
    if "pref_large_text" not in st.session_state:
        st.session_state.pref_large_text = False


def reset_session_state(preserve_theme: bool = False):
    for key, default in INITIAL_STATE.items():
        st.session_state[key] = list(default) if isinstance(default, list) else default
    if not preserve_theme:
        st.session_state.theme_mode = DEFAULT_THEME


# ═══════════════════════════════════════════════════════════════════════════
# Theme
# ═══════════════════════════════════════════════════════════════════════════

def apply_theme():
    """Apply dark theme and accessibility overrides via CSS injection.
    Must be called early in the render cycle, before any content."""
    parts = []

    if st.session_state.get("theme_mode") == "Dark":
        parts.append("""
        :root {
            --color-primary: #60a5fa !important;
            --color-primary-hover: #93bbfd !important;
            --color-primary-light: #1e3a5f !important;
            --color-bg-page: #0f1117 !important;
            --color-bg-card: #1a1d27 !important;
            --color-text-primary: #f1f5f9 !important;
            --color-text-secondary: #94a3b8 !important;
            --color-text-muted: #64748b !important;
            --color-border: #334155 !important;
            --color-border-light: #1e293b !important;
            --color-success: #34d399 !important;
            --color-success-light: #132f21 !important;
            --color-warning: #fbbf24 !important;
            --color-warning-light: #3b2f10 !important;
            --color-error: #f87171 !important;
            --color-error-light: #3b1515 !important;
            --color-pain: #fb7185 !important;
            --color-pain-light: #3b1525 !important;
            --color-gain: #2dd4bf !important;
            --color-gain-light: #0f3b35 !important;
        }
        .stApp.stApp { background: #0f1117 !important; color: #f1f5f9 !important; color-scheme: dark !important; }
        [data-testid="stAppViewContainer"],
        .main, .main .block-container { background: #0f1117 !important; color: #f1f5f9 !important; }
        section[data-testid="stSidebar"],
        section[data-testid="stSidebar"] > div { background: #1a1d27 !important; border-right-color: #334155 !important; }
        .stTextArea > div > div > textarea,
        .stTextInput > div > div > input { background: #1a1d27 !important; color: #f1f5f9 !important; border-color: #334155 !important; }
        .stSelectbox > div > div,
        .stSelectbox [data-baseweb="select"],
        [data-baseweb="popover"] > div { background: #1a1d27 !important; color: #f1f5f9 !important; }
        h1, h2, h3, h4, p, span, label, .stMarkdown, .stCaption, a { color: #f1f5f9 !important; }
        .stButton > button:not([kind="primary"]) { background: #1a1d27 !important; color: #f1f5f9 !important; border-color: #334155 !important; }
        .stButton > button[kind="primary"] { background: #60a5fa !important; border-color: #60a5fa !important; }
        hr { background: #334155 !important; }
        .stTabs [data-baseweb="tab-list"] { border-bottom-color: #334155 !important; }
        .stTabs [data-baseweb="tab"] { color: #94a3b8 !important; }
        .stRadio label, .stCheckbox label { color: #f1f5f9 !important; }
        [data-testid="stForm"] { border-color: #334155 !important; }
        .stDownloadButton > button { background: #60a5fa !important; border-color: #60a5fa !important; }
        """)

    if st.session_state.get("pref_large_text"):
        parts.append(":root { --font-scale: 1.1; }")

    if st.session_state.get("pref_high_contrast"):
        parts.append("""
        :root { --color-border: #374151; --color-text-muted: #374151; }
        .stButton > button, .stTextInput > div > div > input, .stTextArea > div > div > textarea { border-width: 2px; }
        """)

    if parts:
        st.markdown(f"<style>{''.join(parts)}</style>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# API Helpers
# ═══════════════════════════════════════════════════════════════════════════

@st.cache_resource
def get_http_client() -> httpx.Client:
    return httpx.Client(timeout=30.0)


def get_api_headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if API_SECRET_KEY:
        headers["X-API-Key"] = API_SECRET_KEY
    auth_token = st.session_state.get("auth_token")
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    return headers


def call_api(endpoint: str, method: str = "GET", data: dict = None) -> dict:
    try:
        headers = get_api_headers()
        client = get_http_client()
        if method == "GET":
            response = client.get(f"{API_BASE_URL}{endpoint}", headers=headers)
        else:
            response = client.post(f"{API_BASE_URL}{endpoint}", json=data, headers=headers)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            # Session expired — clear auth and trigger rerun
            st.session_state.pop("auth_token", None)
            st.session_state.pop("auth_user", None)
            st.session_state["session_expired"] = True
            st.rerun()
        elif response.status_code == 429:
            return {"error": "Rate limit exceeded. Please wait before trying again."}
        else:
            return {"error": f"API error: {response.status_code}"}
    except Exception as e:
        return {"error": f"Connection error: {str(e)}"}


# ═══════════════════════════════════════════════════════════════════════════
# Cached Validation / Coaching
# ═══════════════════════════════════════════════════════════════════════════

def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


@st.cache_data(ttl=3600)
def _coaching_tip_cached(step: str) -> str:
    result = call_api(f"/api/coaching-tip/{step}")
    return result.get("tip", "")


@st.cache_data(ttl=300)
def _validate_job_cached(h: str, desc: str) -> dict:
    return call_api("/api/validate/job-description", "POST", {"description": desc})


@st.cache_data(ttl=300)
def _validate_pains_cached(h: str, points: tuple) -> dict:
    return call_api("/api/validate/pain-points", "POST", {"pain_points": list(points)})


@st.cache_data(ttl=300)
def _validate_gains_cached(h: str, points: tuple) -> dict:
    return call_api("/api/validate/gain-points", "POST", {"gain_points": list(points)})


# ═══════════════════════════════════════════════════════════════════════════
# UI Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _is_duplicate(candidate: str, items: list, exclude: Optional[int] = None) -> bool:
    n = _normalize(candidate)
    for i, item in enumerate(items):
        if exclude is not None and i == exclude:
            continue
        if _normalize(item) == n:
            return True
    return False


def _render_validation_msg(msg_type: str, message: str):
    icons = {"success": "✓", "warning": "!", "error": "✕"}
    safe = html.escape(message)
    role = "alert" if msg_type == "error" else "status"
    st.markdown(
        f'<div class="validation-msg {msg_type}" role="{role}">'
        f'<span class="validation-icon">{icons.get(msg_type, "")}</span> {safe}</div>',
        unsafe_allow_html=True,
    )


def _render_quality_badge(score: int):
    if score >= 75:
        level = "high"
    elif score >= 50:
        level = "medium"
    else:
        level = "low"
    st.markdown(
        f'<div class="quality-badge {level}" role="status">'
        f'Quality: {score}%</div>',
        unsafe_allow_html=True,
    )


def _render_coaching_tip(tip: str):
    if not tip:
        return
    safe = html.escape(tip).replace(chr(10), "<br>")
    st.markdown(
        f'<div class="coaching-tip">'
        f'<div class="coaching-tip-title">Coaching</div>'
        f'<p class="coaching-tip-text">{safe}</p></div>',
        unsafe_allow_html=True,
    )


def _render_empty_state(title: str, description: str):
    st.markdown(
        f'<div class="empty-state">'
        f'<div class="empty-state-title">{html.escape(title)}</div>'
        f'<div class="empty-state-desc">{html.escape(description)}</div></div>',
        unsafe_allow_html=True,
    )


def _build_item_html(index: int, text: str, item_type: str) -> str:
    safe = html.escape(text)
    prefix = "!" if item_type == "pain" else "+"
    return (
        f'<div class="item-card">'
        f'<div class="item-badge {item_type}">{prefix}{index + 1}</div>'
        f'<div class="item-text">{safe}</div></div>'
    )


# ═══════════════════════════════════════════════════════════════════════════
# Quality Thermometer (sidebar)
# ═══════════════════════════════════════════════════════════════════════════

def _quality_level_label(pain_count: int, gain_count: int, job_desc: str) -> tuple:
    """Returns (label, css_class) for the overall quality."""
    total = pain_count + gain_count
    has_job = bool(job_desc.strip())
    if total >= 15 and has_job:
        return ("Strong", "strong")
    elif total >= 6 and has_job:
        return ("Working", "working")
    else:
        return ("Draft", "draft")


def render_quality_thermometer():
    """Render the multi-dimensional quality indicator in the sidebar."""
    pains = st.session_state.get("pain_points", [])
    gains = st.session_state.get("gain_points", [])
    # Read from widget key (current value) or session state (saved value)
    job = (st.session_state.get("spatial_job_input")
           or st.session_state.get("guided_job_input")
           or st.session_state.get("job_description", ""))

    pain_count = len(pains)
    gain_count = len(gains)

    # Completeness: items vs ideal (7 pains + 8 gains = 15)
    completeness = min(100, int((pain_count + gain_count) / 15 * 100))
    # Balance: how close is the ratio to ideal 7:8
    if pain_count + gain_count > 0:
        ratio = min(pain_count, gain_count) / max(pain_count, gain_count, 1)
        balance = int(ratio * 100)
    else:
        balance = 0
    # Job presence
    job_score = 100 if job.strip() else 0

    label, label_class = _quality_level_label(pain_count, gain_count, job)

    def bar_class(v):
        if v >= 70:
            return "high"
        elif v >= 40:
            return "medium"
        return "low"

    st.markdown(f"""
    <div class="quality-thermo">
        <div class="quality-thermo-title">Canvas Quality</div>
        <div class="quality-dimension">
            <div class="quality-dimension-label"><span>Completeness</span><span>{completeness}%</span></div>
            <div class="quality-bar"><div class="quality-bar-fill {bar_class(completeness)}" style="width:{completeness}%"></div></div>
        </div>
        <div class="quality-dimension">
            <div class="quality-dimension-label"><span>Balance</span><span>{balance}%</span></div>
            <div class="quality-bar"><div class="quality-bar-fill {bar_class(balance)}" style="width:{balance}%"></div></div>
        </div>
        <div class="quality-dimension">
            <div class="quality-dimension-label"><span>Job Defined</span><span>{"Yes" if job_score else "No"}</span></div>
            <div class="quality-bar"><div class="quality-bar-fill {bar_class(job_score)}" style="width:{job_score}%"></div></div>
        </div>
        <div class="quality-label {label_class}">{label}</div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# Header
# ═══════════════════════════════════════════════════════════════════════════

def render_header():
    st.markdown("""
    <div class="app-header">
        <h1>Value Proposition Canvas</h1>
        <p>Map your job, pains, and gains into a clear strategy narrative.</p>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# Spatial Canvas Mode (default)
# ═══════════════════════════════════════════════════════════════════════════

def _add_item_from_brainstorm(collection_key: str, endpoint: str, payload_key: str,
                               item_label: str, raw_text: str) -> int:
    """Parse brainstorm text (newline-separated), deduplicate, validate batch.
    Returns count of items added."""
    lines = [line.strip() for line in raw_text.strip().split("\n") if line.strip()]
    if not lines:
        return 0

    existing = st.session_state.get(collection_key, [])
    added = 0
    for line in lines:
        if not _is_duplicate(line, existing):
            existing.append(line)
            added += 1

    if added > 0:
        st.session_state[collection_key] = existing
    return added


def _job_section():
    """Editable job statement section."""
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("### Job Statement")

    job = st.text_area(
        "What is the main task or goal you're trying to accomplish?",
        value=st.session_state.job_description,
        height=120,
        placeholder="Example: I need to track my team's monthly expenses and generate financial reports efficiently, so I can make informed budget decisions...",
        key="spatial_job_input",
        label_visibility="collapsed",
    )
    st.session_state.job_description = job

    if job.strip():
        result = _validate_job_cached(_content_hash(job), job)
        if result and "error" not in result:
            col1, col2 = st.columns([1, 3])
            with col1:
                _render_quality_badge(result.get("score", 0))
            with col2:
                if result.get("feedback"):
                    for fb in result["feedback"]:
                        _render_validation_msg("warning", fb)
            st.session_state.job_validated = result.get("valid", False)

            if result.get("suggestions"):
                with st.expander("Suggestions"):
                    for s in result["suggestions"]:
                        st.markdown(f"- {s}")
        elif result and "error" in result:
            st.caption("Validation service unavailable — your work is saved.")
            st.session_state.job_validated = True

    # AI suggestions
    if st.button("Get AI suggestions", key="spatial_job_suggest", type="secondary"):
        with st.spinner("Thinking..."):
            suggestions = call_api("/api/suggestions", "POST", {
                "step": "job",
                "job_description": job,
            })
            if "error" not in suggestions:
                st.info(suggestions.get("suggestions", "No suggestions available."))
            else:
                st.warning(suggestions["error"])

    st.markdown("</div>", unsafe_allow_html=True)


def _items_column(collection_key: str, item_type: str, item_label: str,
                  validate_endpoint: str, payload_key: str, validate_fn,
                  validated_key: str, editing_key: str, ideal_min: int):
    """Render a pain/gain column with brainstorm input and item list."""
    items = st.session_state.get(collection_key, [])
    icon = "!" if item_type == "pain" else "+"

    # Column header
    st.markdown(
        f'<div class="col-header {item_type}">'
        f'<div class="col-header-icon {item_type}">{icon}</div>'
        f'<span class="col-header-title">{item_label.title()}s</span>'
        f'<span class="col-header-count">{len(items)}</span></div>',
        unsafe_allow_html=True,
    )

    # Item list
    if items:
        for i, text in enumerate(items):
            if st.session_state.get(editing_key) == i:
                # Inline edit mode
                with st.form(f"edit_{item_type}_{i}", clear_on_submit=False):
                    edited = st.text_input(
                        f"Edit {item_label}",
                        value=text,
                        key=f"edit_{item_type}_text_{i}",
                        label_visibility="collapsed",
                    )
                    c1, c2 = st.columns(2)
                    save = c1.form_submit_button("Save", use_container_width=True)
                    cancel = c2.form_submit_button("Cancel", use_container_width=True)

                if save:
                    clean = edited.strip()
                    if clean and not _is_duplicate(clean, items, exclude=i):
                        st.session_state[collection_key][i] = clean
                        st.session_state[editing_key] = None
                        st.toast(f"{item_label.title()} updated")
                        st.rerun()
                    elif not clean:
                        st.warning("Cannot be empty.")
                    else:
                        st.warning("Duplicate entry.")
                if cancel:
                    st.session_state[editing_key] = None
                    st.rerun()
            else:
                st.markdown(_build_item_html(i, text, item_type), unsafe_allow_html=True)
                c1, c2 = st.columns([1, 1])
                with c1:
                    if st.button("Edit", key=f"edit_{item_type}_btn_{i}", use_container_width=True):
                        st.session_state[editing_key] = i
                        st.rerun()
                with c2:
                    if st.button("Delete", key=f"del_{item_type}_btn_{i}", use_container_width=True):
                        st.session_state[collection_key].pop(i)
                        if st.session_state.get(editing_key) == i:
                            st.session_state[editing_key] = None
                        st.toast(f"{item_label.title()} removed")
                        st.rerun()
    else:
        _render_empty_state(
            f"No {item_label}s yet",
            f"Add {item_label}s below — one per line for batch, or one at a time.",
        )

    # Brainstorm input — clear if flagged from previous add
    clear_key = f"_clear_brainstorm_{item_type}"
    if st.session_state.get(clear_key):
        st.session_state[f"brainstorm_{item_type}"] = ""
        st.session_state[clear_key] = False

    st.markdown("---")
    brainstorm = st.text_area(
        f"Add {item_label}s (one per line for batch)",
        placeholder=f"Type a {item_label}, or paste multiple separated by newlines...",
        key=f"brainstorm_{item_type}",
        height=80,
        label_visibility="collapsed",
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button(f"Add {item_label}(s)", key=f"add_{item_type}_btn", type="primary",
                      use_container_width=True):
            if brainstorm.strip():
                added = _add_item_from_brainstorm(
                    collection_key, validate_endpoint, payload_key,
                    item_label, brainstorm,
                )
                if added > 0:
                    st.session_state[clear_key] = True
                    st.toast(f"Added {added} {item_label}{'s' if added > 1 else ''}")
                    st.rerun()
                else:
                    st.warning("All entries are duplicates.")
            else:
                st.warning(f"Enter a {item_label} first.")

    with c2:
        remaining = max(0, ideal_min - len(items))
        if remaining > 0:
            if st.button(f"Suggest {remaining} more", key=f"suggest_{item_type}_btn",
                          use_container_width=True):
                with st.spinner("Getting suggestions..."):
                    suggestions = call_api("/api/suggestions", "POST", {
                        "step": "pains" if item_type == "pain" else "gains",
                        "job_description": st.session_state.job_description,
                        "existing_items": items,
                        "count_needed": remaining,
                    })
                    if "error" not in suggestions:
                        st.info(suggestions.get("suggestions", "No suggestions."))
                    else:
                        st.warning(suggestions["error"])

    # Validation (when 2+ items)
    if len(items) >= 2:
        points_tuple = tuple(items)
        result = validate_fn(_content_hash(str(points_tuple)), points_tuple)
        if result and "error" not in result:
            st.session_state[validated_key] = result.get("valid", False)
            for fb in result.get("overall_feedback", []):
                _render_validation_msg("warning", fb)
            independence = result.get("independence_check", {})
            if independence and not independence.get("independent", True):
                for issue in independence.get("issues", []):
                    _render_validation_msg("error", issue.get("message", ""))
        elif result and "error" in result:
            # Validation service unavailable — don't block the user
            st.session_state[validated_key] = True
    else:
        st.session_state[validated_key] = False

    # Coaching nudge
    nudge_thresholds = {3: "Strong canvases typically have 6-8 items.", 0: ""}
    for threshold, msg in sorted(nudge_thresholds.items(), reverse=True):
        if len(items) == threshold and msg:
            _render_coaching_tip(f"{msg} You have {len(items)} — keep going?")
            break


def render_spatial_canvas():
    """Render the single-page spatial canvas layout."""
    # Job statement at top
    _job_section()

    # Pains (left) and Gains (right)
    pain_col, gain_col = st.columns(2, gap="large")

    with pain_col:
        _items_column(
            collection_key="pain_points",
            item_type="pain",
            item_label="pain point",
            validate_endpoint="/api/validate/pain-points",
            payload_key="pain_points",
            validate_fn=_validate_pains_cached,
            validated_key="pains_validated",
            editing_key="editing_pain_index",
            ideal_min=7,
        )

    with gain_col:
        _items_column(
            collection_key="gain_points",
            item_type="gain",
            item_label="gain point",
            validate_endpoint="/api/validate/gain-points",
            payload_key="gain_points",
            validate_fn=_validate_gains_cached,
            validated_key="gains_validated",
            editing_key="editing_gain_index",
            ideal_min=8,
        )

    # Export bar
    st.markdown("---")
    render_export_bar()


# ═══════════════════════════════════════════════════════════════════════════
# Guided Mode (optional)
# ═══════════════════════════════════════════════════════════════════════════

def _render_guided_progress():
    """Render step progress indicator for guided mode."""
    steps = ["Job Description", "Pain Points", "Gain Points", "Review"]
    current = st.session_state.step - 1  # guided mode starts at step 1

    parts = []
    for i, name in enumerate(steps):
        if i < current:
            dot_cls, label_cls, indicator = "complete", "complete", "✓"
        elif i == current:
            dot_cls, label_cls, indicator = "active", "active", str(i + 1)
        else:
            dot_cls, label_cls, indicator = "", "", str(i + 1)

        line_html = ""
        if i < len(steps) - 1:
            line_cls = "complete" if i < current else ""
            line_html = f'<div class="progress-line {line_cls}"></div>'

        parts.append(
            f'<div class="progress-step">'
            f'<div class="progress-step-inner">'
            f'<div class="progress-dot {dot_cls}">{indicator}</div>'
            f'<div class="progress-step-label {label_cls}">{name}</div>'
            f'</div>{line_html}</div>'
        )

    st.markdown(
        f'<div class="progress-bar" role="list">{"".join(parts)}</div>',
        unsafe_allow_html=True,
    )


def _guided_step_nav(back_step: Optional[int], next_step: Optional[int],
                     back_label: str = "Back", next_label: str = "Continue",
                     next_disabled: bool = False):
    """Render back/next navigation for guided mode."""
    c1, c2 = st.columns(2)
    with c1:
        if back_step is not None:
            if st.button(back_label, key=f"guided_back_{back_step}", use_container_width=True):
                st.session_state.step = back_step
                st.rerun()
    with c2:
        if next_step is not None:
            if st.button(next_label, key=f"guided_next_{next_step}", use_container_width=True,
                          type="primary", disabled=next_disabled):
                st.session_state.step = next_step
                st.rerun()


def _guided_job_step():
    """Guided mode: Job Description step."""
    st.markdown("### Define the Core Job")
    tip = _coaching_tip_cached("job")
    if tip:
        _render_coaching_tip(tip)

    job = st.text_area(
        "Describe the task, goal, or objective:",
        value=st.session_state.job_description,
        height=160,
        placeholder="Example: I need to track my team's monthly expenses and generate financial reports efficiently...",
        key="guided_job_input",
    )
    st.session_state.job_description = job

    result = None
    if job.strip():
        result = _validate_job_cached(_content_hash(job), job)

    if result and "error" not in result:
        _render_quality_badge(result.get("score", 0))
        for fb in result.get("feedback", []):
            _render_validation_msg("warning", fb)
        if result.get("suggestions"):
            with st.expander("Suggestions"):
                for s in result["suggestions"]:
                    st.markdown(f"- {s}")
        st.session_state.job_validated = result.get("valid", False)
    elif result and "error" in result and job.strip():
        st.caption("Validation service unavailable — your work is saved.")
        st.session_state.job_validated = True

    if st.button("Get AI suggestions", key="guided_job_suggest"):
        with st.spinner("Thinking..."):
            suggestions = call_api("/api/suggestions", "POST", {
                "step": "job", "job_description": job,
            })
            if "error" not in suggestions:
                st.info(suggestions.get("suggestions", "No suggestions."))
            else:
                st.warning(suggestions["error"])

    st.markdown("---")
    _guided_step_nav(
        back_step=None, next_step=2,
        next_label="Continue to Pain Points",
        next_disabled=not st.session_state.job_validated,
    )
    if not st.session_state.job_validated and job.strip():
        if result and "error" not in result and result.get("feedback"):
            st.caption("Address the feedback above before continuing.")


def _guided_items_step(collection_key: str, item_type: str, item_label: str,
                        validate_endpoint: str, payload_key: str, validate_fn,
                        validated_key: str, editing_key: str, min_required: int,
                        tip_step: str, suggest_step: str,
                        back_step: int, next_step: int,
                        back_label: str, next_label: str):
    """Guided mode: Pain/Gain collection step."""
    items = st.session_state.get(collection_key, [])
    tip = _coaching_tip_cached(tip_step)
    if tip:
        _render_coaching_tip(tip)

    st.markdown(f"You need at least **{min_required}** independent {item_label}s. Currently: **{len(items)}**/{min_required}")

    # Item list with edit/delete
    if items:
        for i, text in enumerate(items):
            if st.session_state.get(editing_key) == i:
                with st.form(f"guided_edit_{item_type}_{i}", clear_on_submit=False):
                    edited = st.text_input(f"Edit {item_label}", value=text,
                                           key=f"guided_edit_text_{item_type}_{i}",
                                           label_visibility="collapsed")
                    c1, c2 = st.columns(2)
                    save = c1.form_submit_button("Save", use_container_width=True)
                    cancel = c2.form_submit_button("Cancel", use_container_width=True)
                if save:
                    clean = edited.strip()
                    if clean and not _is_duplicate(clean, items, exclude=i):
                        st.session_state[collection_key][i] = clean
                        st.session_state[editing_key] = None
                        st.toast(f"{item_label.title()} updated")
                        st.rerun()
                if cancel:
                    st.session_state[editing_key] = None
                    st.rerun()
            else:
                st.markdown(_build_item_html(i, text, item_type), unsafe_allow_html=True)
                c1, c2 = st.columns([1, 1])
                with c1:
                    if st.button("Edit", key=f"guided_edit_{item_type}_btn_{i}",
                                  use_container_width=True):
                        st.session_state[editing_key] = i
                        st.rerun()
                with c2:
                    if st.button("Delete", key=f"guided_del_{item_type}_btn_{i}",
                                  use_container_width=True):
                        st.session_state[collection_key].pop(i)
                        st.toast(f"{item_label.title()} removed")
                        st.rerun()
    else:
        _render_empty_state(f"No {item_label}s yet", f"Add your first {item_label} below.")

    # Add form
    with st.form(f"guided_add_{item_type}", clear_on_submit=True):
        new_text = st.text_input(
            f"Add a {item_label}:",
            placeholder=f"Describe a specific {item_label}...",
            key=f"guided_new_{item_type}",
        )
        submitted = st.form_submit_button(f"Add {item_label.title()}", use_container_width=True)

    if submitted and new_text.strip():
        clean = new_text.strip()
        if not _is_duplicate(clean, items):
            st.session_state[collection_key].append(clean)
            st.toast(f"{item_label.title()} added")
            st.rerun()
        else:
            st.warning("Duplicate entry.")

    # Validation
    if len(items) >= 2:
        result = validate_fn(_content_hash(str(tuple(items))), tuple(items))
        if result and "error" not in result:
            st.session_state[validated_key] = result.get("valid", False)
            for fb in result.get("overall_feedback", []):
                _render_validation_msg("warning", fb)
            independence = result.get("independence_check", {})
            if independence and not independence.get("independent", True):
                for issue in independence.get("issues", []):
                    _render_validation_msg("error", issue.get("message", ""))
        elif result and "error" in result:
            st.session_state[validated_key] = True

    # Suggestions
    remaining = max(0, min_required - len(items))
    if remaining > 0:
        if st.button(f"Get AI suggestions for {remaining} more", key=f"guided_suggest_{item_type}"):
            with st.spinner("Thinking..."):
                suggestions = call_api("/api/suggestions", "POST", {
                    "step": suggest_step,
                    "job_description": st.session_state.job_description,
                    "existing_items": items,
                    "count_needed": remaining,
                })
                if "error" not in suggestions:
                    st.info(suggestions.get("suggestions", "No suggestions."))
                else:
                    st.warning(suggestions["error"])

    st.markdown("---")
    can_proceed = len(items) >= min_required and st.session_state.get(validated_key, False)
    _guided_step_nav(
        back_step=back_step, next_step=next_step,
        back_label=back_label, next_label=next_label,
        next_disabled=not can_proceed,
    )
    if not can_proceed:
        st.caption(f"Add {remaining} more unique {item_label}s to continue.")


def _guided_review_step():
    """Guided mode: Review and export step."""
    st.markdown("""
    <div class="success-banner">
        <h2>Canvas ready</h2>
        <p>Review your canvas below, then export.</p>
    </div>
    """, unsafe_allow_html=True)

    # Job
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("### Job Statement")
    st.markdown(html.escape(st.session_state.job_description))
    st.markdown("</div>", unsafe_allow_html=True)

    # Pains & Gains side by side
    p_col, g_col = st.columns(2, gap="large")
    with p_col:
        st.markdown(
            f'<div class="col-header pain">'
            f'<div class="col-header-icon pain">!</div>'
            f'<span class="col-header-title">Pain Points</span>'
            f'<span class="col-header-count">{len(st.session_state.pain_points)}</span></div>',
            unsafe_allow_html=True,
        )
        for i, pain in enumerate(st.session_state.pain_points):
            st.markdown(_build_item_html(i, pain, "pain"), unsafe_allow_html=True)

    with g_col:
        st.markdown(
            f'<div class="col-header gain">'
            f'<div class="col-header-icon gain">+</div>'
            f'<span class="col-header-title">Gain Points</span>'
            f'<span class="col-header-count">{len(st.session_state.gain_points)}</span></div>',
            unsafe_allow_html=True,
        )
        for i, gain in enumerate(st.session_state.gain_points):
            st.markdown(_build_item_html(i, gain, "gain"), unsafe_allow_html=True)

    st.markdown("---")
    render_export_bar()

    _guided_step_nav(
        back_step=3, next_step=None,
        back_label="Back to Gains",
    )

    if st.button("Start a new canvas", use_container_width=True):
        reset_session_state(preserve_theme=True)
        st.rerun()


def render_guided_mode():
    """Render the step-by-step guided wizard."""
    # Ensure step is at least 1 for guided mode
    if st.session_state.step < 1:
        st.session_state.step = 1

    _render_guided_progress()

    if st.session_state.step == 1:
        _guided_job_step()
    elif st.session_state.step == 2:
        st.markdown("### Identify Pain Points")
        _guided_items_step(
            collection_key="pain_points", item_type="pain", item_label="pain point",
            validate_endpoint="/api/validate/pain-points", payload_key="pain_points",
            validate_fn=_validate_pains_cached, validated_key="pains_validated",
            editing_key="editing_pain_index", min_required=7,
            tip_step="pains", suggest_step="pains",
            back_step=1, next_step=3,
            back_label="Back to Job", next_label="Continue to Gains",
        )
    elif st.session_state.step == 3:
        st.markdown("### Identify Gain Points")
        _guided_items_step(
            collection_key="gain_points", item_type="gain", item_label="gain point",
            validate_endpoint="/api/validate/gain-points", payload_key="gain_points",
            validate_fn=_validate_gains_cached, validated_key="gains_validated",
            editing_key="editing_gain_index", min_required=8,
            tip_step="gains", suggest_step="gains",
            back_step=2, next_step=4,
            back_label="Back to Pains", next_label="Continue to Review",
        )
    elif st.session_state.step == 4:
        _guided_review_step()


# ═══════════════════════════════════════════════════════════════════════════
# Export Bar
# ═══════════════════════════════════════════════════════════════════════════

def render_export_bar():
    """Render the export/download section."""
    pains = st.session_state.get("pain_points", [])
    gains = st.session_state.get("gain_points", [])
    job = st.session_state.get("job_description", "")

    label, label_class = _quality_level_label(len(pains), len(gains), job)

    st.markdown(f'<div class="quality-label {label_class}" style="margin-bottom: 0.75rem;">Quality: {label}</div>', unsafe_allow_html=True)

    if not job.strip() and not pains and not gains:
        st.caption("Add content to enable export.")
        return

    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"Generate Word ({label})", key="generate_doc_btn", type="primary",
                      use_container_width=True):
            with st.spinner("Generating document..."):
                try:
                    response = get_http_client().post(
                        f"{API_BASE_URL}/api/generate-document",
                        headers=get_api_headers(),
                        json={
                            "job_description": job,
                            "pain_points": pains,
                            "gain_points": gains,
                            "title": "Value Proposition Canvas",
                        },
                    )
                    if response.status_code == 200:
                        st.session_state["_doc_data"] = response.content
                        st.session_state["_doc_label"] = label
                    else:
                        st.error("Failed to generate document.")
                except Exception as e:
                    st.error(f"Connection error: {e}")
                    st.caption("Make sure the backend is running.")

        # Show download button only after generation
        if st.session_state.get("_doc_data"):
            st.download_button(
                label=f"Download Word ({st.session_state.get('_doc_label', label)})",
                data=st.session_state["_doc_data"],
                file_name="Value_Proposition_Canvas.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )

    with col2:
        if st.button("Start new canvas", key="new_canvas_btn", use_container_width=True):
            st.session_state.pop("_doc_data", None)
            st.session_state.pop("_doc_label", None)
            reset_session_state(preserve_theme=True)
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# DB Persistence
# ═══════════════════════════════════════════════════════════════════════════

def _save_canvas_to_db():
    token = st.session_state.get("auth_token")
    if not token:
        return
    api = CanvasAPIClient(API_BASE_URL, token)
    api.save_current({
        "job_description": st.session_state.get("job_description", ""),
        "pain_points": st.session_state.get("pain_points", []),
        "gain_points": st.session_state.get("gain_points", []),
        "wizard_step": st.session_state.get("step", 0),
        "job_validated": st.session_state.get("job_validated", False),
        "pains_validated": st.session_state.get("pains_validated", False),
        "gains_validated": st.session_state.get("gains_validated", False),
    })


def _load_canvas_from_db():
    token = st.session_state.get("auth_token")
    if not token:
        return
    api = CanvasAPIClient(API_BASE_URL, token)
    canvas = api.get_current()
    if canvas:
        st.session_state.step = canvas.get("wizard_step", 0)
        st.session_state.job_description = canvas.get("job_description", "")
        st.session_state.pain_points = list(canvas.get("pain_points", []))
        st.session_state.gain_points = list(canvas.get("gain_points", []))
        st.session_state.job_validated = canvas.get("job_validated", False)
        st.session_state.pains_validated = canvas.get("pains_validated", False)
        st.session_state.gains_validated = canvas.get("gains_validated", False)
        st.session_state.session_loaded = True


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

@st.dialog("Change Password")
def _change_password_dialog():
    """Dialog for changing the current user's password."""
    current = st.text_input("Current Password", type="password", key="cp_current")
    new_pw = st.text_input("New Password", type="password", key="cp_new",
                            help="Min 10 chars, upper+lower+digit+special")
    _render_password_strength(new_pw)
    confirm = st.text_input("Confirm New Password", type="password", key="cp_confirm")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Change", type="primary", use_container_width=True, key="cp_submit"):
            if not current or not new_pw:
                st.error("All fields are required.")
            elif new_pw != confirm:
                st.error("Passwords do not match.")
            else:
                token = st.session_state.get("auth_token", "")
                result = change_password_request(token, current, new_pw)
                if result.get("status_code") == 200:
                    st.session_state.pop("must_change_password", None)
                    st.toast("Password changed successfully.")
                    st.rerun()
                else:
                    st.error(result.get("detail", "Password change failed."))
    with c2:
        if st.button("Cancel", use_container_width=True, key="cp_cancel"):
            st.rerun()


def _render_forced_password_change():
    """Full-page password change form when must_change_password is set."""
    st.markdown("""
    <div class="auth-container">
        <h1>Password Change Required</h1>
        <p>An administrator has reset your password. You must set a new password before continuing.</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("forced_pw_change"):
        current = st.text_input("Current Password", type="password")
        new_pw = st.text_input("New Password", type="password",
                                help="Min 10 chars, upper+lower+digit+special")
        confirm = st.text_input("Confirm New Password", type="password")
        submitted = st.form_submit_button("Change Password", use_container_width=True)

    if new_pw:
        _render_password_strength(new_pw)

    if submitted:
        if not current or not new_pw:
            st.error("All fields are required.")
        elif new_pw != confirm:
            st.error("Passwords do not match.")
        else:
            token = st.session_state.get("auth_token", "")
            result = change_password_request(token, current, new_pw)
            if result.get("status_code") == 200:
                st.session_state.pop("must_change_password", None)
                # Explicitly clear the flag in auth_user to avoid stale state
                if "auth_user" in st.session_state:
                    st.session_state["auth_user"]["must_change_password"] = False
                st.session_state.pop("db_canvas_loaded", None)
                st.toast("Password changed successfully.")
                st.rerun()
            else:
                st.error(result.get("detail", "Password change failed."))

    st.markdown("---")
    if st.button("Sign Out", use_container_width=True):
        logout()


def _render_canvas_content():
    """Render the main canvas content (spatial or guided mode)."""
    render_header()

    if st.session_state.canvas_mode == "spatial":
        render_spatial_canvas()
    else:
        render_guided_mode()

    # Auto-save
    has_content = (
        st.session_state.job_description.strip()
        or len(st.session_state.pain_points) > 0
        or len(st.session_state.gain_points) > 0
    )
    if has_content:
        _save_canvas_to_db()


def main():
    init_session_state()

    # Auth gate
    if not check_auth():
        render_login_page()
        return

    auth_user = st.session_state.get("auth_user", {})
    user_status = auth_user.get("status", "active")

    if user_status == "pending":
        render_pending_page()
        return
    if user_status in ("paused", "declined"):
        render_blocked_page(user_status)
        return

    # Forced password change gate
    if st.session_state.get("must_change_password") or auth_user.get("must_change_password"):
        _render_forced_password_change()
        return

    # Load canvas from DB on first load
    if not st.session_state.get("db_canvas_loaded"):
        _load_canvas_from_db()
        st.session_state.db_canvas_loaded = True

    is_admin = auth_user.get("is_admin", False)

    # Sidebar
    with st.sidebar:
        st.markdown(f"**{auth_user.get('display_name', 'User')}**")
        st.caption(auth_user.get("email", ""))
        st.markdown("---")

        # Mode toggle
        mode = st.radio(
            "Mode",
            ["Spatial Canvas", "Guided Wizard"],
            index=0 if st.session_state.canvas_mode == "spatial" else 1,
            key="mode_toggle",
            help="Spatial: all sections visible at once. Guided: step-by-step flow.",
        )
        st.session_state.canvas_mode = "spatial" if mode == "Spatial Canvas" else "guided"

        st.markdown("---")

        # Quality thermometer
        render_quality_thermometer()

        st.markdown("---")

        # Theme
        theme = st.selectbox("Theme", list(THEME_CONFIGS.keys()),
                              index=list(THEME_CONFIGS.keys()).index(st.session_state.theme_mode),
                              key="theme_select")
        st.session_state.theme_mode = theme

        # Accessibility
        st.checkbox("High Contrast", key="pref_high_contrast")
        st.checkbox("Large Text", key="pref_large_text")

        st.markdown("---")
        if st.button("Change Password", key="change_pw_btn", use_container_width=True):
            _change_password_dialog()
        if st.button("Sign Out", key="logout_btn", use_container_width=True):
            logout()

    # Apply theme CSS after sidebar sets theme_mode
    apply_theme()

    # Main content — admin gets tabs, non-admin gets canvas directly
    if is_admin:
        tab_canvas, tab_admin = st.tabs(["Canvas", "Admin"])
        with tab_canvas:
            _render_canvas_content()
        with tab_admin:
            token = st.session_state.get("auth_token", "")
            admin_client = AdminAPIClient(API_BASE_URL, token)
            admin_tab_dash, admin_tab_users = st.tabs(["Dashboard", "Users"])
            with admin_tab_dash:
                render_admin_dashboard(admin_client)
            with admin_tab_users:
                render_admin_user_management(admin_client, str(auth_user.get("id", "")))
    else:
        _render_canvas_content()


if __name__ == "__main__":
    main()
