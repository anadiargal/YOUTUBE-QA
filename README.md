# YOUTUBE - Q&A

Paste a YouTube link → the app fetches the transcript, chunks it, embeds it with Gemini, stores the vectors in FAISS,
and answers questions **only from the transcript** (with clickable timestamp sources). Anything the video doesn't
cover gets a refusal, never a guess.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                    # then put your key in GOOGLE_API_KEY
streamlit run app.py
```

Get a free key at <https://aistudio.google.com/apikey>. Offline logic tests (no key needed): `python tests/test_core.py`.

## How the RAG pipeline works (read in this order)

| # | File | Concept |
|---|------|---------|
| 1 | `services/pipeline.py` | The whole flow in one place: ingest + ask |
| 2 | `services/transcript.py` | What a transcript is (timed snippets), cleaning, segments |
| 3 | `services/chunking.py` | Why chunk, why overlap, keeping timestamps |
| 4 | `services/embeddings.py` | What an embedding is, normalization → cosine similarity |
| 5 | `services/vector_store.py` | How vectors are stored/searched in FAISS |
| 6 | `services/retriever.py` | Top-K retrieval + the relevance threshold |
| 7 | `prompts/qa_prompt.py` | Strict grounded prompt, exact refusal sentence |
| 8 | `services/qa.py` | Context → Gemini → answer, refusal detection, timestamp citations |

### Three layers against hallucination
1. **Similarity threshold** – chunks below `similarity_threshold` never reach Gemini. If none survive, the app refuses *without calling the LLM*.
2. **Strict system prompt** – only the supplied excerpts may be used; exact refusal sentence otherwise.
3. **Refusal normalization** – a refusal is shown verbatim with no sources.

### How citations reach the video
Chunks carry `start_time`/`end_time` metadata → Gemini reports which numbered excerpts it used → `qa.py` narrows each
to the best-matching ~20 s segments → the UI shows `05:12 - 05:34 ▶`. Clicking it restarts the embedded player at
that second and highlights (and scrolls to) the matching transcript segments.

## Settings & tuning
* **Chunk size / overlap / Top K / threshold** live on the Settings page (defaults in `config.py`).
* Every answer shows its best match score next to the threshold. If good questions get refused, lower the threshold;
  if off-topic questions slip through, raise it. Cosine scores depend on the embedding model, so tune on your own videos.
* Re-analyzing a video with different chunk settings rebuilds its index; otherwise saved data in `data/` is reused.

## Notes
* Data is stored locally in `data/` (git-ignored): `library.json`, cleaned transcripts, FAISS indexes.
* Metadata (views, publish date, duration) is scraped best-effort; if YouTube changes its page the app still works.
* YouTube sometimes blocks transcript requests from cloud/VPN IPs — run locally if you see that message.
* The player is Streamlit's `st.video`. Seeking works by restarting playback at the cited second.
* Colors and layout are driven by CSS variables in `utils/styles.py` (light mode follows the reference design).
