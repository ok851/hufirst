#!/usr/bin/env python3
"""
测试文本提取功能
"""

import asyncio
from playwright_automation import automation

async def test_text_extraction():
    """测试文本提取功能"""
    try:
        # 启动浏览器（非headless模式便于观察）
        print("启动浏览器...")
        await automation.start_browser(headless=False)
        
        # 导航到测试页面
        print("导航到测试页面...")
        await automation.navigate_to("https://example.com")
        
        # 测试1: 提取页面标题
        print("\n测试1: 提取页面标题")
        title_selector = "h1"
        title = await automation.extract_element_text(title_selector)
        print(f"页面标题: '{title}'")
        
        # 测试2: 提取段落文本
        print("\n测试2: 提取段落文本")
        paragraph_selector = "p"
        paragraph_text = await automation.extract_element_text(paragraph_selector)
        print(f"段落文本: '{paragraph_text}'")
        
        # 测试3: 提取链接文本
        print("\n测试3: 提取链接文本")
        link_selector = "a"
        link_text = await automation.extract_element_text(link_selector)
        print(f"链接文本: '{link_text}'")
        
        # 测试4: 测试iframe提取（example.com没有iframe，这里只是测试方法）
        print("\n测试4: 测试iframe提取功能")
        iframe_test_selector = "iframe"
        iframe_text = await automation.extract_element_text(iframe_test_selector)
        print(f"iframe提取结果: '{iframe_text}'")
        
        # 测试5: 测试Shadow DOM提取（example.com没有Shadow DOM，这里只是测试方法）
        print("\n测试5: 测试Shadow DOM提取功能")
        shadow_dom_test_selector = "div"
        shadow_text = await automation.extract_element_text(shadow_dom_test_selector)
        print(f"Shadow DOM提取结果: '{shadow_text}'")
        
        # 测试6: 导航到一个有输入框的页面测试
        print("\n测试6: 测试输入框文本提取")
        await automation.navigate_to("https://www.google.com")
        input_selector = "input[name='q']"
        input_text = await automation.extract_element_text(input_selector)
        print(f"输入框文本: '{input_text}'")
        
        print("\n所有测试完成!")
        
    except Exception as e:
        print(f"测试过程中出错: {e}")
    finally:
        # 关闭浏览器
        print("\n关闭浏览器...")
        await automation.close_browser()

if __name__ == "__main__":
    asyncio.run(test_text_extraction())
