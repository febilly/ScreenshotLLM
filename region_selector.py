"""
区域选择模块 - 处理用户在截图上选择矩形区域的功能，支持多显示器
"""

import queue
import time
import tkinter as tk
from tkinter import Toplevel, Canvas
from PIL import ImageTk

# 全局队列用于线程间通信
task_queue = queue.Queue()
result_queue = queue.Queue()

def get_virtual_screen_geometry():
    """获取虚拟屏幕的几何信息（包括所有显示器），直接使用系统未缩放的像素值"""
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        
        # 获取虚拟屏幕的尺寸（系统原始像素，与MSS截图库一致）
        left = user32.GetSystemMetrics(76)    # SM_XVIRTUALSCREEN
        top = user32.GetSystemMetrics(77)     # SM_YVIRTUALSCREEN  
        width = user32.GetSystemMetrics(78)   # SM_CXVIRTUALSCREEN
        height = user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
        
        print(f"[*] 虚拟屏幕尺寸: {width}x{height} 位置({left}, {top})")
        
        return {
            'x': left,
            'y': top, 
            'width': width,
            'height': height
        }
    except Exception as e:
        print(f"[-] 获取虚拟屏幕信息失败: {e}")
        # 回退到主屏幕
        return {
            'x': 0,
            'y': 0,
            'width': 1920,
            'height': 1080
        }  # TODO: 这个默认值可能会出问题

def select_region_on_image(screenshot_image, config_name=None, need_red_box=False):
    """在一个静态的截图上允许用户选择矩形区域 - 使用队列确保在主线程中执行"""
    # 将任务放入队列
    task_queue.put(('select_region', screenshot_image, config_name, need_red_box))
    # 等待结果
    result = result_queue.get()
    return result

