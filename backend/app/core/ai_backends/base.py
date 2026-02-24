from abc import ABC, abstractmethod


class AIBackend(ABC):
    """Abstract base class for AI model backends."""

    @abstractmethod
    async def chat(self, messages: list[dict], temperature: float = 0.1, max_tokens: int = 1000) -> str:
        """Send a chat completion request and return the text response."""
        ...

    @abstractmethod
    async def chat_with_image(self, prompt: str, image_b64: str, temperature: float = 0.1, max_tokens: int = 1000) -> str:
        """Send a multimodal chat request with an image and return the text response."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the backend name for logging."""
        ...

    @property
    @abstractmethod
    def supports_vision(self) -> bool:
        """Whether this backend supports image/vision inputs."""
        ...