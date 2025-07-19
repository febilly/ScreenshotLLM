"""
图像工具模块 - 处理截图、图片裁剪、编码和答案提取等功能
"""

import io
import base64
import re
from PIL import ImageGrab, ImageDraw
from notification import show_notification
from monitor_utils import take_screenshot_multi_monitor

def take_screenshot():
    """截取全屏截图，支持多显示器"""
    try:
        # 使用新的多显示器截图功能，获取包含所有显示器的虚拟桌面
        screenshot_data = take_screenshot_multi_monitor()
        if screenshot_data is None:
            raise ValueError("截图返回了空对象")
        
        # 如果返回的是字典（包含显示器布局信息），提取图像
        if isinstance(screenshot_data, dict) and 'image' in screenshot_data:
            return screenshot_data['image']
        else:
            # 兼容旧的直接返回图像的方式
            return screenshot_data
            
    except Exception as e:
        print(f"[-] 截图失败: {e}")
        show_notification("截图失败", f"无法捕获屏幕: {e}")
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
        show_notification("错误", f"裁剪或编码失败: {e}")
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
    """从文本中提取方括号[]、中文括号【】或LaTeX格式的boxed答案作为最终答案"""
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
    
    # 尝试提取中文方括号【】内的内容
    chinese_bracket_matches = re.findall(r'【([^】]*)】', text)
    if chinese_bracket_matches:
        # 返回最后一个匹配的内容（通常是最终答案）
        return chinese_bracket_matches[-1].strip()
    
    # 如果没有找到LaTeX格式和中文方括号，则查找普通方括号内的内容
    matches = re.findall(r'\[([^\]]*)\]', text)
    if matches:
        # 返回最后一个匹配的内容（通常是最终答案）
        return matches[-1].strip()
    
    return None
