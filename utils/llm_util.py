import os
import re
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("LLM_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = os.getenv("LLM_MODEL", "mistralai/mistral-small-3.1-24b-instruct:free")
DEFAULT_FALLBACK_MODELS = [
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen3-32b:free",
    "google/gemma-3-27b-it:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "openai/gpt-oss-120b:free",
    "qwen/qwen3-coder:free",
    "stepfun/step-3.5-flash:free",
]

MAX_RETRIES_PER_MODEL = 2
RETRY_BACKOFF_SECONDS = 2


def _fallback_models():
    configured = [model.strip() for model in os.getenv("LLM_FALLBACK_MODELS", "").split(",") if model.strip()]
    if configured:
        return configured
    return DEFAULT_FALLBACK_MODELS


def _extractive_summary(text, max_sentences=3):
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return "No content was available to summarize."

    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    selected = [sentence.strip() for sentence in sentences if sentence.strip()][:max_sentences]
    summary = " ".join(selected).strip()

    action_signals = []
    for sentence in sentences:
        lowered = sentence.lower()
        if any(keyword in lowered for keyword in ("todo", "action", "deadline", "by ", "tomorrow", "next week", "follow up", "finish", "confirm", "prepare")):
            action_signals.append(sentence.strip())
        if len(action_signals) == 2:
            break

    if action_signals:
        summary += "\n\nAction items: " + " ".join(action_signals)

    return summary


def chat_completion(system_prompt, user_prompt, timeout=60):
    if not OPENROUTER_API_KEY:
        raise ValueError("LLM_API_KEY is missing from the environment.")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://autopilot.local",
        "X-Title": "AutoPilotAI-BrowserUI",
    }
    models_to_try = []
    for model in [OPENROUTER_MODEL, *_fallback_models()]:
        if model and model not in models_to_try:
            models_to_try.append(model)

    last_error = None

    for model in models_to_try:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        for attempt in range(MAX_RETRIES_PER_MODEL):
            try:
                response = httpx.post(
                    OPENROUTER_BASE_URL,
                    json=payload,
                    headers=headers,
                    timeout=timeout,
                )

                if response.status_code == 404:
                    last_error = f"Model {model} is unavailable: {response.text}"
                    break

                if response.status_code == 429:
                    retry_after = int(response.headers.get("retry-after", RETRY_BACKOFF_SECONDS))
                    last_error = f"Model {model} rate-limited (429)"
                    if attempt < MAX_RETRIES_PER_MODEL - 1:
                        time.sleep(min(retry_after, 5))
                        continue
                    break

                if response.status_code == 503:
                    last_error = f"Model {model} temporarily unavailable (503)"
                    if attempt < MAX_RETRIES_PER_MODEL - 1:
                        time.sleep(RETRY_BACKOFF_SECONDS)
                        continue
                    break

                response.raise_for_status()
                data = response.json()

                choices = data.get("choices")
                if not choices or not choices[0].get("message", {}).get("content"):
                    last_error = f"Model {model} returned empty response"
                    break

                return choices[0]["message"]["content"].strip()

            except httpx.TimeoutException:
                last_error = f"Model {model} timed out"
                break
            except httpx.HTTPStatusError as exc:
                last_error = f"Model {model} HTTP error: {exc.response.status_code}"
                break

    raise ValueError(last_error or "No LLM model could complete the request.")


def summarize_text(text, instruction=None):
    summary_prompt = instruction or (
        "Summarize the following text in 2 to 3 sentences and call out any clear action items."
    )
    return chat_completion(summary_prompt, text)


def polish_message(raw_message, subject="", instruction=None):
    system_prompt = instruction or (
        "Rewrite the user's draft as a complete email. Preserve the intent and keep it concise. "
        "Do not invent facts that are not in the draft."
    )
    user_prompt = "\n".join(
        [
            f"Subject: {subject or 'No subject provided'}",
            "",
            "Draft:",
            raw_message,
        ]
    )
    return chat_completion(system_prompt, user_prompt)
