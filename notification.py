"""
通知系统模块 - 处理Windows桌面通知和弹窗显示
"""

import threading
import time
import tkinter as tk
from tkinter import scrolledtext
from win10toast import ToastNotifier
from config import NOTIFICATION_CONFIGS

# 初始化Windows通知工具
toaster = ToastNotifier()

def show_notification(title, message, duration=10, threaded=True):
    """显示Windows桌面通知"""
    try:
        # 考虑中文字符和显示限制的智能检测
        max_toast_chars = NOTIFICATION_CONFIGS['max_toast_chars']
        max_toast_lines = NOTIFICATION_CONFIGS['max_toast_lines']
        max_line_length = NOTIFICATION_CONFIGS['max_line_length']
        
        # 检查是否需要使用弹窗
        needs_popup = False
        
        # 1. 检查总字符数
        if len(message) > max_toast_chars:
            needs_popup = True
        
        # 2. 检查行数和单行长度（考虑自动换行）
        lines = message.split('\n')
        if len(lines) > max_toast_lines:
            needs_popup = True
        
        # 3. 计算所有行换行后的总显示行数
        total_display_lines = 0
        for line in lines:
            if len(line) <= max_line_length:
                total_display_lines += 1
            else:
                # 计算这一行会被拆分成多少显示行
                display_lines_for_this_line = (len(line) + max_line_length - 1) // max_line_length
                total_display_lines += display_lines_for_this_line
        
        # 如果总显示行数超过限制，使用弹窗
        if total_display_lines > max_toast_lines:
            needs_popup = True
        
        # 直接显示通知，不使用队列
        if needs_popup:
            show_long_message_popup(title, message)
        else:
            success = False
            # 尝试多次显示通知，直到成功
            max_attempts = NOTIFICATION_CONFIGS['max_attempts']
            retry_delay = NOTIFICATION_CONFIGS['retry_delay']
            attempt = 0
            while not success and attempt < max_attempts:
                success = toaster.show_toast(title, message, duration=duration, threaded=threaded)
                if not success:
                    print(f"[Toast] 尝试显示通知失败，等待{retry_delay}秒后重试... (尝试 {attempt + 1}/{max_attempts})")
                    time.sleep(retry_delay)
                attempt += 1
                
            if success:
                # 打印成功的通知信息
                print(f"[Toast] 成功显示通知: {title} - {message}")
            else:
                print(f"[Toast] 无法显示通知: {title} - {message}")
        
    except Exception:
        print(f"通知显示失败:\n标题: {title}\n内容: {message}")

def show_long_message_popup(title, message):
    """显示长消息的弹窗"""
    def create_popup():
        # 创建弹窗
        popup = tk.Tk()
        popup.title(title)
        popup.resizable(True, True)  # 允许调整大小
        
        # 先设置初始大小但不显示位置
        popup.geometry("700x500")
        
        # 设置窗口图标（如果需要）
        try:
            popup.iconbitmap(default=None)
        except:
            pass
        
        # 创建文本框架
        frame = tk.Frame(popup)
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # 创建可滚动的文本区域
        text_area = scrolledtext.ScrolledText(
            frame, 
            wrap=tk.WORD, 
            width=80, 
            height=25,
            font=("微软雅黑", 11),
            bg="#ffffff",
            fg="#333333",
            selectbackground="#0078d4",
            selectforeground="white",
            relief="solid",
            borderwidth=1
        )
        text_area.pack(fill=tk.BOTH, expand=True)
        
        # 插入消息内容
        text_area.insert(tk.END, message)
        text_area.config(state=tk.DISABLED)  # 设为只读
        
        # 创建按钮框架
        button_frame = tk.Frame(popup)
        button_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        # 复制到剪贴板按钮
        def copy_to_clipboard():
            popup.clipboard_clear()
            popup.clipboard_append(message)
            copy_btn.config(text="✓ 已复制!", state=tk.DISABLED, bg="#28a745", fg="white")
            popup.after(2000, lambda: copy_btn.config(
                text="📋 复制到剪贴板", 
                state=tk.NORMAL, 
                bg="#f8f9fa", 
                fg="#333333"
            ))
        
        copy_btn = tk.Button(
            button_frame, 
            text="📋 复制到剪贴板", 
            command=copy_to_clipboard,
            font=("微软雅黑", 10),
            bg="#f8f9fa",
            fg="#333333",
            relief="solid",
            borderwidth=1,
            padx=15,
            pady=8
        )
        copy_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 关闭按钮
        close_btn = tk.Button(
            button_frame, 
            text="❌ 关闭", 
            command=popup.destroy,
            font=("微软雅黑", 10),
            bg="#dc3545",
            fg="white",
            relief="solid",
            borderwidth=1,
            padx=15,
            pady=8
        )
        close_btn.pack(side=tk.RIGHT)
        
        # 计算屏幕居中位置
        popup.update_idletasks()  # 确保窗口尺寸计算完毕
        screen_width = popup.winfo_screenwidth()
        screen_height = popup.winfo_screenheight()
        window_width = popup.winfo_reqwidth()
        window_height = popup.winfo_reqheight()
        
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # 设置窗口位置并显示
        popup.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 强制抢夺鼠标和键盘焦点 - 在窗口完全创建后执行
        popup.update()  # 确保窗口完全显示
        
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            
            # 定义函数参数类型以避免类型错误
            user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
            user32.GetWindowThreadProcessId.restype = wintypes.DWORD
            user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
            user32.AttachThreadInput.restype = wintypes.BOOL
            
            # 获取当前窗口句柄
            hwnd = popup.winfo_id()
            
            # 释放任何现有的鼠标捕获
            user32.ReleaseCapture()
            
            # 解除鼠标区域限制
            user32.ClipCursor(None)
            
            # 获取当前前台窗口的线程ID
            current_thread = kernel32.GetCurrentThreadId()
            foreground_hwnd = user32.GetForegroundWindow()
            if foreground_hwnd:
                process_id = wintypes.DWORD()
                foreground_thread = user32.GetWindowThreadProcessId(foreground_hwnd, ctypes.byref(process_id))
                # 附加到前台窗口的线程
                if foreground_thread:
                    user32.AttachThreadInput(current_thread, foreground_thread, True)
            
            # 设置窗口属性
            popup.attributes("-topmost", True)
            popup.lift()
            popup.focus_force()
            
            # 强制设置为前台窗口
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
            user32.SetActiveWindow(hwnd)
            user32.SetFocus(hwnd)
            user32.BringWindowToTop(hwnd)
            
            # 分离线程
            if foreground_hwnd and foreground_thread:
                user32.AttachThreadInput(current_thread, foreground_thread, False)
                
        except Exception as e:
            print(f"设置窗口焦点时出错: {e}")
        
        # 设置键盘事件
        popup.bind('<Escape>', lambda e: popup.destroy())
        
        # 多次尝试获得焦点，确保成功
        def ensure_focus():
            try:
                popup.attributes("-topmost", True)
                popup.lift()
                popup.focus_force()
            except:
                pass
        
        popup.after(50, ensure_focus)
        popup.after(100, ensure_focus)
        
        popup.mainloop()
    
    # 在新线程中创建弹窗，避免阻塞主程序
    popup_thread = threading.Thread(target=create_popup, daemon=True)
    popup_thread.start()
