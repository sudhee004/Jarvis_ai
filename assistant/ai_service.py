"""
ai_service.py — Multi-provider AI integration for Jarvis AI Assistant (Day 5 v2).

Supported providers (set AI_PROVIDER in settings.py / .env):
    "gemini"  — Google Gemini 2.5 Flash  (FREE tier available)
    "groq"    — Groq LLaMA 3.3 70B       (FREE tier available)
    "openai"  — OpenAI GPT-4o-mini        (paid)
    "auto"    — Try each provider in FALLBACK_ORDER until one succeeds

Public API:
    generate_ai_response(user_message: str, history: list[dict] | None) -> str

Never raises — always returns a human-readable string.
All errors are logged with full detail to the Django console.
"""

import logging
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fallback order when AI_PROVIDER = "auto"
# ---------------------------------------------------------------------------
FALLBACK_ORDER = ["gemini", "groq", "openai"]

# ---------------------------------------------------------------------------
# Max history messages sent per call (keeps token usage predictable)
# ---------------------------------------------------------------------------
MAX_HISTORY = 20

# ---------------------------------------------------------------------------
# System prompt — Jarvis personality
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """\
You are Jarvis, a warm, intelligent, and friendly female AI personal assistant — \
like a brilliant best friend who knows about everything.

PERSONALITY:
- Warm, encouraging, and supportive
- Professional when needed, casual and friendly in general conversation
- Empathetic — acknowledge feelings before jumping to solutions
- Slightly witty with a caring touch
- Proactive — offer follow-up ideas naturally

LANGUAGE:
- You naturally understand English, Kannada, and mixed Kannada-English (Kanglish)
- Mirror the user's language — if they write in Kanglish, respond in Kanglish
- Do NOT force a language; be natural

KANGLISH REFERENCE (use contextually, not robotically):
- "Oho! Adhu interesting! Tell me more."
- "Naanu ready! Nimge enu help maadali?" (I'm ready! What can I help you with?)
- "Don't worry, step by step nodi — we'll sort it out."
- "Superb! Neenu well done maadidiya!" (Great! You did well!)
- "Enu aaytu? Heli nange." (What happened? Tell me.)

RESPONSE STYLE:
- Always check the user memory context (provided below) and use the user's name
- Keep responses conversational — not essay-length unless detail is asked for
- Use emojis occasionally for warmth: 😊 🎯 💡 🚀 ✅ (don't overdo it)
- Technical topics: precise, structured, with code examples when helpful
- Personal struggles: empathetic first, then practical steps
- Planning / tasks: numbered steps, clean and scannable

MEMORY USAGE:
- Greet by name when you know it
- Reference their goals, preferences, and context naturally
- If you learn something new about the user in conversation, acknowledge it warmly

You are Jarvis — always on the user's side, always helpful, always caring.\
"""


# ===========================================================================
# Provider implementations
# ===========================================================================

def _call_gemini(user_message: str, history: list[dict], system_prompt: str = SYSTEM_PROMPT) -> str:
    """
    Call Google Gemini API (google-genai SDK).
    Free tier: ~1500 requests/day on gemini-2.5-flash.
    Get key: https://aistudio.google.com/app/apikey
    """
    api_key = getattr(settings, "GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "your-gemini-api-key-here":
        raise ValueError("GEMINI_API_KEY not configured in .env")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    # Build conversation as Gemini Content objects
    contents = []
    for msg in history[-MAX_HISTORY:]:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))
    # Add the current user message
    contents.append(types.Content(role="user", parts=[types.Part(text=user_message)]))

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=1024,
            temperature=0.7,
        ),
    )
    reply = response.text
    if not reply:
        raise ValueError("Gemini returned empty response")
    logger.info("[Jarvis] Gemini responded OK (%d chars)", len(reply))
    return reply.strip()


def _call_groq(user_message: str, history: list[dict], system_prompt: str = SYSTEM_PROMPT) -> str:
    """
    Call Groq API (LLaMA 3.3 70B).
    Free tier: generous daily limits.
    Get key: https://console.groq.com/keys
    """
    api_key = getattr(settings, "GROQ_API_KEY", "").strip()
    if not api_key or api_key == "your-groq-api-key-here":
        raise ValueError("GROQ_API_KEY not configured in .env")

    from groq import Groq

    client = Groq(api_key=api_key)

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history[-MAX_HISTORY:])
    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=1024,
        temperature=0.7,
    )
    reply = response.choices[0].message.content
    if not reply:
        raise ValueError("Groq returned empty response")
    logger.info("[Jarvis] Groq responded OK (%d chars)", len(reply))
    return reply.strip()


