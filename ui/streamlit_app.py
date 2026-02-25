"""
Streamlit UI for Value Proposition Canvas Coaching Application.
A modern, step-by-step wizard that guides users through creating a high-quality canvas.
"""

import os
import html
import json
import hashlib
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
import httpx
from typing import Optional
import time
from textwrap import dedent
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============ Performance: Debounce Configuration ============
VALIDATION_DEBOUNCE_MS = 500  # Wait 500ms after typing stops before validating

# ============ Session Persistence Configuration ============
SESSION_FILE = Path.home() / ".value_proposition_canvas_session.json"
AUTO_SAVE_ENABLED = True

# ============ Theme Configuration ============
DEFAULT_THEME = "Light"
THEME_ICONS = {
    "Light": "☀️",
    "Dark": "🌙",
    "Sepia": "📜",
    "Ocean": "🌊",
}
THEME_CONFIGS = {
    "Light": {
        "color_bg_primary": "#faf8f5",
        "color_bg_card": "#ffffff",
        "color_bg_elevated": "#ffffff",
        "color_text_primary": "#1a1a2e",
        "color_text_secondary": "#5a5a6e",
        "color_text_muted": "#8a8a9e",
        "color_accent_gold": "#c9a227",
        "color_accent_gold_light": "#f5ead6",
        "color_pain": "#c45c3e",
        "color_pain_light": "#fdeae5",
        "color_gain": "#2d6a6a",
        "color_gain_light": "#e5f0f0",
        "color_success": "#4a7c59",
        "color_success_light": "#e8f0eb",
        "color_warning": "#b8860b",
        "color_warning_light": "#fdf6e3",
        "color_error": "#a63d40",
        "color_error_light": "#fce8e8",
        "color_border": "#e8e4df",
        "color_border_light": "#f3f0ec",
        "header_gradient": "linear-gradient(145deg, #1a1a2e 0%, #2d2d44 50%, #1a1a2e 100%)",
        "header_overlay_a": "rgba(201, 162, 39, 0.15)",
        "header_overlay_b": "rgba(45, 106, 106, 0.12)",
        "header_text": "#ffffff",
        "surface_tint": "#f8f6f2",
        "success_tint": "#d8e8de",
        "warning_tint": "#f9f1dc",
        "primary_hover": "#2d2d44",
        "restore_title": "#7a5c0a",
        "restore_description": "#8a6b1a",
        "success_text": "#3a6348",
        "noise_opacity": "0.015",
        "progress_active": "#1a1a2e",
        "progress_active_text": "#ffffff",
        "progress_active_glow": "rgba(26, 26, 46, 0.1)",
        "progress_complete": "#4a7c59",
        "progress_complete_text": "#ffffff",
        "progress_upcoming_bg": "#ffffff",
        "progress_upcoming_border": "#e8e4df",
        "progress_upcoming_text": "#8a8a9e",
        "font_display": "'Fraunces', Georgia, serif",
        "font_body": "'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif",
        "texture_tint": "rgba(201, 162, 39, 0.08)",
        "motif_color": "rgba(201, 162, 39, 0.35)",
        "rail_gradient": "linear-gradient(160deg, #ffffff 0%, #f8f4ec 100%)",
        "motion_distance": "10px",
    },
    "Dark": {
        "color_bg_primary": "#0f141a",
        "color_bg_card": "#1b232d",
        "color_bg_elevated": "#242e3a",
        "color_text_primary": "#edf3fb",
        "color_text_secondary": "#c5d2e3",
        "color_text_muted": "#9fb0c5",
        "color_accent_gold": "#f1c56d",
        "color_accent_gold_light": "#3d3220",
        "color_pain": "#ff8a7a",
        "color_pain_light": "#3a2324",
        "color_gain": "#5dc6c6",
        "color_gain_light": "#1f3338",
        "color_success": "#6bc08a",
        "color_success_light": "#1f362a",
        "color_warning": "#f6c85f",
        "color_warning_light": "#3c321e",
        "color_error": "#ef6c7f",
        "color_error_light": "#3b2229",
        "color_border": "#324154",
        "color_border_light": "#283544",
        "header_gradient": "linear-gradient(145deg, #1d2633 0%, #18202a 50%, #101722 100%)",
        "header_overlay_a": "rgba(241, 197, 109, 0.18)",
        "header_overlay_b": "rgba(93, 198, 198, 0.16)",
        "header_text": "#f8fbff",
        "surface_tint": "#222c37",
        "success_tint": "#264433",
        "warning_tint": "#4b3b22",
        "primary_hover": "#304055",
        "restore_title": "#f6d072",
        "restore_description": "#ebc767",
        "success_text": "#c5e9d5",
        "noise_opacity": "0.035",
        "progress_active": "#f1c56d",
        "progress_active_text": "#0f141a",
        "progress_active_glow": "rgba(241, 197, 109, 0.22)",
        "progress_complete": "#6bc08a",
        "progress_complete_text": "#0f141a",
        "progress_upcoming_bg": "#1b232d",
        "progress_upcoming_border": "#324154",
        "progress_upcoming_text": "#9fb0c5",
        "font_display": "'Bricolage Grotesque', 'Segoe UI', sans-serif",
        "font_body": "'Manrope', -apple-system, BlinkMacSystemFont, sans-serif",
        "texture_tint": "rgba(93, 198, 198, 0.09)",
        "motif_color": "rgba(241, 197, 109, 0.5)",
        "rail_gradient": "linear-gradient(160deg, #202a36 0%, #18212a 100%)",
        "motion_distance": "8px",
    },
    "Sepia": {
        "color_bg_primary": "#f4ece0",
        "color_bg_card": "#fff9f1",
        "color_bg_elevated": "#fffdf8",
        "color_text_primary": "#3b2c22",
        "color_text_secondary": "#6f5644",
        "color_text_muted": "#947a67",
        "color_accent_gold": "#b7863f",
        "color_accent_gold_light": "#f2dfc2",
        "color_pain": "#b55a3d",
        "color_pain_light": "#f6dfd4",
        "color_gain": "#4f6f5b",
        "color_gain_light": "#dce8dd",
        "color_success": "#5a7a4e",
        "color_success_light": "#e4eddc",
        "color_warning": "#aa7a2d",
        "color_warning_light": "#f4e8d1",
        "color_error": "#9f4633",
        "color_error_light": "#f7ddd7",
        "color_border": "#dbc8b1",
        "color_border_light": "#e8d8c5",
        "header_gradient": "linear-gradient(145deg, #4a3a2e 0%, #5d4737 50%, #4a3a2e 100%)",
        "header_overlay_a": "rgba(230, 190, 130, 0.16)",
        "header_overlay_b": "rgba(120, 150, 120, 0.13)",
        "header_text": "#fff9f1",
        "surface_tint": "#f3e9da",
        "success_tint": "#d4e3cc",
        "warning_tint": "#efe1c4",
        "primary_hover": "#6a503f",
        "restore_title": "#896126",
        "restore_description": "#9b7340",
        "success_text": "#4b6b42",
        "noise_opacity": "0.02",
        "progress_active": "#6a503f",
        "progress_active_text": "#fff9f1",
        "progress_active_glow": "rgba(106, 80, 63, 0.18)",
        "progress_complete": "#5a7a4e",
        "progress_complete_text": "#fff9f1",
        "progress_upcoming_bg": "#fff9f1",
        "progress_upcoming_border": "#dbc8b1",
        "progress_upcoming_text": "#947a67",
        "font_display": "'Cormorant Garamond', Georgia, serif",
        "font_body": "'Instrument Sans', -apple-system, BlinkMacSystemFont, sans-serif",
        "texture_tint": "rgba(151, 115, 63, 0.09)",
        "motif_color": "rgba(183, 134, 63, 0.42)",
        "rail_gradient": "linear-gradient(160deg, #fff8ef 0%, #f4e8d8 100%)",
        "motion_distance": "11px",
    },
    "Ocean": {
        "color_bg_primary": "#edf6f7",
        "color_bg_card": "#ffffff",
        "color_bg_elevated": "#f7fbfc",
        "color_text_primary": "#102c3a",
        "color_text_secondary": "#385766",
        "color_text_muted": "#6b8795",
        "color_accent_gold": "#3c9db3",
        "color_accent_gold_light": "#d9eef2",
        "color_pain": "#cf6b4d",
        "color_pain_light": "#f8e2da",
        "color_gain": "#1b7f83",
        "color_gain_light": "#d9f0f1",
        "color_success": "#2f8660",
        "color_success_light": "#dff0e8",
        "color_warning": "#b7862f",
        "color_warning_light": "#f6ecd9",
        "color_error": "#b14b53",
        "color_error_light": "#f9e0e2",
        "color_border": "#d5e6eb",
        "color_border_light": "#e4f0f3",
        "header_gradient": "linear-gradient(145deg, #123447 0%, #1b4d63 50%, #123447 100%)",
        "header_overlay_a": "rgba(60, 157, 179, 0.2)",
        "header_overlay_b": "rgba(27, 127, 131, 0.16)",
        "header_text": "#f3fcff",
        "surface_tint": "#edf5f7",
        "success_tint": "#cde8db",
        "warning_tint": "#f1e4c8",
        "primary_hover": "#22566e",
        "restore_title": "#7b5c18",
        "restore_description": "#8d6e2b",
        "success_text": "#24563f",
        "noise_opacity": "0.02",
        "progress_active": "#123447",
        "progress_active_text": "#f3fcff",
        "progress_active_glow": "rgba(18, 52, 71, 0.2)",
        "progress_complete": "#2f8660",
        "progress_complete_text": "#f3fcff",
        "progress_upcoming_bg": "#ffffff",
        "progress_upcoming_border": "#d5e6eb",
        "progress_upcoming_text": "#6b8795",
        "font_display": "'Sora', 'Segoe UI', sans-serif",
        "font_body": "'Nunito Sans', -apple-system, BlinkMacSystemFont, sans-serif",
        "texture_tint": "rgba(60, 157, 179, 0.1)",
        "motif_color": "rgba(27, 127, 131, 0.4)",
        "rail_gradient": "linear-gradient(160deg, #ffffff 0%, #e9f5f7 100%)",
        "motion_distance": "9px",
    },
}

STEP_PURPOSES = [
    ("Welcome", "Set context and align on what you are solving."),
    ("Job Description", "Define one precise work objective."),
    ("Pain Points", "Capture friction and failure risk."),
    ("Gain Points", "Specify outcomes worth pursuing."),
    ("Review", "Publish a polished reflection canvas."),
]

