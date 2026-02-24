import asyncio
import structlog
from app.core.ai_backends.base import AIBackend
from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class HuggingFaceLocalBackend(AIBackend):
    """
    AI backend using HuggingFace Transformers locally.
    Loads the model into GPU/CPU memory and runs inference directly.
    Supports MedGemma, Gemma, Llama, Mistral, or any HF chat model.
    """

    def __init__(self):
        self._model_id = settings.HF_MODEL_ID
        self._pipeline = None
        self._loaded = False

    def _load_model(self):
        if self._loaded:
            return

        try:
            import torch
            from transformers import pipeline

            dtype_map = {
                "float16": torch.float16,
                "bfloat16": torch.bfloat16,
                "float32": torch.float32,
                "auto": "auto",
            }
            torch_dtype = dtype_map.get(settings.HF_TORCH_DTYPE, "auto")

            device_map = settings.HF_DEVICE if settings.HF_DEVICE != "auto" else "auto"

            logger.info("loading_hf_model", model=self._model_id, device=device_map, dtype=settings.HF_TORCH_DTYPE)

            pipe_kwargs = {
                "model": self._model_id,
                "torch_dtype": torch_dtype,
                "device_map": device_map,
            }
            if settings.HF_TOKEN:
                pipe_kwargs["token"] = settings.HF_TOKEN

            self._pipeline = pipeline("text-generation", **pipe_kwargs)
            self._loaded = True
            logger.info("hf_model_loaded", model=self._model_id)

        except ImportError:
            raise RuntimeError(
                "HuggingFace Transformers backend requires: pip install transformers torch accelerate. "
                "Install them or switch AI_BACKEND to 'ollama' or 'huggingface_api'."
            )

    def _generate(self, messages: list[dict], temperature: float, max_tokens: int) -> str:
        self._load_model()
        output = self._pipeline(
            messages,
            max_new_tokens=max_tokens,
            temperature=temperature if temperature > 0 else None,
            do_sample=temperature > 0,
            return_full_text=False,
        )
        return output[0]["generated_text"].strip()

    @property
    def name(self) -> str:
        return f"huggingface_local:{self._model_id}"

    @property
    def supports_vision(self) -> bool:
        # Vision support depends on the model; MedGemma multimodal supports it
        return "medgemma" in self._model_id.lower()

    async def chat(self, messages: list[dict], temperature: float = 0.1, max_tokens: int = 1000) -> str:
        # Run in thread pool to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._generate, messages, temperature, max_tokens)

    async def chat_with_image(self, prompt: str, image_b64: str, temperature: float = 0.1, max_tokens: int = 1000) -> str:
        if not self.supports_vision:
            raise NotImplementedError(f"Model {self._model_id} does not support vision. Use a multimodal model.")

        # For HF transformers with vision models, pass image as part of content
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                ],
            }
        ]
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._generate, messages, temperature, max_tokens)
