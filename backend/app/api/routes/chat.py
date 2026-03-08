from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core import chat_service
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def ask_ai(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Doctor asks AI a question about a patient's data, allergies, or medicine safety."""
    if not body.question.strip():
        raise HTTPException(status_code=422, detail="Question cannot be empty")

    result = await chat_service.ask_about_patient(
        db=db,
        patient_id=body.patient_id,
        question=body.question,
        medicine_name=body.medicine_name,
        conversation_history=body.conversation_history,
    )

    if result.get("error") and "not found" in result.get("answer", "").lower():
        raise HTTPException(status_code=404, detail="Patient not found")

    return ChatResponse(**result)
