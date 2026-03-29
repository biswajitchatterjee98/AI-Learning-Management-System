import json
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

from app.core.config import settings


def call_llm(system_prompt: str, user_prompt: str) -> str:
    if not settings.AI_API_KEY:
        raise RuntimeError("AI_API_KEY is not configured")

    body = json.dumps(
        {
            "model": settings.AI_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
    ).encode("utf-8")
    base_url = settings.AI_BASE_URL.rstrip("/")
    provider = (settings.AI_PROVIDER or "").lower().strip()
    if provider == "groq" and "groq.com" not in base_url:
        base_url = "https://api.groq.com/openai/v1"
    elif provider == "openai" and "openai.com" not in base_url:
        base_url = "https://api.openai.com/v1"

    req = urlrequest.Request(
        f"{base_url}/chat/completions",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {settings.AI_API_KEY}"},
    )
    try:
        with urlrequest.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            return str(payload["choices"][0]["message"]["content"]).strip()
    except (HTTPError, URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"LLM call failed: {exc}") from exc


def build_lesson_content(team: str, focus_topic: str, kpis: list[str]) -> str:
    return (
        f"Team context: {team}\n\n"
        f"Focus topic: {focus_topic}\n\n"
        "Learning goals:\n"
        f"- Apply {focus_topic.replace('_', ' ')} using tenant SOP patterns.\n"
        f"- Improve KPI signals: {', '.join(kpis[:2]) if kpis else 'core business outcomes'}.\n"
        "- Practice with scenario-based responses and self-review prompts.\n\n"
        "Practice task:\n"
        f"Write a short response for a realistic {team.lower()} scenario that demonstrates {focus_topic.replace('_', ' ')}."
    )

