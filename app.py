"""
YouTube Q&A - transcript-grounded RAG, Streamlit UI.

This file is ONLY the interface. The RAG logic lives in services/ (start with
services/pipeline.py). Streamlit re-runs this script top-to-bottom on every
interaction, so durable state lives in st.session_state.
"""
import html
import re

import streamlit as st
import streamlit.components.v1 as components

import config
from services import pipeline, storage
from utils.errors import AppError, logger
from utils.helpers import (
    format_date, format_timestamp, format_views, highlight_matches,
    inline_markdown_to_html, thumbnail_url, transcript_to_text,
)
from utils.styles import brand_html, build_css, svg

st.set_page_config(page_title="YouTube Q&A", page_icon="▶️", layout="wide", initial_sidebar_state="collapsed")

PAGES = ["Home", "My Videos", "History", "Settings"]
ss = st.session_state


# --------------------------------------------------------------------------- state
def init_state():
    ss.setdefault("settings", dict(config.DEFAULTS))
    ss.setdefault("current", None)       # the loaded video workspace (meta, segments, FAISS index, ...)
    ss.setdefault("chats", {})           # video_id -> list of chat messages
    ss.setdefault("highlight", None)     # (start, end) seconds of the highlighted transcript range
    ss.setdefault("seek", None)          # {"t": seconds} -> where the player should start
    ss.setdefault("scroll_transcript", False)
    ss.setdefault("scroll_chat", False)
    ss.setdefault("error", None)
    ss.setdefault("nav", "Home")


# --------------------------------------------------------------------------- callbacks
def seek_to(start: float, end: float, scroll: bool = True):
    """Used by transcript timestamps AND answer citations: seek player + highlight transcript."""
    ss.seek = {"t": int(start)}
    ss.highlight = (float(start), float(end))
    ss.scroll_transcript = scroll


def ask(question: str):
    ss.pending_q = question


def submit_question():
    question = (ss.get("ask_input") or "").strip()
    if question:
        ss.pending_q = question


def toggle_theme():
    ss.settings["theme"] = "dark" if ss.settings["theme"] == "light" else "light"


def open_video(video_id: str):
    try:
        ss.current = pipeline.load_video(video_id)
        ss.highlight, ss.seek, ss.error = None, None, None
    except AppError as exc:
        ss.error = exc.user_message
    ss.nav = "Home"


def delete_video(video_id: str):
    storage.delete_video(video_id)
    ss.chats.pop(video_id, None)
    if ss.current and ss.current["meta"]["video_id"] == video_id:
        ss.current = None


def sync_setting(name: str, widget_key: str, transform=lambda v: v):
    """Settings widgets are copied into ss.settings so values survive page changes."""
    ss.settings[name] = transform(ss[widget_key])


# --------------------------------------------------------------------------- header
def render_header():
    with st.container(key="header"):
        c1, c2, c3 = st.columns([2.2, 4.2, 1.5], vertical_alignment="center")
        c1.markdown(brand_html(), unsafe_allow_html=True)
        with c2:
            st.radio("Navigation", PAGES, key="nav", horizontal=True, label_visibility="collapsed")
        with c3:
            a, b = st.columns(2, vertical_alignment="center")
            icon = ":material/dark_mode:" if ss.settings["theme"] == "light" else ":material/light_mode:"
            a.button("\u200b", key="theme_btn", icon=icon, on_click=toggle_theme, help="Toggle light / dark mode")
            b.markdown('<div class="avatar-user">U</div>', unsafe_allow_html=True)


def error_card(message: str):
    st.markdown(f'<div class="err-card">{svg("alert", 20)}<div>{html.escape(message)}</div></div>', unsafe_allow_html=True)


