import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import chat, reports

app = FastAPI(title="Investment Intelligence Copilot", version="1.0.0")

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(reports.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "Investment Intelligence Copilot"}
