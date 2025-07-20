"""
显示器工具模块 - 处理多显示器检测、截图和选择功能
"""

import mss
from PIL import Image
import tkinter as tk
from tkinter import messagebox
from config import MONITOR_CONFIGS
import threading

class MonitorManager:
    """显示器管理器，处理多显示器相关功能"""
    
    def __init__(self):
        # 使用线程本地存储来避免线程安全问题
        self._local = threading.local()
        self.current_monitor = 0  # 默认使用全部显示器
        self._initialized = False  # 标记是否已初始化过
        self._init_monitors()
        
        if MONITOR_CONFIGS.get('show_monitor_info', True) and not self._initialized:
            self.print_monitor_info()
            self._initialized = True
    
    def _get_sct(self):
        """获取线程本地的MSS实例"""
        if not hasattr(self._local, 'sct'):
            self._local.sct = mss.mss()
        return self._local.sct
    
    def _init_monitors(self):
        """初始化显示器信息"""
        try:
            sct = self._get_sct()
            self.monitors = sct.monitors
        except Exception as e:
            print(f"[-] 初始化显示器失败: {e}")
            # 回退到单显示器模式
            self.monitors = [
                {'left': 0, 'top': 0, 'width': 1920, 'height': 1080},  # 虚拟显示器
                {'left': 0, 'top': 0, 'width': 1920, 'height': 1080}   # 主显示器
            ]
    
    def print_monitor_info(self):
        """打印显示器信息"""
        print(f"\n=== 显示器信息 ===")
        print(f"检测到 {len(self.monitors) - 1} 个显示器:")
        
        for i, monitor in enumerate(self.monitors):
            if i == 0:
                # 第0个是所有显示器的虚拟区域
                print(f"  全部显示器: {monitor['width']}x{monitor['height']} (虚拟区域)")
            else:
                print(f"  显示器 {i}: {monitor['width']}x{monitor['height']} "
                      f"位置({monitor['left']}, {monitor['top']})")
        
        current_desc = "全部显示器" if self.current_monitor == 0 else f"显示器 {self.current_monitor}"
        print(f"当前使用: {current_desc}")
        print("===================\n")
    
    def take_all_monitors_screenshot(self):
        """截取所有显示器，返回包含各显示器位置信息的完整虚拟桌面"""
        try:
            # 截取包含所有显示器的虚拟桌面
            virtual_monitor = self.monitors[0]  # 索引0是虚拟桌面
            sct = self._get_sct()
            screenshot = sct.grab(virtual_monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            
            print(f"[+] 成功截取包含所有显示器的虚拟桌面 ({img.size[0]}x{img.size[1]})")
            
            # 返回图像和显示器布局信息
            monitor_info = []
            for i in range(1, len(self.monitors)):
                monitor = self.monitors[i]
                monitor_info.append({
                    'index': i,
                    'left': monitor['left'],
                    'top': monitor['top'],
                    'width': monitor['width'],
                    'height': monitor['height']
                })
            
            return {
                'image': img,
                'virtual_bounds': virtual_monitor,
                'monitors': monitor_info
            }
            
        except Exception as e:
            print(f"[-] 虚拟桌面截图失败: {e}")
            # 如果MSS失败，尝试使用PIL的ImageGrab作为回退
            try:
                from PIL import ImageGrab
                img = ImageGrab.grab()
                print(f"[+] 使用PIL回退方式成功截取虚拟桌面 ({img.size[0]}x{img.size[1]})")
                
                # 简化的显示器信息（单显示器模式）
                return {
                    'image': img,
                    'virtual_bounds': {'left': 0, 'top': 0, 'width': img.size[0], 'height': img.size[1]},
                    'monitors': [{'index': 1, 'left': 0, 'top': 0, 'width': img.size[0], 'height': img.size[1]}]
                }
            except Exception as e2:
                print(f"[-] PIL回退截图也失败: {e2}")
                return None
    
# 全局显示器管理器实例 - 使用懒加载避免初始化问题
_monitor_manager = None
_manager_lock = threading.Lock()

def get_monitor_manager():
    """获取显示器管理器实例（懒加载，线程安全）"""
    global _monitor_manager
    if _monitor_manager is None:
        with _manager_lock:
            if _monitor_manager is None:
                _monitor_manager = MonitorManager()
    return _monitor_manager

def take_screenshot_multi_monitor():
    """支持多显示器的截图函数 - 自动截取包含所有显示器的虚拟桌面"""
    return get_monitor_manager().take_all_monitors_screenshot()