# --------------------------------------------------------------------------- home
def run_ingest(url: str):
    """Runs the ingestion pipeline while showing intentional progress states."""
    ss.error = None
    with st.status("Analyzing video…", expanded=True) as status:
        try:
            video = pipeline.ingest(url, ss.settings, on_step=lambda msg: st.write(msg))
            ss.current = video
            ss.highlight, ss.seek = None, None
            status.update(label="Ready ✓", state="complete", expanded=False)
        except AppError as exc:
            ss.error = exc.user_message
            status.update(label="Couldn't analyze this video", state="error")
        except Exception:  # never show raw exceptions to the user
            logger.exception("Unexpected ingestion error")
            ss.error = "Something unexpected went wrong while analyzing this video. Please try again."
            status.update(label="Couldn't analyze this video", state="error")
    st.rerun()


def render_url_bar():
    with st.form("url_form", border=False):
        c1, c2 = st.columns([6, 1.35], vertical_alignment="center")
        url = c1.text_input("YouTube URL", key="url_input", placeholder="Paste YouTube video URL here…",
                            label_visibility="collapsed")
        submitted = c2.form_submit_button("Analyze Video  →", key="analyze_btn", type="primary", use_container_width=True)
    if submitted:
        run_ingest(url)


def render_empty_state():
    steps = ["Transcript", "Chunks", "Embeddings", "FAISS search", "Gemini", "Cited answer"]
    chips = '<span class="arrow">→</span>'.join(f'<span class="chip">{s}</span>' for s in steps)
    st.markdown(
        f'<div class="hero"><h1>Ask questions about any YouTube video</h1>'
        f"<p>Paste a link above. Answers come <b>only</b> from the video's transcript — "
        f"if it isn't in the video, you'll be told so instead of getting a guess.</p>"
        f'<div class="pipeline">{chips}</div></div>',
        unsafe_allow_html=True,
    )


def render_home():
    if not config.GOOGLE_API_KEY:
        error_card("GOOGLE_API_KEY is not set. Copy .env.example to .env, add your key, and restart the app.")
    render_url_bar()
    if ss.error:
        error_card(ss.error)
    if ss.current:
        render_workspace(ss.current)
    else:
        render_empty_state()


# --------------------------------------------------------------------------- workspace
def active_indices(segments, highlight):
    if not highlight:
        return []
    start, end = highlight
    return [i for i, s in enumerate(segments) if s["start"] < end and s["end"] > start - 0.01 and s["end"] > start]


def render_workspace(video: dict):
    segments = video["segments"]
    active = active_indices(segments, ss.highlight)
    if active:  # the highlight color for the active transcript segment(s)
        rules = ",".join(f".st-key-seg_{i}" for i in active)
        st.markdown(f"<style>{rules}{{background: var(--active) !important;}}</style>", unsafe_allow_html=True)

    with st.container(key="workspace"):
        left, mid, right = st.columns([1.15, 1, 1.05], gap="medium")
        with left:
            render_video_column(video)
        with mid:
            render_transcript_panel(video, active)
        with right:
            render_qa_panel(video)


def render_video_column(video: dict):
    meta = video["meta"]
    url = f"https://www.youtube.com/watch?v={meta['video_id']}"
    if ss.seek:  # a citation / timestamp was clicked -> player (re)starts at that second
        st.video(url, start_time=ss.seek["t"], autoplay=True)
    else:
        st.video(url)

    channel = meta.get("channel") or ""
    bits = [b for b in (channel, format_views(meta.get("views")), format_date(meta.get("published"))) if b]
    initial = html.escape((channel or "?")[:1].upper())
    st.markdown(
        f'<div class="video-title">{html.escape(meta["title"])}</div>'
        f'<div class="channel-row"><div class="channel-avatar">{initial}</div>'
        f'<span>{" &nbsp;•&nbsp; ".join(html.escape(b) for b in bits)}</span></div>',
        unsafe_allow_html=True,
    )
    duration = format_timestamp(meta["duration"]) if meta.get("duration") else "—"
    rows = [("user", "Channel", channel or "—"), ("clock", "Duration", duration),
            ("calendar", "Published", format_date(meta.get("published")) or "—")]
    rows_html = "".join(
        f'<div class="info-row"><div class="k">{svg(icon, 18)}{label}</div><div class="v">{html.escape(value)}</div></div>'
        for icon, label, value in rows
    )
    st.markdown(f'<div class="info-card"><h4>{svg("info", 20)}Video Info</h4>{rows_html}</div>', unsafe_allow_html=True)


