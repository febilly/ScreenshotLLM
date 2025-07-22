"""
配置文件 - 包含所有配置常量和快捷键设置
"""

import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# 翻译的目标语言
TARGET_LANGUAGE = "中文"

# 快捷键配置
HOTKEY_CONFIGS = {
    # 快捷键 1: 回答问题
    'ctrl+shift+1': {
        'name': "智能问答",
        'prompt': "请回答图中问题，请进行**简短**的思考，并给用户提供最终答案。将最终答案使用一对**英文方括号**，即[]符号，将答案括起来。例如[答案]。用与图中问题相同的语言给出最终答案。",
        'model': "google/gemini-2.5-flash",
        'draw_box': False,
        'stream': False
    },
    # 快捷键 2: 识别选定区域的文字并翻译
    'ctrl+shift+2': {
        'name': "文字识别与翻译",
        'prompt': f"请提取并返回这张图片选定区域中的所有文字。并且这些文字翻译为**{TARGET_LANGUAGE}**。如果图中文本是对另一种语言的解释，则不要翻译目标语言的文本。如果图中是漫画，则按照漫画的阅读顺序进行转录和翻译。在回复中，首先提供原文，将全部原文使用一对圆括号()括起来。然后提供{TARGET_LANGUAGE}翻译，将整个翻译结果使用一对**英文方括号[]**，即[]符号，将答案括起来。例如[答案]。（即使有多段，也全放进一对英文方括号[]中）。",
        'model': "openai/gpt-4.1-mini",
        'draw_box': False,
        'stream': True
    },
    # 快捷键 3: 描述图中内容
    'ctrl+shift+3': {
        'name': "图像描述",
        'prompt': f"请描述图中内容，使用精炼的语言简要介绍图中内容。如果图中是某个名字、名词、习语等，则解释这段字。如果图中着重强调了某一部分，则解释这一部分。使用{TARGET_LANGUAGE}回答。使用一对**英文方括号[]**，即[]符号，将答案括起来。例如[答案]。",
        'model': "openai/gpt-4.1-mini",
        'draw_box': False,
        'stream': True
    },
    # 快捷键 4: 解释框选区域
    'ctrl+shift+4': {
        'name': "解释框选区域",
        'prompt': f"请简要解释图中红色框起来的部分，及它在整个上下文中发挥的作用。使用{TARGET_LANGUAGE}回答。使用一对**英文方括号[]**，即[]符号，将答案括起来。例如[答案]。",
        'model': "openai/gpt-4.1-mini",
        'draw_box': True,
        'stream': True
    },
}

# API 配置
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# 显示器配置
MONITOR_CONFIGS = {
    'auto_detect': True,        # 自动检测所有显示器
    'capture_all': True,        # 自动截取包含所有显示器的虚拟桌面
    'show_monitor_info': False,  # 启动时显示显示器信息
}

# 通知配置
NOTIFICATION_CONFIGS = {
    'max_toast_chars': 50,  # 中文字符限制更严格
    'max_toast_lines': 4,    # 行数限制
    'max_line_length': 25,   # 单行字符限制
    'max_attempts': 20,      # 最大重试次数
    'retry_delay': 0.5       # 重试间隔（秒）
}

# 弹窗窗口配置
POPUP_CONFIGS = {
    'width': 600,                    # 弹窗宽度
    'height': 500,                   # 弹窗高度
    'font_family': "微软雅黑",        # 字体系列
    'font_size': 11,                 # 字体大小
    'button_font_size': 10,          # 按钮字体大小
    'window_padding': 15,            # 窗口内边距
    'button_padding_x': 15,          # 按钮水平内边距
    'button_padding_y': 8,           # 按钮垂直内边距
    'resizable': True,               # 是否允许调整窗口大小
}
