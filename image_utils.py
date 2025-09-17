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

def crop_and_encode_image(image_obj, bbox, red_box_bboxes=None):
    """从大图中裁剪出选定区域并进行Base64编码"""
    try:
        # 裁剪图片
        cropped_img = image_obj.crop(bbox)
        
        # 如果有红框区域，在裁剪后的图片上画框
        if red_box_bboxes:
            cropped_img = draw_red_box_on_image(cropped_img, red_box_bboxes)
        
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

def draw_red_box_on_image(image, red_box_bboxes):
    """在图片上画红色框标识重点区域，支持多个红框"""
    try:
        # 复制图片以避免修改原图
        img_with_box = image.copy()
        draw = ImageDraw.Draw(img_with_box)
        
        # 获取图片尺寸
        width, height = img_with_box.size
        
        # 如果传入的是单个红框（向后兼容）
        if isinstance(red_box_bboxes, tuple) and len(red_box_bboxes) == 4:
            red_box_bboxes = [red_box_bboxes]
        
        # 画多个红框
        for red_box_bbox in red_box_bboxes:
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

def extract_answer_from_markers(text):
    """从文本中提取<answer>和</answer>标签中的答案作为最终答案"""
    
    def _extract_from_complete_markers():
        """提取完整标记对中的内容"""
        # 定义所有完整标记的模式
        complete_patterns = [
            # XML标签标记（优先级最高）
            r'<answer>(.*?)</answer>',             # <answer>答案</answer>
        ]
        
        for pattern in complete_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            if matches:
                return matches[-1].strip()
        
        return None
    
    def _extract_from_incomplete_markers():
        """从不完整的标记中提取内容（标记后到文本结尾）"""
        # 定义不完整标记的模式
        incomplete_patterns = [
            r'<answer>(.*?)(?:\s*$)',              # <answer>答案 (缺少</answer>)
        ]
        
        for pattern in incomplete_patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                # 从匹配位置开始，提取到文本结尾
                start_pos = match.start(1)
                remaining_text = text[start_pos:].strip()
                if remaining_text:
                    return remaining_text
        
        return None
    
    # 首先尝试完整标记对
    result = _extract_from_complete_markers()
    if result:
        return result
    
    # 如果没有找到完整标记对，尝试不完整标记
    return _extract_from_incomplete_markers()
