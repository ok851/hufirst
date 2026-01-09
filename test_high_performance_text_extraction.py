#!/usr/bin/env python3
"""
测试高性能文本提取功能
"""

import asyncio
import time
from playwright_automation import automation


async def test_performance_comparison():
    """比较优化前后的文本提取性能"""
    print("启动浏览器...")
    await automation.start_browser(headless=True)  # 使用headless模式进行性能测试
    
    try:
        # 导航到测试页面
        print("导航到测试页面...")
        await automation.navigate_to("https://example.com")
        
        # 测试选择器
        test_selector = "h1"
        
        print(f"\n测试选择器: {test_selector}")
        
        # 测试优化后的快速提取方法
        print("\n1. 测试快速文本提取方法 (extract_element_text_fast)...")
        start_time = time.time()
        fast_result = await automation.extract_element_text_fast(test_selector)
        fast_time = (time.time() - start_time) * 1000  # 转换为毫秒
        print(f"   结果: '{fast_result}'")
        print(f"   耗时: {fast_time:.2f}ms")
        
        # 测试带降级策略的提取方法
        print("\n2. 测试带降级策略的文本提取方法 (extract_element_text_with_fallback)...")
        start_time = time.time()
        fallback_result = await automation.extract_element_text_with_fallback(test_selector)
        fallback_time = (time.time() - start_time) * 1000  # 转换为毫秒
        print(f"   结果: '{fallback_result}'")
        print(f"   耗时: {fallback_time:.2f}ms")
        
        # 测试按优先级提取方法
        print("\n3. 测试按优先级文本提取方法 (extract_text_by_priority)...")
        start_time = time.time()
        priority_result = await automation.extract_text_by_priority(test_selector)
        priority_time = (time.time() - start_time) * 1000  # 转换为毫秒
        print(f"   结果: '{priority_result}'")
        print(f"   耗时: {priority_time:.2f}ms")
        
        # 测试原始优化方法
        print("\n4. 测试原始优化的文本提取方法 (extract_element_text)...")
        start_time = time.time()
        original_result = await automation.extract_element_text(test_selector)
        original_time = (time.time() - start_time) * 1000  # 转换为毫秒
        print(f"   结果: '{original_result}'")
        print(f"   耗时: {original_time:.2f}ms")
        
        # 测试页面文本提取
        print("\n5. 测试页面文本提取 (get_page_text)...")
        start_time = time.time()
        page_text = await automation.get_page_text()
        page_time = (time.time() - start_time) * 1000  # 转换为毫秒
        print(f"   页面文本长度: {len(page_text)} 字符")
        print(f"   耗时: {page_time:.2f}ms")
        
        # 测试批量提取
        print("\n6. 测试批量文本提取 (extract_multiple_elements_batch)...")
        selectors = ["h1", "p", "title"]
        start_time = time.time()
        batch_results = await automation.extract_multiple_elements_batch(selectors)
        batch_time = (time.time() - start_time) * 1000  # 转换为毫秒
        print(f"   批量提取结果: {batch_results}")
        print(f"   耗时: {batch_time:.2f}ms")
        
        print(f"\n性能对比总结:")
        print(f"快速提取:     {fast_time:.2f}ms")
        print(f"降级策略:     {fallback_time:.2f}ms") 
        print(f"优先级提取:   {priority_time:.2f}ms")
        print(f"原始优化方法: {original_time:.2f}ms")
        print(f"页面文本提取: {page_time:.2f}ms")
        print(f"批量提取:     {batch_time:.2f}ms")
        
        # 验证结果一致性
        results = [fast_result, fallback_result, priority_result, original_result]
        unique_results = set(result for result in results if result)
        print(f"\n结果一致性检查: {len(unique_results)} 种不同结果")
        if len(unique_results) <= 1:
            print("✓ 所有方法返回相同或相似结果")
        else:
            print("⚠ 不同方法返回不同结果，可能需要调整提取策略")
            print(f"  不同结果: {unique_results}")
            
    except Exception as e:
        print(f"测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n关闭浏览器...")
        await automation.close_browser()


async def test_accuracy_validation():
    """验证文本提取的准确性"""
    print("启动浏览器进行准确性测试...")
    await automation.start_browser(headless=True)
    
    try:
        # 测试不同的页面和选择器
        test_cases = [
            {"url": "https://example.com", "selector": "h1", "description": "Example Domain标题"},
            {"url": "https://example.com", "selector": "p", "description": "Example Domain段落"},
            {"url": "https://httpbin.org/html", "selector": "h1", "description": "Sample Page标题"},
        ]
        
        for i, test_case in enumerate(test_cases):
            print(f"\n准确性测试 {i+1}: {test_case['description']}")
            print(f"  URL: {test_case['url']}")
            print(f"  选择器: {test_case['selector']}")
            
            await automation.navigate_to(test_case['url'])
            
            # 使用多种方法提取文本
            methods = [
                ("快速提取", automation.extract_element_text_fast),
                ("降级策略", automation.extract_element_text_with_fallback),
                ("优先级提取", automation.extract_text_by_priority),
                ("原始优化", automation.extract_element_text),
            ]
            
            results = {}
            for method_name, method in methods:
                try:
                    result = await method(test_case['selector'])
                    results[method_name] = result
                    print(f"  {method_name}: '{result[:50]}{'...' if len(result) > 50 else ''}'")
                except Exception as e:
                    results[method_name] = f"错误: {e}"
                    print(f"  {method_name}: 错误 - {e}")
        
        print("\n✓ 准确性测试完成")
        
    except Exception as e:
        print(f"准确性测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("关闭浏览器...")
        await automation.close_browser()


if __name__ == "__main__":
    print("开始高性能文本提取功能测试\n")
    print("="*50)
    print("性能对比测试:")
    asyncio.run(test_performance_comparison())
    
    print("\n" + "="*50)
    print("准确性验证测试:")
    asyncio.run(test_accuracy_validation())
    
    print("\n" + "="*50)
    print("所有测试完成!")