"""
区域选择模块 - 处理用户在截图上选择矩形区域的功能，支持多显示器
"""

import queue
import time
import tkinter as tk
from tkinter import Toplevel, Canvas
from PIL import ImageTk
import keyboard  # 用于检测键盘状态

# 全局队列用于线程间通信
task_queue = queue.Queue()
result_queue = queue.Queue()

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
        self.red_box_bboxes = []  # 存储多个红框区域
        
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
        
        # 立即尝试获取焦点
        self.top.focus_force()
        self.top.lift()
        
        # Windows 特定的强制焦点获取
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            
            # 获取当前前台窗口，稍后恢复
            self.original_foreground_window = user32.GetForegroundWindow()
            
            # 定义函数参数类型
            user32.SetForegroundWindow.argtypes = [wintypes.HWND]
            user32.SetForegroundWindow.restype = wintypes.BOOL
            user32.SetActiveWindow.argtypes = [wintypes.HWND]
            user32.SetActiveWindow.restype = wintypes.HWND
            user32.SetFocus.argtypes = [wintypes.HWND]
            user32.SetFocus.restype = wintypes.HWND
            user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
            user32.ShowWindow.restype = wintypes.BOOL
            user32.BringWindowToTop.argtypes = [wintypes.HWND]
            user32.BringWindowToTop.restype = wintypes.BOOL
            
            # 获取当前线程和前台窗口线程ID
            kernel32 = ctypes.windll.kernel32
            current_thread_id = kernel32.GetCurrentThreadId()
            foreground_thread_id = user32.GetWindowThreadProcessId(self.original_foreground_window, None)
            
            # 如果不是同一个线程，需要连接输入队列
            if current_thread_id != foreground_thread_id:
                user32.AttachThreadInput(current_thread_id, foreground_thread_id, True)
            
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
        
        # 创建标题文字
        self._create_title_text()

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
        self.top.bind("<KeyPress>", self.on_key_press)
        self.top.focus_set()  # 确保窗口可以接收键盘事件
        self.selection = None

    def _create_title_text(self, custom_text=None):
        """创建或更新标题文字"""
        # 删除旧的标题
        self.canvas.delete("title_bg")
        self.canvas.delete("title")
        
        # 生成标题文本
        if custom_text:
            title_text = f"模式: {self.config_name} - {custom_text}"
        elif self.need_red_box:
            if self.selection_stage == 1:
                title_text = f"模式: {self.config_name} - 第1步: 选择裁切区域"
            else:
                title_text = f"模式: {self.config_name} - 第2步: 选择红框区域 (按空格/回车完成)"
        else:
            title_text = f"模式: {self.config_name}"
        
        # 先创建临时文字对象来测量实际尺寸
        temp_text = self.canvas.create_text(0, 0, text=title_text, font=("微软雅黑", 16, "bold"))
        text_bbox = self.canvas.bbox(temp_text)
        self.canvas.delete(temp_text)
        
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
            stipple="gray50",
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

    def _clamp_coords_to_bounds(self, x, y, width, height):
        """将坐标约束在指定范围内"""
        return (
            max(0, min(width, x)),
            max(0, min(height, y))
        )
    
    def _calculate_final_coords(self, start_x, start_y, end_x, end_y, bounds_width, bounds_height):
        """计算最终的选择区域坐标"""
        start_x, start_y = self._clamp_coords_to_bounds(start_x, start_y, bounds_width, bounds_height)
        end_x, end_y = self._clamp_coords_to_bounds(end_x, end_y, bounds_width, bounds_height)
        
        x1 = int(min(start_x, end_x))
        y1 = int(min(start_y, end_y))
        x2 = int(max(start_x, end_x))
        y2 = int(max(start_y, end_y))
        
        # 再次确保坐标在边界内
        x1, y1 = self._clamp_coords_to_bounds(x1, y1, bounds_width, bounds_height)
        x2, y2 = self._clamp_coords_to_bounds(x2, y2, bounds_width, bounds_height)
        
        return x1, y1, x2, y2

    def _reset_selection_state(self):
        """重置选择状态"""
        self.is_selecting = False
        self.start_x = None
        self.start_y = None
        
        # 清除选择框
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
            self.selection_rect = None

    def _complete_selection(self, selection_data):
        """完成选择并关闭窗口"""
        self.selection = selection_data
        self.top.destroy()
        self.master.quit()

    def on_escape(self, event):
        self._complete_selection(None)

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

    def is_point_in_image(self, canvas_x, canvas_y):
        """检查画布坐标是否在图像范围内"""
        return 0 <= canvas_x < self.image.width and 0 <= canvas_y < self.image.height

    def _get_canvas_coords(self, event):
        """获取画布坐标"""
        return self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

    def _is_in_crop_area(self, image_x, image_y):
        """检查坐标是否在裁切区域内"""
        if not self.crop_bbox:
            return False
        crop_x1, crop_y1, crop_x2, crop_y2 = self.crop_bbox
        return crop_x1 <= image_x <= crop_x2 and crop_y1 <= image_y <= crop_y2

    def on_mouse_motion(self, event):
        """鼠标移动时显示十字瞄准线"""
        if not self.is_selecting:
            canvas_x, canvas_y = self._get_canvas_coords(event)
            
            # 检查是否在有效区域内
            if self.selection_stage == 1:
                # 第一步：整个图像区域都可以显示十字线
                if self.is_point_in_image(canvas_x, canvas_y):
                    self.throttled_update(self.update_crosshair, canvas_x, canvas_y)
                else:
                    self.clear_crosshair()
            else:
                # 第二步：只在裁切区域内显示十字线
                if self._is_in_crop_area(canvas_x, canvas_y):
                    self.throttled_update(self.update_crosshair, canvas_x, canvas_y)
                else:
                    self.clear_crosshair()

    def on_mouse_down(self, event):
        canvas_x, canvas_y = self._get_canvas_coords(event)
        
        # 检查点击是否在有效区域内
        if self.selection_stage == 1:
            # 第一步：可以在整个图像区域内选择
            if self.is_point_in_image(canvas_x, canvas_y):
                self.start_x = canvas_x
                self.start_y = canvas_y
                self.is_selecting = True
                
                # 清除十字线并显示选择框
                self.clear_crosshair()
                self.update_selection_rect(canvas_x, canvas_y, canvas_x, canvas_y)
        else:
            # 第二步：只能在裁切区域内选择
            if self._is_in_crop_area(canvas_x, canvas_y):
                crop_x1, crop_y1, _, _ = self.crop_bbox
                # 坐标相对于裁切区域
                self.start_x = canvas_x - crop_x1
                self.start_y = canvas_y - crop_y1
                self.is_selecting = True
                
                # 清除十字线并显示选择框
                self.clear_crosshair()
                self.update_selection_rect(canvas_x, canvas_y, canvas_x, canvas_y)

    def on_mouse_move(self, event):
        if self.is_selecting and self.start_x is not None and self.start_y is not None:
            canvas_x, canvas_y = self._get_canvas_coords(event)
            
            # 将起始点转换为画布坐标
            if self.selection_stage == 1:
                start_canvas_x, start_canvas_y = self.start_x, self.start_y
            else:
                # 第二步时，起始点是相对于裁切区域的
                crop_x1, crop_y1, _, _ = self.crop_bbox
                start_canvas_x = crop_x1 + self.start_x
                start_canvas_y = crop_y1 + self.start_y
            
            # 使用节流更新来提高性能
            self.throttled_update(self.update_selection_rect, start_canvas_x, start_canvas_y, canvas_x, canvas_y)

    def on_mouse_up(self, event):
        if self.is_selecting and self.start_x is not None and self.start_y is not None:
            canvas_x, canvas_y = self._get_canvas_coords(event)
            
            if self.selection_stage == 1:
                # 第一步：计算最终选择区域坐标
                x1, y1, x2, y2 = self._calculate_final_coords(
                    self.start_x, self.start_y, canvas_x, canvas_y,
                    self.image.width, self.image.height
                )
                
            else:
                # 第二步：相对坐标已经在start_x, start_y中
                crop_x1, crop_y1, crop_x2, crop_y2 = self.crop_bbox
                end_rel_x = canvas_x - crop_x1
                end_rel_y = canvas_y - crop_y1
                
                # 计算裁切区域的尺寸
                crop_width = crop_x2 - crop_x1
                crop_height = crop_y2 - crop_y1
                
                # 计算最终选择区域坐标
                x1, y1, x2, y2 = self._calculate_final_coords(
                    self.start_x, self.start_y, end_rel_x, end_rel_y,
                    crop_width, crop_height
                )
            
            # 处理两步选择逻辑
            if self.selection_stage == 1 and self.need_red_box:
                # 第一步：选择裁切区域
                self.crop_bbox = (x1, y1, x2, y2)
                self.selection_stage = 2
                
                # 更新显示的图片为裁切后的图片
                self.update_to_cropped_image()
                
                # 更新标题
                self._create_title_text()
                
                # 重置鼠标状态
                self._reset_selection_state()
                
                # 绘制已选择的红框
                self.draw_existing_red_boxes_on_canvas()
                
            else:
                # 最后一步：完成选择
                if self.need_red_box and self.selection_stage == 2:
                    # 添加当前红框到列表中
                    current_red_box = (x1, y1, x2, y2)
                    self.red_box_bboxes.append(current_red_box)
                    
                    # 检查是否按住了Shift键
                    shift_pressed = keyboard.is_pressed('shift')
                    
                    if shift_pressed:
                        # 继续选择下一个红框
                        self._reset_selection_state()
                        
                        # 更新标题显示当前红框数量
                        self._create_title_text(f"第2步: 选择红框区域 (已选择{len(self.red_box_bboxes)}个，按住Shift继续，或按空格/回车完成)")
                        
                        # 在画布上绘制已选择的红框
                        self.draw_existing_red_boxes_on_canvas()
                        
                        # 不退出，继续等待下一个红框选择
                        return
                    else:
                        # 完成所有红框选择
                        selection_data = {
                            'crop_bbox': self.crop_bbox,
                            'red_box_bboxes': self.red_box_bboxes
                        }
                        self._complete_selection(selection_data)
                        return
                else:
                    # 普通模式，只返回裁切区域
                    self._complete_selection((x1, y1, x2, y2))
                    return

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

    def get_selection(self):
        return self.selection

    def _draw_thick_rectangle(self, x1, y1, x2, y2, outline_color, tag):
        """绘制粗线矩形"""
        for width_offset in range(3):  # 画粗线
            self.canvas.create_rectangle(
                x1 + width_offset, y1 + width_offset,
                x2 - width_offset, y2 - width_offset,
                outline=outline_color, width=1, tags=tag
            )

    def draw_existing_red_boxes_on_canvas(self):
        """在画布上绘制已经选择的红框"""
        if not self.red_box_bboxes or not self.crop_bbox:
            return
            
        crop_x1, crop_y1, _, _ = self.crop_bbox
        
        # 删除之前绘制的红框
        self.canvas.delete("existing_red_box")
        
        # 绘制每个已选择的红框
        for i, red_box in enumerate(self.red_box_bboxes):
            # 转换相对坐标为绝对画布坐标
            abs_x1 = crop_x1 + red_box[0]
            abs_y1 = crop_y1 + red_box[1]
            abs_x2 = crop_x1 + red_box[2] 
            abs_y2 = crop_y1 + red_box[3]
            
            # 在画布上绘制红框
            self._draw_thick_rectangle(abs_x1, abs_y1, abs_x2, abs_y2, 'red', "existing_red_box")

    def on_key_press(self, event):
        """处理键盘按键事件"""
        # 只在红框选择阶段且没有正在画框时才处理空格和回车键
        if (self.need_red_box and self.selection_stage == 2 and 
            not self.is_selecting and len(self.red_box_bboxes) > 0):
            
            if event.keysym in ['space', 'Return']:
                # 空格键或回车键：完成所有红框选择
                selection_data = {
                    'crop_bbox': self.crop_bbox,
                    'red_box_bboxes': self.red_box_bboxes
                }
                self._complete_selection(selection_data)
