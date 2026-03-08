from pydantic import BaseModel


class ChatRequest(BaseModel):
    patient_id: str
    question: str
    medicine_name: str = ""
    conversation_history: list[dict] | None = None


class ChatResponse(BaseModel):
    answer: str
    patient_name: str = ""
    patient_id: str = ""
    context_used: dict = {}
    error: bool = False