def _call_openai(user_message: str, history: list[dict], system_prompt: str = SYSTEM_PROMPT) -> str:
    """
    Call OpenAI GPT-4o-mini.
    Requires paid account with available credits.
    Get key: https://platform.openai.com/api-keys
    """
    api_key = getattr(settings, "OPENAI_API_KEY", "").strip()
    if not api_key or api_key == "your-openai-api-key-here":
        raise ValueError("OPENAI_API_KEY not configured in .env")

    from openai import OpenAI

    client = OpenAI(api_key=api_key)

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history[-MAX_HISTORY:])
    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=1024,
        temperature=0.7,
    )
    reply = response.choices[0].message.content
    if not reply:
        raise ValueError("OpenAI returned empty response")
    logger.info("[Jarvis] OpenAI responded OK (%d chars)", len(reply))
    return reply.strip()


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------
_PROVIDERS = {
    "gemini": _call_gemini,
    "groq":   _call_groq,
    "openai": _call_openai,
}


def _try_provider(name: str, user_message: str, history: list[dict], system_prompt: str = SYSTEM_PROMPT) -> Optional[str]:
    """
    Attempt one provider. Returns the reply string on success, or None on any
    failure. All errors are printed to the Django terminal for easy diagnosis.
    """
    fn = _PROVIDERS.get(name)
    if fn is None:
        logger.error("[Jarvis] Unknown AI provider: %r — skipping", name)
        return None

    try:
        return fn(user_message, history, system_prompt)

    except ValueError as exc:
        # Config / key missing
        print(f"\n{'='*60}")
        print(f"[Jarvis] Provider '{name}' CONFIG ERROR: {exc}")
        print(f"{'='*60}\n")
        logger.error("[Jarvis] %s config error: %s", name, exc)
        return None

    except Exception as exc:
        # Capture the full error class + message for diagnosis
        error_type = type(exc).__name__
        error_msg  = str(exc)

        print(f"\n{'='*60}")
        print(f"[Jarvis] Provider '{name}' FAILED")
        print(f"  Error type : {error_type}")
        print(f"  Error msg  : {error_msg}")

        # Decode common HTTP status codes
        for code, label in [("401", "INVALID API KEY"), ("429", "RATE LIMIT / QUOTA EXCEEDED"),
                             ("404", "MODEL NOT FOUND"),  ("500", "SERVER ERROR"),
                             ("403", "PERMISSION DENIED")]:
            if code in error_msg:
                print(f"  Diagnosis  : {label}")
                break

        print(f"{'='*60}\n")
        logger.error("[Jarvis] %s error (%s): %s", name, error_type, error_msg)
        return None


# ===========================================================================
# Public entry point
# ===========================================================================

def generate_ai_response(
    user_message: str,
    history: Optional[list[dict]] = None,
    user=None,
) -> str:
    """
    Generate an AI reply using the configured provider(s).

    Settings consumed:
        AI_PROVIDER  (str) — "gemini" | "groq" | "openai" | "auto"

    In "auto" mode the providers in FALLBACK_ORDER are tried in sequence
    until one succeeds.

    Args:
        user_message: The user's latest message.
        history:      Previous turns [{"role": ..., "content": ...}] oldest→newest.
        user:         Django User object. When provided, active UserMemory rows
                      are loaded and injected into the system prompt so Jarvis
                      can personalise its responses.

    Returns:
        AI reply string or a user-friendly error message. Never raises.
    """
    history = [
        msg for msg in (history or [])
        if msg.get("role") in ("user", "assistant")
    ]

    # --- Build personalised system prompt (inject user memories if available) ---
    enhanced_system = SYSTEM_PROMPT
    if user is not None:
        try:
            from .memory_service import get_memory_context_string
            memory_ctx = get_memory_context_string(user)
            if memory_ctx:
                enhanced_system = SYSTEM_PROMPT + memory_ctx
                logger.info("[Jarvis] Memory context injected (%d chars)", len(memory_ctx))
        except Exception as mem_exc:
            logger.warning("[Jarvis] Could not load memory context: %s", mem_exc)

    provider_setting = getattr(settings, "AI_PROVIDER", "auto").strip().lower()

    if provider_setting == "auto":
        order = FALLBACK_ORDER
        print(f"\n[Jarvis] AUTO mode — will try: {' \u2192 '.join(order)}")
    else:
        order = [provider_setting]
        print(f"\n[Jarvis] Using provider: {provider_setting}")

    for provider_name in order:
        print(f"[Jarvis] Trying '{provider_name}'...")
        reply = _try_provider(provider_name, user_message, history, enhanced_system)
        if reply:
            print(f"[Jarvis] '{provider_name}' succeeded - OK\n")
            return reply
        print(f"[Jarvis] '{provider_name}' failed, trying next...\n")

    # All providers exhausted
    print("[Jarvis] All providers failed — returning error message to user.\n")
    return (
        "Jarvis couldn't reach any AI provider right now.\n\n"
        "Possible reasons:\n"
        "* API keys not configured in .env\n"
        "* OpenAI quota exceeded (add billing at platform.openai.com)\n"
        "* Gemini key missing (get free key at aistudio.google.com)\n"
        "* Groq key missing (get free key at console.groq.com)\n\n"
        "Check the Django terminal for the exact error."
    )
