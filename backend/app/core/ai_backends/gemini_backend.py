import json
import structlog
import httpx
from app.core.ai_backends.base import AIBackend
from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiBackend(AIBackend):
    """
    AI backend using Google Gemini API (via Google AI Studio).
    Supports text chat and multimodal (vision) inputs.
    """

    def __init__(self):
        self._model_id = settings.GEMINI_MODEL
        self._api_key = settings.GEMINI_API_KEY
        if not self._api_key:
            raise ValueError(
                "GEMINI_API_KEY is required for Google Gemini backend. "
                "Get a free key at https://aistudio.google.com/apikey"
            )

    @property
    def name(self) -> str:
        return f"gemini:{self._model_id}"

    @property
    def supports_vision(self) -> bool:
        return True

    def _url(self, action: str = "generateContent") -> str:
        return f"{GEMINI_API_URL}/{self._model_id}:{action}?key={self._api_key}"

    def _convert_messages(self, messages: list[dict]) -> tuple[str | None, list[dict]]:
        """Convert OpenAI-style messages to Gemini format.
        Returns (system_instruction, contents)."""
        system_text = None
        contents = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                system_text = content
                continue

            gemini_role = "user" if role == "user" else "model"

            if isinstance(content, str):
                contents.append({
                    "role": gemini_role,
                    "parts": [{"text": content}]
                })
            elif isinstance(content, list):
                parts = []
                for part in content:
                    if part.get("type") == "text":
                        parts.append({"text": part["text"]})
                    elif part.get("type") == "image_url":
                        url = part["image_url"]["url"]
                        if url.startswith("data:"):
                            mime, b64 = url.split(";base64,", 1)
                            mime = mime.replace("data:", "")
                            parts.append({
                                "inline_data": {
                                    "mime_type": mime,
                                    "data": b64,
                                }
                            })
                contents.append({"role": gemini_role, "parts": parts})

        return system_text, contents

    async def _call_api(self, messages: list[dict], temperature: float, max_tokens: int) -> str:
        system_text, contents = self._convert_messages(messages)

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        if system_text:
            payload["systemInstruction"] = {
                "parts": [{"text": system_text}]
            }

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                self._url("generateContent"),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                text_parts = [p["text"] for p in parts if "text" in p]
                return "\n".join(text_parts).strip()

            raise ValueError(f"Unexpected Gemini API response: {json.dumps(data)[:500]}")

    async def chat(self, messages: list[dict], temperature: float = 0.1, max_tokens: int = 1000) -> str:
        return await self._call_api(messages, temperature, max_tokens)

    async def chat_with_image(self, prompt: str, image_b64: str, temperature: float = 0.1, max_tokens: int = 1000) -> str:
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                ],
            }
        ]
        return await self._call_api(messages, temperature, max_tokens)
