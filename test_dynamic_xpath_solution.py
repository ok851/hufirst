#!/usr/bin/env python3
"""
测试动态XPath解决方案
验证extract_element_text方法对多种定位方式的支持
"""

import asyncio
from playwright_automation import PlaywrightAutomation
import time

async def test_dynamic_xpath_solution():
    """测试动态XPath解决方案"""
    automation = PlaywrightAutomation()
    
    try:
        # 启动浏览器
        await automation.start_browser(headless=False)
        
        # 1. 测试本地HTML文件
        await automation.navigate_to('file:///d:/mkst_baixiang/Python_Code/NewUITestPlatform/test_extraction.html')
        await asyncio.sleep(2)  # 等待页面加载
        
        print("\n=== 测试本地HTML文件 ===")
        
        # 测试CSS选择器
        css_result = await automation.extract_element_text('#test-heading', 'css')
        print(f"CSS选择器('#test-heading'): {css_result}")
        
        # 测试XPath选择器
        xpath_result = await automation.extract_element_text('//h1[@id="test-heading"]', 'xpath')
        print(f"XPath选择器('//h1[@id=\"test-heading\"]'): {xpath_result}")
        
        # 测试文本内容选择器
        text_result = await automation.extract_element_text('测试标题', 'text')
        print(f"文本选择器('测试标题'): {text_result}")
        
        # 测试角色选择器
        role_result = await automation.extract_element_text('heading,level=1', 'role')
        print(f"角色选择器('heading,level=1'): {role_result}")
        
        # 测试testid选择器
        testid_result = await automation.extract_element_text('test-paragraph', 'testid')
        print(f"testid选择器('test-paragraph'): {testid_result}")
        
        # 2. 测试简单的在线网站
        await automation.navigate_to('https://example.com')
        await asyncio.sleep(2)  # 等待页面加载
        
        print("\n=== 测试在线网站 (https://example.com) ===")
        
        # 测试CSS选择器
        css_result = await automation.extract_element_text('h1', 'css')
        print(f"CSS选择器('h1'): {css_result}")
        
        # 测试XPath选择器
        xpath_result = await automation.extract_element_text('//h1', 'xpath')
        print(f"XPath选择器('//h1'): {xpath_result}")
        
        # 测试文本内容选择器
        text_result = await automation.extract_element_text('Example Domain', 'text')
        print(f"文本选择器('Example Domain'): {text_result}")
        
        # 测试角色选择器
        role_result = await automation.extract_element_text('heading,level=1', 'role')
        print(f"角色选择器('heading,level=1'): {role_result}")
        
        # 3. 测试复杂的在线网站
        await automation.navigate_to('https://www.baidu.com')
        await asyncio.sleep(2)  # 等待页面加载
        
        print("\n=== 测试复杂网站 (https://www.baidu.com) ===")
        
        # 测试CSS选择器
        css_result = await automation.extract_element_text('#su', 'css')
        print(f"CSS选择器('#su'): {css_result}")
        
        # 测试文本内容选择器
        text_result = await automation.extract_element_text('百度一下', 'text')
        print(f"文本选择器('百度一下'): {text_result}")
        
        # 测试角色选择器
        role_result = await automation.extract_element_text('button', 'role')
        print(f"角色选择器('button'): {role_result}")
        
    except Exception as e:
        print(f"测试过程中出错: {str(e)}")
    finally:
        # 关闭浏览器
        await automation.close_browser()

if __name__ == "__main__":
    asyncio.run(test_dynamic_xpath_solution())
