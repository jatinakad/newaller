import structlog
from openai import AsyncOpenAI
from app.core.ai_backends.base import AIBackend
from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class OllamaBackend(AIBackend):
    """AI backend using Ollama's OpenAI-compatible API."""

    def __init__(self):
        self._client = AsyncOpenAI(
            base_url=f"{settings.OLLAMA_BASE_URL}/v1",
            api_key="ollama",
        )
        self._model = settings.OLLAMA_MODEL

    @property
    def name(self) -> str:
        return f"ollama:{self._model}"

    @property
    def supports_vision(self) -> bool:
        return True

    async def chat(self, messages: list[dict], temperature: float = 0.1, max_tokens: int = 1000) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()

    async def chat_with_image(self, prompt: str, image_b64: str, temperature: float = 0.1, max_tokens: int = 1000) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                    ],
                }
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()