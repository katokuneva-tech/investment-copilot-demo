import asyncio
import json
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
from app.models.schemas import ChatRequest
from app.services import skill_router

router = APIRouter()


@router.post("/api/chat")
async def chat(request: ChatRequest):
    response = await skill_router.route(request.skill_id, request.message, request.session_id)
    return response


@router.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    response = await skill_router.route(request.skill_id, request.message, request.session_id)

    async def event_generator():
        for block in response.blocks:
            if block.type == "text":
                words = block.data.split(" ")
                for word in words:
                    yield {"data": json.dumps({"type": "text_delta", "content": word + " "})}
                    await asyncio.sleep(0.025)
                yield {"data": json.dumps({"type": "text_done"})}
            else:
                block_data = block.data if isinstance(block.data, dict) else (block.data.model_dump() if hasattr(block.data, "model_dump") else block.data)
                yield {"data": json.dumps({"type": block.type, "data": block_data}, ensure_ascii=False)}
                await asyncio.sleep(0.1)
        yield {"data": json.dumps({"type": "done", "session_id": response.session_id})}

    return EventSourceResponse(event_generator())
