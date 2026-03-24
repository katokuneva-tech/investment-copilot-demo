import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "reports")


@router.get("/api/reports/{report_id}")
async def download_report(report_id: str):
    path = os.path.join(REPORTS_DIR, f"{report_id}.pdf")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(path, media_type="application/pdf", filename=f"report_{report_id}.pdf")
