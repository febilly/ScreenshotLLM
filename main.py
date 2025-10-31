"""
主程序文件 - 处理快捷键、截图、区域选择和整体流程控制
"""

import sys
import threading
from pynput import keyboard
import tkinter as tk
from PIL import ImageTk

# 设置DPI感知，防止Windows拉伸窗口
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)  # 设置为系统DPI感知
except:
    pass

# 导入自定义模块
from config import HOTKEY_CONFIGS
from notification import show_notification, show_notification_stream
from region_selector import RegionSelector, task_queue, result_queue
from image_utils import take_screenshot, crop_and_encode_image
from image_processor import process_image_sync, process_image_stream
from monitor_utils import take_screenshot_multi_monitor

def print_analysis_result(result):
    """打印分析结果到命令行"""
    if result and result.get('success'):
        print("[+] 分析完成!")
        if result['extracted_answer']:
            print("[+] 提取的答案: " + result['extracted_answer'])
            print("[+] 完整回复: " + result['raw_result'])
        else:
            print("[+] AI分析结果: " + result['raw_result'])
    else:
        print("[-] 未能获取分析结果。")
        if result and 'error' in result:
            print(f"[-] 错误: {result['error']}")

def process_hotkey(config):
    """处理单个快捷键触发的完整流程"""
    hotkey_name = next(key for key, val in HOTKEY_CONFIGS.items() if val == config)
    config_name = config.get('name', '未知模式')
    draw_box = config.get('draw_box', False)
    print(f"\n[*] 检测到快捷键 '{hotkey_name}'，开始处理... 模式: {config_name}")
    if draw_box:
        print(f"[*] 将在选定区域画红框标识")
    
    # 1. 立刻截取全屏
    full_screenshot = take_screenshot()
    if not full_screenshot:
        return
        
    # 2. 在截图中选择区域
    bbox = None
    try:
        from region_selector import select_region_on_image
        bbox = select_region_on_image(full_screenshot, config_name, draw_box)
    except Exception as e:
        print(f"[-] 区域选择失败: {e}")
        show_notification("错误", f"区域选择失败: {e}")
        return

    # 3. 检查选区是否有效
    if draw_box:
        # 画红框模式，检查返回的数据结构
        if not bbox or not isinstance(bbox, dict) or 'crop_bbox' not in bbox:
            print("[-] 操作取消：选择的区域无效。")
            return
        crop_bbox = bbox['crop_bbox']
        # 支持新的多红框格式和旧的单红框格式
        red_box_bboxes = bbox.get('red_box_bboxes')  # 新格式：多个红框
        if not red_box_bboxes:
            # 兼容旧格式：单个红框
            red_box_bbox = bbox.get('red_box_bbox')
            red_box_bboxes = [red_box_bbox] if red_box_bbox else None
        
        if (crop_bbox[2] - crop_bbox[0]) <= 1 or (crop_bbox[3] - crop_bbox[1]) <= 1:
            print("[-] 操作取消：选择的裁切区域过小或无效。")
            return
    else:
        # 普通模式
        if not bbox or (bbox[2] - bbox[0]) <= 1 or (bbox[3] - bbox[1]) <= 1:
            print("[-] 操作取消：选择的区域过小或无效。")
            return
        crop_bbox = bbox
        red_box_bboxes = None

    # 4. 裁剪并编码选定区域
    base64_image = crop_and_encode_image(full_screenshot, crop_bbox, red_box_bboxes)
    if not base64_image:
        return

    # 5. 调用核心处理器分析图片
    if config.get('stream', False):
        # 流式模式
        import threading
        import queue
        
        # 用于存储最终结果和同步完成状态
        final_result = None
        completion_event = threading.Event()
        
        def content_iter():
            nonlocal final_result
            for result in process_image_stream(base64_image, config['prompt'], config['model'], config['provider']):
                if not result or not result.get('success'):
                    final_result = result  # 保存失败结果
                    yield "(AI分析失败)"
                    break
                # 优先显示提取答案，否则显示全部
                content = result['extracted_answer'] if result['extracted_answer'] else result['raw_result']
                final_result = result  # 保存最终结果
                yield content
            # 流式处理完成，设置事件
            completion_event.set()
        
        # 启动流式弹窗（异步）
        show_notification_stream("AI分析结果", content_iter())
        
        # 等待流式处理完成
        completion_event.wait()
        
        # 流式处理完成后，输出命令行结果
        print_analysis_result(final_result)
    else:
        # 非流式
        result = process_image_sync(base64_image, config['prompt'], config['model'], config['provider'])
        if result['success']:
            if result['extracted_answer']:
                show_notification("AI分析结果", result['extracted_answer'])
            else:
                show_notification("AI分析结果", result['raw_result'])
        else:
            if 'error' in result:
                show_notification("处理错误", f"图片处理失败: {result['error']}")
        
        # 输出命令行结果
        print_analysis_result(result)

def handle_task_queue(root):
    """处理队列中的任务"""
    try:
        while True:
            task_data = task_queue.get(block=False)
            if task_data[0] == 'select_region':
                task_type, screenshot_image, config_name, need_red_box = task_data
                
                # 确保主窗口处于正确状态
                root.withdraw()
                root.update()  # 强制更新窗口状态
                
                selector = RegionSelector(root, screenshot_image, config_name, need_red_box)
                
                # 强制获得焦点的额外措施
                selector.top.update_idletasks()
                selector.top.after(1, lambda: _ensure_focus(selector.top))
                
                selector.top.mainloop()
                result_queue.put(selector.get_selection())
                
                root.after(50, lambda: handle_task_queue(root))
                
                return  # 等待延迟执行
            else:
                continue
    except:
        pass
    # 每50ms检查一次队列（提高响应速度）
    root.after(50, lambda: handle_task_queue(root))

def _ensure_focus(window):
    """确保窗口获得焦点的辅助函数"""
    try:
        window.lift()
        window.focus_force()
        window.grab_set()  # 获取全局焦点
        
        # Windows特定的焦点设置
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        
        # 获取窗口句柄
        hwnd = window.winfo_id()
        
        # 强制设置为前台窗口
        user32.SetForegroundWindow(hwnd)
        user32.SetActiveWindow(hwnd)
        user32.SetFocus(hwnd)
        
        # 确保窗口可见
        user32.ShowWindow(hwnd, 1)  # SW_SHOWNORMAL
        user32.BringWindowToTop(hwnd)
        
    except Exception as e:
        print(f"设置窗口焦点时出错: {e}")
        pass

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

    print("--- 截图分析助手已启动---")
    print("正在监听以下快捷键:")

    # 构建快捷键字典
    hotkey_map = {
        hotkey: (lambda data=config: threading.Thread(target=process_hotkey, args=(data,)).start())
        for hotkey, config in HOTKEY_CONFIGS.items()
    }

    # 注册分析功能快捷键
    for hotkey, config in HOTKEY_CONFIGS.items():
        config_name = config.get('name', '未知模式')
        print(f"  - {hotkey}: {config_name} (模型: {config['model']})")

    # 启动快捷键监听器
    listener = keyboard.GlobalHotKeys(hotkey_map)
    listener.start()

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
