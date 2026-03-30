import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api import chat, reports, documents
from app.api import analytics as analytics_router
from app.auth import AuthMiddleware, USERS, create_token, change_password

app = FastAPI(title="Investment Intelligence Copilot", version="1.0.0")

allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(reports.router)
app.include_router(documents.router)
app.include_router(analytics_router.router)


@app.post("/api/auth/login")
async def login(body: dict):
    password = body.get("password", "")
    user = USERS.get(password)
    if not user:
        return {"error": "Invalid password"}
    token = create_token(user["name"], user["role"])
    return {"token": token, "name": user["name"], "role": user["role"]}


@app.post("/api/auth/change-password")
async def change_pwd(body: dict):
    old = body.get("old_password", "")
    new = body.get("new_password", "")
    return change_password(old, new)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "Investment Intelligence Copilot"}


@app.get("/api/model")
async def get_model():
    from app.services.llm_client import llm_client
    return {
        "provider": llm_client.provider,
        "model": llm_client.cotype_model if llm_client.provider == "cotype" else llm_client.claude_model,
    }


@app.post("/api/model")
async def set_model(body: dict):
    from app.services.llm_client import llm_client
    provider = body.get("provider")
    if provider in ("cotype", "claude"):
        llm_client.provider = provider
        model = llm_client.cotype_model if provider == "cotype" else llm_client.claude_model
        return {"provider": provider, "model": model}
    return {"error": "Invalid provider. Use 'cotype' or 'claude'."}
