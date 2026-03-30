#!/bin/bash
# Start backend (FastAPI) on port 8000
cd /app/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# Wait for backend
sleep 3

# Start frontend (Next.js) on PORT (Railway sets this, default 3000)
cd /app/frontend
PORT=${PORT:-3000} npx next start -p ${PORT:-3000}
