# app_improved.py
import os
import time
import json
import random
from typing import List, Optional, Literal, AsyncGenerator

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# ===== FastAPI 基础配置 =====
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 上线后改成你的小程序/前端域名
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== 模型定义 =====
Role = Literal["system", "user", "assistant"]

class Message(BaseModel):
    role: Role
    content: str

class ChatReq(BaseModel):
    prompt: str = ""
    messages: Optional[List[Message]] = None
    stream: Optional[bool] = None  # 这里接受但本实现不做流式返回
    userId: Optional[str] = None
    timeout: Optional[float] = Field(default=60.0, ge=10.0, le=300.0, description="请求超时秒数")

class ChatResp(BaseModel):
    answer: str

# ===== DeepSeek API 封装 =====
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")  # 从环境变量读取 API Key

API_URL = "https://api.deepseek.com/v1/chat/completions"

def build_messages(req: ChatReq) -> List[dict]:
    """优先使用 messages；若无则用 prompt 构造单轮对话。"""
    if req.messages and len(req.messages) > 0:
        return [m.model_dump() for m in req.messages]
    if req.prompt and req.prompt.strip():
        return [{"role": "user", "content": req.prompt.strip()}]
    raise HTTPException(status_code=422, detail="必须提供 messages 或 prompt 中的至少一项。")

def call_deepseek_stream(messages: List[dict], timeout: float = 60.0):
    """流式调用 DeepSeek API"""
    if not DEEPSEEK_API_KEY:
        raise HTTPException(status_code=500, detail="服务未配置 DEEPSEEK_API_KEY。")

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.1,
        "stream": True,  # 启用流式输出
    }

    start = time.time()
    try:
        resp = requests.post(API_URL, json=payload, headers=headers, timeout=timeout, stream=True)
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="调用大模型超时")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"调用大模型失败：{str(e)}")

    if resp.status_code >= 400:
        try:
            err = resp.json()
        except Exception:
            err = {"message": resp.text}
        raise HTTPException(status_code=502, detail={"upstream_error": err})

    try:
        for line in resp.iter_lines():
            if time.time() - start > timeout:
                raise HTTPException(status_code=504, detail="调用大模型超时（业务层）")
            
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = line[6:]  # 移除 'data: ' 前缀
                    if data.strip() == '[DONE]':
                        break
                    try:
                        chunk = json.loads(data)
                        if 'choices' in chunk and len(chunk['choices']) > 0:
                            delta = chunk['choices'][0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"解析流式响应失败：{str(e)}")

def call_deepseek(messages: List[dict], timeout: float = 60.0) -> str:
    """调用DeepSeek API，支持重试机制和更好的错误处理"""
    if not DEEPSEEK_API_KEY:
        raise HTTPException(status_code=500, detail="服务未配置 DEEPSEEK_API_KEY。")

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.1,
    }

    # 重试机制
    max_retries = 3
    for attempt in range(max_retries):
        start = time.time()
        try:
            resp = requests.post(API_URL, json=payload, headers=headers, timeout=timeout)
            
            if time.time() - start > timeout:
                raise HTTPException(status_code=504, detail="调用大模型超时（业务层）")

            if resp.status_code >= 400:
                try:
                    err = resp.json()
                    error_msg = err.get('message', '未知错误')
                except Exception:
                    error_msg = resp.text
                
                # 如果是认证错误，不重试
                if resp.status_code == 401:
                    raise HTTPException(status_code=502, detail=f"API认证失败：{error_msg}")
                
                # 如果是服务器错误且还有重试次数，则重试
                if resp.status_code >= 500 and attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)  # 指数退避 + 随机抖动
                    print(f"API服务器错误，{wait_time:.1f}秒后重试 (第{attempt + 1}次)")
                    time.sleep(wait_time)
                    continue
                
                raise HTTPException(status_code=502, detail=f"API调用失败：{error_msg}")

            try:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            except Exception as e:
                raise HTTPException(status_code=502, detail=f"解析大模型返回失败：{str(e)}")
                
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                print(f"请求超时，{wait_time:.1f}秒后重试 (第{attempt + 1}次)")
                time.sleep(wait_time)
                continue
            raise HTTPException(status_code=504, detail="调用大模型超时，请稍后重试")
            
        except requests.exceptions.ConnectionError as e:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                print(f"连接错误，{wait_time:.1f}秒后重试 (第{attempt + 1}次)")
                time.sleep(wait_time)
                continue
            raise HTTPException(status_code=502, detail="网络连接失败，请检查网络设置")
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                print(f"请求异常，{wait_time:.1f}秒后重试 (第{attempt + 1}次)")
                time.sleep(wait_time)
                continue
            raise HTTPException(status_code=502, detail=f"调用大模型失败：{str(e)}")
    
    # 如果所有重试都失败了
    raise HTTPException(status_code=502, detail="调用大模型失败，已重试多次")

# ===== 健康检查 =====
@app.get("/")
def read_root():
    return {"status": "ok", "message": "FastAPI service is running"}

@app.get("/health")
def health():
    return {"status": "healthy"}

