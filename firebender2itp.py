import os
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import json
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

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
AI_MODEL = "claude-3-7-sonnet"
REQUEST_TIMEOUT = 60.0

class Message(BaseModel):
    role: str
    content: str

def convert_anthropic_to_openai(anthropic_request: dict) -> dict:
    """Convert Anthropic request format to OpenAI format"""
    messages = []
    for message in anthropic_request.get("messages", []):
        messages.append({
            "role": message.get("role", "user"),
            "content": message.get("content", "")
        })
    
    return {
        "model": AI_MODEL,
        "messages": messages,
        "max_tokens": anthropic_request.get("max_tokens", 4097),
        "temperature": anthropic_request.get("temperature", 0.7),
        "stream": anthropic_request.get("stream", False)
    }

def convert_openai_to_anthropic(openai_response: dict) -> dict:
    """Convert OpenAI response format to Anthropic format"""
    if "choices" not in openai_response:
        return openai_response
    
    return {
        "id": openai_response.get("id", ""),
        "type": "chat.completion",
        "role": "assistant",
        "content": openai_response["choices"][0]["message"]["content"],
        "model": openai_response.get("model", AI_MODEL),
        "created": openai_response.get("created", 0)
    }

async def send_request(request_data: dict):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {OPENAI_API_KEY}'
    }

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.post(OPENAI_API_URL + "/chat/completions", headers=headers, json=request_data)
        if request_data.get('stream'):
            async for chunk in resp.aiter_bytes():
                yield chunk
        elif resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        else:
            yield resp.content

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "firebender2itp"}

@app.post("/v1/messages")
async def get_messages(request: Request):
    anthropic_request = await request.json()
    openai_request = convert_anthropic_to_openai(anthropic_request)
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
    stream = request_data.get("stream", False)

    if stream:
        return StreamingResponse(send_request(request_data), media_type="text/event-stream")
    else:
        async for chunk in send_request(request_data):
            return json.loads(chunk)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)