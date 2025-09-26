#!/usr/bin/env python3
import asyncio
import httpx
import json
import time

# 配置
BASE_URL = "http://localhost:8080"

async def test_miniprogram_api():
    """测试 /api/chat/miniprogram 接口"""
    print("🚀 开始测试 /api/chat/miniprogram 接口")
    print("==================================================")

    async with httpx.AsyncClient(timeout=60.0) as client:
        # 测试数据
        test_cases = [
            {
                "name": "简单问题",
                "data": {
                    "prompt": "你好，请简单介绍一下自己",
                    "timeout": 30.0
                }
            },
            {
                "name": "复杂问题",
                "data": {
                    "prompt": "请详细解释一下人工智能的发展历程，包括各个重要阶段和里程碑事件",
                    "timeout": 60.0
                }
            },
            {
                "name": "使用messages格式",
                "data": {
                    "messages": [
                        {"role": "user", "content": "什么是机器学习？"}
                    ],
                    "timeout": 30.0
                }
            }
        ]

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{i}️⃣ 测试 {test_case['name']}...")
            print(f"   请求数据: {json.dumps(test_case['data'], indent=2, ensure_ascii=False)}")
            
            try:
                start_time = time.time()
                response = await client.post(f"{BASE_URL}/api/chat/miniprogram", json=test_case['data'])
                end_time = time.time()
                
                print(f"   状态码: {response.status_code}")
                print(f"   响应时间: {end_time - start_time:.2f}秒")
                
                if response.status_code == 200:
                    result = response.json()
                    print("   ✅ 请求成功!")
                    print(f"   返回码: {result['code']}")
                    print(f"   消息: {result['message']}")
                    
                    if 'data' in result:
                        data = result['data']
                        print(f"   总块数: {data.get('total_chunks', 0)}")
                        print(f"   块延迟: {data.get('chunk_delay', 0)}ms")
                        print(f"   完整回答长度: {len(data.get('complete_answer', ''))}")
                        print(f"   回答预览: {data.get('complete_answer', '')[:100]}...")
                        
                        # 显示前几个chunks
                        chunks = data.get('chunks', [])
                        if chunks:
                            print(f"   前5个块: {chunks[:5]}")
                else:
                    print(f"   ❌ 请求失败!")
                    print(f"   响应内容: {response.text}")
                    
            except httpx.TimeoutException:
                print(f"   ⚠️ 请求超时!")
            except Exception as e:
                print(f"   ❌ 请求异常: {e}")

    print("\n==================================================")
    print("🏁 测试完成")

if __name__ == "__main__":
    asyncio.run(test_miniprogram_api())