def render_transcript_panel(video: dict, active: list[int]):
    segments = video["segments"]
    with st.container(key="panel_mid"):
        h1, h2 = st.columns([1, 1], vertical_alignment="center")
        h1.markdown('<div class="panel-title">Transcript</div>', unsafe_allow_html=True)
        with h2:
            st.download_button("Download", transcript_to_text(segments), file_name=f"{video['meta']['video_id']}_transcript.txt",
                               mime="text/plain", icon=":material/download:", key="dl")
        # Transcript search is plain string matching - fast, no LLM call.
        query = st.text_input("Search transcript", key="tsearch", placeholder="Search transcript…", label_visibility="collapsed")

        needle = query.strip().lower()
        shown = [(i, s) for i, s in enumerate(segments) if not needle or needle in s["text"].lower()]
        if needle:
            st.caption(f"{len(shown)} matching segment{'s' if len(shown) != 1 else ''}")

        with st.container(height=520, border=False, key="transcript_box"):
            if not shown:
                st.markdown('<div class="chat-empty">No matches in this transcript.</div>', unsafe_allow_html=True)
            for i, seg in shown:
                with st.container(key=f"seg_{i}"):
                    c1, c2 = st.columns([1, 4.6], vertical_alignment="top")
                    c1.button(format_timestamp(seg["start"]), key=f"ts_{i}", on_click=seek_to,
                              args=(seg["start"], seg["end"], False), help="Jump to this moment")
                    c2.markdown(f'<div class="seg-text">{highlight_matches(seg["text"], query)}</div>', unsafe_allow_html=True)

    if ss.scroll_transcript and active:  # bring the cited segment into view
        scroll_js(f"const el = doc.querySelector('.st-key-seg_{active[0]}'); if (el) el.scrollIntoView({{behavior:'smooth', block:'center'}});")
    ss.scroll_transcript = False


def scroll_js(body: str):
    """Tiny helper: run JS against the parent Streamlit page (for scrolling only)."""
    page = f"<script>try{{const doc = window.parent.document; setTimeout(() => {{ {body} }}, 200);}}catch(e){{}}</script>"
    if hasattr(st, "iframe"):          # newer Streamlit (st.components.v1.html is deprecated there)
        st.iframe(page, height=1)
    else:
        components.html(page, height=0)


# --------------------------------------------------------------------------- Q&A
def render_message(idx: int, msg: dict):
    if msg["role"] == "user":
        st.markdown(
            f'<div class="msg user"><div class="bubble">{html.escape(msg["content"])}</div>'
            f'<div class="ava">{svg("user", 18)}</div></div>', unsafe_allow_html=True)
        return

    css = "msg ai err" if msg.get("error") else "msg ai"
    st.markdown(
        f'<div class="{css}"><div class="ava bot">{svg("bot", 18)}</div>'
        f'<div class="bubble">{inline_markdown_to_html(msg["content"])}</div></div>', unsafe_allow_html=True)
    if msg.get("best_score") is not None and not msg.get("error"):
        st.markdown(f'<div class="msg-meta">Best transcript match: {msg["best_score"]:.2f} · threshold {msg["threshold"]:.2f}</div>',
                    unsafe_allow_html=True)
    if msg.get("sources"):
        with st.container(key=f"srcs_{idx}"):
            for j, src in enumerate(msg["sources"]):
                c1, c2, _ = st.columns([1, 2.4, 1.2], vertical_alignment="center")
                if j == 0:
                    c1.markdown('<div class="src-label">Source:</div>', unsafe_allow_html=True)
                c2.button(f"{format_timestamp(src['start'])} - {format_timestamp(src['end'])}", key=f"src_{idx}_{j}",
                          icon=":material/play_circle:", on_click=seek_to, args=(src["start"], src["end"]),
                          help="Jump to this moment in the video")