# ===== 业务路由：对话 =====
async def generate_stream_response(req: ChatReq):
    """生成流式响应"""
    try:
        messages = build_messages(req)
        
        # 发送开始标记
        yield f"data: {json.dumps({'type': 'start', 'message': '开始生成回答...'}, ensure_ascii=False)}\n\n"
        
        # 流式调用 DeepSeek
        for chunk in call_deepseek_stream(messages, timeout=req.timeout or 60.0):
            yield f"data: {json.dumps({'type': 'content', 'content': chunk}, ensure_ascii=False)}\n\n"
        
        # 发送结束标记
        yield f"data: {json.dumps({'type': 'end', 'message': '回答生成完成'}, ensure_ascii=False)}\n\n"
        
    except HTTPException as e:
        yield f"data: {json.dumps({'type': 'error', 'error': str(e.detail)}, ensure_ascii=False)}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'error': f'未知错误: {str(e)}'}, ensure_ascii=False)}\n\n"

@app.post("/api/chat")
async def chat(req: ChatReq):
    """流式聊天接口"""
    return StreamingResponse(
        generate_stream_response(req),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.post("/api/chat/sync")
def chat_sync(req: ChatReq):
    """同步聊天接口（兼容性保留）"""
    messages = build_messages(req)
    answer = call_deepseek(messages, timeout=req.timeout or 60.0)
    return {"answer": answer}

@app.post("/api/chat/miniprogram")
def chat_miniprogram(req: ChatReq):
    """微信小程序专用接口 - 分块返回，增强错误处理"""
    messages = build_messages(req)
    
    try:
        # 调用 DeepSeek 获取完整回答
        answer = call_deepseek(messages, timeout=req.timeout or 60.0)
        
        # 将回答分成小块（按字符分割，模拟打字效果）
        chunks = []
        chunk_size = 2  # 每块2个字符，更流畅的打字效果
        
        for i in range(0, len(answer), chunk_size):
            chunks.append(answer[i:i+chunk_size])
        
        return {
            "code": 200,
            "message": "success",
            "data": {
                "chunks": chunks,
                "total_chunks": len(chunks),
                "complete_answer": answer,
                "chunk_delay": 50,  # 建议的延迟时间（毫秒）
                "timestamp": int(time.time())
            }
        }
    except HTTPException as e:
        # 根据错误类型返回不同的错误信息
        error_detail = str(e.detail)
        if "超时" in error_detail:
            error_msg = "请求超时，请稍后重试"
        elif "连接失败" in error_detail or "网络" in error_detail:
            error_msg = "网络连接失败，请检查网络设置"
        elif "认证失败" in error_detail:
            error_msg = "服务配置错误，请联系管理员"
        elif "解析" in error_detail:
            error_msg = "服务响应异常，请稍后重试"
        else:
            error_msg = f"服务异常：{error_detail}"
        
        return {
            "code": 500,
            "message": "error",
            "data": {
                "error": error_msg,
                "timestamp": int(time.time())
            }
        }
    except Exception as e:
        return {
            "code": 500,
            "message": "error",
            "data": {
                "error": f"未知错误：{str(e)}",
                "timestamp": int(time.time())
            }
        }

@app.post("/api/chat/simple")
def chat_simple(req: ChatReq):
    """微信小程序简化接口 - 直接返回完整回答"""
    messages = build_messages(req)
    
    try:
        answer = call_deepseek(messages, timeout=req.timeout or 60.0)
        
        return {
            "code": 200,
            "message": "success",
            "data": {
                "answer": answer,
                "timestamp": int(time.time())
            }
        }
    except HTTPException as e:
        # 根据错误类型返回不同的错误信息
        error_detail = str(e.detail)
        if "超时" in error_detail:
            error_msg = "请求超时，请稍后重试"
        elif "连接失败" in error_detail or "网络" in error_detail:
            error_msg = "网络连接失败，请检查网络设置"
        elif "认证失败" in error_detail:
            error_msg = "服务配置错误，请联系管理员"
        elif "解析" in error_detail:
            error_msg = "服务响应异常，请稍后重试"
        else:
            error_msg = f"服务异常：{error_detail}"
        
        return {
            "code": 500,
            "message": "error",
            "data": {
                "error": error_msg,
                "timestamp": int(time.time())
            }
        }
    except Exception as e:
        return {
            "code": 500,
            "message": "error",
            "data": {
                "error": f"未知错误：{str(e)}",
                "timestamp": int(time.time())
            }
        }

# ===== 网络连通性检查 =====
@app.get("/api/health/network")
def check_network():
    """检查网络连通性"""
    try:
        # 测试到DeepSeek API的连通性
        resp = requests.get("https://api.deepseek.com", timeout=10)
        return {
            "code": 200,
            "message": "网络正常",
            "data": {
                "deepseek_api": "可访问",
                "timestamp": int(time.time())
            }
        }
    except requests.exceptions.Timeout:
        return {
            "code": 500,
            "message": "网络超时",
            "data": {
                "deepseek_api": "超时",
                "timestamp": int(time.time())
            }
        }
    except requests.exceptions.ConnectionError:
        return {
            "code": 500,
            "message": "网络连接失败",
            "data": {
                "deepseek_api": "无法连接",
                "timestamp": int(time.time())
            }
        }
    except Exception as e:
        return {
            "code": 500,
            "message": "网络检查失败",
            "data": {
                "error": str(e),
                "timestamp": int(time.time())
            }
        }
