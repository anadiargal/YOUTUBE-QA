"""
Central configuration.

Everything you may want to tweak while learning lives here. The Settings page
in the UI overrides the DEFAULTS at runtime (per browser session).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Reads GOOGLE_API_KEY (and friends) from a local ".env" file.
# The key is never hardcoded and never shown in the UI.
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"            # library.json, transcripts, FAISS indexes
TRANSCRIPT_DIR = DATA_DIR / "transcripts"
INDEX_DIR = DATA_DIR / "indexes"

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")

# Languages tried (in order) when fetching a transcript.
TRANSCRIPT_LANGUAGES = ("en", "en-US", "en-GB", "en-IN", "hi")

# The raw caption snippets from YouTube are only 2-5 seconds long. For display
# (and as the unit we chunk), we merge them into ~20 second "segments".
SEGMENT_SECONDS = 20

# Runtime-adjustable settings (Settings page).
DEFAULTS = {
    "theme": "light",
    "chunk_size": 700,            # tokens per chunk (approx. 500-1000 recommended)
    "chunk_overlap": 120,         # tokens shared between neighbouring chunks (100-150)
    "top_k": 4,                   # how many chunks to retrieve per question
    "similarity_threshold": 0.55, # cosine similarity below which a chunk is "irrelevant"
}

# Suggested questions are generated once per video.
NUM_SUGGESTED_QUESTIONS = 5
