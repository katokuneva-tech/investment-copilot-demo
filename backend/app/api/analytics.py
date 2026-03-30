from fastapi import APIRouter, Request, HTTPException
from app.services.analytics import get_dashboard

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/dashboard")
async def dashboard(request: Request):
    # Admin only
    if getattr(request.state, "user_role", "") != "admin":
        raise HTTPException(403, "Admin access required")
    return get_dashboard()
