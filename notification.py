"""
通知系统模块 - 处理Windows桌面通知和弹窗显示
"""

import threading
import time
import datetime
import tkinter as tk
from tkinter import scrolledtext
from config import NOTIFICATION_CONFIGS, POPUP_CONFIGS

# 尝试导入通知库
try:
    from windows_toasts import Toast, WindowsToaster, ToastDuration
    toaster = WindowsToaster('ScreenshotLLM')
    NOTIFICATION_BACKEND = 'windows_toasts'
    HAS_TOAST_DURATION = True
except ImportError:
    NOTIFICATION_BACKEND = 'popup_only'
    HAS_TOAST_DURATION = False

print(f"[通知] 使用通知后端: {NOTIFICATION_BACKEND}")

def show_notification(title, message):
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
        
        # 根据后端显示通知
        if needs_popup:
            show_long_message_popup(title, message)
        else:
            show_toast_notification(title, message)
        
    except Exception as e:
        print(f"通知显示失败:\n标题: {title}\n内容: {message}\n错误: {e}")

def show_toast_notification(title, message):
    """显示toast通知，根据可用的后端选择实现方式"""
    if NOTIFICATION_BACKEND == 'windows_toasts':
        try:
            # 使用 windows-toasts 显示通知
            toast = Toast()
            toast_title = f"{title}（点击展开）"
            toast.text_fields = [toast_title, message]
            
            # 设置点击回调
            def on_toast_click(_):
                print(f"[Toast] 用户点击了通知: {title}")
                show_long_message_popup(title, message)
            
            toast.on_activated = on_toast_click
            
            # 让toast在被dismiss后从通知中心移除
            toast.on_dismissed = lambda _: toaster.remove_toast(toast)
            
            # 设置持续时间为短时间显示
            toast.duration = ToastDuration.Short
            
            # 显示通知
            toaster.show_toast(toast)
            print(f"[WindowsToasts] 成功显示通知: {title} - {message}")
            return True
            
        except Exception as e:
            print(f"[WindowsToasts] 显示通知失败: {e}")
            return False
    else:
        # 如果没有可用的toast库，直接显示弹窗
        print("[通知] 没有可用的toast库，直接显示弹窗")
        show_long_message_popup(title, message)
        return True

def _create_popup_base(title):
    """创建弹窗基础结构，返回弹窗组件"""
    popup = tk.Tk()
    popup.title(title)
    popup.resizable(POPUP_CONFIGS['resizable'], POPUP_CONFIGS['resizable'])
    popup.geometry(f"{POPUP_CONFIGS['width']}x{POPUP_CONFIGS['height']}")
    
    # 设置窗口图标（可选）
    try:
        popup.iconbitmap(default=None)
    except:
        pass
    
    # 创建文本框架
    frame = tk.Frame(popup)
    frame.pack(fill=tk.BOTH, expand=True, 
               padx=POPUP_CONFIGS['window_padding'], 
               pady=POPUP_CONFIGS['window_padding'])
    
    # 先创建按钮框架（底部固定）
    button_frame = tk.Frame(frame)
    button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
    
    # 创建可滚动的文本区域（占据剩余空间）
    text_area = scrolledtext.ScrolledText(
        frame,
        wrap=tk.WORD,
        font=(POPUP_CONFIGS['font_family'], POPUP_CONFIGS['font_size']),
        bg="#ffffff",
        fg="#333333",
        selectbackground="#0078d4",
        selectforeground="white",
        relief="solid",
        borderwidth=1
    )
    text_area.pack(fill=tk.BOTH, expand=True)
    
    return popup, text_area, button_frame

