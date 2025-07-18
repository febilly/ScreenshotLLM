"""
图像工具模块 - 处理截图、图片裁剪、编码和答案提取等功能
"""

import io
import base64
import re
from PIL import ImageGrab, ImageDraw
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

def crop_and_encode_image(image_obj, bbox, red_box_bbox=None):
    """从大图中裁剪出选定区域并进行Base64编码"""
    try:
        # 裁剪图片
        cropped_img = image_obj.crop(bbox)
        
        # 如果有红框区域，在裁剪后的图片上画框
        if red_box_bbox:
            cropped_img = draw_red_box_on_image(cropped_img, red_box_bbox)
        
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

def draw_red_box_on_image(image, red_box_bbox):
    """在图片上画红色框标识重点区域"""
    try:
        # 复制图片以避免修改原图
        img_with_box = image.copy()
        draw = ImageDraw.Draw(img_with_box)
        
        # 获取图片尺寸
        width, height = img_with_box.size
        
        # 使用用户选择的红框坐标
        x1, y1, x2, y2 = red_box_bbox
        
        # 确保坐标在图片范围内
        x1 = max(0, min(width, x1))
        y1 = max(0, min(height, y1))
        x2 = max(0, min(width, x2))
        y2 = max(0, min(height, y2))
        
        # 画红色框
        box_width = max(3, min(width, height) // 200)  # 动态调整框线宽度
        for i in range(box_width):
            draw.rectangle([
                x1 + i, y1 + i, 
                x2 - i, y2 - i
            ], outline='red', width=1)
        
        return img_with_box
        
    except Exception as e:
        print(f"[-] 画红框失败: {e}")
        # 如果画框失败，返回原图
        return image

def extract_answer_from_brackets(text):
    """从文本中提取方括号[]内的内容或LaTeX格式的boxed答案作为最终答案"""
    # 首先尝试提取LaTeX格式的boxed答案：$\boxed{\text{答案}}$ 或 $\boxed{答案}$
    latex_patterns = [
        r'\$\\boxed\{\\text\{([^}]*)\}\}\$',  # $\boxed{\text{答案}}$
        r'\$\\boxed\{([^}]*)\}\$',           # $\boxed{答案}$
        r'\\boxed\{\\text\{([^}]*)\}\}',     # \boxed{\text{答案}}
        r'\\boxed\{([^}]*)\}'                # \boxed{答案}
    ]
    
    for pattern in latex_patterns:
        matches = re.findall(pattern, text)
        if matches:
            # 返回最后一个匹配的内容（通常是最终答案）
            return matches[-1].strip()
    
    # 如果没有找到LaTeX格式，则查找普通方括号内的内容
    matches = re.findall(r'\[([^\]]*)\]', text)
    if matches:
        # 返回最后一个匹配的内容（通常是最终答案）
        return matches[-1].strip()
    
    return None
