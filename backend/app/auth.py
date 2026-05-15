"""Simple password-based auth with JWT tokens and password change."""
import jwt
import json
import time
import os
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pathlib import Path

SECRET = "mws-copilot-2026-secret-key"
TOKEN_EXPIRY = 7 * 24 * 3600  # 7 days
PASSWORDS_FILE = Path(__file__).parent / "data" / "passwords.json"

# Default passwords (used on first run)
_DEFAULT_USERS = {
    "admin-mws": {"name": "Админ", "role": "admin"},
    "investor-alpha": {"name": "Тестировщик 1", "role": "user"},
    "analyst-beta": {"name": "Тестировщик 2", "role": "user"},
    "partner-gamma": {"name": "Тестировщик 3", "role": "user"},
    "advisor-delta": {"name": "Тестировщик 4", "role": "user"},
    "director-omega": {"name": "Тестировщик 5", "role": "user"},
    "samsonov-sistema": {"name": "Самсонов", "role": "user"},
    "cherkasov-sistema": {"name": "Черкасов М.Х.", "role": "user"},
    "MWSCopilot-Demo-2026": {"name": "Demo", "role": "demo"},
}


def _load_users() -> dict:
    """Load users from persistent file, or initialize from defaults."""
    if PASSWORDS_FILE.exists():
        try:
            return json.loads(PASSWORDS_FILE.read_text("utf-8"))
        except Exception:
            pass
    # Initialize from defaults
    _save_users(_DEFAULT_USERS)
    return dict(_DEFAULT_USERS)


def _save_users(users: dict):
    """Persist users to JSON file."""
    PASSWORDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PASSWORDS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2), "utf-8")


# Live users dict (loaded once, mutated in-memory + persisted)
USERS = _load_users()

# Paths that don't require auth
PUBLIC_PATHS = {"/api/auth/login", "/api/auth/change-password", "/api/health"}


def create_token(name: str, role: str) -> str:
    payload = {"name": name, "role": role, "exp": int(time.time()) + TOKEN_EXPIRY}
    return jwt.encode(payload, SECRET, algorithm="HS256")


def verify_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET, algorithms=["HS256"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def change_password(old_password: str, new_password: str) -> dict:
    """Change password. Returns new token or error."""
    user = USERS.get(old_password)
    if not user:
        return {"error": "Неверный текущий пароль"}

    if len(new_password) < 4:
        return {"error": "Пароль должен быть не менее 4 символов"}

    if new_password in USERS:
        return {"error": "Этот пароль уже занят"}

    # Move user to new password
    USERS[new_password] = user
    del USERS[old_password]
    _save_users(USERS)

    # Return new token
    token = create_token(user["name"], user["role"])
    return {"token": token, "name": user["name"], "role": user["role"]}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip auth for public paths and OPTIONS (CORS preflight)
        if path in PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        # Skip auth for non-API paths (Next.js static files)
        if not path.startswith("/api/"):
            return await call_next(request)

        # Check token
        auth = request.headers.get("authorization", "")
        if not auth.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})

        token = auth[7:]
        payload = verify_token(token)
        if not payload:
            return JSONResponse(status_code=401, content={"error": "Token expired or invalid"})

        # Attach user info to request state
        request.state.user_name = payload.get("name", "Unknown")
        request.state.user_role = payload.get("role", "user")

        return await call_next(request)
