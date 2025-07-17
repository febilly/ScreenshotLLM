"""
API客户端模块 - 负责与OpenRouter API进行通信
"""

import requests
from config import OPENROUTER_API_KEY, OPENROUTER_API_URL
from notification import show_notification

def analyze_image_with_openrouter(base64_image, prompt, model):
    """将图片和提示词发送到OpenRouter API"""
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
        "max_tokens": 2048,
    }

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
        show_notification("API 错误", error_message, threaded=True)
        return None
    except (KeyError, IndexError) as e:
        print(f"[-] 解析API响应失败: {e}")
        show_notification("API 错误", f"解析API响应失败，收到的数据格式不正确。", threaded=True)
        return None
