"""
memory_service.py — Day 6: User Memory extraction and injection for Jarvis AI.

Public API:
    extract_and_save_memories(user, user_message, session=None) -> list[str]
        Calls AI to extract personal facts from user_message and upserts them
        into the UserMemory table. Returns a list of saved key names.

    get_memory_context_string(user) -> str
        Loads all active UserMemory rows for user and formats them as a string
        suitable for injection into the AI system prompt.
"""

import json
import logging

from django.conf import settings

from .models import UserMemory

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Category display labels (must match UserMemory.CATEGORY_CHOICES)
# ---------------------------------------------------------------------------
CATEGORY_LABELS: dict[str, str] = {
    'preference': 'Preference',
    'fact':       'Personal Fact',
    'goal':       'Goal',
    'context':    'Context',
    'other':      'Other',
}

# ---------------------------------------------------------------------------
# Memory extraction prompt
# ---------------------------------------------------------------------------
_EXTRACTION_PROMPT = """\
You are a JSON extraction tool. Analyze the user message and extract ONLY \
personal information about the user themselves.

User message: "{message}"

Return a JSON array of objects. Each object must have exactly these keys:
  "key"      — snake_case identifier (e.g. "name", "favorite_language", "career_goal")
  "value"    — concise value string
  "category" — one of: fact | preference | goal | context | other

Rules:
- Only extract information about the USER (not general knowledge).
- Return [] (empty array) if no personal info is present.
- key must be lowercase snake_case, max 40 chars.
- value must be concise, max 200 chars.
- Return ONLY the JSON array. No explanation, no markdown fences.

Examples:
  "My name is Sudhee"                       → [{{"key":"name","value":"Sudhee","category":"fact"}}]
  "My favourite language is Python"         → [{{"key":"favorite_language","value":"Python","category":"preference"}}]
  "I am preparing for SE interviews"        → [{{"key":"current_goal","value":"Software engineering interview preparation","category":"goal"}}]
  "I work at TechCorp as a backend dev"     → [{{"key":"workplace","value":"TechCorp","category":"fact"}},{{"key":"role","value":"Backend developer","category":"fact"}}]
  "What is a linked list?"                  → []
  "Hello, how are you?"                     → []

Return ONLY the JSON array:"""


# ===========================================================================
# Public functions
# ===========================================================================

def extract_and_save_memories(user, user_message: str, session=None) -> list[str]:
    """
    Use AI to extract personal facts from `user_message` and upsert them
    into UserMemory.  Returns list of keys that were saved/updated.
    Never raises — all errors are logged.
    """
    try:
        raw = _call_ai_for_extraction(user_message)
        if not raw:
            return []

        # Strip markdown fences that some models add
        text = raw.strip()
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            if text.lower().startswith("json"):
                text = text[4:]
        text = text.strip()

        data = json.loads(text)
        if not isinstance(data, list):
            return []

        saved: list[str] = []
        for item in data:
            key   = str(item.get('key', '')).strip().lower().replace(' ', '_').replace('-', '_')
            value = str(item.get('value', '')).strip()
            cat   = str(item.get('category', 'other')).lower()

            if not key or not value:
                continue
            if len(key) > 120 or len(value) > 2000:
                continue
            if cat not in CATEGORY_LABELS:
                cat = 'other'

            obj, created = UserMemory.objects.update_or_create(
                user=user,
                key=key,
                defaults={
                    'value':          value,
                    'category':       cat,
                    'is_active':      True,
                    'source_session': session,
                    'confidence':     0.9,
                },
            )
            action = "Created" if created else "Updated"
            logger.info("[Memory] %s  key=%s  value=%s", action, key, value[:60])
            saved.append(key)

        if saved:
            print(f"[Memory] Saved {len(saved)} memories: {saved}")

        return saved

    except json.JSONDecodeError as exc:
        logger.warning("[Memory] JSON parse error: %s | raw=%s", exc, raw[:120] if 'raw' in dir() else '?')
        return []
    except Exception as exc:
        logger.error("[Memory] extract_and_save_memories failed: %s", exc)
        return []


def get_memory_context_string(user) -> str:
    """
    Load all active memories for `user` and return a formatted block
    ready to be appended to the AI system prompt.  Returns '' if no memories.
    """
    memories = list(
        UserMemory.objects.filter(user=user, is_active=True).order_by('category', 'key')
    )
    if not memories:
        return ''

    by_cat: dict[str, list[UserMemory]] = {}
    for mem in memories:
        by_cat.setdefault(mem.category, []).append(mem)

    lines = [
        "",
        "--- Personal context about this user (use it to personalise your responses) ---",
    ]
    for cat in ('fact', 'preference', 'goal', 'context', 'other'):
        if cat not in by_cat:
            continue
        lines.append(f"\n{CATEGORY_LABELS[cat]}s:")
        for mem in by_cat[cat]:
            label = mem.key.replace('_', ' ').title()
            lines.append(f"  * {label}: {mem.value}")
    lines.append("--- End of user context ---")
    lines.append("")

    return '\n'.join(lines)


# ===========================================================================
# Internal helpers
# ===========================================================================

def _call_ai_for_extraction(user_message: str) -> str:
    """
    Send the extraction prompt to the configured AI provider.
    Returns raw string (expected JSON array).  Returns '' on failure.
    """
    prompt = _EXTRACTION_PROMPT.format(message=user_message.replace('"', "'"))

    provider = getattr(settings, 'AI_PROVIDER', 'gemini').strip().lower()
    order    = ['gemini', 'groq', 'openai'] if provider == 'auto' else [provider]

    for p in order:
        try:
            if p == 'gemini':
                result = _gemini_extract(prompt)
            elif p == 'groq':
                result = _groq_extract(prompt)
            elif p == 'openai':
                result = _openai_extract(prompt)
            else:
                continue
            if result:
                return result
        except Exception as exc:
            logger.warning("[Memory] %s extraction attempt failed: %s", p, exc)

    return ''


def _gemini_extract(prompt: str) -> str:
    from google import genai
    from google.genai import types

    api_key = getattr(settings, 'GEMINI_API_KEY', '')
    if not api_key or api_key == 'your-gemini-api-key-here':
        raise ValueError("GEMINI_API_KEY not configured")

    client = genai.Client(api_key=api_key)
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
        config=types.GenerateContentConfig(max_output_tokens=256, temperature=0.0),
    )
    return (resp.text or '').strip()


def _groq_extract(prompt: str) -> str:
    from groq import Groq

    api_key = getattr(settings, 'GROQ_API_KEY', '')
    if not api_key or api_key == 'your-groq-api-key-here':
        raise ValueError("GROQ_API_KEY not configured")

    client = Groq(api_key=api_key)
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=256,
        temperature=0.0,
    )
    return (resp.choices[0].message.content or '').strip()


def _openai_extract(prompt: str) -> str:
    from openai import OpenAI

    api_key = getattr(settings, 'OPENAI_API_KEY', '')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not configured")

    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=256,
        temperature=0.0,
    )
    return (resp.choices[0].message.content or '').strip()
