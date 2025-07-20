"""
API客户端模块 - 负责与OpenRouter API进行通信
"""

import requests
from config import OPENROUTER_API_KEY, OPENROUTER_API_URL
from notification import show_notification

def _prepare_request_data(base64_image, prompt, model, stream=False):
    """准备API请求的headers和data"""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "Screenshot Assistant"
    }

    data = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": base64_image},
                    },
                ],
            }
        ],
        "max_tokens": 32768,
    }
    
    if stream:
        data["stream"] = True
    
    return headers, data

def analyze_image_with_openrouter_sync(base64_image, prompt, model):
    """将图片和提示词发送到OpenRouter API - 非流式版本"""
    headers, data = _prepare_request_data(base64_image, prompt, model, stream=False)

    try:
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=data, timeout=120)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        print(f"[-] API 请求失败: {e}")
        error_message = f"API 请求失败: {e}"
        if hasattr(e, 'response') and e.response is not None:
            error_message += f"\n响应内容: {e.response.text}"
        show_notification("API 错误", error_message)
        return None
    except (KeyError, IndexError) as e:
        print(f"[-] 解析API响应失败: {e}")
        show_notification("API 错误", f"解析API响应失败，收到的数据格式不正确。")
        return None

def analyze_image_with_openrouter_stream(base64_image, prompt, model):
    """将图片和提示词发送到OpenRouter API - 流式版本"""
    headers, data = _prepare_request_data(base64_image, prompt, model, stream=True)

    try:
        # 流式SSE
        with requests.post(OPENROUTER_API_URL, headers=headers, json=data, timeout=120, stream=True) as response:
            response.raise_for_status()
            response.encoding = 'utf-8'  # 强制使用UTF-8编码
            buffer = ""
            for line in response.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data:"):
                    continue
                content = line[len("data:"):].strip()
                if content == "[DONE]":
                    break
                try:
                    import json
                    delta = json.loads(content)
                    # OpenRouter兼容OpenAI格式
                    delta_content = delta.get('choices', [{}])[0].get('delta', {}).get('content')
                    if delta_content:
                        buffer += delta_content
                        yield buffer
                except Exception as e:
                    continue
    except requests.exceptions.RequestException as e:
        print(f"[-] API 请求失败: {e}")
        error_message = f"API 请求失败: {e}"
        if hasattr(e, 'response') and e.response is not None:
            error_message += f"\n响应内容: {e.response.text}"
        show_notification("API 错误", error_message)
        yield None
    except (KeyError, IndexError) as e:
        print(f"[-] 解析API响应失败: {e}")
        show_notification("API 错误", f"解析API响应失败，收到的数据格式不正确。")
        yield None

def analyze_image_with_openrouter(base64_image, prompt, model, stream=False):
    """将图片和提示词发送到OpenRouter API - 兼容性包装函数"""
    if stream:
        return analyze_image_with_openrouter_stream(base64_image, prompt, model)
    else:
        return analyze_image_with_openrouter_sync(base64_image, prompt, model)
