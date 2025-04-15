from typing import Any

import os
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import json
from dotenv import load_dotenv
from pydantic import BaseModel
import logging

load_dotenv()

logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="Firebender2ITP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OPENAI_API_URL = os.getenv("OPENAI_API_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
REQUEST_TIMEOUT = 60.0

MODEL_MAPPING = {
    "claude-3-7-sonnet": "claude-3-7-sonnet",
    "claude-3.5-sonnet": "claude-3-7-sonnet", 
    "o3-mini": "3o-mini",
    "gpt-4o": "gpt-4o",
}
AI_BASE_MODEL = "gpt-4o"

# --- Helper Functions ---
def get_mapped_model(requested_model: str) -> str:
    """
    Maps the requested model name to a supported target model.
    Returns the original requested model name and the mapped model name.
    """
    normalized_model = requested_model.lower().replace(" ", "-")
    target_model = MODEL_MAPPING.get(normalized_model, AI_BASE_MODEL)
    logger.info(f"Model: '{requested_model}' has been mapped to: '{target_model}'")


    return target_model


def convert_anthropic_to_openai(anthropic_request: dict, target_model: str) -> dict:
    messages = []
    for message in anthropic_request.get("messages", []):
        messages.append({
            "role": message.get("role", "user"),
            "content": message.get("content", "")
        })

    return {
        "model": target_model,
        "messages": messages,
        "max_tokens": anthropic_request.get("max_tokens", 4097),
        "temperature": anthropic_request.get("temperature", 0.7),
        "stream": anthropic_request.get("stream", False)
    }

def convert_openai_to_anthropic(openai_response: dict) -> dict:
    if "choices" not in openai_response:
        return openai_response
    
    return {
        "id": openai_response.get("id", ""),
        "type": "chat.completion",
        "role": "assistant",
        "content": openai_response["choices"][0]["message"]["content"],
        "model": openai_response.get("model", AI_BASE_MODEL),
        "created": openai_response.get("created", 0)
    }

async def send_request(request_data: dict):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {OPENAI_API_KEY}'
    }
    is_stream = request_data.get('stream', False)

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        try:
            async with client.stream("POST", OPENAI_API_URL + "/chat/completions", headers=headers, json=request_data) as resp:
                if resp.status_code != 200:
                    error_detail_bytes = await resp.aread()
                    raise HTTPException(status_code=resp.status_code, detail=error_detail_bytes.decode())

                if is_stream:
                    async for chunk in resp.aiter_bytes():
                        yield chunk
                else:
                    full_body = await resp.aread()
                    yield full_body

        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Service Unavailable: {exc}")

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "firebender2itp"}

@app.post("/v1/messages")
async def get_messages(request: Request):
    anthropic_request = await request.json()
    target_model = get_mapped_model(anthropic_request.get("model"))
    openai_request = convert_anthropic_to_openai(anthropic_request, target_model)
    stream = openai_request.get("stream", False)

    if stream:
        return StreamingResponse(send_request(openai_request), media_type="text/event-stream")
    else:
        async for chunk in send_request(openai_request):
            openai_response = json.loads(chunk)
            anthropic_response = convert_openai_to_anthropic(openai_response)
            return anthropic_response

@app.post("/v1/chat/completions")
async def get_completions(request: Request):
    request_data = await request.json()
    request_data['model'] = get_mapped_model(request_data.get("model"))
    stream = request_data.get("stream", False)

    if stream:
        return StreamingResponse(send_request(request_data), media_type="text/event-stream")
    else:
        async for chunk in send_request(request_data):
            openai_response = json.loads(chunk)
            return openai_response

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)