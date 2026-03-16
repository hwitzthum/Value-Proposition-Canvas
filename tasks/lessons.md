# Lessons Learned

## 2026-03-16: Always grep for ALL call sites before changing a function signature

**What happened:** Changed `_quality_level_label()` to require a new `ideal_total` parameter during the simplify review. Updated 2 of 3 call sites but missed the one in `render_export_bar()`, causing a runtime TypeError.

**Rule:** When adding/removing/changing parameters on any function, always `grep` for ALL usages of that function name across the entire codebase before committing. Don't rely on the call sites you already know about.

## 2026-03-16: Streamlit widget keys cannot be mutated after instantiation

**What happened:** Tried to set `st.session_state["spatial_job_input"]` after the text_area was already rendered — got `StreamlitAPIException`. Then tried popping the widget key before the widget on rerun — Streamlit restored it from its internal registry, so the text_area stayed empty.

**Rule:** Never directly set or pop widget keys from `st.session_state`. Use versioned keys (`key=f"widget_v{ver}"`) and bump the version counter to force widget re-initialization with a new `value=` parameter. Also bump the version in any reset/clear function.
