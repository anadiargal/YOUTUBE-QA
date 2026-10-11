"""
Custom CSS + inline SVG icons.

Streamlit's default look is overridden with a small design system:
white surfaces, hairline borders, 12-16px radius, near-black primary buttons.
Colors are CSS variables so Light / Dark mode only swaps the variable block.
"""

_ICON_PATHS = {
    "link": '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
    "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    "user": '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    "calendar": '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
    "message": '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><path d="M8 9h8M8 13h5"/>',
    "sparkles": '<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/><path d="M19 3v4M17 5h4"/>',
    "bot": '<rect x="4" y="7" width="16" height="13" rx="3"/><path d="M12 7V3"/><circle cx="9" cy="13" r="1" fill="currentColor"/><circle cx="15" cy="13" r="1" fill="currentColor"/>',
    "alert": '<circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/>',
}


def svg(name: str, size: int = 18) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        f'style="flex:none;vertical-align:middle">{_ICON_PATHS[name]}</svg>'
    )


def brand_html() -> str:
    return (
        '<div class="brand">'
        '<svg width="38" height="28" viewBox="0 0 38 28"><rect width="38" height="28" rx="8" fill="currentColor"/>'
        '<path d="M15 8l10 6-10 6z" class="brand-play"/></svg>'
        '<span class="brand-text">YouTube Q&amp;A</span></div>'
    )


def _icon_uri(name: str, color: str = "%236b7280") -> str:
    """SVG as a CSS data-URI (used for icons inside text inputs)."""
    inner = _ICON_PATHS[name].replace('"', "'")
    return (
        "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='20' height='20' "
        f"viewBox='0 0 24 24' fill='none' stroke='{color}' stroke-width='2' stroke-linecap='round' "
        f"stroke-linejoin='round'>{inner}</svg>\")"
    )


_LIGHT = """
  --bg:#ffffff; --surface:#ffffff; --surface-2:#f4f5f9; --input-bg:#f8f9fc;
  --border:#e5e7ee; --text:#0f1222; --muted:#6b7280; --active:#e6eeff;
  --primary:#0b0c14; --primary-text:#ffffff; --mark:#fff2a8; --shadow:0 1px 2px rgba(16,24,40,.04);
  --danger-bg:#fff4f4; --danger-border:#f5c6c6; --danger-text:#9b1c1c;
"""
_DARK = """
  --bg:#0c0e13; --surface:#13161d; --surface-2:#1b1f29; --input-bg:#171a22;
  --border:#262b37; --text:#eef0f6; --muted:#9aa3b2; --active:#1c2b4a;
  --primary:#eef0f6; --primary-text:#0c0e13; --mark:#5a4b00; --shadow:none;
  --danger-bg:#2a1517; --danger-border:#5b2a2d; --danger-text:#ffb4b4;
"""

_CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

.stApp { background: var(--bg); color: var(--text); font-family: 'Inter', -apple-system, 'Segoe UI', Roboto, sans-serif; }
.stApp button, .stApp input, .stApp textarea { font-family: 'Inter', -apple-system, 'Segoe UI', Roboto, sans-serif; }
.stApp, .stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
[data-testid="stMarkdownContainer"] p, [data-testid="stWidgetLabel"] p, [data-testid="stCaptionContainer"] { color: var(--text); }
header[data-testid="stHeader"], #MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }
.stMainBlockContainer, .block-container { max-width: 1400px; padding: 1.1rem 2rem 2.5rem; }
[data-testid="stVerticalBlock"] { gap: .75rem; }
.stApp .muted { color: var(--muted); }

/* ---------- Header ---------- */
.st-key-header { border-bottom: 1px solid var(--border); padding-bottom: .55rem; margin-bottom: .9rem; }
.stApp .brand { display: flex; align-items: center; gap: .65rem; color: var(--text); }
.stApp .brand .brand-play { fill: var(--bg); }
.stApp .brand-text { font-weight: 700; font-size: 1.2rem; letter-spacing: -.01em; color: var(--text); white-space: nowrap; }
.st-key-nav [role="radiogroup"] { gap: 1.7rem; justify-content: center; flex-wrap: wrap; }
.st-key-nav label { margin: 0; padding: 0 0 .55rem; border-bottom: 2px solid transparent; cursor: pointer; }
.st-key-nav label > div:first-child { display: none; }
.st-key-nav label p { font-size: .95rem; font-weight: 500; color: var(--muted); }
.st-key-nav label:hover p { color: var(--text); }
.st-key-nav label:has(input:checked) { border-bottom-color: var(--text); }
.st-key-nav label:has(input:checked) p { color: var(--text); font-weight: 700; }
.stApp .avatar-user { width: 40px; height: 40px; border-radius: 50%; background: #6b7280; color: #fff; display: flex;
  align-items: center; justify-content: center; font-weight: 600; margin-left: auto; }
.st-key-theme_btn button { border-radius: 50%; width: 40px; height: 40px; min-height: 40px; padding: 0; margin-left: auto; background: var(--surface-2); border: none; }

