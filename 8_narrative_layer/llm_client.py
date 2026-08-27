"""
llm_client.py
Thin wrapper around the Anthropic API for Phase 8 narrative synthesis
ONLY. This is deliberately the single place in the entire codebase an
LLM is called — every other phase (2-7, 9-12) remains 100% deterministic.

Design constraint: the LLM is given the ALREADY-COMPUTED facts (driver,
action, owner, impact numbers, confidence tier) and asked only to
phrase them naturally for a specific persona. It is explicitly
instructed not to invent, alter, or add any fact, number, or claim not
already present in the input. This is narrative synthesis, not
diagnosis — the diagnosis already happened upstream in Phases 2-7.

Fails gracefully: if no API key is set, or the call errors out for any
reason (network, rate limit, bad response), callers fall back to the
deterministic template narrative from persona_narrator.py's original
logic. The demo never breaks because of this layer.
"""

import os
import time
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 300

_client = None


def _get_client():
    """Lazily initializes the Anthropic client only if a key is present."""
    global _client
    if _client is not None:
        return _client

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic
        _client = anthropic.Anthropic(api_key=api_key)
        return _client
    except ImportError:
        return None


def is_llm_available() -> bool:
    """Checks whether an LLM call is even possible right now (key present, package installed)."""
    return _get_client() is not None


def generate_persona_narrative(system_prompt: str, facts_prompt: str, step_name: str = "narrate_personas") -> dict:
    """
    Makes a single LLM call to phrase the given facts naturally.

    Returns a dict: {"success": bool, "text": str or None, "input_tokens": int,
    "output_tokens": int, "latency_ms": float, "error": str or None}

    On any failure (no key, network error, API error), returns
    success=False with error set — caller is responsible for falling
    back to the template-based narrative.
    """
    client = _get_client()
    if client is None:
        return {
            "success": False, "text": None,
            "input_tokens": 0, "output_tokens": 0, "latency_ms": 0,
            "error": "No LLM client available (missing ANTHROPIC_API_KEY or anthropic package).",
        }

    start = time.perf_counter()
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            temperature=0.3,  # low temperature — this is phrasing, not creative writing
            system=system_prompt,
            messages=[{"role": "user", "content": facts_prompt}],
        )
        latency_ms = (time.perf_counter() - start) * 1000

        text = "".join(block.text for block in response.content if hasattr(block, "text")).strip()

        return {
            "success": True, "text": text,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "latency_ms": round(latency_ms, 2),
            "error": None,
        }

    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        return {
            "success": False, "text": None,
            "input_tokens": 0, "output_tokens": 0, "latency_ms": round(latency_ms, 2),
            "error": f"{type(e).__name__}: {e}",
        }


if __name__ == "__main__":
    print(f"LLM available: {is_llm_available()}")
    if is_llm_available():
        result = generate_persona_narrative(
            system_prompt="You rephrase structured business facts into one short, natural paragraph. Never add facts not given to you.",
            facts_prompt="Store: 18. Driver: Supply disruption. Action: Expedite restock. Confidence: HIGH.",
        )
        print(result)
    else:
        print("Set ANTHROPIC_API_KEY in .env to test the actual API call.")