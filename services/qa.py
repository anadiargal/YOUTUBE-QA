"""
GROUNDED QUESTION ANSWERING

Retrieved chunks -> prompt -> Gemini -> answer + timestamp citations.

How citations work:
    Every chunk carries start_time / end_time metadata from the moment it was created.
    We number the chunks we send to Gemini ([1], [2], ...), and Gemini reports which
    numbers it used ("SOURCES: 1, 3"). We map those numbers back to timestamps, then
    narrow each citation to the ~20 s transcript segments that best match the answer,
    so clicking a source seeks the video to the right moment.
"""
import json
import re
from dataclasses import dataclass, field

import config
from prompts.qa_prompt import (
    HUMAN_TEMPLATE,
    REFUSAL_MESSAGE,
    SUGGESTED_QUESTIONS_PROMPT,
    SYSTEM_PROMPT,
)
from services.retriever import RetrievalResult, RetrievedChunk
from utils.errors import LLMError, api_error_message, logger
from utils.helpers import format_timestamp

_STOPWORDS = set(
    "the a an and or but of to in on at for with is are was were be been it this that these those "
    "as by from about into than then so such not no can will would should could has have had do does did "
    "they them their there here what which who how why when where also very more most some any".split()
)


@dataclass
class Answer:
    text: str
    sources: list[dict] = field(default_factory=list)  # [{"start": 312.0, "end": 334.0}]
    refused: bool = False
    best_score: float = 0.0


def _get_llm():
    from langchain_google_genai import ChatGoogleGenerativeAI

    # temperature=0: we want faithful extraction from the context, not creativity.
    return ChatGoogleGenerativeAI(
        model=config.GEMINI_MODEL, google_api_key=config.GOOGLE_API_KEY, temperature=0, max_retries=2
    )


def _text_of(content) -> str:
    if isinstance(content, str):
        return content
    parts = []
    for block in content or []:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts)


def _split_sources(raw: str) -> tuple[str, list[int]]:
    """Separates the answer body from the trailing 'SOURCES: 1, 3' line."""
    match = re.search(r"\n?\s*SOURCES:\s*([\d,\s]+)\s*$", raw.strip(), flags=re.IGNORECASE)
    if not match:
        return raw.strip(), []
    numbers = [int(n) for n in re.findall(r"\d+", match.group(1))]
    return raw.strip()[: match.start()].strip(), numbers


def _is_refusal(text: str) -> bool:
    normalized = text.strip().strip("'\"").strip().lower()
    return REFUSAL_MESSAGE.lower().rstrip(".") in normalized


def _content_words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9']+", text.lower()) if len(w) > 3 and w not in _STOPWORDS}


def _refine_citation(answer_text: str, chunk: RetrievedChunk, segments: list[dict]) -> dict:
    """
    A chunk can span several minutes. Find the 1-2 consecutive ~20 s segments inside it
    whose words overlap most with the answer, so the citation is tight (e.g. 05:12 - 05:34).
    """
    inside = [s for s in segments if chunk.start_time - 0.5 <= s["start"] < chunk.end_time]
    answer_words = _content_words(answer_text)
    if not inside or not answer_words:
        return {"start": chunk.start_time, "end": chunk.end_time}

    scores = [len(answer_words & _content_words(s["text"])) for s in inside]
    best = max(range(len(inside)), key=lambda i: scores[i])
    if scores[best] == 0:
        return {"start": chunk.start_time, "end": chunk.end_time}

    lo = hi = best
    neighbours = [i for i in (best - 1, best + 1) if 0 <= i < len(inside)]
    if neighbours:
        nb = max(neighbours, key=lambda i: scores[i])
        if scores[nb] > 0:
            lo, hi = min(best, nb), max(best, nb)
    return {"start": inside[lo]["start"], "end": inside[hi]["end"]}


def answer_question(question: str, retrieval: RetrievalResult, segments: list[dict]) -> Answer:
    # GATE: nothing relevant retrieved -> refuse WITHOUT calling the LLM at all.
    if not retrieval.chunks:
        return Answer(REFUSAL_MESSAGE, [], True, retrieval.best_score)

    # Numbered, timestamped context that Gemini is allowed to use.
    context = "\n\n".join(
        f"[{i}] ({format_timestamp(c.start_time)} - {format_timestamp(c.end_time)})\n{c.text}"
        for i, c in enumerate(retrieval.chunks, start=1)
    )

    try:
        response = _get_llm().invoke([
            ("system", SYSTEM_PROMPT),
            ("human", HUMAN_TEMPLATE.format(context=context, question=question)),
        ])
        raw = _text_of(response.content)
    except Exception as exc:
        logger.exception("Gemini answer generation failed")
        raise LLMError(api_error_message(exc, "Gemini couldn't generate an answer right now. Please try again.")) from exc

    body, cited_numbers = _split_sources(raw)
    if not body or _is_refusal(body):
        return Answer(REFUSAL_MESSAGE, [], True, retrieval.best_score)

    cited = [retrieval.chunks[n - 1] for n in cited_numbers if 1 <= n <= len(retrieval.chunks)]
    if not cited:  # model forgot the SOURCES line: fall back to the best retrieved chunk(s)
        cited = sorted(retrieval.chunks, key=lambda c: -c.score)[:2]
    cited = sorted(sorted(cited, key=lambda c: -c.score)[:3], key=lambda c: c.start_time)

    sources, seen = [], set()
    for chunk in cited:
        cite = _refine_citation(body, chunk, segments)
        key = (round(cite["start"]), round(cite["end"]))
        if key not in seen:
            seen.add(key)
            sources.append(cite)
    return Answer(body, sources, False, retrieval.best_score)


def _sample_transcript(segments: list[dict], max_chars: int = 24000) -> str:
    full = " ".join(s["text"] for s in segments)
    if len(full) <= max_chars:
        return full
    windows = 8  # sample evenly across the whole video
    size, step = max_chars // windows, len(full) // windows
    return " [...] ".join(full[i * step: i * step + size] for i in range(windows))


def generate_suggested_questions(segments: list[dict], n: int = config.NUM_SUGGESTED_QUESTIONS) -> list[str]:
    """Questions generated ONLY from the transcript. Failures are non-fatal (returns [])."""
    try:
        response = _get_llm().invoke([
            ("human", SUGGESTED_QUESTIONS_PROMPT.format(n=n, transcript=_sample_transcript(segments)))
        ])
        text = _text_of(response.content)
        match = re.search(r"\[.*\]", text, flags=re.DOTALL)
        questions = json.loads(match.group(0)) if match else []
        return [q.strip() for q in questions if isinstance(q, str) and q.strip()][:n]
    except Exception:
        logger.exception("Suggested question generation failed")
        return []