# ============ Page Configuration ============
st.set_page_config(
    page_title="Work Process Reflection Canvas",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============ Custom CSS ============
st.markdown("""
<style>
    /* ═══════════════════════════════════════════════════════════════════════════
       VALUE PROPOSITION CANVAS - EDITORIAL LUXURY DESIGN SYSTEM
       A sophisticated, magazine-inspired aesthetic with warm tones
       ═══════════════════════════════════════════════════════════════════════════ */

    /* Import Distinctive Typography */
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;0,9..144,500;0,9..144,600;0,9..144,700;1,9..144,400&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,400&family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,600;12..96,700&family=Manrope:wght@400;500;600;700&family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,500&family=Instrument+Sans:wght@400;500;600;700&family=Sora:wght@400;500;600;700&family=Nunito+Sans:wght@400;600;700&display=swap');

    /* CSS Custom Properties - Refined Color Palette */
    :root {
        --color-bg-primary: #faf8f5;
        --color-bg-card: #ffffff;
        --color-bg-elevated: #ffffff;
        --color-text-primary: #1a1a2e;
        --color-text-secondary: #5a5a6e;
        --color-text-muted: #8a8a9e;
        --color-accent-gold: #c9a227;
        --color-accent-gold-light: #f5ead6;
        --color-pain: #c45c3e;
        --color-pain-light: #fdeae5;
        --color-gain: #2d6a6a;
        --color-gain-light: #e5f0f0;
        --color-success: #4a7c59;
        --color-success-light: #e8f0eb;
        --color-warning: #b8860b;
        --color-warning-light: #fdf6e3;
        --color-error: #a63d40;
        --color-error-light: #fce8e8;
        --color-border: #e8e4df;
        --color-border-light: #f3f0ec;
        --shadow-sm: 0 1px 2px rgba(26, 26, 46, 0.04);
        --shadow-md: 0 4px 12px rgba(26, 26, 46, 0.08);
        --shadow-lg: 0 12px 32px rgba(26, 26, 46, 0.12);
        --shadow-glow: 0 0 40px rgba(201, 162, 39, 0.15);
        --radius-sm: 8px;
        --radius-md: 12px;
        --radius-lg: 20px;
        --radius-full: 999px;
        --transition-fast: 0.15s cubic-bezier(0.4, 0, 0.2, 1);
        --transition-smooth: 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        --transition-bounce: 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
        --font-display: 'Fraunces', Georgia, serif;
        --font-body: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        --texture-tint: rgba(201, 162, 39, 0.08);
        --motif-color: rgba(201, 162, 39, 0.35);
        --rail-gradient: linear-gradient(160deg, #ffffff 0%, #f8f4ec 100%);
        --motion-distance: 10px;
        --font-scale: 1;
    }

    /* Global App Styling */
    .stApp {
        font-family: var(--font-body);
        background: var(--color-bg-primary);
        color: var(--color-text-primary);
        font-size: calc(1rem * var(--font-scale));
    }

    /* Subtle noise texture overlay */
    .stApp::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        pointer-events: none;
        opacity: 0.015;
        background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
        mix-blend-mode: soft-light;
        filter: saturate(0.9) hue-rotate(6deg);
        z-index: 9999;
    }

    /* Main container styling */
    .main .block-container {
        padding-top: 2.5rem;
        padding-bottom: 3rem;
        max-width: 880px;
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       HEADER - Elegant Editorial Hero
       ═══════════════════════════════════════════════════════════════════════════ */
    .main-header {
        text-align: center;
        padding: 3rem 2rem;
        background: linear-gradient(145deg, #1a1a2e 0%, #2d2d44 50%, #1a1a2e 100%);
        border-radius: var(--radius-lg);
        margin-bottom: 2.5rem;
        color: #ffffff;
        position: relative;
        overflow: hidden;
        box-shadow: var(--shadow-lg), inset 0 1px 0 rgba(255,255,255,0.05);
    }

    .main-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background:
            radial-gradient(ellipse at 20% 30%, rgba(201, 162, 39, 0.15) 0%, transparent 50%),
            radial-gradient(ellipse at 80% 70%, rgba(45, 106, 106, 0.12) 0%, transparent 50%);
        pointer-events: none;
    }

    .main-header::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, var(--color-accent-gold), transparent);
        opacity: 0.4;
    }

    .main-header .hero-kicker {
        font-family: var(--font-body);
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        border: 1px solid rgba(255, 255, 255, 0.26);
        padding: 0.35rem 0.75rem;
        border-radius: var(--radius-full);
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.09em;
        margin-bottom: 0.9rem;
        position: relative;
        z-index: 1;
        background: rgba(255, 255, 255, 0.08);
    }

    .hero-signature {
        margin-top: 1.1rem;
        position: relative;
        z-index: 1;
    }

    .hero-signature-line {
        height: 2px;
        width: 100px;
        margin: 0 auto 0.45rem;
        background: linear-gradient(90deg, transparent, var(--motif-color), transparent);
    }

    .hero-signature-copy {
        font-size: 0.8rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        opacity: 0.8;
    }

    .main-header h1 {
        font-family: var(--font-display);
        font-size: 2.75rem;
        font-weight: 600;
        letter-spacing: -0.02em;
        margin-bottom: 0.75rem;
        position: relative;
        z-index: 1;
        line-height: 1.2;
    }

    .main-header h1::before {
        content: '';
        display: block;
        width: 60px;
        height: 2px;
        background: var(--color-accent-gold);
        margin: 0 auto 1.25rem;
        opacity: 0.8;
    }

    .main-header p {
        font-size: 1.05rem;
        opacity: 0.85;
        font-weight: 400;
        letter-spacing: 0.01em;
        position: relative;
        z-index: 1;
    }

    .theme-switcher {
        background: var(--color-bg-card);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-md);
        padding: 0.75rem 1rem 0.25rem;
        margin-bottom: 1rem;
        box-shadow: var(--shadow-sm);
    }

    .theme-switcher-label {
        margin-bottom: 0.35rem;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--color-text-secondary);
    }

    .theme-switcher-help {
        margin-top: 0.15rem;
        font-size: 0.78rem;
        color: var(--color-text-muted);
    }

    .preference-row {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0.25rem;
        margin-top: 0.5rem;
    }

    .design-grid {
        display: grid;
        grid-template-columns: minmax(0, 2.05fr) minmax(240px, 1fr);
        gap: 1.25rem;
        align-items: start;
    }

    .design-main {
        min-width: 0;
    }

    .design-rail {
        background: var(--rail-gradient);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-md);
        padding: 0.95rem;
        position: sticky;
        top: 1rem;
        box-shadow: var(--shadow-sm);
    }

    .rail-title {
        font-size: 0.72rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--color-text-secondary);
        margin-bottom: 0.45rem;
        font-weight: 700;
    }

    .rail-copy {
        color: var(--color-text-secondary);
        font-size: 0.86rem;
        line-height: 1.45;
        margin-bottom: 0.7rem;
    }

    .rail-list {
        margin: 0;
        padding-left: 1rem;
        color: var(--color-text-secondary);
        font-size: 0.84rem;
        line-height: 1.45;
    }

    .rail-list li {
        margin-bottom: 0.3rem;
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       PROGRESS INDICATOR - Refined Step Navigation
       ═══════════════════════════════════════════════════════════════════════════ */
    .progress-bar-container {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        padding: 0 0.5rem;
        margin: 2rem 0 2.5rem;
    }

    .progress-step-wrapper {
        display: flex;
        align-items: center;
        flex: 1;
    }

    .progress-step-wrapper:last-child {
        flex: 0;
    }

    .progress-step-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        min-width: 72px;
    }

    .progress-indicator {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        font-size: 0.875rem;
        font-family: var(--font-body);
        z-index: 2;
        transition: all var(--transition-smooth);
        border: 2px solid transparent;
        background: var(--color-bg-card);
        color: var(--color-text-muted);
        box-shadow: var(--shadow-sm);
    }

    .progress-label {
        margin-top: 0.625rem;
        font-size: 0.6875rem;
        text-align: center;
        max-width: 80px;
        font-weight: 500;
        letter-spacing: 0.02em;
        text-transform: uppercase;
        transition: color var(--transition-fast);
    }

    .progress-line {
        flex: 1;
        height: 2px;
        margin: 0 0.375rem;
        margin-bottom: 1.75rem;
        border-radius: 1px;
        transition: background var(--transition-smooth);
        background: var(--color-border);
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       COACHING TIP - Elegant Callout Box
       ═══════════════════════════════════════════════════════════════════════════ */
    .coaching-tip {
        background: linear-gradient(135deg, var(--color-accent-gold-light) 0%, #faf5eb 100%);
        border-radius: var(--radius-md);
        padding: 1.375rem 1.5rem;
        margin: 1.25rem 0;
        border-left: 3px solid var(--color-accent-gold);
        position: relative;
        box-shadow: var(--shadow-sm);
    }

    .coaching-tip::before {
        content: '';
        position: absolute;
        top: 0;
        right: 0;
        width: 80px;
        height: 80px;
        background: radial-gradient(circle at top right, rgba(201, 162, 39, 0.08) 0%, transparent 70%);
        pointer-events: none;
    }

    .coaching-tip h4 {
        font-family: var(--font-display);
        color: var(--color-accent-gold);
        margin-bottom: 0.625rem;
        font-size: 0.9375rem;
        font-weight: 600;
        letter-spacing: 0.01em;
    }

    .coaching-tip p {
        color: var(--color-text-primary);
        font-size: 0.9375rem;
        line-height: 1.65;
        margin: 0;
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       VALIDATION MESSAGES - Refined Feedback States
       ═══════════════════════════════════════════════════════════════════════════ */
    .validation-success {
        background: var(--color-success-light);
        border: 1px solid rgba(74, 124, 89, 0.25);
        border-radius: var(--radius-sm);
        padding: 0.875rem 1.125rem;
        color: var(--color-success);
        font-size: 0.875rem;
        margin: 0.625rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.5);
    }

    .validation-success::before {
        content: '✓';
        font-weight: 600;
        font-size: 1rem;
    }

    .validation-warning {
        background: var(--color-warning-light);
        border: 1px solid rgba(184, 134, 11, 0.25);
        border-radius: var(--radius-sm);
        padding: 0.875rem 1.125rem;
        color: var(--color-warning);
        font-size: 0.875rem;
        margin: 0.625rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.5);
    }

    .validation-warning::before {
        content: '!';
        font-weight: 700;
        font-size: 0.875rem;
        width: 18px;
        height: 18px;
        border-radius: 50%;
        background: var(--color-warning);
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }

    .validation-error {
        background: var(--color-error-light);
        border: 1px solid rgba(166, 61, 64, 0.25);
        border-radius: var(--radius-sm);
        padding: 0.875rem 1.125rem;
        color: var(--color-error);
        font-size: 0.875rem;
        margin: 0.625rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.5);
    }

    .validation-error::before {
        content: '✕';
        font-weight: 600;
        font-size: 0.875rem;
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       QUALITY SCORE - Premium Badge
       ═══════════════════════════════════════════════════════════════════════════ */
    .quality-score {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.625rem 1.125rem;
        border-radius: var(--radius-full);
        font-weight: 600;
        font-size: 0.875rem;
        letter-spacing: 0.01em;
        box-shadow: var(--shadow-sm);
    }

    .quality-score.high {
        background: var(--color-success-light);
        color: var(--color-success);
        border: 1px solid rgba(74, 124, 89, 0.2);
    }

    .quality-score.medium {
        background: var(--color-warning-light);
        color: var(--color-warning);
        border: 1px solid rgba(184, 134, 11, 0.2);
    }

    .quality-score.low {
        background: var(--color-error-light);
        color: var(--color-error);
        border: 1px solid rgba(166, 61, 64, 0.2);
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       ITEM CARDS - Refined Content Cards
       ═══════════════════════════════════════════════════════════════════════════ */
    .item-card {
        background: var(--color-bg-card);
        border-radius: var(--radius-sm);
        padding: 1rem 1.125rem;
        margin: 0.5rem 0;
        display: flex;
        align-items: flex-start;
        gap: 0.875rem;
        border: 1px solid var(--color-border-light);
        box-shadow: var(--shadow-sm);
        transition: all var(--transition-fast);
    }

    .item-card:hover {
        box-shadow: var(--shadow-md);
        border-color: var(--color-border);
        transform: translateY(-1px);
    }

    .item-number {
        width: 26px;
        height: 26px;
        border-radius: 6px;
        background: var(--color-text-primary);
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.75rem;
        font-weight: 600;
        flex-shrink: 0;
        font-family: var(--font-body);
        letter-spacing: 0.02em;
    }

    .item-number.pain {
        background: var(--color-pain);
    }

    .item-number.gain {
        background: var(--color-gain);
    }

    .item-text {
        flex: 1;
        font-size: 0.9375rem;
        color: var(--color-text-primary);
        line-height: 1.6;
    }

    .item-metadata {
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
        margin-top: 0.55rem;
    }

    .item-chip {
        font-size: 0.68rem;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        border: 1px solid var(--color-border);
        border-radius: var(--radius-full);
        padding: 0.18rem 0.45rem;
        color: var(--color-text-secondary);
        background: var(--color-bg-primary);
    }

    .item-chip.accent {
        border-color: var(--color-accent-gold);
        color: var(--color-text-primary);
        font-weight: 600;
        background: var(--color-accent-gold-light);
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       BUTTONS - Refined Interactive Elements
       ═══════════════════════════════════════════════════════════════════════════ */
    .stButton > button {
        border-radius: var(--radius-sm);
        font-weight: 500;
        font-family: var(--font-body);
        padding: 0.625rem 1.5rem;
        min-height: 44px;
        transition: all var(--transition-smooth);
        border: 1px solid transparent;
        letter-spacing: 0.01em;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-md);
    }

    .stButton > button:active {
        transform: translateY(0);
    }

    /* Primary button styling */
    .stButton > button[kind="primary"] {
        background: var(--color-text-primary);
        color: white;
        border-color: var(--color-text-primary);
    }

    .stButton > button[kind="primary"]:hover {
        background: #2d2d44;
        border-color: #2d2d44;
        box-shadow: var(--shadow-md), var(--shadow-glow);
    }

    /* Secondary button styling */
    .stButton > button:not([kind="primary"]) {
        background: var(--color-bg-card);
        color: var(--color-text-primary);
        border-color: var(--color-border);
    }

    .stButton > button:not([kind="primary"]):hover {
        background: var(--color-bg-primary);
        border-color: var(--color-text-secondary);
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       TEXT AREAS - Refined Input Fields
       ═══════════════════════════════════════════════════════════════════════════ */
    .stTextArea > div > div > textarea {
        border-radius: var(--radius-sm);
        border: 1px solid var(--color-border);
        font-family: var(--font-body);
        font-size: 0.9375rem;
        line-height: 1.6;
        padding: 0.875rem 1rem;
        background: var(--color-bg-card);
        color: var(--color-text-primary);
        transition: all var(--transition-fast);
    }

    .stTextArea > div > div > textarea:focus {
        border-color: var(--color-accent-gold);
        box-shadow: 0 0 0 3px rgba(201, 162, 39, 0.15);
        outline: none;
    }

    .stTextArea > div > div > textarea::placeholder {
        color: var(--color-text-muted);
    }

    .stTextInput > div > div > input {
        border-radius: var(--radius-sm);
        border: 1px solid var(--color-border);
        background: var(--color-bg-card);
        color: var(--color-text-primary);
        min-height: 44px;
    }

    .stTextInput > div > div > input:focus {
        border-color: var(--color-accent-gold);
        box-shadow: 0 0 0 3px var(--color-accent-gold-light);
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       SUMMARY SECTION - Elegant Content Blocks
       ═══════════════════════════════════════════════════════════════════════════ */
    .summary-section {
        background: linear-gradient(145deg, var(--color-bg-card) 0%, #f8f6f2 100%);
        border-radius: var(--radius-md);
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid var(--color-border-light);
        box-shadow: var(--shadow-sm);
        position: relative;
    }

    .summary-section::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 3px;
        background: linear-gradient(180deg, var(--color-accent-gold), var(--color-gain));
        border-radius: 3px 0 0 3px;
    }

    .summary-section h3 {
        font-family: var(--font-display);
        color: var(--color-text-primary);
        margin-bottom: 1rem;
        font-weight: 600;
        letter-spacing: -0.01em;
    }

    .summary-section p {
        color: var(--color-text-secondary);
        line-height: 1.7;
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       SUCCESS BANNER - Celebratory Completion
       ═══════════════════════════════════════════════════════════════════════════ */
    .success-banner {
        background: linear-gradient(145deg, var(--color-success-light) 0%, #d8e8de 100%);
        border-radius: var(--radius-md);
        padding: 2.5rem;
        text-align: center;
        margin: 2rem 0;
        position: relative;
        overflow: hidden;
        border: 1px solid rgba(74, 124, 89, 0.15);
    }

    .success-banner::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(74, 124, 89, 0.05) 0%, transparent 50%);
        pointer-events: none;
    }

    .success-banner h2 {
        font-family: var(--font-display);
        color: var(--color-success);
        margin-bottom: 0.5rem;
        font-weight: 600;
        letter-spacing: -0.01em;
        position: relative;
    }

    .success-banner p {
        color: #3a6348;
        font-size: 1rem;
        position: relative;
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       EMPTY STATE - Inviting Placeholder
       ═══════════════════════════════════════════════════════════════════════════ */
    .empty-state {
        background: linear-gradient(145deg, var(--color-bg-card) 0%, #f8f6f2 100%);
        border: 2px dashed var(--color-border);
        border-radius: var(--radius-md);
        padding: 2.5rem 2rem;
        text-align: center;
        margin: 1rem 0;
    }

    .empty-state-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
        opacity: 0.7;
    }

    .empty-state-title {
        color: var(--color-text-secondary);
        font-family: var(--font-display);
        font-size: 1.0625rem;
        font-weight: 500;
        margin-bottom: 0.5rem;
    }

    .empty-state-description {
        color: var(--color-text-muted);
        font-size: 0.875rem;
        line-height: 1.6;
    }

    .empty-state-hint {
        margin-top: 0.75rem;
        color: var(--color-text-secondary);
        font-size: 0.8125rem;
        font-weight: 500;
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       RESTORE BANNER - Session Recovery
       ═══════════════════════════════════════════════════════════════════════════ */
    .restore-banner {
        background: linear-gradient(145deg, var(--color-warning-light) 0%, #f9f1dc 100%);
        border: 1px solid rgba(184, 134, 11, 0.25);
        border-radius: var(--radius-md);
        padding: 1.25rem 1.5rem;
        margin-bottom: 1.5rem;
        position: relative;
    }

    .restore-banner::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 3px;
        background: var(--color-warning);
        border-radius: 3px 0 0 3px;
    }

    .restore-banner-title {
        color: var(--color-warning);
        font-family: var(--font-display);
        font-weight: 600;
        margin-bottom: 0.375rem;
        font-size: 1rem;
    }

    .restore-banner-description {
        color: var(--color-text-secondary);
        font-size: 0.875rem;
        line-height: 1.5;
    }

    .restore-banner-hint {
        margin-top: 0.5rem;
        font-size: 0.8125rem;
        color: var(--color-text-secondary);
    }

    .step-actions-bar {
        position: sticky;
        bottom: 0.5rem;
        z-index: 50;
        margin-top: 1rem;
        padding: 0.9rem;
        border-radius: var(--radius-md);
        background: var(--color-bg-elevated);
        border: 1px solid var(--color-border);
        backdrop-filter: blur(8px);
        box-shadow: var(--shadow-md);
    }

    .composer-hint {
        color: var(--color-text-muted);
        font-size: 0.78rem;
        margin-top: -0.15rem;
        margin-bottom: 0.45rem;
    }

    .milestone-card {
        border: 1px solid var(--color-border);
        border-radius: var(--radius-md);
        background: var(--color-bg-card);
        padding: 0.85rem 1rem;
        margin: 0.65rem 0 0.9rem;
        box-shadow: var(--shadow-sm);
    }

    .milestone-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 0.84rem;
        color: var(--color-text-secondary);
        margin-bottom: 0.35rem;
    }

    .milestone-title {
        font-weight: 700;
        color: var(--color-text-primary);
    }

    .milestone-purpose {
        font-size: 0.82rem;
        color: var(--color-text-secondary);
        line-height: 1.4;
    }

    .publish-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.9rem;
    }

    .publish-section {
        border: 1px solid var(--color-border);
        border-radius: var(--radius-md);
        background: var(--color-bg-card);
        padding: 0.85rem;
    }

    .step-actions-bar .stButton > button {
        width: 100%;
    }

    .item-action-group .stButton > button {
        padding: 0.5rem;
        min-height: 40px;
        min-width: 40px;
    }

    .item-edit-row {
        margin-top: 0.45rem;
    }

    .section-reveal {
        animation: sectionFadeUp 0.45s ease both;
    }

    .stagger-1 { animation-delay: 0.04s; }
    .stagger-2 { animation-delay: 0.09s; }
    .stagger-3 { animation-delay: 0.14s; }

    @keyframes sectionFadeUp {
        from {
            opacity: 0;
            transform: translateY(var(--motion-distance));
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       TYPOGRAPHY REFINEMENTS
       ═══════════════════════════════════════════════════════════════════════════ */
    h1, h2, h3 {
        font-family: var(--font-display);
        color: var(--color-text-primary);
        letter-spacing: -0.01em;
    }

    h2 {
        font-weight: 600;
        margin-bottom: 1rem;
    }

    h3 {
        font-weight: 500;
        color: var(--color-text-secondary);
    }

    h4 {
        font-family: var(--font-body);
        font-weight: 600;
        color: var(--color-text-primary);
        letter-spacing: 0.01em;
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       STREAMLIT OVERRIDES - Clean Up Default Styling
       ═══════════════════════════════════════════════════════════════════════════ */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Horizontal rule styling */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, var(--color-border), transparent);
        margin: 1.5rem 0;
    }

    /* Expander styling */
    .streamlit-expanderHeader {
        font-family: var(--font-body);
        font-weight: 500;
        color: var(--color-text-secondary);
    }

    /* Caption styling */
    .stCaption {
        color: var(--color-text-muted);
        font-size: 0.8125rem;
    }

    /* Info/warning boxes */
    .stAlert {
        border-radius: var(--radius-sm);
        border: 1px solid var(--color-border);
    }

    /* Spinner styling */
    .stSpinner > div {
        border-color: var(--color-accent-gold) transparent transparent transparent;
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       ACCESSIBILITY & FOCUS STATES
       ═══════════════════════════════════════════════════════════════════════════ */
    .stButton > button:focus {
        outline: 2px solid var(--color-accent-gold);
        outline-offset: 2px;
    }

    .stTextArea > div > div > textarea:focus {
        outline: none;
    }

    .stRadio [role="radiogroup"] label {
        min-height: 40px;
    }

    .stRadio [role="radio"] {
        outline-offset: 2px;
    }

    /* High contrast mode adjustments */
    @media (prefers-contrast: high) {
        :root {
            --color-border: #1a1a2e;
            --color-text-muted: #3a3a4e;
        }
    }

    /* Reduced motion preferences */
    @media (prefers-reduced-motion: reduce) {
        * {
            transition-duration: 0.01ms !important;
            animation-duration: 0.01ms !important;
        }
    }

    @media (max-width: 768px) {
        .main .block-container {
            padding-top: 1.25rem;
            padding-bottom: 2rem;
        }

        .main-header {
            padding: 2rem 1.2rem;
        }

        .main-header h1 {
            font-size: 2rem;
        }

        .progress-label {
            font-size: 0.64rem;
            max-width: 64px;
        }

        .progress-step-content {
            min-width: 62px;
        }

        .design-grid {
            grid-template-columns: 1fr;
        }

        .design-rail {
            position: static;
        }

        .publish-grid {
            grid-template-columns: 1fr;
        }

        .step-actions-bar {
            bottom: 0;
            border-radius: var(--radius-sm);
            padding: 0.75rem;
        }
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       AUTO-SAVE INDICATOR - Subtle Feedback
       ═══════════════════════════════════════════════════════════════════════════ */
    .auto-save-indicator {
        position: fixed;
        bottom: 1.5rem;
        right: 1.5rem;
        background: var(--color-success);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: var(--radius-full);
        font-size: 0.75rem;
        font-weight: 500;
        font-family: var(--font-body);
        box-shadow: var(--shadow-md);
        animation: fadeInOut 2s ease-in-out;
        display: flex;
        align-items: center;
        gap: 0.375rem;
    }

    .auto-save-indicator::before {
        content: '✓';
    }

    @keyframes fadeInOut {
        0% { opacity: 0; transform: translateY(10px); }
        20% { opacity: 1; transform: translateY(0); }
        80% { opacity: 1; transform: translateY(0); }
        100% { opacity: 0; transform: translateY(-10px); }
    }

    /* ═══════════════════════════════════════════════════════════════════════════
       DOWNLOAD BUTTON ENHANCEMENT
       ═══════════════════════════════════════════════════════════════════════════ */
    .stDownloadButton > button {
        background: linear-gradient(135deg, var(--color-text-primary) 0%, #2d2d44 100%);
        border: 1px solid transparent;
    }

    .stDownloadButton > button:hover {
        background: linear-gradient(135deg, #2d2d44 0%, var(--color-text-primary) 100%);
        box-shadow: var(--shadow-lg), var(--shadow-glow);
    }
</style>
""", unsafe_allow_html=True)


def get_active_theme() -> dict:
    """Get the currently active theme configuration."""
    theme_name = st.session_state.get("theme_mode", DEFAULT_THEME)
    return THEME_CONFIGS.get(theme_name, THEME_CONFIGS[DEFAULT_THEME])


def render_theme_picker():
    """Render theme picker UI and update session state."""
    options = list(THEME_CONFIGS.keys())
    current = st.session_state.get("theme_mode", DEFAULT_THEME)
    if current not in THEME_CONFIGS:
        current = DEFAULT_THEME

    if "theme_picker" not in st.session_state:
        st.session_state.theme_picker = current

    _, picker_col = st.columns([3, 2])
    with picker_col:
        st.markdown('<div class="theme-switcher section-reveal"><div class="theme-switcher-label">Appearance</div>', unsafe_allow_html=True)
        selected = st.radio(
            "Theme Mode",
            options,
            format_func=lambda mode: f"{THEME_ICONS.get(mode, '🎨')} {mode}",
            horizontal=True,
            label_visibility="collapsed",
            key="theme_picker",
            index=options.index(current),
        )
        pref_col1, pref_col2, pref_col3 = st.columns(3)
        with pref_col1:
            st.session_state.pref_high_contrast = st.checkbox(
                "High Contrast",
                key="pref_high_contrast_checkbox",
            )
        with pref_col2:
            st.session_state.pref_reduce_motion = st.checkbox(
                "Low Motion",
                key="pref_reduce_motion_checkbox",
            )
        with pref_col3:
            st.session_state.pref_large_text = st.checkbox(
                "Large Text",
                key="pref_large_text_checkbox",
            )
        st.markdown('<div class="theme-switcher-help">Switch visual mode without losing your progress.</div></div>', unsafe_allow_html=True)

    st.session_state.theme_mode = selected


def apply_theme_styles():
    """Apply dynamic CSS overrides for the selected theme."""
    theme = get_active_theme()
    high_contrast = st.session_state.get("pref_high_contrast_checkbox", st.session_state.get("pref_high_contrast", False))
    reduce_motion = st.session_state.get("pref_reduce_motion_checkbox", st.session_state.get("pref_reduce_motion", False))
    large_text = st.session_state.get("pref_large_text_checkbox", st.session_state.get("pref_large_text", False))

    st.session_state.pref_high_contrast = bool(high_contrast)
    st.session_state.pref_reduce_motion = bool(reduce_motion)
    st.session_state.pref_large_text = bool(large_text)

    high_contrast_styles = """
    :root {
        --color-border: #000000;
        --color-border-light: #111111;
        --color-text-muted: #1d1d1d;
    }
    .stButton > button, .stTextInput > div > div > input, .stTextArea > div > div > textarea {
        border-width: 2px;
    }
    """ if high_contrast else ""

    reduce_motion_styles = """
    * {
        transition-duration: 0.01ms !important;
        animation-duration: 0.01ms !important;
        scroll-behavior: auto !important;
    }
    """ if reduce_motion else ""

    st.markdown(
        f"""
<style>
    :root {{
        --color-bg-primary: {theme["color_bg_primary"]};
        --color-bg-card: {theme["color_bg_card"]};
        --color-bg-elevated: {theme["color_bg_elevated"]};
        --color-text-primary: {theme["color_text_primary"]};
        --color-text-secondary: {theme["color_text_secondary"]};
        --color-text-muted: {theme["color_text_muted"]};
        --color-accent-gold: {theme["color_accent_gold"]};
        --color-accent-gold-light: {theme["color_accent_gold_light"]};
        --color-pain: {theme["color_pain"]};
        --color-pain-light: {theme["color_pain_light"]};
        --color-gain: {theme["color_gain"]};
        --color-gain-light: {theme["color_gain_light"]};
        --color-success: {theme["color_success"]};
        --color-success-light: {theme["color_success_light"]};
        --color-warning: {theme["color_warning"]};
        --color-warning-light: {theme["color_warning_light"]};
        --color-error: {theme["color_error"]};
        --color-error-light: {theme["color_error_light"]};
        --color-border: {theme["color_border"]};
        --color-border-light: {theme["color_border_light"]};
        --font-display: {theme["font_display"]};
        --font-body: {theme["font_body"]};
        --texture-tint: {theme["texture_tint"]};
        --motif-color: {theme["motif_color"]};
        --rail-gradient: {theme["rail_gradient"]};
        --motion-distance: {theme["motion_distance"]};
        --font-scale: {"1.08" if large_text else "1"};
    }}

    .stApp::before {{
        opacity: {theme["noise_opacity"]};
        background:
            radial-gradient(circle at 10% 10%, var(--texture-tint) 0%, transparent 45%),
            radial-gradient(circle at 90% 70%, var(--texture-tint) 0%, transparent 45%),
            url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
    }}

    .main-header {{
        background: {theme["header_gradient"]};
        color: {theme["header_text"]};
    }}

    .main-header::before {{
        background:
            radial-gradient(ellipse at 20% 30%, {theme["header_overlay_a"]} 0%, transparent 50%),
            radial-gradient(ellipse at 80% 70%, {theme["header_overlay_b"]} 0%, transparent 50%);
    }}

    .summary-section,
    .empty-state {{
        background: linear-gradient(145deg, var(--color-bg-card) 0%, {theme["surface_tint"]} 100%);
    }}

    .success-banner {{
        background: linear-gradient(145deg, var(--color-success-light) 0%, {theme["success_tint"]} 100%);
    }}

    .success-banner p {{
        color: {theme["success_text"]};
    }}

    .restore-banner {{
        background: linear-gradient(145deg, var(--color-warning-light) 0%, {theme["warning_tint"]} 100%);
    }}

    .restore-banner-title {{
        color: {theme["restore_title"]};
    }}

    .restore-banner-description,
    .restore-banner-hint {{
        color: {theme["restore_description"]};
    }}

    .stButton > button[kind="primary"]:hover {{
        background: {theme["primary_hover"]};
        border-color: {theme["primary_hover"]};
    }}

    .stDownloadButton > button {{
        background: linear-gradient(135deg, var(--color-text-primary) 0%, {theme["primary_hover"]} 100%);
    }}

    .stDownloadButton > button:hover {{
        background: linear-gradient(135deg, {theme["primary_hover"]} 0%, var(--color-text-primary) 100%);
    }}

    {high_contrast_styles}
    {reduce_motion_styles}
</style>
""",
        unsafe_allow_html=True,
    )


# ============ API Configuration ============
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "")  # Optional API key for authentication


