"""
核心处理器模块 - 接受图片和prompt，返回AI分析结果
这是一个纯粹的处理器，不包含UI交互，专注于图片处理
"""

from api_client import analyze_image_with_openrouter_sync, analyze_image_with_openrouter_stream
from image_utils import extract_answer_from_markers

def _create_result_dict(success, raw_result=None, extracted_answer=None, error=None):
    """创建标准化的结果字典"""
    final_answer = extracted_answer if extracted_answer else raw_result
    return {
        'success': success,
        'raw_result': raw_result,
        'extracted_answer': extracted_answer,
        'final_answer': final_answer,
        'error': error
    }

def _process_analysis_result(analysis_result):
    """处理分析结果，提取答案并返回标准化字典"""
    if not analysis_result:
        return _create_result_dict(success=False)
    
    extracted_answer = extract_answer_from_markers(analysis_result)
    return _create_result_dict(
        success=True,
        raw_result=analysis_result,
        extracted_answer=extracted_answer
    )

def process_image_sync(base64_image, prompt, model):
    """
    非流式处理已编码的图片
    
    参数：
    - base64_image: base64编码的图片数据
    - prompt: 提示词
    - model: 使用的模型
    
    返回：
    - dict: 包含原始结果和提取答案的字典
    """
    try:
        print("[*] 正在调用AI模型进行分析，请稍候...")
        
        # 非流式调用API
        analysis_result = analyze_image_with_openrouter_sync(base64_image, prompt, model)
        result = _process_analysis_result(analysis_result)
        
        if result['success']:
            print("[+] 分析完成!")
        
        return result
        
    except Exception as e:
        print(f"[-] 图片处理失败: {e}")
        return _create_result_dict(success=False, error=str(e))

def process_image_stream(base64_image, prompt, model):
    """
    流式处理已编码的图片
    
    参数：
    - base64_image: base64编码的图片数据
    - prompt: 提示词
    - model: 使用的模型
    
    Yields:
    - dict: 包含递增内容的字典
    """
    try:
        print("[*] 正在调用AI模型进行分析，请稍候...")
        
        for partial in analyze_image_with_openrouter_stream(base64_image, prompt, model):
            if partial is None:
                yield _create_result_dict(success=False)
                return
            
            result = _process_analysis_result(partial)
            yield result
    
    except Exception as e:
        print(f"[-] 图片处理失败: {e}")
        yield _create_result_dict(success=False, error=str(e))
