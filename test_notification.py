#!/usr/bin/env python3
"""
测试通知功能
"""

from notification import show_notification

# 设置DPI感知，防止Windows拉伸窗口
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)  # 设置为系统DPI感知
except:
    pass

def test_short_notification():
    """测试短通知（应该显示可点击的toast）"""
    title = "测试短通知"
    message = "这是一个短消息，点击查看详情！"
    show_notification(title, message)

def test_long_notification():
    """测试长通知（应该直接显示弹窗）"""
    title = "测试长通知"
    message = """这是一个很长的消息，应该直接显示弹窗。
    
包含多行内容：
1. 第一行内容
2. 第二行内容
3. 第三行内容
4. 第四行内容
5. 第五行内容

这个消息足够长，应该会触发弹窗而不是toast通知。
用户可以在弹窗中看到完整的内容，并且可以复制到剪贴板。"""
    show_notification(title, message)

if __name__ == "__main__":
    print("测试通知系统...")
    print("1. 测试短通知（可点击）")
    test_short_notification()
    
    import time
    time.sleep(3)
    
    print("2. 测试长通知（直接弹窗）")
    test_long_notification()
    
    print("测试完成！弹窗应该已经显示，请手动关闭它。")
    # 保持脚本运行，让弹窗有时间显示
    input("按 Enter 键退出测试...")
