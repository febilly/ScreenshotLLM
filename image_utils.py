"""
图像工具模块 - 处理截图、图片裁剪、编码和答案提取等功能
"""

import io
import base64
import re
from PIL import ImageGrab
from notification import show_notification

def take_screenshot():
    """截取全屏截图"""
    try:
        # 使用 ImageGrab.grab() 来进行截图
        full_screenshot = ImageGrab.grab()
        if full_screenshot is None:
            raise ValueError("截图返回了空对象")
        return full_screenshot
    except Exception as e:
        print(f"[-] 截图失败: {e}")
        show_notification("截图失败", f"无法捕获屏幕: {e}", threaded=True)
        return None

def crop_and_encode_image(image_obj, bbox):
    """从大图中裁剪出选定区域并进行Base64编码"""
    try:
        # 裁剪图片
        cropped_img = image_obj.crop(bbox)
        
        # 将图片存入内存中的字节流
        buffered = io.BytesIO()
        cropped_img.save(buffered, format="JPEG", quality=85)
        
        # 进行Base64编码
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        return f"data:image/jpeg;base64,{img_str}"
            
    except Exception as e:
        print(f"[-] 裁剪或编码失败: {e}")
        show_notification("错误", f"裁剪或编码失败: {e}", threaded=True)
        return None

def extract_answer_from_brackets(text):
    """从文本中提取方括号[]内的内容作为最终答案"""
    # 查找方括号内的内容
    matches = re.findall(r'\[([^\]]*)\]', text)
    if matches:
        # 返回最后一个匹配的内容（通常是最终答案）
        return matches[-1].strip()
    return None
