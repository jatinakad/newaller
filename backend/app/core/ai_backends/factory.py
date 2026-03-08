import structlog
from app.core.ai_backends.base import AIBackend
from app.config import get_settings

logger = structlog.get_logger()

_backend_instance: AIBackend | None = None


def get_ai_backend() -> AIBackend:
    """
    Factory: returns the configured AI backend singleton.

    Set AI_BACKEND env var to one of:
      - "gemini"            → Google Gemini API via AI Studio (recommended)
      - "ollama"            → Ollama local server
      - "huggingface_local" → HuggingFace Transformers loaded in-process (needs GPU/RAM)
      - "huggingface_api"   → HuggingFace Inference API (free tier, needs HF_TOKEN)
    """
    global _backend_instance
    if _backend_instance is not None:
        return _backend_instance

    settings = get_settings()
    backend_name = settings.AI_BACKEND.lower().strip()

    if backend_name == "gemini":
        from app.core.ai_backends.gemini_backend import GeminiBackend
        _backend_instance = GeminiBackend()

    elif backend_name == "ollama":
        from app.core.ai_backends.ollama_backend import OllamaBackend
        _backend_instance = OllamaBackend()

    elif backend_name == "huggingface_local":
        from app.core.ai_backends.huggingface_local_backend import HuggingFaceLocalBackend
        _backend_instance = HuggingFaceLocalBackend()

    elif backend_name == "huggingface_api":
        from app.core.ai_backends.huggingface_api_backend import HuggingFaceAPIBackend
        _backend_instance = HuggingFaceAPIBackend()

    else:
        raise ValueError(
            f"Unknown AI_BACKEND: '{backend_name}'. "
            f"Must be one of: gemini, ollama, huggingface_local, huggingface_api"
        )

    logger.info("ai_backend_initialized", backend=_backend_instance.name)
    return _backend_instance