def _create_popup_buttons(button_frame, popup, copy_content_func):
    """创建弹窗按钮"""
    # 复制到剪贴板按钮
    def copy_to_clipboard():
        popup.clipboard_clear()
        popup.clipboard_append(copy_content_func())
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
        font=(POPUP_CONFIGS['font_family'], POPUP_CONFIGS['button_font_size']),
        bg="#f8f9fa",
        fg="#333333",
        relief="solid",
        borderwidth=1,
        padx=POPUP_CONFIGS['button_padding_x'],
        pady=POPUP_CONFIGS['button_padding_y']
    )
    copy_btn.pack(side=tk.LEFT, padx=(0, 10))
    
    # 关闭按钮
    close_btn = tk.Button(
        button_frame,
        text="❌ 关闭",
        command=popup.destroy,
        font=(POPUP_CONFIGS['font_family'], POPUP_CONFIGS['button_font_size']),
        bg="#dc3545",
        fg="white",
        relief="solid",
        borderwidth=1,
        padx=POPUP_CONFIGS['button_padding_x'],
        pady=POPUP_CONFIGS['button_padding_y']
    )
    close_btn.pack(side=tk.RIGHT)

def _setup_popup_display(popup, title):
    """设置弹窗显示位置和焦点"""
    # 居中显示窗口
    popup.update_idletasks()
    screen_width = popup.winfo_screenwidth()
    screen_height = popup.winfo_screenheight()
    window_width = POPUP_CONFIGS['width']
    window_height = POPUP_CONFIGS['height']
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    popup.geometry(f"{window_width}x{window_height}+{x}+{y}")
    popup.update()
    
    # 简化的焦点设置逻辑
    try:
        popup.attributes("-topmost", True)
        popup.lift()
        popup.focus_force()
        print(f"[弹窗] 弹窗 '{title}' 已显示")
    except Exception as e:
        print(f"设置窗口焦点时出错: {e}")
    
    # 设置键盘事件
    popup.bind('<Escape>', lambda e: popup.destroy())
    
    # 简化焦点确保逻辑
    def ensure_focus():
        try:
            popup.attributes("-topmost", False)  # 取消置顶，避免干扰用户
            popup.lift()
        except:
            pass
    popup.after(100, ensure_focus)

def show_long_message_popup(title, message):
    """显示长消息的弹窗"""
    def create_popup():
        popup, text_area, button_frame = _create_popup_base(title)
        
        # 插入消息内容
        text_area.insert(tk.END, message)
        text_area.config(state=tk.DISABLED)  # 设为只读
        
        # 创建按钮
        _create_popup_buttons(button_frame, popup, lambda: message)
        
        # 设置显示位置和焦点
        _setup_popup_display(popup, title)
        
        popup.mainloop()
    
    # 在新线程中创建弹窗，避免阻塞主程序
    popup_thread = threading.Thread(target=create_popup, daemon=True)
    popup_thread.start()

def show_notification_stream(title, content_iter):
    """流式显示通知，content_iter为内容生成器/迭代器"""
    def create_stream_popup():
        popup, text_area, button_frame = _create_popup_base(title)
        
        # 初始显示提示
        text_area.insert(tk.END, "(AI正在生成...)")
        text_area.config(state=tk.DISABLED)

        # 创建按钮
        _create_popup_buttons(button_frame, popup, lambda: text_area.get("1.0", tk.END).strip())

        # 设置显示位置和焦点
        _setup_popup_display(popup, title)

        # 流式内容刷新逻辑
        def update_content():
            last_content = ""
            first_chunk = True
            for content in content_iter:
                if content is None:
                    break

                # 收到第一个有效数据块时，清空初始提示
                if first_chunk and content:
                    text_area.config(state=tk.NORMAL)
                    text_area.delete("1.0", tk.END)
                    text_area.config(state=tk.DISABLED)
                    first_chunk = False

                if content != last_content:
                    text_area.config(state=tk.NORMAL)
                    
                    # 智能更新逻辑：处理内容跳变（如提取答案时）
                    if content.startswith(last_content):
                        # 增量更新：只追加新内容，避免闪烁
                        delta = content[len(last_content):]
                        text_area.insert(tk.END, delta)
                    else:
                        # 内容跳变：完全重写文本框
                        text_area.delete("1.0", tk.END)
                        text_area.insert(tk.END, content)

                    text_area.see(tk.END)  # 自动滚动到末尾
                    text_area.config(state=tk.DISABLED)
                    last_content = content

        threading.Thread(target=update_content, daemon=True).start()
        popup.mainloop()
    popup_thread = threading.Thread(target=create_stream_popup, daemon=True)
    popup_thread.start()
