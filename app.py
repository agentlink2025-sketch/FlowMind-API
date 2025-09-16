# app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 上线后换成你的小程序请求域名
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatReq(BaseModel):
    prompt: str = ""
    messages: list | None = None
    stream: bool | None = None
    userId: str | None = None

@app.get("/")
def read_root():
    return {"status": "ok", "message": "FastAPI service is running"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/api/chat")
def chat(req: ChatReq):
    # 暂时忽略入参，固定回复
    return {"answer": "这是固定回复：你好，我已经收到你的问题，会在接入大模型后给出智能回答。"}
