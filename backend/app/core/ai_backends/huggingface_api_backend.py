import structlog
import httpx
from app.core.ai_backends.base import AIBackend
from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

HF_INFERENCE_URL = "https://router.huggingface.co/novita/v3/openai/chat/completions"


class HuggingFaceAPIBackend(AIBackend):
    """
    AI backend using HuggingFace Inference API (free tier available).
    No local GPU needed — runs on HF's servers.
    Works with any model hosted on HF that supports the chat completions endpoint.
    """

    def __init__(self):
        self._model_id = settings.HF_MODEL_ID
        self._token = settings.HF_TOKEN
        if not self._token:
            raise ValueError(
                "HF_TOKEN is required for HuggingFace Inference API. "
                "Get a free token at https://huggingface.co/settings/tokens"
            )

    @property
    def name(self) -> str:
        return f"huggingface_api:{self._model_id}"

    @property
    def supports_vision(self) -> bool:
        return "medgemma" in self._model_id.lower()

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    async def _call_api(self, messages: list[dict], temperature: float, max_tokens: int) -> str:
        payload = {
            "model": self._model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                HF_INFERENCE_URL,
                headers=self._headers(),
                json=payload,
            )

            if response.status_code == 422 or response.status_code == 404:
                # Fallback: try the model-specific endpoint
                fallback_url = f"https://api-inference.huggingface.co/models/{self._model_id}/v1/chat/completions"
                logger.info("hf_api_fallback", url=fallback_url)
                response = await client.post(
                    fallback_url,
                    headers=self._headers(),
                    json=payload,
                )

            response.raise_for_status()
            data = response.json()

            if "choices" in data:
                return data["choices"][0]["message"]["content"].strip()

            # Some HF endpoints return generated_text directly
            if isinstance(data, list) and len(data) > 0:
                return data[0].get("generated_text", "").strip()

            raise ValueError(f"Unexpected HF API response format: {data}")

    async def chat(self, messages: list[dict], temperature: float = 0.1, max_tokens: int = 1000) -> str:
        return await self._call_api(messages, temperature, max_tokens)

    async def chat_with_image(self, prompt: str, image_b64: str, temperature: float = 0.1, max_tokens: int = 1000) -> str:
        if not self.supports_vision:
            raise NotImplementedError(f"Model {self._model_id} does not support vision via API.")

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
