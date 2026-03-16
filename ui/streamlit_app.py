"""
Value Proposition Canvas — Streamlit UI.
Spatial canvas (default) with optional guided mode.
"""

import io
import json
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

# ── Load external CSS (read fresh each rerun to pick up changes) ──
_CSS_PATH = Path(__file__).parent / "assets" / "style.css"
_ADMIN_CSS_PATH = Path(__file__).parent / "assets" / "admin.css"


def _load_css():
    """Load CSS files on every Streamlit rerun to avoid stale caches."""
    parts = []
    if _CSS_PATH.exists():
        parts.append(_CSS_PATH.read_text())
    if _ADMIN_CSS_PATH.exists():
        parts.append(_ADMIN_CSS_PATH.read_text())
    if parts:
        st.markdown(f"<style>{''.join(parts)}</style>", unsafe_allow_html=True)


_load_css()

# ── API Configuration ──
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "")

# ── Backend Config (fetched once per session, with safe fallbacks) ──
_DEFAULT_CONFIG = {
    "ai_enabled": True,
    "min_pain_points": 7,
    "min_gain_points": 7,
    "similarity_threshold": 0.8,
    "password_min_length": 10,
    "password_rules_text": "Min 10 chars, upper+lower+digit+special",
}


def _fetch_backend_config() -> dict:
    """Fetch business config from the backend /api/config endpoint."""
    try:
        resp = httpx.get(
            f"{API_BASE_URL}/api/config",
            headers={"X-API-Key": API_SECRET_KEY} if API_SECRET_KEY else {},
            timeout=2.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            # Merge with defaults so missing keys don't break the UI
            return {**_DEFAULT_CONFIG, **data}
    except Exception as e:
        logger.warning("Failed to fetch backend config: %s", e)
    return dict(_DEFAULT_CONFIG)


def get_backend_config() -> dict:
    """Return cached backend config from session state, fetching if missing."""
    if "_backend_config" not in st.session_state:
        st.session_state["_backend_config"] = _fetch_backend_config()
    return st.session_state["_backend_config"]

# ── Theme Configuration ──
DEFAULT_THEME = "Light"
THEME_CONFIGS = {
    "Light": {},  # Uses CSS :root defaults
    "Dark": {"attr": "dark"},
    "Ocean": {"attr": "ocean"},
    "Forest": {"attr": "forest"},
    "Sunset": {"attr": "sunset"},
}

# Color palettes for CSS injection (Streamlit overrides require !important)
_THEME_PALETTES = {
    "Dark": {
        "scheme": "dark",
        "primary": "#60a5fa", "primary_hover": "#93bbfd", "primary_light": "#1e3a5f",
        "bg_page": "#0f1117", "bg_card": "#1a1d27",
        "text_primary": "#f1f5f9", "text_secondary": "#94a3b8", "text_muted": "#64748b",
        "border": "#334155", "border_light": "#1e293b",
        "success": "#34d399", "success_light": "#132f21",
        "warning": "#fbbf24", "warning_light": "#3b2f10",
        "error": "#f87171", "error_light": "#3b1515",
        "pain": "#fb7185", "pain_light": "#3b1525",
        "gain": "#2dd4bf", "gain_light": "#0f3b35",
    },
    "Ocean": {
        "scheme": "light",
        "primary": "#0891b2", "primary_hover": "#0e7490", "primary_light": "#e0f7fa",
        "bg_page": "#f0f9ff", "bg_card": "#ffffff",
        "text_primary": "#0c4a6e", "text_secondary": "#475569", "text_muted": "#94a3b8",
        "border": "#bae6fd", "border_light": "#e0f2fe",
        "success": "#059669", "success_light": "#ecfdf5",
        "warning": "#d97706", "warning_light": "#fffbeb",
        "error": "#dc2626", "error_light": "#fef2f2",
        "pain": "#7c3aed", "pain_light": "#f5f3ff",
        "gain": "#0d9488", "gain_light": "#f0fdfa",
    },
    "Forest": {
        "scheme": "light",
        "primary": "#15803d", "primary_hover": "#166534", "primary_light": "#f0fdf4",
        "bg_page": "#f8faf5", "bg_card": "#ffffff",
        "text_primary": "#1a2e05", "text_secondary": "#4b5563", "text_muted": "#9ca3af",
        "border": "#bbcfad", "border_light": "#ecfccb",
        "success": "#16a34a", "success_light": "#f0fdf4",
        "warning": "#ca8a04", "warning_light": "#fefce8",
        "error": "#dc2626", "error_light": "#fef2f2",
        "pain": "#b45309", "pain_light": "#fffbeb",
        "gain": "#047857", "gain_light": "#ecfdf5",
    },
    "Sunset": {
        "scheme": "light",
        "primary": "#ea580c", "primary_hover": "#c2410c", "primary_light": "#fff7ed",
        "bg_page": "#fffbf5", "bg_card": "#ffffff",
        "text_primary": "#431407", "text_secondary": "#57534e", "text_muted": "#a8a29e",
        "border": "#e7e5e4", "border_light": "#f5f5f4",
        "success": "#16a34a", "success_light": "#f0fdf4",
        "warning": "#d97706", "warning_light": "#fffbeb",
        "error": "#dc2626", "error_light": "#fef2f2",
        "pain": "#be123c", "pain_light": "#fff1f2",
        "gain": "#0d9488", "gain_light": "#f0fdfa",
    },
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
    # Fetch backend config once per session
    get_backend_config()
    if "theme_mode" not in st.session_state:
        st.session_state.theme_mode = DEFAULT_THEME
    if "pref_high_contrast" not in st.session_state:
        st.session_state.pref_high_contrast = False
    if "pref_large_text" not in st.session_state:
        st.session_state.pref_large_text = False


def reset_session_state(preserve_theme: bool = False):
    for key, default in INITIAL_STATE.items():
        st.session_state[key] = list(default) if isinstance(default, list) else default
    # Bump version to force text_area re-initialization with empty value
    st.session_state["_job_input_ver"] = st.session_state.get("_job_input_ver", 0) + 1
    if not preserve_theme:
        st.session_state.theme_mode = DEFAULT_THEME


# ═══════════════════════════════════════════════════════════════════════════
# Theme
# ═══════════════════════════════════════════════════════════════════════════

def _build_theme_css(palette: dict) -> str:
    """Generate CSS variable overrides + Streamlit component overrides for a theme."""
    p = palette
    is_dark = p["scheme"] == "dark"
    color_scheme = "dark" if is_dark else "light"

    # CSS variable overrides (covers all custom components via var() references)
    css = f"""
    :root {{
        --color-primary: {p['primary']} !important;
        --color-primary-hover: {p['primary_hover']} !important;
        --color-primary-light: {p['primary_light']} !important;
        --color-bg-page: {p['bg_page']} !important;
        --color-bg-card: {p['bg_card']} !important;
        --color-text-primary: {p['text_primary']} !important;
        --color-text-secondary: {p['text_secondary']} !important;
        --color-text-muted: {p['text_muted']} !important;
        --color-border: {p['border']} !important;
        --color-border-light: {p['border_light']} !important;
        --color-success: {p['success']} !important;
        --color-success-light: {p['success_light']} !important;
        --color-warning: {p['warning']} !important;
        --color-warning-light: {p['warning_light']} !important;
        --color-error: {p['error']} !important;
        --color-error-light: {p['error_light']} !important;
        --color-pain: {p['pain']} !important;
        --color-pain-light: {p['pain_light']} !important;
        --color-gain: {p['gain']} !important;
        --color-gain-light: {p['gain_light']} !important;
    }}
    /* Streamlit component overrides (Streamlit inlines styles, so !important is required) */
    .stApp.stApp {{ background: {p['bg_page']} !important; color: {p['text_primary']} !important; color-scheme: {color_scheme} !important; }}
    [data-testid="stAppViewContainer"],
    .main, .main .block-container {{ background: {p['bg_page']} !important; color: {p['text_primary']} !important; }}
    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"] > div {{ background: {p['bg_card']} !important; border-right-color: {p['border']} !important; }}
    .stTextArea > div > div > textarea,
    .stTextInput > div > div > input {{ background: {p['bg_card']} !important; color: {p['text_primary']} !important; border-color: {p['border']} !important; }}
    .stSelectbox > div > div,
    .stSelectbox [data-baseweb="select"],
    [data-baseweb="popover"] > div {{ background: {p['bg_card']} !important; color: {p['text_primary']} !important; }}
    h1, h2, h3, h4, p, span, label, .stMarkdown, .stCaption, a {{ color: {p['text_primary']} !important; }}
    .stButton > button:not([kind="primary"]) {{ background: {p['bg_card']} !important; color: {p['text_primary']} !important; border-color: {p['border']} !important; }}
    .stButton > button[kind="primary"] {{ background: {p['primary']} !important; border-color: {p['primary']} !important; }}
    hr {{ background: {p['border']} !important; }}
    .stTabs [data-baseweb="tab-list"] {{ border-bottom-color: {p['border']} !important; }}
    .stTabs [data-baseweb="tab"] {{ color: {p['text_secondary']} !important; }}
    .stRadio label, .stCheckbox label {{ color: {p['text_primary']} !important; }}
    [data-testid="stForm"] {{ border-color: {p['border']} !important; }}
    .stDownloadButton > button {{ background: {p['primary']} !important; border-color: {p['primary']} !important; }}
    """
    return css


def apply_theme():
    """Apply theme and accessibility overrides via CSS injection.
    Must be called early in the render cycle, before any content."""
    parts = []

    theme_name = st.session_state.get("theme_mode", DEFAULT_THEME)
    palette = _THEME_PALETTES.get(theme_name)
    if palette:
        parts.append(_build_theme_css(palette))

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


@st.cache_data(ttl=300)
def _validate_relevance_cached(h: str, items: tuple, job_desc: str, item_type: str) -> dict:
    return call_api("/api/validate/relevance", "POST", {
        "items": list(items),
        "job_description": job_desc,
        "item_type": item_type,
    })


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


def _build_item_html(index: int, text: str, item_type: str, similar: bool = False) -> str:
    safe = html.escape(text)
    prefix = "!" if item_type == "pain" else "+"
    card_class = "item-card item-card-similar" if similar else "item-card"
    return (
        f'<div class="{card_class}">'
        f'<div class="item-badge {item_type}">{prefix}{index + 1}</div>'
        f'<div class="item-text">{safe}</div></div>'
    )


def _render_suggestion_cards(suggestions_list: list, collection_key: str, item_type: str):
    """Render clickable suggestion cards with 'Add this' buttons."""
    if not suggestions_list:
        return
    for idx, suggestion in enumerate(suggestions_list):
        text = suggestion.get('text', '')
        if not text:
            continue
        category = suggestion.get('category', '')

        # Show the suggestion card with an Add button
        col_text, col_btn = st.columns([4, 1])
        with col_text:
            cat_html = f'<div class="suggestion-card-category">{html.escape(category)}</div>' if category else ''
            st.markdown(
                f'<div class="suggestion-card">'
                f'<div class="suggestion-card-text">{html.escape(text)}{cat_html}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col_btn:
            if st.button("Add this", key=f"add_suggestion_{item_type}_{idx}", width='stretch'):
                items = st.session_state.get(collection_key, [])
                if not _is_duplicate(text, items):
                    items.append(text)
                    st.session_state[collection_key] = items
                    # Clear suggestions after adding
                    st.session_state.pop(f"_suggestions_{item_type}", None)
                    st.toast(f"Added suggestion to {item_type}s")
                    st.rerun()
                else:
                    st.warning("This suggestion is already in your list.")


def _render_job_suggestion_cards(suggestions_list: list, prefix: str = "spatial"):
    """Render clickable job statement suggestion cards with 'Use this' buttons."""
    if not suggestions_list:
        return
    state_key = f"_suggestions_job_{prefix}"
    for idx, suggestion in enumerate(suggestions_list):
        text = suggestion.get('text', '')
        if not text:
            continue

        col_text, col_btn = st.columns([4, 1])
        with col_text:
            st.markdown(
                f'<div class="suggestion-card">'
                f'<div class="suggestion-card-text">{html.escape(text)}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col_btn:
            if st.button("Use this", key=f"{prefix}_use_job_suggestion_{idx}", width='stretch'):
                current = st.session_state.get("job_description", "").strip()
                new_text = (current + "\n\n" + text) if current else text
                st.session_state.job_description = new_text
                # Bump version to force text_area re-initialization with new value
                st.session_state["_job_input_ver"] = st.session_state.get("_job_input_ver", 0) + 1
                st.session_state.pop(state_key, None)
                st.toast("Job statement updated")
                st.rerun()


def _render_dimension_minimap(dimension_distribution: dict, item_type: str):
    """Render the dimension distribution minimap (functional/emotional/social bar)."""
    func_count = dimension_distribution.get('functional', 0)
    emot_count = dimension_distribution.get('emotional', 0)
    soc_count = dimension_distribution.get('social', 0)
    total = func_count + emot_count + soc_count

    if total == 0:
        return

    func_pct = round(func_count / total * 100)
    emot_pct = round(emot_count / total * 100)
    soc_pct = 100 - func_pct - emot_pct  # Ensure it sums to 100

    st.markdown(f'''
    <div class="dimension-minimap">
        <div class="dimension-minimap-title">Dimension Coverage</div>
        <div class="dimension-bar-container">
            <div class="dimension-bar-segment functional" style="width:{func_pct}%"></div>
            <div class="dimension-bar-segment emotional" style="width:{emot_pct}%"></div>
            <div class="dimension-bar-segment social" style="width:{soc_pct}%"></div>
        </div>
        <div class="dimension-legend">
            <div class="dimension-legend-item"><div class="dimension-dot functional"></div>Functional ({func_count})</div>
            <div class="dimension-legend-item"><div class="dimension-dot emotional"></div>Emotional ({emot_count})</div>
            <div class="dimension-legend-item"><div class="dimension-dot social"></div>Social ({soc_count})</div>
        </div>
    </div>
    ''', unsafe_allow_html=True)


def _render_improve_comparison(original: str, improved: str, explanation: str):
    """Render a before/after comparison for an improved item."""
    st.markdown(f'''
    <div class="improve-comparison">
        <div class="improve-comparison-label before">Original</div>
        <div class="improve-comparison-text before">{html.escape(original)}</div>
        <div class="improve-comparison-label after">Improved</div>
        <div class="improve-comparison-text after">{html.escape(improved)}</div>
        <div class="improve-explanation">{html.escape(explanation)}</div>
    </div>
    ''', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# Quality Thermometer (sidebar)
# ═══════════════════════════════════════════════════════════════════════════

def _quality_level_label(pain_count: int, gain_count: int, job_desc: str,
                         ideal_total: int) -> tuple:
    """Returns (label, css_class) for the overall quality."""
    total = pain_count + gain_count
    has_job = bool(job_desc.strip())
    if total >= ideal_total and has_job:
        return ("Strong", "strong")
    elif total >= 6 and has_job:
        return ("Working", "working")
    else:
        return ("Draft", "draft")


def render_quality_thermometer():
    """Render the multi-dimensional quality indicator in the sidebar."""
    pains = st.session_state.get("pain_points", [])
    gains = st.session_state.get("gain_points", [])
    job = st.session_state.get("job_description", "")

    pain_count = len(pains)
    gain_count = len(gains)

    # Completeness: items vs ideal total from backend config
    cfg = get_backend_config()
    ideal_total = cfg["min_pain_points"] + cfg["min_gain_points"]
    completeness = min(100, int((pain_count + gain_count) / ideal_total * 100))
    # Balance: how close is the ratio to ideal
    if pain_count + gain_count > 0:
        ratio = min(pain_count, gain_count) / max(pain_count, gain_count, 1)
        balance = int(ratio * 100)
    else:
        balance = 0
    # Job presence
    job_score = 100 if job.strip() else 0

    label, label_class = _quality_level_label(pain_count, gain_count, job, ideal_total)

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

    _ver = st.session_state.get("_job_input_ver", 0)
    _widget_key = f"spatial_job_input_v{_ver}"
    if _widget_key not in st.session_state:
        st.session_state[_widget_key] = st.session_state.job_description
    job = st.text_area(
        "What is the main task or goal you're trying to accomplish?",
        height=120,
        placeholder="Example: I need to track my team's monthly expenses and generate financial reports efficiently, so I can make informed budget decisions...",
        key=_widget_key,
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

    # AI suggestions — clickable cards
    _sug_key = "_suggestions_job_spatial"
    if st.button("Get AI suggestions", key="spatial_job_suggest", type="secondary"):
        with st.spinner("Thinking..."):
            suggestions = call_api("/api/suggestions/job-statement", "POST", {
                "current_description": job,
                "count": 3,
            })
            if "error" not in suggestions:
                suggestions_list = suggestions.get("suggestions_list", [])
                if suggestions_list:
                    st.session_state[_sug_key] = suggestions_list
                    st.rerun()
                else:
                    st.info(suggestions.get("suggestions", "No suggestions available."))
            else:
                st.warning(suggestions["error"])

    # Render suggestion cards outside button callback (Streamlit pattern)
    if _sug_key in st.session_state:
        _render_job_suggestion_cards(st.session_state[_sug_key], prefix="spatial")
        if st.button("Dismiss suggestions", key="dismiss_job_suggestions_spatial"):
            del st.session_state[_sug_key]
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def _items_column(collection_key: str, item_type: str, item_label: str,
                  validate_endpoint: str, payload_key: str, validate_fn,
                  validated_key: str, editing_key: str, ideal_min: int):
    """Render a pain/gain column with brainstorm input and item list."""
    items = st.session_state.get(collection_key, [])
    icon = "!" if item_type == "pain" else "+"

    # Track which items are flagged as similar (for highlighting)
    similar_indices = set()

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
                    save = c1.form_submit_button("Save", width='stretch')
                    cancel = c2.form_submit_button("Cancel", width='stretch')

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
                is_similar = i in similar_indices
                st.markdown(_build_item_html(i, text, item_type, similar=is_similar), unsafe_allow_html=True)
                c1, c2, c3 = st.columns([1, 1, 1])
                with c1:
                    if st.button("Edit", key=f"edit_{item_type}_btn_{i}", width='stretch'):
                        st.session_state[editing_key] = i
                        st.rerun()
                with c2:
                    if st.button("Improve", key=f"improve_{item_type}_btn_{i}", width='stretch'):
                        with st.spinner("Improving..."):
                            result = call_api("/api/improve-item", "POST", {
                                "item": text,
                                "item_type": item_type.replace(" ", "_"),
                                "job_description": st.session_state.get("job_description", ""),
                                "context_items": [t for j, t in enumerate(items) if j != i][:5],
                            })
                            if "error" not in result:
                                st.session_state[f"_improve_result_{item_type}_{i}"] = result
                            else:
                                st.warning(result["error"])
                with c3:
                    if st.button("Delete", key=f"del_{item_type}_btn_{i}", width='stretch'):
                        st.session_state[collection_key].pop(i)
                        if st.session_state.get(editing_key) == i:
                            st.session_state[editing_key] = None
                        st.toast(f"{item_label.title()} removed")
                        st.rerun()

                # Show improve comparison if available
                improve_key = f"_improve_result_{item_type}_{i}"
                if st.session_state.get(improve_key):
                    imp = st.session_state[improve_key]
                    _render_improve_comparison(
                        imp.get('original', text),
                        imp.get('improved', text),
                        imp.get('explanation', ''),
                    )
                    acc_col, rej_col = st.columns(2)
                    with acc_col:
                        if st.button("Accept", key=f"accept_improve_{item_type}_{i}", type="primary", width='stretch'):
                            st.session_state[collection_key][i] = imp['improved']
                            del st.session_state[improve_key]
                            st.toast("Improvement accepted")
                            st.rerun()
                    with rej_col:
                        if st.button("Reject", key=f"reject_improve_{item_type}_{i}", width='stretch'):
                            del st.session_state[improve_key]
                            st.rerun()
    else:
        _render_empty_state(
            f"No {item_label}s yet",
            f"Start with your most obvious {'frustration' if item_type == 'pain' else 'desired outcome'} — the one you'd mention first.",
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
                      width='stretch'):
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
        suggestions_state_key = f"_suggestions_{item_type}"
        if remaining > 0:
            if st.button(f"Suggest {remaining} more", key=f"suggest_{item_type}_btn",
                          width='stretch'):
                with st.spinner("Getting suggestions..."):
                    suggestions = call_api("/api/suggestions", "POST", {
                        "step": "pains" if item_type == "pain" else "gains",
                        "job_description": st.session_state.job_description,
                        "existing_items": items,
                        "count_needed": remaining,
                    })
                    if "error" not in suggestions:
                        suggestions_list = suggestions.get("suggestions_list", [])
                        if suggestions_list:
                            st.session_state[suggestions_state_key] = suggestions_list
                            st.rerun()
                        else:
                            st.info(suggestions.get("suggestions", "No suggestions."))
                    else:
                        st.warning(suggestions["error"])

    # Render suggestion cards outside button callback so "Add this" works
    suggestions_state_key = f"_suggestions_{item_type}"
    if suggestions_state_key in st.session_state:
        _render_suggestion_cards(
            st.session_state[suggestions_state_key], collection_key, item_type
        )
        if st.button("Dismiss suggestions", key=f"dismiss_suggestions_{item_type}"):
            del st.session_state[suggestions_state_key]
            st.rerun()

    # Validation (when 2+ items) — progressive disclosure
    if len(items) >= 2:
        points_tuple = tuple(items)
        result = validate_fn(_content_hash(str(points_tuple)), points_tuple)
        if result and "error" not in result:
            st.session_state[validated_key] = result.get("valid", False)
            priority = result.get("priority_level", "count")

            # Positive feedback first
            for pfb in result.get("positive_feedback", []):
                st.markdown(
                    f'<div class="positive-feedback"><span>✓</span> {html.escape(pfb)}</div>',
                    unsafe_allow_html=True,
                )

            # Progressive disclosure: only show the most relevant tier
            if priority == "count":
                for fb in result.get("overall_feedback", []):
                    _render_validation_msg("warning", fb)
            elif priority == "quality":
                # Show quality issues for individual items
                for q in result.get("individual_quality", []):
                    if not q.get("valid", True):
                        idx = q.get("index", "?")
                        for fb in q.get("feedback", []):
                            _render_validation_msg("warning", f"Item {idx + 1}: {fb}")
            elif priority == "independence":
                independence = result.get("independence_check", {})
                if independence and not independence.get("independent", True):
                    for issue in independence.get("issues", []):
                        sim = issue.get("similarity", 0)
                        i1 = issue.get("item1_index", 0)
                        i2 = issue.get("item2_index", 0)
                        similar_indices.add(i1)
                        similar_indices.add(i2)
                        # Coaching-style message
                        _render_validation_msg(
                            "warning",
                            f"Items {i1 + 1} and {i2 + 1} are {sim}% similar — "
                            f"could you combine them into one stronger point, or sharpen the difference?"
                        )
                        # Merge button
                        if st.button(
                            f"Merge items {i1 + 1} & {i2 + 1}",
                            key=f"merge_{item_type}_{i1}_{i2}",
                        ):
                            with st.spinner("Merging..."):
                                merge_result = call_api("/api/merge-items", "POST", {
                                    "item1": items[i1],
                                    "item2": items[i2],
                                    "item_type": item_type,
                                    "job_description": st.session_state.get("job_description", ""),
                                })
                                if "error" not in merge_result:
                                    st.session_state[f"_merge_result_{item_type}_{i1}_{i2}"] = merge_result
                                else:
                                    st.warning(merge_result["error"])

                        # Show merge result if available
                        merge_key = f"_merge_result_{item_type}_{i1}_{i2}"
                        if st.session_state.get(merge_key):
                            mr = st.session_state[merge_key]
                            st.markdown(
                                f'<div class="merge-prompt">'
                                f'<div class="merge-prompt-text">'
                                f'Suggested merge: <strong>{html.escape(mr.get("merged", ""))}</strong><br>'
                                f'<em>{html.escape(mr.get("explanation", ""))}</em>'
                                f'</div></div>',
                                unsafe_allow_html=True,
                            )
                            mc1, mc2 = st.columns(2)
                            with mc1:
                                if st.button("Accept merge", key=f"accept_merge_{item_type}_{i1}_{i2}", type="primary", width='stretch'):
                                    # Replace item at i1 with merged, remove item at i2
                                    st.session_state[collection_key][i1] = mr["merged"]
                                    st.session_state[collection_key].pop(i2)
                                    del st.session_state[merge_key]
                                    st.toast("Items merged")
                                    st.rerun()
                            with mc2:
                                if st.button("Dismiss", key=f"dismiss_merge_{item_type}_{i1}_{i2}", width='stretch'):
                                    del st.session_state[merge_key]
                                    st.rerun()
            # 'complete' priority → no warnings needed, positive feedback handles it

        elif result and "error" in result:
            st.session_state[validated_key] = True
    else:
        st.session_state[validated_key] = False

    # Relevance check (when job is validated and 2+ items)
    job_desc = st.session_state.get("job_description", "")
    if st.session_state.get("job_validated", False) and len(items) >= 2 and job_desc.strip():
        points_tuple = tuple(items)
        relevance = _validate_relevance_cached(
            _content_hash(f"rel_{str(points_tuple)}_{job_desc}"),
            points_tuple, job_desc, item_type,
        )
        if relevance and "error" not in relevance:
            # Show relevance warnings
            for score_entry in relevance.get("item_scores", []):
                if not score_entry.get("relevant", True):
                    fb = score_entry.get("feedback", "This item may not be relevant to your job.")
                    idx = score_entry.get("index", "?")
                    st.markdown(
                        f'<div class="relevance-warning">Item {idx + 1}: {html.escape(fb)}</div>',
                        unsafe_allow_html=True,
                    )

            # Dimension minimap
            dim_dist = relevance.get("dimension_distribution", {})
            if sum(dim_dist.values()) > 0:
                _render_dimension_minimap(dim_dist, item_type)

    # Coaching nudge — multiple thresholds
    if len(items) == 0:
        pass  # Empty state handles this
    elif len(items) == 1:
        _render_coaching_tip(f"Good start! Add more {item_label}s to build a complete picture.")
    elif len(items) == 3:
        _render_coaching_tip(f"You have {len(items)} {item_label}s — strong canvases typically have {ideal_min}+. Keep going!")
    elif len(items) == 5:
        _render_coaching_tip(f"Almost there — {ideal_min - len(items)} more for a solid canvas.")
    elif len(items) >= ideal_min:
        _render_coaching_tip(f"Great coverage with {len(items)} {item_label}s! Review for any overlaps.")


def _compute_nudges(job: str, pains: list, gains: list) -> list:
    """Fetch nudges from the validate/canvas endpoint (cached per content hash)."""
    if not job.strip() and not pains and not gains:
        return []
    content_hash = hashlib.md5(
        f"{job}|{pains}|{gains}".encode()
    ).hexdigest()
    cache_key = f"_nudges_{content_hash}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]
    try:
        resp = get_http_client().post(
            f"{API_BASE_URL}/api/validate/canvas",
            headers=get_api_headers(),
            json={
                "job_description": job,
                "pain_points": pains,
                "gain_points": gains,
            },
        )
        if resp.status_code == 200:
            nudges = resp.json().get("nudges", [])
            st.session_state[cache_key] = nudges
            return nudges
    except Exception:
        pass
    return []


def _render_nudge_cards(nudges: list, section_filter: str = None):
    """Render nudge cards, optionally filtered by section."""
    dismissed = st.session_state.get("_dismissed_nudges", set())
    filtered = [n for n in nudges
                if (section_filter is None or n.get("section") == section_filter)
                and n.get("id") not in dismissed]
    if not filtered:
        return
    for nudge in filtered:
        severity = nudge.get("severity", "info")
        icon = "💡" if severity == "suggestion" else "ℹ️"
        css_class = "coaching-tip" if severity == "suggestion" else "validation-msg success"
        st.markdown(f"""
        <div class="nudge-card {severity}">
            <span class="nudge-icon">{icon}</span>
            <span class="nudge-text">{html.escape(nudge.get('message', ''))}</span>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Dismiss", key=f"dismiss_{nudge['id']}", type="secondary"):
            if "_dismissed_nudges" not in st.session_state:
                st.session_state["_dismissed_nudges"] = set()
            st.session_state["_dismissed_nudges"].add(nudge["id"])
            st.rerun()


def render_spatial_canvas():
    """Render the single-page spatial canvas layout."""
    # Job statement at top
    _job_section()

    # Pains (left) and Gains (right)
    pain_col, gain_col = st.columns(2, gap="large")

    cfg = get_backend_config()

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
            ideal_min=cfg["min_pain_points"],
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
            ideal_min=cfg["min_gain_points"],
        )

    # Proactive nudges
    job = st.session_state.get("job_description", "")
    pains = st.session_state.get("pain_points", [])
    gains = st.session_state.get("gain_points", [])
    nudges = _compute_nudges(job, pains, gains)
    if nudges:
        _render_nudge_cards(nudges)

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
            if st.button(back_label, key=f"guided_back_{back_step}", width='stretch'):
                st.session_state.step = back_step
                st.rerun()
    with c2:
        if next_step is not None:
            if st.button(next_label, key=f"guided_next_{next_step}", width='stretch',
                          type="primary", disabled=next_disabled):
                st.session_state.step = next_step
                st.rerun()


def _guided_job_step():
    """Guided mode: Job Description step."""
    st.markdown("### Define the Core Job")
    tip = _coaching_tip_cached("job")
    if tip:
        _render_coaching_tip(tip)

    _ver = st.session_state.get("_job_input_ver", 0)
    _widget_key = f"guided_job_input_v{_ver}"
    if _widget_key not in st.session_state:
        st.session_state[_widget_key] = st.session_state.job_description
    job = st.text_area(
        "Describe the task, goal, or objective:",
        height=160,
        placeholder="Example: I need to track my team's monthly expenses and generate financial reports efficiently...",
        key=_widget_key,
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

    _sug_key = "_suggestions_job_guided"
    if st.button("Get AI suggestions", key="guided_job_suggest"):
        with st.spinner("Thinking..."):
            suggestions = call_api("/api/suggestions/job-statement", "POST", {
                "current_description": job,
                "count": 3,
            })
            if "error" not in suggestions:
                suggestions_list = suggestions.get("suggestions_list", [])
                if suggestions_list:
                    st.session_state[_sug_key] = suggestions_list
                    st.rerun()
                else:
                    st.info(suggestions.get("suggestions", "No suggestions."))
            else:
                st.warning(suggestions["error"])

    # Render suggestion cards outside button callback (Streamlit pattern)
    if _sug_key in st.session_state:
        _render_job_suggestion_cards(st.session_state[_sug_key], prefix="guided")
        if st.button("Dismiss suggestions", key="dismiss_job_suggestions_guided"):
            del st.session_state[_sug_key]
            st.rerun()

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
                    save = c1.form_submit_button("Save", width='stretch')
                    cancel = c2.form_submit_button("Cancel", width='stretch')
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
                                  width='stretch'):
                        st.session_state[editing_key] = i
                        st.rerun()
                with c2:
                    if st.button("Delete", key=f"guided_del_{item_type}_btn_{i}",
                                  width='stretch'):
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
        submitted = st.form_submit_button(f"Add {item_label.title()}", width='stretch')

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

    if st.button("Start a new canvas", width='stretch'):
        reset_session_state(preserve_theme=True)
        st.rerun()


def render_guided_mode():
    """Render the step-by-step guided wizard."""
    # Ensure step is at least 1 for guided mode
    if st.session_state.step < 1:
        st.session_state.step = 1

    _render_guided_progress()

    cfg = get_backend_config()

    if st.session_state.step == 1:
        _guided_job_step()
    elif st.session_state.step == 2:
        st.markdown("### Identify Pain Points")
        _guided_items_step(
            collection_key="pain_points", item_type="pain", item_label="pain point",
            validate_endpoint="/api/validate/pain-points", payload_key="pain_points",
            validate_fn=_validate_pains_cached, validated_key="pains_validated",
            editing_key="editing_pain_index", min_required=cfg["min_pain_points"],
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
            editing_key="editing_gain_index", min_required=cfg["min_gain_points"],
            tip_step="gains", suggest_step="gains",
            back_step=2, next_step=4,
            back_label="Back to Pains", next_label="Continue to Review",
        )
    elif st.session_state.step == 4:
        _guided_review_step()


# ═══════════════════════════════════════════════════════════════════════════
# Export Bar
# ═══════════════════════════════════════════════════════════════════════════

def _generate_export(endpoint: str, job: str, pains: list, gains: list,
                     session_key: str) -> bool:
    """Generate an export document via the backend. Returns True on success."""
    try:
        response = get_http_client().post(
            f"{API_BASE_URL}{endpoint}",
            headers=get_api_headers(),
            json={
                "job_description": job,
                "pain_points": pains,
                "gain_points": gains,
                "title": "Value Proposition Canvas",
            },
        )
        if response.status_code == 200:
            st.session_state[session_key] = response.content
            return True
        else:
            st.error("Failed to generate. Ensure all sections pass validation.")
    except Exception as e:
        st.error(f"Connection error: {e}")
    return False


def render_export_bar():
    """Render the export/download section with Word, PDF, CSV, JSON, and Share."""
    pains = st.session_state.get("pain_points", [])
    gains = st.session_state.get("gain_points", [])
    job = st.session_state.get("job_description", "")

    cfg = get_backend_config()
    ideal_total = cfg["min_pain_points"] + cfg["min_gain_points"]
    label, label_class = _quality_level_label(len(pains), len(gains), job, ideal_total)

    st.markdown(f'<div class="quality-label {label_class}" style="margin-bottom: 0.75rem;">Quality: {label}</div>', unsafe_allow_html=True)

    if not job.strip() and not pains and not gains:
        st.caption("Add content to enable export.")
        return

    # ── Document Exports (2x2 grid) ──
    st.markdown("**Export Documents**")
    row1_c1, row1_c2 = st.columns(2)
    row2_c1, row2_c2 = st.columns(2)

    # Word export
    with row1_c1:
        if st.button(f"Generate Word", key="generate_doc_btn", type="primary",
                      width='stretch'):
            with st.spinner("Generating Word..."):
                _generate_export("/api/generate-document", job, pains, gains, "_doc_data")
        if st.session_state.get("_doc_data"):
            st.download_button(
                label="Download .docx",
                data=st.session_state["_doc_data"],
                file_name="Value_Proposition_Canvas.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                width='stretch',
            )

    # PDF export
    with row1_c2:
        if st.button("Generate PDF", key="generate_pdf_btn", width='stretch'):
            with st.spinner("Generating PDF..."):
                _generate_export("/api/generate-pdf", job, pains, gains, "_pdf_data")
        if st.session_state.get("_pdf_data"):
            st.download_button(
                label="Download .pdf",
                data=st.session_state["_pdf_data"],
                file_name="Value_Proposition_Canvas.pdf",
                mime="application/pdf",
                width='stretch',
            )

    # CSV export
    with row2_c1:
        if st.button("Generate CSV", key="generate_csv_btn", width='stretch'):
            with st.spinner("Generating CSV..."):
                _generate_export("/api/generate-csv", job, pains, gains, "_csv_data")
        if st.session_state.get("_csv_data"):
            st.download_button(
                label="Download .csv",
                data=st.session_state["_csv_data"],
                file_name="Value_Proposition_Canvas.csv",
                mime="text/csv",
                width='stretch',
            )

    # JSON export
    with row2_c2:
        if st.button("Export JSON", key="export_json_btn", width='stretch'):
            with st.spinner("Exporting JSON..."):
                try:
                    token = st.session_state.get("auth_token", "")
                    api = CanvasAPIClient(API_BASE_URL, token)
                    resp = httpx.post(
                        f"{API_BASE_URL}/api/canvases/export/json",
                        headers=get_api_headers(),
                        timeout=10.0,
                    )
                    if resp.status_code == 200:
                        st.session_state["_json_data"] = resp.text
                    else:
                        st.error("Failed to export JSON.")
                except Exception as e:
                    st.error(f"Connection error: {e}")
        if st.session_state.get("_json_data"):
            st.download_button(
                label="Download .json",
                data=st.session_state["_json_data"],
                file_name="Value_Proposition_Canvas.json",
                mime="application/json",
                width='stretch',
            )

    # ── JSON Import ──
    st.markdown("---")
    st.markdown("**Import Canvas**")
    uploaded = st.file_uploader("Import from JSON file", type=["json"], key="json_import_file")
    if uploaded is not None:
        try:
            imported_data = json.loads(uploaded.read().decode("utf-8"))
            if st.button("Import this canvas", key="import_json_btn", type="primary"):
                with st.spinner("Importing..."):
                    resp = httpx.post(
                        f"{API_BASE_URL}/api/canvases/import/json",
                        headers=get_api_headers(),
                        json=imported_data,
                        timeout=10.0,
                    )
                    if resp.status_code == 201:
                        st.toast("Canvas imported successfully!")
                        # Reload from DB
                        st.session_state.pop("db_canvas_loaded", None)
                        st.rerun()
                    else:
                        detail = resp.json().get("detail", "Import failed.")
                        st.error(f"Import failed: {detail}")
        except json.JSONDecodeError:
            st.error("Invalid JSON file.")
        except Exception as e:
            st.error(f"Error reading file: {e}")

    # ── Share Link ──
    st.markdown("---")
    st.markdown("**Share Canvas**")
    share_c1, share_c2 = st.columns(2)
    with share_c1:
        share_pw = st.text_input("Password (optional)", type="password", key="share_pw_input_create")
    with share_c2:
        share_expiry = st.selectbox("Expires in", ["Never", "1 hour", "24 hours", "7 days", "30 days"],
                                     key="share_expiry_select")
    expiry_map = {"Never": None, "1 hour": 1, "24 hours": 24, "7 days": 168, "30 days": 720}

    if st.button("Create Share Link", key="create_share_btn", width='stretch'):
        # Need the canvas ID from the current canvas
        try:
            canvas_resp = httpx.get(
                f"{API_BASE_URL}/api/canvases/current",
                headers=get_api_headers(),
                timeout=10.0,
            )
            if canvas_resp.status_code == 200:
                canvas_id = canvas_resp.json()["id"]
                share_payload = {}
                if share_pw:
                    share_payload["password"] = share_pw
                hours = expiry_map.get(share_expiry)
                if hours:
                    share_payload["expires_in_hours"] = hours

                share_resp = httpx.post(
                    f"{API_BASE_URL}/api/canvases/{canvas_id}/share",
                    headers=get_api_headers(),
                    json=share_payload,
                    timeout=10.0,
                )
                if share_resp.status_code == 201:
                    token_val = share_resp.json()["share_token"]
                    # Build the frontend URL with share query param
                    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:8501")
                    share_url = f"{frontend_url}/?share={token_val}"
                    st.session_state["_share_url"] = share_url
                else:
                    st.error("Failed to create share link.")
            else:
                st.error("No canvas found to share.")
        except Exception as e:
            st.error(f"Connection error: {e}")

    if st.session_state.get("_share_url"):
        st.code(st.session_state["_share_url"], language=None)
        st.caption("Anyone with this link can view your canvas (read-only).")

    # ── New Canvas ──
    st.markdown("---")
    if st.button("Start new canvas", key="new_canvas_btn", width='stretch'):
        for k in ("_doc_data", "_pdf_data", "_csv_data", "_json_data", "_share_url"):
            st.session_state.pop(k, None)
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
        st.session_state["_job_input_ver"] = st.session_state.get("_job_input_ver", 0) + 1
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
    cfg = get_backend_config()
    new_pw = st.text_input("New Password", type="password", key="cp_new",
                            help=cfg["password_rules_text"])
    _render_password_strength(new_pw)
    confirm = st.text_input("Confirm New Password", type="password", key="cp_confirm")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Change", type="primary", width='stretch', key="cp_submit"):
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
        if st.button("Cancel", width='stretch', key="cp_cancel"):
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
        cfg = get_backend_config()
        new_pw = st.text_input("New Password", type="password",
                                help=cfg["password_rules_text"])
        confirm = st.text_input("Confirm New Password", type="password")
        submitted = st.form_submit_button("Change Password", width='stretch')

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
    if st.button("Sign Out", width='stretch'):
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


def _render_shared_canvas():
    """Render a read-only shared canvas view (no auth required)."""
    token = st.query_params.get("share", "")
    if not token:
        return False

    try:
        url = f"{API_BASE_URL}/api/shared/{token}"
        stored_pw = st.session_state.get("_share_password")

        if stored_pw:
            # Password already entered — send via POST body (not query string)
            resp = httpx.post(url, json={"password": stored_pw}, timeout=10.0)
        else:
            # Try without password first (GET)
            resp = httpx.get(url, timeout=10.0)

        if resp.status_code == 401:
            # Password required
            st.markdown("""
            <div class="auth-container">
                <h1>Password Required</h1>
                <p>This shared canvas is password-protected.</p>
            </div>
            """, unsafe_allow_html=True)
            pw = st.text_input("Enter password", type="password", key="share_pw_input")
            if st.button("View Canvas", type="primary"):
                st.session_state["_share_password"] = pw
                st.rerun()
            return True

        if resp.status_code == 410:
            st.error("This share link has expired or been revoked.")
            return True

        if resp.status_code != 200:
            st.error("Unable to load shared canvas.")
            return True

        data = resp.json()
    except Exception as e:
        st.error(f"Could not connect to the server: {e}")
        return True

    # Render read-only view
    st.markdown(f"""
    <div class="app-header">
        <h1>{html.escape(data.get('title', 'Shared Canvas'))}</h1>
        <p>Shared read-only view</p>
    </div>
    """, unsafe_allow_html=True)

    # Job description
    st.markdown("### Job Description")
    st.markdown(f"> {html.escape(data.get('job_description', ''))}")

    pain_col, gain_col = st.columns(2, gap="large")
    with pain_col:
        pains = data.get("pain_points", [])
        st.markdown(f"""
        <div class="col-header pain">
            <div class="col-header-icon pain">P</div>
            <div class="col-header-title">Pain Points</div>
            <div class="col-header-count">{len(pains)} items</div>
        </div>
        """, unsafe_allow_html=True)
        for i, p in enumerate(pains, 1):
            st.markdown(f"""
            <div class="item-card">
                <div class="item-badge pain">{i}</div>
                <div class="item-text">{html.escape(p)}</div>
            </div>
            """, unsafe_allow_html=True)

    with gain_col:
        gains = data.get("gain_points", [])
        st.markdown(f"""
        <div class="col-header gain">
            <div class="col-header-icon gain">G</div>
            <div class="col-header-title">Gain Points</div>
            <div class="col-header-count">{len(gains)} items</div>
        </div>
        """, unsafe_allow_html=True)
        for i, g in enumerate(gains, 1):
            st.markdown(f"""
            <div class="item-card">
                <div class="item-badge gain">{i}</div>
                <div class="item-text">{html.escape(g)}</div>
            </div>
            """, unsafe_allow_html=True)

    return True


def main():
    init_session_state()

    # Shared canvas viewer (before auth gate)
    if st.query_params.get("share"):
        if _render_shared_canvas():
            return

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
        if st.button("Change Password", key="change_pw_btn", width='stretch'):
            _change_password_dialog()
        if st.button("Sign Out", key="logout_btn", width='stretch'):
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