/* ---------- Buttons ---------- */
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
  border-radius: 10px; border: 1px solid var(--border); background: var(--surface); color: var(--text);
  font-weight: 500; box-shadow: var(--shadow); transition: background .15s, border-color .15s; }
.stButton > button:hover, .stDownloadButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover { background: var(--surface-2); border-color: var(--border); color: var(--text); }
.stApp button p, .stApp button span { color: inherit; }
.stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button[kind="primaryFormSubmit"],
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {
  background: var(--primary); color: var(--primary-text); border: none; font-weight: 600; }
[data-testid="stBaseButton-primary"]:hover, [data-testid="stBaseButton-primaryFormSubmit"]:hover { background: var(--primary); opacity: .88; color: var(--primary-text); }

/* ---------- Inputs ---------- */
[data-baseweb="input"], [data-baseweb="base-input"] { background: var(--input-bg) !important; border-radius: 12px !important; }
[data-baseweb="input"] { border: 1px solid var(--border) !important; }
[data-baseweb="input"]:focus-within { border-color: var(--muted) !important; box-shadow: none !important; }
.stApp input { color: var(--text) !important; -webkit-text-fill-color: var(--text) !important; }
.stApp input::placeholder { color: var(--muted) !important; -webkit-text-fill-color: var(--muted) !important; opacity: 1; }
[data-testid="stForm"] { border: none; padding: 0; }
.st-key-url_input [data-baseweb="input"] { min-height: 52px; }
.st-key-url_input input { padding-left: 46px !important; font-size: .98rem; background-repeat: no-repeat; background-position: 16px center; background-image: __LINK__; }
.st-key-analyze_btn button { height: 52px; font-size: .98rem; border-radius: 12px; }
.st-key-tsearch input { padding-left: 40px !important; background-repeat: no-repeat; background-position: 13px center; background-image: __SEARCH__; }
.st-key-ask_input input { height: 48px; padding-left: 14px; }
.st-key-send_btn button { height: 48px; border-radius: 12px; }
.st-key-send_btn button p { display: none; }
.st-key-dl { display: flex; justify-content: flex-end; }
.st-key-dl button { padding: .3rem .8rem; background: var(--surface-2); border: none; box-shadow: none; }

/* ---------- Workspace panels ---------- */
.st-key-workspace { border: 1px solid var(--border); border-radius: 20px; padding: 1.25rem; background: var(--surface); }
.st-key-panel_mid, .st-key-panel_right { border: 1px solid var(--border); border-radius: 16px; padding: 1rem 1rem .9rem; background: var(--surface); box-shadow: var(--shadow); }
[data-testid="stVideo"], [data-testid="stVideo"] iframe, [data-testid="stVideo"] video { border-radius: 14px; overflow: hidden; }
[data-testid="stVideo"] iframe { width: 100%; aspect-ratio: 16/9; height: auto; }
.stApp .panel-title { display: flex; align-items: center; gap: .55rem; font-weight: 700; font-size: 1.1rem; color: var(--text); }
.stApp .video-title { font-size: 1.25rem; font-weight: 700; letter-spacing: -.01em; margin: .7rem 0 .15rem; line-height: 1.3; color: var(--text); }
.stApp .channel-row { display: flex; align-items: center; gap: .6rem; color: var(--muted); font-size: .9rem; flex-wrap: wrap; }
.stApp .channel-avatar { width: 32px; height: 32px; border-radius: 50%; background: var(--primary); color: var(--primary-text); display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: .85rem; }
.stApp .info-card { border: 1px solid var(--border); border-radius: 14px; padding: 1rem 1.1rem; margin-top: .9rem; background: var(--surface); }
.stApp .info-card h4 { display: flex; align-items: center; gap: .55rem; margin: 0 0 .8rem; font-size: 1.02rem; font-weight: 700; color: var(--text); }
.stApp .info-row { display: flex; align-items: center; gap: .7rem; padding: .42rem 0; font-size: .92rem; }
.stApp .info-row .k { display: flex; align-items: center; gap: .6rem; color: var(--muted); width: 8.2rem; }
.stApp .info-row .v { color: var(--text); }

/* ---------- Transcript ---------- */
.st-key-transcript_box [data-testid="stVerticalBlock"] { gap: .15rem; }
[class*="st-key-seg_"] { padding: .3rem .35rem; border-radius: 10px; }
[class*="st-key-seg_"] [data-testid="stHorizontalBlock"] { gap: .4rem; }
[class*="st-key-seg_"] .stButton > button { border: none; background: transparent; box-shadow: none; padding: .1rem .35rem; min-height: 0;
  color: var(--muted); font-variant-numeric: tabular-nums; justify-content: flex-start; font-weight: 500; }
[class*="st-key-seg_"] .stButton > button:hover { background: transparent; color: var(--text); text-decoration: underline; }
.stApp .seg-text { font-size: .9rem; line-height: 1.55; color: var(--text); padding-top: .1rem; }
.stApp mark { background: var(--mark); color: inherit; border-radius: 3px; padding: 0 1px; }