class RegionSelector:
    def __init__(self, master, screenshot_image, config_name=None, need_red_box=False):
        self.master = master
        self.image = screenshot_image
        self.original_image = screenshot_image  # 保存原始图片
        self.config_name = config_name if config_name else "截图分析"
        self.need_red_box = need_red_box
        self.selection_stage = 1  # 1: 选择裁切区域, 2: 选择红框区域
        self.crop_bbox = None  # 存储第一次选择的裁切区域
        
        # 使用截图的实际尺寸来设置窗口，而不是虚拟屏幕几何
        # 这样确保窗口尺寸与截图完全匹配
        screenshot_width, screenshot_height = screenshot_image.size

        # 将Pillow图像转换为Tkinter可以使用的格式
        self.tk_image = ImageTk.PhotoImage(self.image)

        self.top = Toplevel(self.master)
        
        # 设置窗口大小为截图尺寸，位置从(0,0)开始覆盖所有显示器
        self.top.geometry(f"{screenshot_width}x{screenshot_height}+0+0")
        self.top.overrideredirect(True)  # 移除窗口边框
        self.top.attributes("-topmost", True)
        self.top.focus_force()
        self.top.lift()
        
        # 强制抢夺鼠标焦点
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            
            # 定义函数参数类型
            user32.SetForegroundWindow.argtypes = [wintypes.HWND]
            user32.SetForegroundWindow.restype = wintypes.BOOL
            user32.SetActiveWindow.argtypes = [wintypes.HWND]
            user32.SetActiveWindow.restype = wintypes.HWND
            
            # 释放任何鼠标捕获
            user32.ReleaseCapture()
            # 解除鼠标剪切区域
            user32.ClipCursor(None)
            # 强制设置窗口为前台
            hwnd = self.top.winfo_id()
            user32.SetForegroundWindow(hwnd)
            user32.SetActiveWindow(hwnd)
        except Exception as e:
            print(f"设置窗口焦点时出错: {e}")
            pass

        # 创建画布，使用截图尺寸
        self.canvas = Canvas(self.top, 
                           width=screenshot_width, 
                           height=screenshot_height, 
                           cursor="crosshair",
                           bg='black')  # 设置黑色背景
        self.canvas.pack(fill="both", expand=True)
        
        # 图像直接放在(0,0)位置，无需偏移
        self.image_offset_x = 0
        self.image_offset_y = 0
        
        # 在画布上显示图像
        self.canvas_image_id = self.canvas.create_image(
            0, 0, anchor="nw", image=self.tk_image)
        
        # 在左上角显示配置名称
        title_text = f"模式: {self.config_name}"
        if self.need_red_box:
            if self.selection_stage == 1:
                title_text += " - 第1步: 选择裁切区域"
            else:
                title_text += " - 第2步: 选择红框区域"
        
        # 先创建临时文字对象来测量实际尺寸
        temp_text = self.canvas.create_text(0, 0, text=title_text, font=("微软雅黑", 16, "bold"))
        text_bbox = self.canvas.bbox(temp_text)
        self.canvas.delete(temp_text)  # 删除临时文字
        
        # 计算实际文字尺寸
        if text_bbox:
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
        else:
            # fallback 到估算值
            text_width = len(title_text) * 10
            text_height = 20
        
        # 添加内边距
        padding = 8
        bg_x1 = 10
        bg_y1 = 10
        bg_x2 = bg_x1 + text_width + padding * 2
        bg_y2 = bg_y1 + text_height + padding * 2
        
        # 创建半透明背景矩形
        self.title_bg = self.canvas.create_rectangle(
            bg_x1, bg_y1, bg_x2, bg_y2,
            fill="black",
            stipple="gray50",  # 使用stipple创建半透明效果
            outline="",
            tags="title_bg"
        )
        
        # 创建文字，位置在背景中心
        text_x = bg_x1 + padding
        text_y = bg_y1 + padding
        
        self.title_text = self.canvas.create_text(
            text_x, text_y, 
            text=title_text, 
            anchor="nw",
            font=("微软雅黑", 16, "bold"),
            fill="white",
            tags="title"
        )
        
        # 确保背景在文字下面
        self.canvas.tag_lower(self.title_bg, self.title_text)

        # 初始化图形元素变量
        self.crosshair_lines = []
        self.selection_rect = None
        
        # 鼠标状态
        self.start_x = None
        self.start_y = None
        self.is_selecting = False
        
        # 性能优化：限制更新频率
        self.last_update_time = 0
        self.update_interval = 16  # 约60FPS的更新间隔（毫秒）
        
        self.top.bind("<Button-1>", self.on_mouse_down)
        self.top.bind("<B1-Motion>", self.on_mouse_move)
        self.top.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.top.bind("<Motion>", self.on_mouse_motion)
        self.top.bind("<Escape>", self.on_escape)
        self.selection = None

    def on_escape(self, event):
        self.selection = None
        self.top.destroy()
        self.master.quit()

    def clear_crosshair(self):
        """清除十字瞄准线"""
        for line in self.crosshair_lines:
            self.canvas.delete(line)
        self.crosshair_lines = []

    def update_crosshair(self, x, y):
        """更新十字瞄准线位置（高性能版本）"""
        # 清除旧的十字线
        self.clear_crosshair()
        
        # 只在图像区域内绘制十字线
        if 0 <= x < self.image.width and 0 <= y < self.image.height:
            # 双色十字线：先画黑色粗线，再画白色细线
            # 水平线
            h_black = self.canvas.create_line(0, y, self.image.width, y, fill='black', width=3)
            h_white = self.canvas.create_line(0, y, self.image.width, y, fill='white', width=1)
            # 垂直线
            v_black = self.canvas.create_line(x, 0, x, self.image.height, fill='black', width=3)
            v_white = self.canvas.create_line(x, 0, x, self.image.height, fill='white', width=1)
            
            self.crosshair_lines = [h_black, h_white, v_black, v_white]

    def update_selection_rect(self, x1, y1, x2, y2):
        """更新选择框（高性能版本）"""
        # 删除旧的选择框
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
        
        # 限制坐标在图像范围内
        x1 = max(0, min(self.image.width, x1))
        y1 = max(0, min(self.image.height, y1))
        x2 = max(0, min(self.image.width, x2))
        y2 = max(0, min(self.image.height, y2))
        
        # 创建新的选择框
        self.selection_rect = self.canvas.create_rectangle(
            x1, y1, x2, y2, 
            outline='red', width=3
        )

    def throttled_update(self, update_func, *args):
        """限制更新频率以提高性能"""
        current_time = time.time() * 1000  # 转换为毫秒
        
        if current_time - self.last_update_time >= self.update_interval:
            update_func(*args)
            self.last_update_time = current_time
            # 使用after_idle确保在主线程中执行
            self.top.update_idletasks()

    def canvas_to_image_coords(self, canvas_x, canvas_y):
        """将画布坐标转换为图像坐标（现在无需转换）"""
        return canvas_x, canvas_y
    
    def image_to_canvas_coords(self, image_x, image_y):
        """将图像坐标转换为画布坐标（现在无需转换）"""
        return image_x, image_y
    
    def is_point_in_image(self, canvas_x, canvas_y):
        """检查画布坐标是否在图像范围内"""
        return 0 <= canvas_x < self.image.width and 0 <= canvas_y < self.image.height

    def on_mouse_motion(self, event):
        """鼠标移动时显示十字瞄准线"""
        if not self.is_selecting:
            canvas_x = self.canvas.canvasx(event.x)
            canvas_y = self.canvas.canvasy(event.y)
            
            # 检查是否在有效区域内
            if self.selection_stage == 1:
                # 第一步：整个图像区域都可以显示十字线
                if self.is_point_in_image(canvas_x, canvas_y):
                    self.throttled_update(self.update_crosshair, canvas_x, canvas_y)
                else:
                    self.clear_crosshair()
            else:
                # 第二步：只在裁切区域内显示十字线
                image_x, image_y = self.canvas_to_image_coords(canvas_x, canvas_y)
                crop_x1, crop_y1, crop_x2, crop_y2 = self.crop_bbox
                if crop_x1 <= image_x <= crop_x2 and crop_y1 <= image_y <= crop_y2:
                    self.throttled_update(self.update_crosshair, canvas_x, canvas_y)
                else:
                    self.clear_crosshair()

    def on_mouse_down(self, event):
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # 检查点击是否在有效区域内
        if self.selection_stage == 1:
            # 第一步：可以在整个图像区域内选择
            if self.is_point_in_image(canvas_x, canvas_y):
                image_x, image_y = self.canvas_to_image_coords(canvas_x, canvas_y)
                self.start_x = image_x
                self.start_y = image_y
                self.is_selecting = True
                
                # 清除十字线
                self.clear_crosshair()
                
                # 立即显示初始选择框（使用画布坐标）
                self.update_selection_rect(canvas_x, canvas_y, canvas_x, canvas_y)
        else:
            # 第二步：只能在裁切区域内选择
            image_x, image_y = self.canvas_to_image_coords(canvas_x, canvas_y)
            crop_x1, crop_y1, crop_x2, crop_y2 = self.crop_bbox
            if crop_x1 <= image_x <= crop_x2 and crop_y1 <= image_y <= crop_y2:
                # 坐标相对于裁切区域
                self.start_x = image_x - crop_x1
                self.start_y = image_y - crop_y1
                self.is_selecting = True
                
                # 清除十字线
                self.clear_crosshair()
                
                # 立即显示初始选择框（使用画布坐标）
                self.update_selection_rect(canvas_x, canvas_y, canvas_x, canvas_y)

    def on_mouse_move(self, event):
        if self.is_selecting and self.start_x is not None and self.start_y is not None:
            canvas_x = self.canvas.canvasx(event.x)
            canvas_y = self.canvas.canvasy(event.y)
            
            # 将起始点转换为画布坐标
            if self.selection_stage == 1:
                start_canvas_x, start_canvas_y = self.image_to_canvas_coords(self.start_x, self.start_y)
            else:
                # 第二步时，起始点是相对于裁切区域的
                crop_x1, crop_y1, _, _ = self.crop_bbox
                abs_start_x = crop_x1 + self.start_x
                abs_start_y = crop_y1 + self.start_y
                start_canvas_x, start_canvas_y = self.image_to_canvas_coords(abs_start_x, abs_start_y)
            
            # 使用节流更新来提高性能
            self.throttled_update(self.update_selection_rect, start_canvas_x, start_canvas_y, canvas_x, canvas_y)

    def on_mouse_up(self, event):
        if self.is_selecting and self.start_x is not None and self.start_y is not None:
            canvas_x = self.canvas.canvasx(event.x)
            canvas_y = self.canvas.canvasy(event.y)
            
            if self.selection_stage == 1:
                # 第一步：转换画布坐标到图像坐标
                end_image_x, end_image_y = self.canvas_to_image_coords(canvas_x, canvas_y)
                
                # 限制坐标在图像范围内
                end_x = max(0, min(self.image.width, end_image_x))
                end_y = max(0, min(self.image.height, end_image_y))
                start_x = max(0, min(self.image.width, self.start_x))
                start_y = max(0, min(self.image.height, self.start_y))
                
                # 计算最终选择区域坐标
                x1 = int(min(start_x, end_x))
                y1 = int(min(start_y, end_y))
                x2 = int(max(start_x, end_x))
                y2 = int(max(start_y, end_y))
                
                # 确保坐标在有效范围内
                x1 = max(0, min(self.image.width, x1))
                y1 = max(0, min(self.image.height, y1))
                x2 = max(0, min(self.image.width, x2))
                y2 = max(0, min(self.image.height, y2))
                
            else:
                # 第二步：相对坐标已经在start_x, start_y中
                crop_x1, crop_y1, crop_x2, crop_y2 = self.crop_bbox
                current_image_x, current_image_y = self.canvas_to_image_coords(canvas_x, canvas_y)
                end_rel_x = current_image_x - crop_x1
                end_rel_y = current_image_y - crop_y1
                
                # 计算裁切区域的尺寸
                crop_width = crop_x2 - crop_x1
                crop_height = crop_y2 - crop_y1
                
                # 限制坐标在裁切区域内
                end_x = max(0, min(crop_width, end_rel_x))
                end_y = max(0, min(crop_height, end_rel_y))
                start_x = max(0, min(crop_width, self.start_x))
                start_y = max(0, min(crop_height, self.start_y))
                
                # 计算最终选择区域坐标
                x1 = int(min(start_x, end_x))
                y1 = int(min(start_y, end_y))
                x2 = int(max(start_x, end_x))
                y2 = int(max(start_y, end_y))
            
            # 处理两步选择逻辑
            if self.selection_stage == 1 and self.need_red_box:
                # 第一步：选择裁切区域
                self.crop_bbox = (x1, y1, x2, y2)
                self.selection_stage = 2
                self.is_selecting = False
                
                # 更新显示的图片为裁切后的图片
                self.update_to_cropped_image()
                
                # 更新标题
                self.update_title_text()
                
                # 重置鼠标状态
                self.start_x = None
                self.start_y = None
                
                # 清除选择框
                if self.selection_rect:
                    self.canvas.delete(self.selection_rect)
                    self.selection_rect = None
                
            else:
                # 最后一步：完成选择
                if self.need_red_box and self.selection_stage == 2:
                    # 在第二步中，x1,y1,x2,y2已经是相对于裁切区域的坐标
                    # 不需要再次转换，直接使用即可
                    red_box_x1 = x1
                    red_box_y1 = y1
                    red_box_x2 = x2
                    red_box_y2 = y2
                                        
                    # 返回裁切区域和红框区域的坐标
                    self.selection = {
                        'crop_bbox': self.crop_bbox,
                        'red_box_bbox': (red_box_x1, red_box_y1, red_box_x2, red_box_y2)
                    }
                else:
                    # 普通模式，只返回裁切区域
                    self.selection = (x1, y1, x2, y2)
                
                self.top.destroy()
                self.master.quit()

    def update_to_cropped_image(self):
        """更新画布显示，在原始图片上叠加暗色遮罩，突出显示裁切区域"""
        try:
            from PIL import Image, ImageDraw
            
            # 创建原始图片的副本
            overlay_img = self.original_image.copy()
            draw = ImageDraw.Draw(overlay_img)
            
            # 在整个图片上添加半透明黑色遮罩
            overlay = Image.new('RGBA', overlay_img.size, (0, 0, 0, 128))  # 半透明黑色
            overlay_img = Image.alpha_composite(overlay_img.convert('RGBA'), overlay)
            
            # 将裁切区域恢复为原始亮度
            x1, y1, x2, y2 = self.crop_bbox
            crop_region = self.original_image.crop(self.crop_bbox)
            overlay_img.paste(crop_region, (x1, y1))
            
            # 在裁切区域周围画一个边框以突出显示
            draw = ImageDraw.Draw(overlay_img)
            border_width = 3
            for i in range(border_width):
                draw.rectangle([x1-i, y1-i, x2+i, y2+i], outline='lime', width=1)
            
            # 转换为RGB并更新Tkinter图片对象
            self.overlay_image = overlay_img.convert('RGB')
            self.tk_image = ImageTk.PhotoImage(self.overlay_image)
            
            # 删除旧的图片
            self.canvas.delete(self.canvas_image_id)
            
            # 显示新的图片（保持原始尺寸和位置）
            self.canvas_image_id = self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
            
            # 更新窗口以确保正确显示
            self.top.update()
            
        except Exception as e:
            print(f"更新遮罩图片失败: {e}")

    def update_title_text(self):
        """更新标题文字"""
        # 删除旧的标题
        self.canvas.delete("title_bg")
        self.canvas.delete("title")
        
        # 重新创建标题
        title_text = f"模式: {self.config_name} - 第2步: 选择红框区域"
        
        # 先创建临时文字对象来测量实际尺寸
        temp_text = self.canvas.create_text(0, 0, text=title_text, font=("微软雅黑", 16, "bold"))
        text_bbox = self.canvas.bbox(temp_text)
        self.canvas.delete(temp_text)
        
        # 计算实际文字尺寸
        if text_bbox:
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
        else:
            text_width = len(title_text) * 10
            text_height = 20
        
        # 添加内边距
        padding = 8
        bg_x1 = 10
        bg_y1 = 10
        bg_x2 = bg_x1 + text_width + padding * 2
        bg_y2 = bg_y1 + text_height + padding * 2
        
        # 创建半透明背景矩形
        self.title_bg = self.canvas.create_rectangle(
            bg_x1, bg_y1, bg_x2, bg_y2,
            fill="black",
            stipple="gray50",
            outline="",
            tags="title_bg"
        )
        
        # 创建文字
        text_x = bg_x1 + padding
        text_y = bg_y1 + padding
        
        self.title_text = self.canvas.create_text(
            text_x, text_y, 
            text=title_text, 
            anchor="nw",
            font=("微软雅黑", 16, "bold"),
            fill="white",
            tags="title"
        )
        
        # 确保背景在文字下面
        self.canvas.tag_lower(self.title_bg, self.title_text)

    def get_selection(self):
        return self.selection