def process_question(video: dict, chat: list[dict], question: str):
    """Retrieve -> threshold -> Gemini -> append the answer (or a friendly error)."""
    with st.status("Searching transcript…", expanded=False) as status:
        try:
            result = pipeline.answer(question, video, ss.settings, on_step=lambda m: status.update(label=m))
            chat.append({
                "role": "assistant", "content": result.text, "sources": result.sources, "refused": result.refused,
                "best_score": result.best_score, "threshold": ss.settings["similarity_threshold"],
            })
            status.update(label="Done", state="complete")
        except AppError as exc:
            chat.append({"role": "assistant", "content": exc.user_message, "error": True})
            status.update(label="Something went wrong", state="error")
        except Exception:
            logger.exception("Unexpected question error")
            chat.append({"role": "assistant", "error": True,
                         "content": "Something went wrong while processing your question. Please try again."})
            status.update(label="Something went wrong", state="error")
    ss.scroll_chat = True
    st.rerun()


def render_qa_panel(video: dict):
    vid = video["meta"]["video_id"]
    chat = ss.chats.setdefault(vid, [])
    pending = ss.pop("pending_q", None)
    if pending:
        chat.append({"role": "user", "content": pending})

    with st.container(key="panel_right"):
        st.markdown(f'<div class="panel-title">{svg("message", 22)}Ask Questions</div>', unsafe_allow_html=True)

        with st.container(height=330, border=False, key="chatbox"):
            if not chat:
                st.markdown('<div class="chat-empty">Ask anything about this video.<br>Answers use only its transcript.</div>',
                            unsafe_allow_html=True)
            for idx, msg in enumerate(chat):
                render_message(idx, msg)
            if pending:
                process_question(video, chat, pending)

        if video["suggested"]:
            st.markdown(f'<div class="sugg-title">{svg("sparkles", 20)}Suggested Questions</div>', unsafe_allow_html=True)
            with st.container(key="suggestions"):
                for k, q in enumerate(video["suggested"]):
                    st.button(q, key=f"sq_{k}", icon=":material/search:", on_click=ask, args=(q,), use_container_width=True)

        with st.form("ask_form", clear_on_submit=True, border=False):
            c1, c2 = st.columns([6, 1], vertical_alignment="center")
            c1.text_input("Question", key="ask_input", placeholder="Ask a question about this video…", label_visibility="collapsed")
            c2.form_submit_button("Send", key="send_btn", icon=":material/send:", type="primary",
                                  on_click=submit_question, use_container_width=True)

    if ss.scroll_chat:
        scroll_js("const box = doc.querySelector('.st-key-chatbox'); if (box) { for (const e of [box, ...box.querySelectorAll('*')]) "
                  "{ if (e.scrollHeight > e.clientHeight + 5 && getComputedStyle(e).overflowY !== 'visible') { e.scrollTop = e.scrollHeight; break; } } }")
        ss.scroll_chat = False


