import asyncio
import time
from playwright_automation import PlaywrightAutomation
from database import Database

async def test_text_extraction():
    """测试文本提取功能"""
    automation = PlaywrightAutomation()
    db = Database()
    
    try:
        # 启动浏览器
        print("启动浏览器...")
        page = await automation.start_browser()
        
        # 导航到测试页面
        await page.goto("https://www.baidu.com")
        print(f"导航到: {page.url}")
        
        # 等待页面加载完成
        await page.wait_for_load_state('networkidle')
        
        # 测试提取页面文本
        print("\n1. 测试提取页面文本...")
        page_text = await automation.get_page_text()
        print(f"提取到页面文本: {page_text[:100]}...")
        
        # 测试提取特定元素文本
        print("\n2. 测试提取特定元素文本...")
        # 提取百度搜索按钮的文本
        button_text = await automation.extract_element_text('input[type="submit"]', 'css')
        print(f"提取到搜索按钮文本: '{button_text}'")
        
        # 提取百度logo的alt文本
        logo_text = await automation.extract_element_text('img[alt*="百度"]', 'css')
        print(f"提取到logo alt文本: '{logo_text}'")
        
        # 测试使用XPath提取文本
        print("\n3. 测试使用XPath提取文本...")
        xpath_text = await automation.extract_element_text('//input[@type="submit"]', 'xpath')
        print(f"使用XPath提取到搜索按钮文本: '{xpath_text}'")
        
        # 保存测试结果到数据库
        print("\n4. 测试保存到数据库...")
        # 先创建一个测试用例
        case_id = db.create_test_case("测试文本提取功能", "测试文本提取和保存到数据库的功能")
        print(f"创建测试用例成功，ID: {case_id}")
        
        # 保存运行历史记录
        history_id = db.create_run_history(case_id, 'passed', 1.0, "", page_text)
        print(f"保存运行历史记录成功，ID: {history_id}")
        
        # 从数据库中获取运行历史记录
        history = db.get_run_history_detail(history_id)
        print(f"从数据库中获取的提取文本: {history['extracted_text'][:100]}...")
        
        # 验证提取的文本是否正确保存到数据库中
        if history['extracted_text'] == page_text:
            print("✅ 测试通过！提取的文本正确保存到数据库中")
        else:
            print("❌ 测试失败！提取的文本没有正确保存到数据库中")
        
        # 清理测试数据
        db.delete_run_history(history_id)
        db.delete_test_case(case_id)
        print("\n清理测试数据完成")
        
        return True
        
    except Exception as e:
        print(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理资源
        if automation.browser and automation.browser.is_connected():
            await automation.browser.close()
        if automation.playwright:
            await automation.playwright.stop()

if __name__ == "__main__":
    asyncio.run(test_text_extraction())