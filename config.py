"""
配置文件 - 包含所有配置常量和快捷键设置
"""

import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# 快捷键配置
HOTKEY_CONFIGS = {
    # 快捷键 1: 回答问题
    'ctrl+shift+1': {
        'prompt': "请回答图中问题，请进行**简短**的思考，并给用户提供最终答案。将最终答案**使用一对英文方括号[]括起来**。",
        'model': "google/gemini-2.5-flash"
    },
    # 快捷键 2: 回答谐音问题
    'ctrl+shift+2': {
        'prompt': "请思考并回答图中关于谐音的问题。请进行**简短**的思考，并在你提供的回复的最后将最终答案**使用一对英文方括号[]括起来**。",
        'model': "google/gemini-2.5-flash"
    },
    # 快捷键 3: 识别选定区域的文字并翻译
    'ctrl+shift+3': {
        'prompt': "请提取并返回这张图片选定区域中的所有文字。并且这些文字翻译为**中文**。如果图中是漫画，则按照漫画的阅读顺序进行转录和翻译。在回复中，首先提供原文，将全部原文使用一对圆括号()括起来。然后提供中文翻译，将整个翻译结果**使用一对英文方括号[]括起来**。（即使有多段，也全放进一对英文方括号[]中）。",
        'model': "openai/gpt-4.1-mini"
    },
    # 快捷键 4: 描述图中内容
    'ctrl+shift+4': {
        'prompt': "请描述图中内容，使用精炼的语言简要介绍图中内容。如果图中是某个名字、名词、习语等，则解释这段字。如果图中着重强调了某一部分，则解释这一部分。**使用一对英文方括号[]将结果括起来**。",
        'model': "openai/gpt-4.1-mini"
    },
}

# API 配置
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# 通知配置
NOTIFICATION_CONFIGS = {
    'max_toast_chars': 100,  # 中文字符限制更严格
    'max_toast_lines': 4,    # 行数限制
    'max_line_length': 25,   # 单行字符限制
    'max_attempts': 20,      # 最大重试次数
    'retry_delay': 0.5       # 重试间隔（秒）
}
