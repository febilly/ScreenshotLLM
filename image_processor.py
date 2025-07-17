"""
核心处理器模块 - 接受图片和prompt，返回AI分析结果
这是一个纯粹的处理器，不包含UI交互，专注于图片处理
"""

from api_client import analyze_image_with_openrouter
from image_utils import extract_answer_from_brackets

def process_image(base64_image, prompt, model):
    """
    处理已编码的图片
    
    参数：
    - base64_image: base64编码的图片数据
    - prompt: 提示词
    - model: 使用的模型
    
    返回：
    - dict: 包含原始结果和提取答案的字典
      {
          'success': bool,           # 是否成功
          'raw_result': str,         # AI的完整回复
          'extracted_answer': str,   # 提取的答案（如果有）
          'final_answer': str        # 最终显示的答案
      }
    """
    try:
        print("[*] 正在调用AI模型进行分析，请稍候...")
        
        # 调用API分析
        analysis_result = analyze_image_with_openrouter(base64_image, prompt, model)
        
        if not analysis_result:
            return {
                'success': False,
                'raw_result': None,
                'extracted_answer': None,
                'final_answer': None
            }
        
        print("[+] 分析完成!")
        
        # 尝试提取方括号内的答案
        extracted_answer = extract_answer_from_brackets(analysis_result)
        
        # 确定最终显示的答案
        final_answer = extracted_answer if extracted_answer else analysis_result
        
        return {
            'success': True,
            'raw_result': analysis_result,
            'extracted_answer': extracted_answer,
            'final_answer': final_answer
        }
        
    except Exception as e:
        print(f"[-] 图片处理失败: {e}")
        return {
            'success': False,
            'raw_result': None,
            'extracted_answer': None,
            'final_answer': None,
            'error': str(e)
        }
