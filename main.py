"""
主程序文件 - 处理快捷键、截图、区域选择和整体流程控制
"""

import sys
import threading
import keyboard
import tkinter as tk
from PIL import ImageTk

# 设置DPI感知，防止Windows拉伸窗口
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)  # 设置为系统DPI感知
except:
    pass

# 导入自定义模块
from config import HOTKEY_CONFIGS, OPENROUTER_API_KEY
from notification import show_notification
from region_selector import RegionSelector, task_queue, result_queue
from image_utils import take_screenshot, crop_and_encode_image
from image_processor import process_image

def process_hotkey(config):
    """处理单个快捷键触发的完整流程"""
    hotkey_name = next(key for key, val in HOTKEY_CONFIGS.items() if val == config)
    print(f"\n[*] 检测到快捷键 '{hotkey_name}'，开始处理...")
    
    # 1. 立刻截取全屏
    full_screenshot = take_screenshot()
    if not full_screenshot:
        return
        
    # 2. 在截图中选择区域
    bbox = None
    try:
        from region_selector import select_region_on_image
        bbox = select_region_on_image(full_screenshot)
    except Exception as e:
        print(f"[-] 区域选择失败: {e}")
        show_notification("错误", f"区域选择失败: {e}", threaded=True)
        return

    # 3. 检查选区是否有效
    if not bbox or (bbox[2] - bbox[0]) <= 1 or (bbox[3] - bbox[1]) <= 1:
        print("[-] 操作取消：选择的区域过小或无效。")
        return

    # 4. 裁剪并编码选定区域
    base64_image = crop_and_encode_image(full_screenshot, bbox)
    if not base64_image:
        return

    # 5. 调用核心处理器分析图片
    result = process_image(base64_image, config['prompt'], config['model'])

    # 6. 显示结果
    if result['success']:
        if result['extracted_answer']:
            # 如果提取到答案，显示提取的答案
            show_notification("AI分析结果 (选定区域)", result['extracted_answer'], duration=1, threaded=True)
            print("[+] 提取的答案: " + result['extracted_answer'])
            print("[+] 完整回复: " + result['raw_result'])
        else:
            # 如果没有提取到答案，显示完整结果
            show_notification("AI分析结果 (选定区域)", result['raw_result'], duration=1, threaded=True)
            print("[+] AI分析结果 (选定区域): " + result['raw_result'])
    else:
        print("[-] 未能获取分析结果。")
        if 'error' in result:
            show_notification("处理错误", f"图片处理失败: {result['error']}", threaded=True)

def handle_task_queue(root):
    """处理队列中的任务"""
    try:
        while True:
            task_type, data = task_queue.get(block=False)
            if task_type == 'select_region':
                selector = RegionSelector(root, data)
                # 先隐藏主窗口，显示选择界面
                root.withdraw()
                selector.top.mainloop()
                result_queue.put(selector.get_selection())
                # 重新显示主窗口
                root.deiconify()
                root.withdraw()
                break
    except:
        pass
    # 每100ms检查一次队列
    root.after(100, lambda: handle_task_queue(root))

def main():
    """主函数，负责注册快捷键并保持脚本运行"""
    # 检查Pillow是否支持Tkinter
    try:
        from PIL import ImageTk
    except ImportError:
        print("错误: Pillow 的 Tkinter 支持未安装。")
        print("请尝试重新安装Pillow: pip install --upgrade Pillow")
        input("按 Enter 键退出。")
        sys.exit(1)

    if not OPENROUTER_API_KEY:
        print("错误: 未找到 OPENROUTER_API_KEY 环境变量。")
        print("请确保在脚本同目录下创建了 .env 文件，并写入了您的API密钥。")
        input("按 Enter 键退出。")
        sys.exit(1)

    print("--- 截图分析助手已启动 (先截图后选择模式) ---")
    print("正在监听以下快捷键:")

    for hotkey, config in HOTKEY_CONFIGS.items():
        print(f"  - {hotkey}: 使用模型 '{config['model']}'")
        keyboard.add_hotkey(hotkey, lambda data=config: threading.Thread(target=process_hotkey, args=(data,)).start())

    print("\n脚本正在后台运行。您可以使用设定的快捷键进行截图和分析。")
    print("要停止脚本，请关闭此窗口或按 Ctrl+C。")

    # 创建主窗口用于处理GUI任务
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    # 启动队列处理
    handle_task_queue(root)

    # 使用Tkinter的主循环，而不是keyboard.wait()
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\n脚本被用户中断。正在退出...")
        root.quit()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n脚本被用户中断。正在退出...")
    finally:
        sys.exit(0)