/* ---------- Chat ---------- */
.stApp .msg { display: flex; gap: .6rem; margin: .45rem 0; align-items: flex-start; }
.stApp .msg.user { justify-content: flex-end; }
.stApp .msg .bubble { padding: .65rem .9rem; border-radius: 12px; font-size: .9rem; line-height: 1.6; max-width: 84%; }
.stApp .msg.user .bubble { background: var(--primary); color: var(--primary-text); }
.stApp .msg.ai .bubble { background: var(--surface-2); color: var(--text); }
.stApp .msg.err .bubble { background: var(--danger-bg); border: 1px solid var(--danger-border); color: var(--danger-text); }
.stApp .msg .ava { width: 34px; height: 34px; border-radius: 50%; flex: none; display: flex; align-items: center; justify-content: center; background: var(--surface-2); color: var(--text); }
.stApp .msg .ava.bot { background: var(--primary); color: var(--primary-text); border-radius: 10px; }
.stApp .msg-meta { font-size: .72rem; color: var(--muted); margin: -.15rem 0 .1rem 44px; }
.stApp .src-label { font-size: .82rem; color: var(--muted); padding-top: .35rem; }
[class*="st-key-srcs_"] { padding-left: 44px; }
[class*="st-key-srcs_"] [data-testid="stHorizontalBlock"] { gap: .4rem; align-items: center; }
[class*="st-key-srcs_"] .stButton > button { border-radius: 10px; background: var(--surface-2); border: none; box-shadow: none; font-weight: 600; font-size: .88rem; padding: .25rem .8rem; }
.stApp .chat-empty { color: var(--muted); font-size: .9rem; text-align: center; padding: 2.2rem 1rem; }
.stApp .sugg-title { display: flex; align-items: center; gap: .5rem; font-weight: 600; font-size: .95rem; color: var(--text); margin-top: .2rem; }
[class*="st-key-sq_"] .stButton > button { justify-content: flex-start; text-align: left; background: var(--surface-2); border: 1px solid var(--border);
  box-shadow: none; font-weight: 400; font-size: .88rem; padding: .5rem .8rem; border-radius: 10px; height: auto; min-height: 0; }
.st-key-suggestions [data-testid="stVerticalBlock"] { gap: .4rem; }
.st-key-chatbox { border-bottom: 1px solid var(--border); padding-bottom: .5rem; }

/* ---------- Pages ---------- */
.stApp .hero { border: 1px solid var(--border); border-radius: 20px; padding: 3rem 1.5rem; text-align: center; background: var(--surface); margin-top: .5rem; }
.stApp .hero h1 { font-size: 2rem; letter-spacing: -.02em; margin: 0 0 .6rem; color: var(--text); }
.stApp .hero p { color: var(--muted); max-width: 640px; margin: 0 auto 1.6rem; font-size: 1rem; line-height: 1.6; }
.stApp .pipeline { display: flex; flex-wrap: wrap; gap: .5rem; justify-content: center; align-items: center; }
.stApp .chip { border: 1px solid var(--border); background: var(--surface-2); border-radius: 999px; padding: .35rem .85rem; font-size: .82rem; font-weight: 500; color: var(--text); }
.stApp .arrow { color: var(--muted); }
.stApp .page-title { font-size: 1.5rem; font-weight: 700; letter-spacing: -.01em; margin: .3rem 0 .2rem; color: var(--text); }
.stApp .err-card { display: flex; gap: .7rem; align-items: flex-start; border: 1px solid var(--danger-border); background: var(--danger-bg); color: var(--danger-text);
  border-radius: 12px; padding: .85rem 1rem; margin: .6rem 0; font-size: .92rem; }
[class*="st-key-vid_"], [class*="st-key-hist_"], .st-key-settings_card { border: 1px solid var(--border); border-radius: 16px; padding: .9rem; background: var(--surface); }
[class*="st-key-vid_"] img, [class*="st-key-hist_"] img { border-radius: 10px; }
[data-testid="stStatus"], [data-testid="stExpander"] { border-radius: 14px; border-color: var(--border); background: var(--surface); }

/* ---------- Responsive ---------- */
.stApp [data-testid="stHorizontalBlock"] { min-width: 0; }
.stApp, .stMainBlockContainer { overflow-x: hidden; }
@media (max-width: 1000px) { .stMainBlockContainer, .block-container { padding: 1rem 1rem 2rem; } .st-key-workspace { padding: .8rem; } }
@media (max-width: 640px) {
  .brand-text { display: none; }
  .st-key-header [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; align-items: center; }
  .st-key-header [data-testid="stColumn"] { min-width: 0 !important; flex: 1 1 auto !important; width: auto !important; }
  .st-key-nav [role="radiogroup"] { gap: .8rem; }
  .st-key-nav label p { font-size: .82rem; }
  .stApp .avatar-user { display: none; }
  .stApp .hero { padding: 2rem 1rem; } .stApp .hero h1 { font-size: 1.5rem; }
}
"""


def build_css(theme: str) -> str:
    variables = _DARK if theme == "dark" else _LIGHT
    css = _CSS.replace("__LINK__", _icon_uri("link")).replace("__SEARCH__", _icon_uri("search"))
    return f":root {{{variables}}}\n{css}"