# ============ Session Persistence Functions ============
def save_session_to_file():
    """Save current session state to a local file for persistence across refreshes."""
    try:
        session_data = {
            "step": st.session_state.get("step", 0),
            "job_description": st.session_state.get("job_description", ""),
            "pain_points": st.session_state.get("pain_points", []),
            "gain_points": st.session_state.get("gain_points", []),
            "job_validated": st.session_state.get("job_validated", False),
            "pains_validated": st.session_state.get("pains_validated", False),
            "gains_validated": st.session_state.get("gains_validated", False),
            "theme_mode": st.session_state.get("theme_mode", DEFAULT_THEME),
            "pref_high_contrast": st.session_state.get("pref_high_contrast", False),
            "pref_reduce_motion": st.session_state.get("pref_reduce_motion", False),
            "pref_large_text": st.session_state.get("pref_large_text", False),
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(SESSION_FILE, "w") as f:
            json.dump(session_data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving session: {e}")
        return False


def load_session_from_file() -> Optional[dict]:
    """Load session state from file if it exists."""
    try:
        if SESSION_FILE.exists():
            with open(SESSION_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading session: {e}")
    return None


def clear_saved_session():
    """Delete the saved session file."""
    try:
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()
        return True
    except Exception:
        return False


def has_saved_session() -> bool:
    """Check if a saved session exists with meaningful data."""
    session = load_session_from_file()
    if session:
        # Only consider it a real session if there's actual content
        has_content = (
            session.get("job_description", "").strip() or
            len(session.get("pain_points", [])) > 0 or
            len(session.get("gain_points", [])) > 0
        )
        return has_content
    return False


def restore_session(session_data: dict):
    """Restore session state from saved data."""
    st.session_state.step = session_data.get("step", 0)
    st.session_state.job_description = session_data.get("job_description", "")
    st.session_state.pain_points = session_data.get("pain_points", [])
    st.session_state.gain_points = session_data.get("gain_points", [])
    st.session_state.job_validated = session_data.get("job_validated", False)
    st.session_state.pains_validated = session_data.get("pains_validated", False)
    st.session_state.gains_validated = session_data.get("gains_validated", False)
    theme_mode = session_data.get("theme_mode", DEFAULT_THEME)
    st.session_state.theme_mode = theme_mode if theme_mode in THEME_CONFIGS else DEFAULT_THEME
    st.session_state.theme_picker = st.session_state.theme_mode
    st.session_state.pref_high_contrast = bool(session_data.get("pref_high_contrast", False))
    st.session_state.pref_reduce_motion = bool(session_data.get("pref_reduce_motion", False))
    st.session_state.pref_large_text = bool(session_data.get("pref_large_text", False))
    st.session_state.pref_high_contrast_checkbox = st.session_state.pref_high_contrast
    st.session_state.pref_reduce_motion_checkbox = st.session_state.pref_reduce_motion
    st.session_state.pref_large_text_checkbox = st.session_state.pref_large_text
    st.session_state.editing_pain_index = None
    st.session_state.editing_gain_index = None
    st.session_state.new_pain_input = ""
    st.session_state.new_gain_input = ""
    clear_inline_notice("pain")
    clear_inline_notice("gain")
    st.session_state.session_loaded = True


# ============ Session State Initialization ============
def init_session_state():
    """Initialize session state variables."""
    if 'step' not in st.session_state:
        st.session_state.step = 0  # 0: Welcome, 1: Job, 2: Pains, 3: Gains, 4: Review
    if 'job_description' not in st.session_state:
        st.session_state.job_description = ""
    if 'pain_points' not in st.session_state:
        st.session_state.pain_points = []
    if 'gain_points' not in st.session_state:
        st.session_state.gain_points = []
    if 'job_validated' not in st.session_state:
        st.session_state.job_validated = False
    if 'pains_validated' not in st.session_state:
        st.session_state.pains_validated = False
    if 'gains_validated' not in st.session_state:
        st.session_state.gains_validated = False
    if 'theme_mode' not in st.session_state:
        st.session_state.theme_mode = DEFAULT_THEME
    elif st.session_state.theme_mode not in THEME_CONFIGS:
        st.session_state.theme_mode = DEFAULT_THEME
    if 'theme_picker' not in st.session_state:
        st.session_state.theme_picker = st.session_state.theme_mode
    if 'pref_high_contrast' not in st.session_state:
        st.session_state.pref_high_contrast = False
    if 'pref_reduce_motion' not in st.session_state:
        st.session_state.pref_reduce_motion = False
    if 'pref_large_text' not in st.session_state:
        st.session_state.pref_large_text = False
    if 'pref_high_contrast_checkbox' not in st.session_state:
        st.session_state.pref_high_contrast_checkbox = st.session_state.pref_high_contrast
    if 'pref_reduce_motion_checkbox' not in st.session_state:
        st.session_state.pref_reduce_motion_checkbox = st.session_state.pref_reduce_motion
    if 'pref_large_text_checkbox' not in st.session_state:
        st.session_state.pref_large_text_checkbox = st.session_state.pref_large_text
    if 'editing_pain_index' not in st.session_state:
        st.session_state.editing_pain_index = None
    if 'editing_gain_index' not in st.session_state:
        st.session_state.editing_gain_index = None
    if 'new_pain_input' not in st.session_state:
        st.session_state.new_pain_input = ""
    if 'new_gain_input' not in st.session_state:
        st.session_state.new_gain_input = ""
    if 'session_loaded' not in st.session_state:
        st.session_state.session_loaded = False
    if 'show_restore_prompt' not in st.session_state:
        st.session_state.show_restore_prompt = has_saved_session()
    # Performance: Track last validation to implement debouncing
    if 'last_validated_job' not in st.session_state:
        st.session_state.last_validated_job = ""
    if 'last_job_validation_result' not in st.session_state:
        st.session_state.last_job_validation_result = None


# ============ Performance: Cached HTTP Client ============
@st.cache_resource
def get_http_client() -> httpx.Client:
    """Get a cached HTTP client for connection pooling (reduces latency by 10-50ms per request)."""
    return httpx.Client(timeout=30.0)


# ============ API Helpers ============
def get_api_headers() -> dict:
    """Get API headers including authentication if configured."""
    headers = {"Content-Type": "application/json"}
    if API_SECRET_KEY:
        headers["X-API-Key"] = API_SECRET_KEY
    return headers


def call_api(endpoint: str, method: str = "GET", data: dict = None) -> dict:
    """Call the backend API with authentication using cached HTTP client."""
    try:
        headers = get_api_headers()
        client = get_http_client()
        if method == "GET":
            response = client.get(f"{API_BASE_URL}{endpoint}", headers=headers)
        else:
            response = client.post(f"{API_BASE_URL}{endpoint}", json=data, headers=headers)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 403:
            return {"error": "Authentication failed. Check API_SECRET_KEY configuration."}
        elif response.status_code == 429:
            return {"error": "Rate limit exceeded. Please wait before trying again."}
        else:
            return {"error": f"API error: {response.status_code}"}
    except Exception as e:
        return {"error": f"Connection error: {str(e)}"}


# ============ Performance: Cached Coaching Tips ============
@st.cache_data(ttl=3600)  # Cache for 1 hour - tips don't change frequently
def get_coaching_tip_cached(step: str) -> str:
    """Get coaching tip with caching to reduce API calls."""
    result = call_api(f"/api/coaching-tip/{step}")
    return result.get("tip", "")


def get_coaching_tip(step: str) -> str:
    """Get coaching tip for the current step (cached)."""
    return get_coaching_tip_cached(step)


# ============ Performance: Cached Validation ============
def get_content_hash(content: str) -> str:
    """Generate a hash for content to enable caching."""
    return hashlib.md5(content.encode()).hexdigest()


@st.cache_data(ttl=300)  # Cache validation results for 5 minutes
def validate_job_description_cached(description_hash: str, description: str) -> dict:
    """Cached job description validation."""
    return call_api("/api/validate/job-description", "POST", {"description": description})


@st.cache_data(ttl=300)  # Cache validation results for 5 minutes
def validate_pain_points_cached(points_hash: str, pain_points: tuple) -> dict:
    """Cached pain points validation (uses tuple for hashability)."""
    return call_api("/api/validate/pain-points", "POST", {"pain_points": list(pain_points)})


@st.cache_data(ttl=300)  # Cache validation results for 5 minutes
def validate_gain_points_cached(points_hash: str, gain_points: tuple) -> dict:
    """Cached gain points validation (uses tuple for hashability)."""
    return call_api("/api/validate/gain-points", "POST", {"gain_points": list(gain_points)})


# ============ UI Interaction Helpers ============
def normalize_item_text(value: str) -> str:
    """Normalize item text for duplicate checks."""
    return " ".join(value.lower().split())


def has_duplicate_item(candidate: str, existing_items: list, exclude_index: Optional[int] = None) -> bool:
    """Check duplicate items with normalization."""
    normalized_candidate = normalize_item_text(candidate)
    for i, item in enumerate(existing_items):
        if exclude_index is not None and i == exclude_index:
            continue
        if normalize_item_text(item) == normalized_candidate:
            return True
    return False


def set_inline_notice(scope: str, msg_type: str, message: str):
    """Set an inline message to show near a section input area."""
    st.session_state[f"{scope}_notice_type"] = msg_type
    st.session_state[f"{scope}_notice_message"] = message


def clear_inline_notice(scope: str):
    """Clear inline message for a section."""
    st.session_state.pop(f"{scope}_notice_type", None)
    st.session_state.pop(f"{scope}_notice_message", None)


def render_inline_notice(scope: str):
    """Render inline message for a section."""
    notice_type = st.session_state.get(f"{scope}_notice_type")
    notice_message = st.session_state.get(f"{scope}_notice_message")
    if notice_type and notice_message:
        render_validation_message(notice_type, notice_message)


def has_related_independence_issue(independence_issues: list, target_index: int) -> Optional[str]:
    """Find independence issue related to the target index."""
    for issue in independence_issues:
        idx1 = issue.get("item1_index")
        idx2 = issue.get("item2_index")
        if target_index in (idx1, idx2):
            return issue.get("message", "This item is too similar to another item. Please make it more distinct.")
    return None


def render_step_actions(
    back_label: str,
    back_key: str,
    back_step: int,
    next_label: str,
    next_key: str,
    next_step: int,
    next_disabled: bool = False,
    next_primary: bool = True,
):
    """Render a sticky action bar for step navigation."""
    st.markdown('<div class="step-actions-bar section-reveal">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button(back_label, key=back_key, use_container_width=True):
            st.session_state.step = back_step
            st.rerun()
    with col2:
        button_type = "primary" if next_primary else "secondary"
        if st.button(next_label, key=next_key, use_container_width=True, type=button_type, disabled=next_disabled):
            st.session_state.step = next_step
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def try_add_collection_item(
    collection_key: str,
    endpoint: str,
    payload_key: str,
    item_label: str,
    scope: str,
    candidate: str,
) -> bool:
    """Try to add a new item with duplicate and independence checks."""
    clean_candidate = candidate.strip()
    if not clean_candidate:
        set_inline_notice(scope, "warning", f"Please enter a {item_label} before adding.")
        return False

    existing_items = st.session_state.get(collection_key, [])
    if has_duplicate_item(clean_candidate, existing_items):
        set_inline_notice(scope, "error", f"This {item_label} is already listed. Add a distinct one.")
        return False

    updated_items = existing_items + [clean_candidate]
    result = call_api(endpoint, "POST", {payload_key: updated_items})
    if "error" in result:
        set_inline_notice(scope, "warning", "Validation is temporarily unavailable. Please try again.")
        return False

    independence = result.get("independence_check", {})
    if independence and not independence.get("independent", True):
        issue_message = has_related_independence_issue(independence.get("issues", []), len(updated_items) - 1)
        if issue_message:
            set_inline_notice(scope, "error", issue_message)
            return False

    st.session_state[collection_key].append(clean_candidate)
    set_inline_notice(scope, "success", f"{item_label.capitalize()} added.")
    return True


def try_update_collection_item(
    collection_key: str,
    endpoint: str,
    payload_key: str,
    item_label: str,
    scope: str,
    item_index: int,
    candidate: str,
) -> bool:
    """Try to update an existing item with duplicate and independence checks."""
    clean_candidate = candidate.strip()
    if not clean_candidate:
        set_inline_notice(scope, "warning", f"{item_label.capitalize()} cannot be empty.")
        return False

    existing_items = st.session_state.get(collection_key, [])
    if item_index < 0 or item_index >= len(existing_items):
        set_inline_notice(scope, "error", f"Unable to edit {item_label}; item no longer exists.")
        return False

    if has_duplicate_item(clean_candidate, existing_items, exclude_index=item_index):
        set_inline_notice(scope, "error", f"This {item_label} duplicates another entry.")
        return False

    updated_items = existing_items.copy()
    updated_items[item_index] = clean_candidate

    result = call_api(endpoint, "POST", {payload_key: updated_items})
    if "error" in result:
        set_inline_notice(scope, "warning", "Validation is temporarily unavailable. Please try again.")
        return False

    independence = result.get("independence_check", {})
    if independence and not independence.get("independent", True):
        issue_message = has_related_independence_issue(independence.get("issues", []), item_index)
        if issue_message:
            set_inline_notice(scope, "error", issue_message)
            return False

    st.session_state[collection_key][item_index] = clean_candidate
    set_inline_notice(scope, "success", f"{item_label.capitalize()} updated.")
    return True


def infer_item_metadata(text: str, item_type: str) -> dict:
    """Infer lightweight metadata chips for list cards."""
    lowered = text.lower()
    words = max(1, len(text.split()))

    if item_type == "pain":
        if any(token in lowered for token in ["delay", "blocked", "risk", "urgent", "critical"]):
            urgency = "high urgency"
        elif any(token in lowered for token in ["slow", "manual", "rework", "waiting"]):
            urgency = "medium urgency"
        else:
            urgency = "steady friction"
    else:
        if any(token in lowered for token in ["revenue", "growth", "customer", "value", "impact"]):
            urgency = "high impact"
        elif any(token in lowered for token in ["clear", "faster", "quality", "focus"]):
            urgency = "medium impact"
        else:
            urgency = "future upside"

    if any(token in lowered for token in ["team", "stakeholder", "customer", "leadership"]):
        category = "collaboration"
    elif any(token in lowered for token in ["report", "document", "analysis", "data", "metric"]):
        category = "information flow"
    elif any(token in lowered for token in ["tool", "system", "automation", "process"]):
        category = "operations"
    else:
        category = "execution"

    confidence = "high confidence" if words >= 10 else "draft confidence"
    return {"category": category, "urgency": urgency, "confidence": confidence}


def build_item_card_html(index: int, item_text: str, item_type: str) -> str:
    """Build HTML for rich item card with metadata chips."""
    safe_text = html.escape(item_text)
    meta = infer_item_metadata(item_text, item_type)
    prefix = "P" if item_type == "pain" else "G"
    return f"""
        <div class="item-card section-reveal">
            <div class="item-number {item_type}">{prefix}{index + 1}</div>
            <div class="item-text">
                {safe_text}
                <div class="item-metadata" aria-label="Item metadata">
                    <span class="item-chip accent">{html.escape(meta["urgency"])}</span>
                    <span class="item-chip">{html.escape(meta["category"])}</span>
                    <span class="item-chip">{html.escape(meta["confidence"])}</span>
                </div>
            </div>
        </div>
    """


def render_step_rail(step_title: str, focus_prompt: str, checks: list, tip: str = ""):
    """Render right-side rail with guidance and shortcuts."""
    safe_title = html.escape(step_title)
    safe_focus = html.escape(focus_prompt)
    checks_md = "\n".join([f"- {html.escape(item)}" for item in checks])
    tip_md = ""
    if tip:
        tip_md = (
            "\n**Coaching Signal**\n"
            + html.escape(tip).replace(chr(10), "  \n")
            + "\n"
        )

    rail_md = dedent(
        f"""
        <div class="design-rail section-reveal stagger-2" aria-label="Step guidance">
        <div class="rail-title">{safe_title}</div>
        <div class="rail-copy">{safe_focus}</div>
        </div>
        """
    ).strip()
    st.markdown(rail_md, unsafe_allow_html=True)
    st.markdown("**Checklist**")
    st.markdown(checks_md)
    if tip_md:
        st.markdown(tip_md)
    st.markdown("**Keyboard**")
    st.markdown("- **Enter**: Add in quick composer")
    st.markdown("- **Cmd/Ctrl + Enter**: Validate now")
    st.markdown("- **Esc**: Cancel current edit")


def render_progress_narrative():
    """Render narrative milestone summary under progress tracker."""
    current = st.session_state.step
    title, purpose = STEP_PURPOSES[current]
    completed = current
    total = len(STEP_PURPOSES) - 1
    if current == 1:
        quality = "validated" if st.session_state.job_validated else "draft"
    elif current == 2:
        quality = "validated" if st.session_state.pains_validated else "in progress"
    elif current == 3:
        quality = "validated" if st.session_state.gains_validated else "in progress"
    elif current == 4:
        quality = "publish-ready"
    else:
        quality = "getting started"
    st.markdown(
        f"""
        <div class="milestone-card section-reveal stagger-2" role="status" aria-label="Current milestone">
            <div class="milestone-head">
                <span class="milestone-title">Current Milestone: {html.escape(title)}</span>
                <span>{completed}/{total} complete · {html.escape(quality)}</span>
            </div>
            <div class="milestone-purpose">{html.escape(purpose)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def inject_hotkeys_script():
    """Inject lightweight client-side keyboard shortcuts."""
    components.html(
        """
        <script>
        (() => {
          const root = window.parent && window.parent.document ? window.parent.document : document;
          if (root.__vpcHotkeysInstalled) return;
          root.__vpcHotkeysInstalled = true;
          root.addEventListener("keydown", (event) => {
            const key = event.key.toLowerCase();
            if ((event.metaKey || event.ctrlKey) && key === "enter") {
              const validateBtn = [...root.querySelectorAll("button")]
                .find((btn) => btn.innerText && btn.innerText.includes("Validate Now"));
              if (validateBtn) {
                event.preventDefault();
                validateBtn.click();
              }
            }
            if (key === "escape") {
              const cancelBtn = [...root.querySelectorAll("button")]
                .find((btn) => btn.innerText && btn.innerText.trim() === "Cancel");
              if (cancelBtn) {
                event.preventDefault();
                cancelBtn.click();
              }
            }
          });
        })();
        </script>
        """,
        height=0,
    )


# ============ UI Components ============
def render_header():
    """Render the main header."""
    st.markdown("""
        <div class="main-header section-reveal">
            <div class="hero-kicker">Canvas Studio • Guided by AI</div>
            <h1>🎯 Work Process Reflection Canvas</h1>
            <p>Understand your work better with AI-powered guidance</p>
            <div class="hero-signature">
                <div class="hero-signature-line"></div>
                <div class="hero-signature-copy">From friction to clarity in one flow</div>
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_progress():
    """Render the progress indicator with connector lines."""
    steps = ["Welcome", "Job Description", "Pain Points", "Gain Points", "Review"]
    current = st.session_state.step
    theme = get_active_theme()

    # Build HTML for progress steps with connectors (single-line to avoid rendering issues)
    steps_html = []
    for i, step_name in enumerate(steps):
        if i < current:
            indicator = "✓"
            indicator_style = (
                f"background: {theme['progress_complete']}; color: {theme['progress_complete_text']}; "
                f"border-color: {theme['progress_complete']};"
            )
            label_style = f"color: {theme['progress_complete']}; font-weight: 500;"
            status = "completed"
        elif i == current:
            indicator = str(i + 1)
            indicator_style = (
                f"background: {theme['progress_active']}; color: {theme['progress_active_text']}; "
                f"box-shadow: 0 0 0 4px {theme['progress_active_glow']}; border-color: {theme['color_accent_gold']};"
            )
            label_style = f"color: {theme['progress_active']}; font-weight: 600;"
            status = "current"
        else:
            indicator = str(i + 1)
            indicator_style = (
                f"background: {theme['progress_upcoming_bg']}; color: {theme['progress_upcoming_text']}; "
                f"border: 2px solid {theme['progress_upcoming_border']};"
            )
            label_style = f"color: {theme['progress_upcoming_text']}; font-weight: 500;"
            status = "upcoming"

        connector_html = ""
        if i < len(steps) - 1:
            connector_color = theme["progress_complete"] if i < current else theme["progress_upcoming_border"]
            connector_html = f'<div class="progress-line" style="background: {connector_color};"></div>'

        # Build as single-line HTML to avoid Streamlit rendering issues with multiline f-strings
        item_html = f'<div class="progress-step-wrapper"><div class="progress-step-content"><div class="progress-indicator" style="{indicator_style}" role="listitem" aria-label="Step {i+1}: {step_name}, {status}">{indicator}</div><div class="progress-label" style="{label_style}">{step_name}</div></div>{connector_html}</div>'
        steps_html.append(item_html)

    # Join steps outside the f-string
    joined_steps = ''.join(steps_html)

    # Style block (separate from content to avoid f-string interpolation issues)
    style_block = """
<style>
.progress-bar-container {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: 0 0.5rem;
    margin: 1rem 0;
}
.progress-step-wrapper {
    display: flex;
    align-items: center;
    flex: 1;
}
.progress-step-wrapper:last-child {
    flex: 0;
}
.progress-step-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    min-width: 70px;
}
.progress-indicator {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    font-size: 0.875rem;
    z-index: 2;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 1px 2px rgba(26, 26, 46, 0.04);
}
.progress-label {
    margin-top: 0.625rem;
    font-size: 0.6875rem;
    text-align: center;
    max-width: 80px;
    letter-spacing: 0.02em;
    text-transform: uppercase;
}
.progress-line {
    flex: 1;
    height: 2px;
    margin: 0 0.375rem;
    margin-bottom: 1.75rem;
    border-radius: 1px;
    transition: background 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
</style>
"""

    container_html = f'<div class="progress-bar-container section-reveal stagger-1" role="list" aria-label="Progress steps">{joined_steps}</div>'
    st.markdown(style_block + container_html, unsafe_allow_html=True)


def render_coaching_tip(tip: str):
    """Render a coaching tip box with XSS protection."""
    # Escape HTML to prevent XSS, then convert newlines to <br>
    safe_tip = html.escape(tip).replace(chr(10), '<br>')
    st.markdown(f"""
        <div class="coaching-tip section-reveal stagger-2">
            <h4>💡 Coaching Tip</h4>
            <p>{safe_tip}</p>
        </div>
    """, unsafe_allow_html=True)


def render_quality_score(score: int):
    """Render a quality score badge with accessibility support."""
    if score >= 75:
        level = "high"
        emoji = "✅"
        level_text = "high quality"
    elif score >= 50:
        level = "medium"
        emoji = "⚠️"
        level_text = "medium quality, needs improvement"
    else:
        level = "low"
        emoji = "❌"
        level_text = "low quality, significant improvements needed"

    st.markdown(f"""
        <div class="quality-score {level}" role="status" aria-label="Quality score: {score}%, {level_text}">
            {emoji} Quality Score: {score}%
        </div>
    """, unsafe_allow_html=True)


def render_validation_message(msg_type: str, message: str):
    """Render a validation message with XSS protection and accessibility support."""
    safe_message = html.escape(message)
    role = "alert" if msg_type == "error" else "status"
    aria_live = "assertive" if msg_type == "error" else "polite"
    st.markdown(f"""
        <div class="validation-{msg_type}" role="{role}" aria-live="{aria_live}">
            {safe_message}
        </div>
    """, unsafe_allow_html=True)


def render_empty_state(icon: str, title: str, description: str, hint: str = ""):
    """Render an empty state placeholder."""
    hint_html = f'<div class="empty-state-hint">{html.escape(hint)}</div>' if hint else ""
    st.markdown(f"""
        <div class="empty-state section-reveal" role="status" aria-label="{title}">
            <div class="empty-state-icon">{icon}</div>
            <div class="empty-state-title">{title}</div>
            <div class="empty-state-description">{description}</div>
            {hint_html}
        </div>
    """, unsafe_allow_html=True)


def render_session_restore_prompt():
    """Render a prompt to restore a previous session."""
    session_data = load_session_from_file()
    if not session_data:
        return

    saved_at = session_data.get("saved_at", "Unknown")
    pain_count = len(session_data.get("pain_points", []))
    gain_count = len(session_data.get("gain_points", []))
    has_job = bool(session_data.get("job_description", "").strip())

    # Build summary
    items = []
    if has_job:
        items.append("job description")
    if pain_count > 0:
        items.append(f"{pain_count} pain point{'s' if pain_count != 1 else ''}")
    if gain_count > 0:
        items.append(f"{gain_count} gain point{'s' if gain_count != 1 else ''}")

    summary = ", ".join(items) if items else "some progress"

    st.markdown(f"""
        <div class="restore-banner section-reveal" role="alert">
            <div class="restore-banner-title">📂 Previous Session Found</div>
            <div class="restore-banner-description">
                You have unsaved work from {saved_at} ({summary}).
            </div>
            <div class="restore-banner-hint">
                Continue from where you left off, or start fresh with a new canvas.
            </div>
        </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Continue Where I Left Off", use_container_width=True, type="primary"):
            restore_session(session_data)
            st.session_state.show_restore_prompt = False
            st.rerun()
    with col2:
        if st.button("🗑️ Start Fresh", use_container_width=True):
            clear_saved_session()
            st.session_state.show_restore_prompt = False
            st.rerun()


# ============ Step Pages ============
def render_welcome():
    """Render the welcome page."""
    # Show session restore prompt if there's a previous session
    if st.session_state.show_restore_prompt:
        render_session_restore_prompt()
        return  # Don't show the rest until user decides

    st.markdown("## Welcome! 👋")
    tip = get_coaching_tip("welcome")

    main_col, rail_col = st.columns([2.05, 1], gap="large")
    with rail_col:
        render_step_rail(
            step_title="Session Setup",
            focus_prompt="You will move from one job statement to pains, gains, and final export.",
            checks=[
                "5-step guided flow",
                "Auto validation each step",
                "Export to Word at completion",
            ],
            tip=tip,
        )

    with main_col:
        st.markdown('<div class="design-main section-reveal">', unsafe_allow_html=True)
        st.markdown("""
            <div class="summary-section section-reveal">
                <h3>What You Will Build</h3>
                <p>A publish-ready reflection canvas that maps one concrete work objective, its critical pain signals, and the gains that define success.</p>
            </div>
        """, unsafe_allow_html=True)
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 Start Building Your Canvas", use_container_width=True, type="primary"):
                st.session_state.step = 1
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


def render_job_description():
    """Render the job description step."""
    st.markdown("## Step 1: Define Your Job 🎯")
    tip = get_coaching_tip("job")

    main_col, rail_col = st.columns([2.05, 1], gap="large")
    with rail_col:
        render_step_rail(
            step_title="Step 1 Focus",
            focus_prompt="Write one crisp objective with a visible outcome and audience.",
            checks=[
                "One objective, not a list",
                "Include why it matters",
                "Make success measurable",
            ],
            tip=tip,
        )

    with main_col:
        st.markdown('<div class="design-main section-reveal">', unsafe_allow_html=True)
        st.markdown("### What is the main task or goal you're trying to accomplish?")

        job_desc = st.text_area(
            "Describe the task, goal, or objective you're working on:",
            value=st.session_state.job_description,
            height=170,
            placeholder="Example: I need to track my team's monthly expenses and generate financial reports efficiently, so I can make informed budget decisions and present clear summaries to leadership...",
            key="job_input",
        )
        st.session_state.job_description = job_desc

        result = None
        if job_desc:
            result = call_api("/api/validate/job-description", "POST", {"description": job_desc})

        if st.button("✅ Validate Now (Cmd/Ctrl+Enter)", key="job_validate_now"):
            if job_desc.strip():
                result = call_api("/api/validate/job-description", "POST", {"description": job_desc})
            else:
                render_validation_message("warning", "Add a job description before validating.")

        if result and "error" not in result:
            render_quality_score(result.get("score", 0))
            if result.get("feedback"):
                for feedback in result["feedback"]:
                    render_validation_message("warning", feedback)
            if result.get("suggestions"):
                with st.expander("💡 Suggestions for improvement"):
                    for suggestion in result["suggestions"]:
                        st.markdown(f"• {suggestion}")
            st.session_state.job_validated = result.get("valid", False)

        if st.button("🤖 Get AI Suggestions", key="job_suggestions"):
            with st.spinner("Getting suggestions..."):
                suggestions = call_api("/api/suggestions", "POST", {
                    "step": "job",
                    "job_description": job_desc
                })
                if "error" not in suggestions:
                    st.info(suggestions.get("suggestions", "No suggestions available."))

        st.markdown("---")
        render_step_actions(
            back_label="⬅️ Back",
            back_key="job_back",
            back_step=0,
            next_label="Continue to Pain Points ➡️",
            next_key="job_next",
            next_step=2,
            next_disabled=not st.session_state.job_validated,
        )

        if not st.session_state.job_validated and job_desc:
            st.caption("Please address the feedback above before continuing.")
        st.markdown("</div>", unsafe_allow_html=True)


def render_pain_points():
    """Render the pain points step."""
    st.markdown("## Step 2: Identify Pain Points 😓")
    tip = get_coaching_tip("pains")
    remaining = max(0, 7 - len(st.session_state.pain_points))

    main_col, rail_col = st.columns([2.05, 1], gap="large")
    with rail_col:
        render_step_rail(
            step_title="Step 2 Focus",
            focus_prompt="Capture distinct, root-cause pains rather than vague complaints.",
            checks=[
                f"{len(st.session_state.pain_points)}/7 captured",
                "Keep each pain independent",
                "Describe observable impact",
            ],
            tip=tip,
        )

    with main_col:
        st.markdown('<div class="design-main section-reveal">', unsafe_allow_html=True)
        st.markdown("### What obstacles and frustrations do you face in this work?")
        st.markdown(f"You need at least **7 independent** pain points. Currently: **{len(st.session_state.pain_points)}**/7")

        st.markdown("#### Your Pain Points:")
        if st.session_state.pain_points:
            for i, pain in enumerate(st.session_state.pain_points):
                col1, col2, col3 = st.columns([9, 1, 1])
                with col1:
                    st.markdown(build_item_card_html(i, pain, "pain"), unsafe_allow_html=True)
                with col2:
                    st.markdown('<div class="item-action-group">', unsafe_allow_html=True)
                    if st.button("✏️", key=f"edit_pain_{i}", help="Edit this pain point"):
                        st.session_state.editing_pain_index = i
                        clear_inline_notice("pain")
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                with col3:
                    st.markdown('<div class="item-action-group">', unsafe_allow_html=True)
                    if st.button("🗑️", key=f"delete_pain_{i}", help="Delete this pain point"):
                        st.session_state.pain_points.pop(i)
                        if st.session_state.editing_pain_index == i:
                            st.session_state.editing_pain_index = None
                        set_inline_notice("pain", "success", "Pain point removed.")
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

                if st.session_state.get("editing_pain_index") == i:
                    with st.form(f"edit_pain_form_{i}", clear_on_submit=False):
                        edited_pain = st.text_input(
                            "Edit this pain point",
                            value=pain,
                            key=f"edit_pain_text_{i}",
                        )
                        edit_col1, edit_col2 = st.columns(2)
                        save_edit = edit_col1.form_submit_button("Save changes", use_container_width=True)
                        cancel_edit = edit_col2.form_submit_button("Cancel", use_container_width=True)

                    if save_edit:
                        if try_update_collection_item(
                            collection_key="pain_points",
                            endpoint="/api/validate/pain-points",
                            payload_key="pain_points",
                            item_label="pain point",
                            scope="pain",
                            item_index=i,
                            candidate=edited_pain,
                        ):
                            st.session_state.editing_pain_index = None
                            st.rerun()
                    if cancel_edit:
                        st.session_state.editing_pain_index = None
                        clear_inline_notice("pain")
                        st.rerun()
        else:
            render_empty_state(
                "😓",
                "No pain points yet",
                "Add your first pain point below to get started. Think about frustrations, obstacles, or risks in your work.",
                "Press Enter to add quickly."
            )

        st.markdown("#### Add a new pain point:")
        st.markdown('<div class="composer-hint">Power composer: Enter adds. Cmd/Ctrl+Enter validates. Esc cancels edit.</div>', unsafe_allow_html=True)
        with st.form("add_pain_form", clear_on_submit=False):
            new_pain = st.text_input(
                "Describe a specific pain, frustration, or obstacle you experience:",
                placeholder="Example: Spending hours manually consolidating data from multiple spreadsheets instead of focusing on analysis...",
                key="new_pain_input",
                help="Press Enter to add this pain point quickly.",
            )
            add_pain_submitted = st.form_submit_button("➕ Add Pain Point")

        if add_pain_submitted:
            if try_add_collection_item(
                collection_key="pain_points",
                endpoint="/api/validate/pain-points",
                payload_key="pain_points",
                item_label="pain point",
                scope="pain",
                candidate=new_pain,
            ):
                st.session_state.editing_pain_index = None
                st.session_state.new_pain_input = ""
                st.rerun()

        render_inline_notice("pain")

        # Validate all pain points
        validation_result = None
        if len(st.session_state.pain_points) >= 2:
            validation_result = call_api("/api/validate/pain-points", "POST", {
                "pain_points": st.session_state.pain_points
            })

        if st.button("✅ Validate Now (Cmd/Ctrl+Enter)", key="pain_validate_now"):
            if len(st.session_state.pain_points) >= 2:
                validation_result = call_api("/api/validate/pain-points", "POST", {
                    "pain_points": st.session_state.pain_points
                })
            else:
                render_validation_message("warning", "Add at least 2 pain points to run validation.")

        if validation_result and "error" not in validation_result:
            st.session_state.pains_validated = validation_result.get("valid", False)

            if validation_result.get("overall_feedback"):
                for feedback in validation_result["overall_feedback"]:
                    render_validation_message("warning", feedback)

            independence = validation_result.get("independence_check", {})
            if independence and not independence.get("independent", True):
                issues = independence.get("issues", [])
                for issue in issues:
                    render_validation_message("error", issue.get("message", ""))
        elif len(st.session_state.pain_points) < 2:
            st.session_state.pains_validated = False

        if remaining > 0:
            if st.button(f"🤖 Get Suggestions for {remaining} More Pain Points", key="pain_suggestions"):
                with st.spinner("Getting suggestions..."):
                    suggestions = call_api("/api/suggestions", "POST", {
                        "step": "pains",
                        "job_description": st.session_state.job_description,
                        "existing_items": st.session_state.pain_points,
                        "count_needed": remaining
                    })
                    if "error" not in suggestions:
                        st.info(suggestions.get("suggestions", "No suggestions available."))

        st.markdown("---")
        can_proceed = len(st.session_state.pain_points) >= 7 and st.session_state.pains_validated
        render_step_actions(
            back_label="⬅️ Back to Job Description",
            back_key="pain_back",
            back_step=1,
            next_label="Continue to Gain Points ➡️",
            next_key="pain_next",
            next_step=3,
            next_disabled=not can_proceed,
        )

        if not can_proceed:
            st.caption(f"Add {max(0, 7 - len(st.session_state.pain_points))} more unique pain points to continue.")
        st.markdown("</div>", unsafe_allow_html=True)


def render_gain_points():
    """Render the gain points step."""
    st.markdown("## Step 3: Identify Gain Points 🌟")
    tip = get_coaching_tip("gains")
    remaining = max(0, 8 - len(st.session_state.gain_points))

    main_col, rail_col = st.columns([2.05, 1], gap="large")
    with rail_col:
        render_step_rail(
            step_title="Step 3 Focus",
            focus_prompt="Define gains as concrete outcomes, not generic wishes.",
            checks=[
                f"{len(st.session_state.gain_points)}/8 captured",
                "Keep each gain independent",
                "Describe user-visible benefit",
            ],
            tip=tip,
        )

    with main_col:
        st.markdown('<div class="design-main section-reveal">', unsafe_allow_html=True)
        st.markdown("### What outcomes and benefits do you desire from your work?")
        st.markdown(f"You need at least **8 independent** gain points. Currently: **{len(st.session_state.gain_points)}**/8")

        st.markdown("#### Your Gain Points:")
        if st.session_state.gain_points:
            for i, gain in enumerate(st.session_state.gain_points):
                col1, col2, col3 = st.columns([9, 1, 1])
                with col1:
                    st.markdown(build_item_card_html(i, gain, "gain"), unsafe_allow_html=True)
                with col2:
                    st.markdown('<div class="item-action-group">', unsafe_allow_html=True)
                    if st.button("✏️", key=f"edit_gain_{i}", help="Edit this gain point"):
                        st.session_state.editing_gain_index = i
                        clear_inline_notice("gain")
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                with col3:
                    st.markdown('<div class="item-action-group">', unsafe_allow_html=True)
                    if st.button("🗑️", key=f"delete_gain_{i}", help="Delete this gain point"):
                        st.session_state.gain_points.pop(i)
                        if st.session_state.editing_gain_index == i:
                            st.session_state.editing_gain_index = None
                        set_inline_notice("gain", "success", "Gain point removed.")
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

                if st.session_state.get("editing_gain_index") == i:
                    with st.form(f"edit_gain_form_{i}", clear_on_submit=False):
                        edited_gain = st.text_input(
                            "Edit this gain point",
                            value=gain,
                            key=f"edit_gain_text_{i}",
                        )
                        edit_col1, edit_col2 = st.columns(2)
                        save_edit = edit_col1.form_submit_button("Save changes", use_container_width=True)
                        cancel_edit = edit_col2.form_submit_button("Cancel", use_container_width=True)

                    if save_edit:
                        if try_update_collection_item(
                            collection_key="gain_points",
                            endpoint="/api/validate/gain-points",
                            payload_key="gain_points",
                            item_label="gain point",
                            scope="gain",
                            item_index=i,
                            candidate=edited_gain,
                        ):
                            st.session_state.editing_gain_index = None
                            st.rerun()
                    if cancel_edit:
                        st.session_state.editing_gain_index = None
                        clear_inline_notice("gain")
                        st.rerun()
        else:
            render_empty_state(
                "🌟",
                "No gain points yet",
                "Add your first gain point below to get started. Think about desired outcomes and benefits you want from your work.",
                "Press Enter to add quickly."
            )

        st.markdown("#### Add a new gain point:")
        st.markdown('<div class="composer-hint">Power composer: Enter adds. Cmd/Ctrl+Enter validates. Esc cancels edit.</div>', unsafe_allow_html=True)
        with st.form("add_gain_form", clear_on_submit=False):
            new_gain = st.text_input(
                "Describe a specific outcome or benefit you desire:",
                placeholder="Example: Having real-time visibility into project progress to make confident resource allocation decisions...",
                key="new_gain_input",
                help="Press Enter to add this gain point quickly.",
            )
            add_gain_submitted = st.form_submit_button("➕ Add Gain Point")

        if add_gain_submitted:
            if try_add_collection_item(
                collection_key="gain_points",
                endpoint="/api/validate/gain-points",
                payload_key="gain_points",
                item_label="gain point",
                scope="gain",
                candidate=new_gain,
            ):
                st.session_state.editing_gain_index = None
                st.session_state.new_gain_input = ""
                st.rerun()

        render_inline_notice("gain")

        validation_result = None
        if len(st.session_state.gain_points) >= 2:
            validation_result = call_api("/api/validate/gain-points", "POST", {
                "gain_points": st.session_state.gain_points
            })

        if st.button("✅ Validate Now (Cmd/Ctrl+Enter)", key="gain_validate_now"):
            if len(st.session_state.gain_points) >= 2:
                validation_result = call_api("/api/validate/gain-points", "POST", {
                    "gain_points": st.session_state.gain_points
                })
            else:
                render_validation_message("warning", "Add at least 2 gain points to run validation.")

        if validation_result and "error" not in validation_result:
            st.session_state.gains_validated = validation_result.get("valid", False)

            if validation_result.get("overall_feedback"):
                for feedback in validation_result["overall_feedback"]:
                    render_validation_message("warning", feedback)

            independence = validation_result.get("independence_check", {})
            if independence and not independence.get("independent", True):
                issues = independence.get("issues", [])
                for issue in issues:
                    render_validation_message("error", issue.get("message", ""))
        elif len(st.session_state.gain_points) < 2:
            st.session_state.gains_validated = False

        if remaining > 0:
            if st.button(f"🤖 Get Suggestions for {remaining} More Gain Points", key="gain_suggestions"):
                with st.spinner("Getting suggestions..."):
                    suggestions = call_api("/api/suggestions", "POST", {
                        "step": "gains",
                        "job_description": st.session_state.job_description,
                        "existing_items": st.session_state.gain_points,
                        "count_needed": remaining
                    })
                    if "error" not in suggestions:
                        st.info(suggestions.get("suggestions", "No suggestions available."))

        st.markdown("---")
        can_proceed = len(st.session_state.gain_points) >= 8 and st.session_state.gains_validated
        render_step_actions(
            back_label="⬅️ Back to Pain Points",
            back_key="gain_back",
            back_step=2,
            next_label="Continue to Review ➡️",
            next_key="gain_next",
            next_step=4,
            next_disabled=not can_proceed,
        )

        if not can_proceed:
            st.caption(f"Add {max(0, 8 - len(st.session_state.gain_points))} more unique gain points to continue.")
        st.markdown("</div>", unsafe_allow_html=True)


def render_review():
    """Render the review and download page."""
    st.markdown("## Step 4: Review & Download 📋")
    tip = get_coaching_tip("review")

    main_col, rail_col = st.columns([2.05, 1], gap="large")
    with rail_col:
        render_step_rail(
            step_title="Publishing",
            focus_prompt="Treat this as a final artifact: clear, traceable, and ready to share.",
            checks=[
                f"{len(st.session_state.pain_points)} pains mapped",
                f"{len(st.session_state.gain_points)} gains mapped",
                "Export once satisfied",
            ],
            tip=tip,
        )

    with main_col:
        st.markdown("""
            <div class="success-banner section-reveal stagger-2">
                <h2>🎉 Congratulations!</h2>
                <p>Your canvas is complete. Review below, then download your document.</p>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("### Publish-Ready Canvas")
        safe_job_desc = html.escape(st.session_state.job_description)
        st.markdown(f"""
            <div class="summary-section section-reveal">
                <h3>🎯 Core Job Statement</h3>
                <p>{safe_job_desc}</p>
            </div>
        """, unsafe_allow_html=True)

        pains_col, gains_col = st.columns(2, gap="large")
        with pains_col:
            st.markdown(f"""
                <section class="publish-section section-reveal">
                    <h4>😓 Pain Signals ({len(st.session_state.pain_points)})</h4>
                </section>
            """, unsafe_allow_html=True)
            for i, pain in enumerate(st.session_state.pain_points):
                st.markdown(build_item_card_html(i, pain, "pain"), unsafe_allow_html=True)

        with gains_col:
            st.markdown(f"""
                <section class="publish-section section-reveal">
                    <h4>🌟 Gain Signals ({len(st.session_state.gain_points)})</h4>
                </section>
            """, unsafe_allow_html=True)
            for i, gain in enumerate(st.session_state.gain_points):
                st.markdown(build_item_card_html(i, gain, "gain"), unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### Download Your Canvas")

        st.markdown('<div class="step-actions-bar section-reveal">', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1])

        with col1:
            if st.button("⬅️ Back to Edit", use_container_width=True):
                st.session_state.step = 3
                st.rerun()

        with col2:
            try:
                with httpx.Client(timeout=30.0) as client:
                    response = client.post(
                        f"{API_BASE_URL}/api/generate-document",
                        json={
                            "job_description": st.session_state.job_description,
                            "pain_points": st.session_state.pain_points,
                            "gain_points": st.session_state.gain_points,
                            "title": "Value Proposition Canvas"
                        }
                    )

                    if response.status_code == 200:
                        st.download_button(
                            label="📥 Download Word Document",
                            data=response.content,
                            file_name="Value_Proposition_Canvas.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True,
                            type="primary"
                        )
                    else:
                        st.error("Failed to generate document. Please try again.")
            except Exception as e:
                st.error(f"Error connecting to server: {str(e)}")
                st.info("Make sure the backend server is running: `uvicorn app.main:app --reload --port 8000`")
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Start over option
    st.markdown("---")
    if st.button("🔄 Start a New Canvas", use_container_width=True):
        # Clear saved session file
        clear_saved_session()
        # Reset all session state
        st.session_state.step = 0
        st.session_state.job_description = ""
        st.session_state.pain_points = []
        st.session_state.gain_points = []
        st.session_state.job_validated = False
        st.session_state.pains_validated = False
        st.session_state.gains_validated = False
        st.session_state.editing_pain_index = None
        st.session_state.editing_gain_index = None
        st.session_state.new_pain_input = ""
        st.session_state.new_gain_input = ""
        clear_inline_notice("pain")
        clear_inline_notice("gain")
        st.session_state.show_restore_prompt = False
        st.rerun()


# ============ Main App ============
def main():
    """Main application entry point."""
    init_session_state()
    render_theme_picker()
    apply_theme_styles()
    inject_hotkeys_script()

    render_header()
    render_progress()
    render_progress_narrative()

    st.markdown("---")

    # Render current step
    if st.session_state.step == 0:
        render_welcome()
    elif st.session_state.step == 1:
        render_job_description()
    elif st.session_state.step == 2:
        render_pain_points()
    elif st.session_state.step == 3:
        render_gain_points()
    elif st.session_state.step == 4:
        render_review()

    # Auto-save session when there's meaningful content (not on welcome or review step)
    if AUTO_SAVE_ENABLED and st.session_state.step > 0 and st.session_state.step < 4:
        has_content = (
            st.session_state.job_description.strip() or
            len(st.session_state.pain_points) > 0 or
            len(st.session_state.gain_points) > 0
        )
        if has_content:
            save_session_to_file()


if __name__ == "__main__":
    main()
