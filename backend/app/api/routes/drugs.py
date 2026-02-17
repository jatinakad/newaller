from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/drugs", tags=["drugs"]) 

@router.get("/search")
async def search_drugs(q: str = ""):
    return {"q": q, "results": []}