# --------------------------------------------------------------------------- other pages
def render_my_videos():
    st.markdown('<div class="page-title">My Videos</div><div class="muted">Videos you have analyzed. Open one to continue asking questions.</div>',
                unsafe_allow_html=True)
    videos = storage.list_videos()
    if not videos:
        st.markdown('<div class="hero"><p>No videos yet. Analyze one from Home.</p></div>', unsafe_allow_html=True)
        return
    cols = st.columns(3, gap="medium")
    for n, v in enumerate(videos):
        with cols[n % 3]:
            with st.container(key=f"vid_{v['video_id']}"):
                st.image(v.get("thumbnail") or thumbnail_url(v["video_id"]), use_container_width=True)
                st.markdown(f"**{html.escape(v['title'])}**", unsafe_allow_html=True)
                st.caption(f"{v.get('channel') or 'Unknown channel'} · analyzed {format_date(v['analyzed_at'])}")
                b1, b2 = st.columns([3, 1])
                b1.button("Open workspace", key=f"open_{v['video_id']}", on_click=open_video, args=(v["video_id"],), use_container_width=True)
                b2.button("", key=f"del_{v['video_id']}", icon=":material/delete:", on_click=delete_video,
                          args=(v["video_id"],), help="Remove from library", use_container_width=True)


def render_history():
    st.markdown('<div class="page-title">History</div><div class="muted">Everything you have analyzed, newest first.</div>',
                unsafe_allow_html=True)
    events = storage.list_history()
    if not events:
        st.markdown('<div class="hero"><p>Your history is empty.</p></div>', unsafe_allow_html=True)
        return
    for n, v in enumerate(events):
        with st.container(key=f"hist_{n}"):
            c1, c2, c3, c4 = st.columns([1.3, 4, 1.6, 1.3], vertical_alignment="center")
            c1.image(v.get("thumbnail") or thumbnail_url(v["video_id"]), use_container_width=True)
            c2.markdown(f"**{html.escape(v['title'])}**<br><span class='muted'>{html.escape(v.get('channel') or '')}</span>",
                        unsafe_allow_html=True)
            c3.markdown(f"<span class='muted'>Analyzed<br>{format_date(v['analyzed_at'])}</span>", unsafe_allow_html=True)
            c4.button("Open", key=f"hopen_{n}", on_click=open_video, args=(v["video_id"],), use_container_width=True)


def render_settings():
    s = ss.settings
    st.markdown('<div class="page-title">Settings</div><div class="muted">Retrieval and chunking behavior. '
                'Chunk settings apply to the next video you analyze.</div>', unsafe_allow_html=True)
    with st.container(key="settings_card"):
        st.radio("Theme", ["Light", "Dark"], index=0 if s["theme"] == "light" else 1, horizontal=True, key="w_theme",
                 on_change=sync_setting, args=("theme", "w_theme", lambda v: v.lower()))
        st.number_input("Chunk size (tokens)", 200, 2000, int(s["chunk_size"]), step=50, key="w_chunk_size",
                        on_change=sync_setting, args=("chunk_size", "w_chunk_size", int),
                        help="Approx. tokens per chunk. 500–1000 is a good range.")
        st.number_input("Chunk overlap (tokens)", 0, 500, int(s["chunk_overlap"]), step=10, key="w_chunk_overlap",
                        on_change=sync_setting, args=("chunk_overlap", "w_chunk_overlap", int),
                        help="Tokens repeated between neighbouring chunks so ideas aren't cut in half.")
        st.slider("Top K retrieval", 1, 10, int(s["top_k"]), key="w_top_k",
                  on_change=sync_setting, args=("top_k", "w_top_k", int), help="How many chunks are retrieved per question.")
        st.slider("Similarity threshold", 0.0, 1.0, float(s["similarity_threshold"]), 0.01, key="w_threshold",
                  on_change=sync_setting, args=("similarity_threshold", "w_threshold", float),
                  help="Chunks scoring below this are treated as irrelevant. Raise it for stricter refusals, lower it if "
                       "relevant questions are being refused.")
        if s["chunk_overlap"] >= s["chunk_size"] // 2:
            st.warning("Overlap should be well below half the chunk size; it will be capped automatically.")


# --------------------------------------------------------------------------- main
def main():
    init_state()
    st.markdown(f"<style>{build_css(ss.settings['theme'])}</style>", unsafe_allow_html=True)
    render_header()
    {"Home": render_home, "My Videos": render_my_videos, "History": render_history, "Settings": render_settings}[ss.nav]()


main()
