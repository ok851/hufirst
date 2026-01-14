import asyncio
import time
from playwright_automation import PlaywrightAutomation

async def test_browser_reopen():
    """测试浏览器关闭后重新打开"""
    automation = PlaywrightAutomation()
    
    try:
        # 第一次打开浏览器
        print("第一次打开浏览器...")
        page = await automation.start_browser()
        await page.goto("https://www.baidu.com")
        print(f"第一次打开浏览器成功，当前URL: {page.url}")
        
        # 手动关闭浏览器（模拟用户关闭）
        print("手动关闭浏览器...")
        await automation.browser.close()
        # 等待一下确保浏览器关闭
        time.sleep(2)
        
        # 尝试重新打开浏览器
        print("尝试重新打开浏览器...")
        await automation.enable_element_selection("https://www.baidu.com")
        print(f"重新打开浏览器成功，当前URL: {automation.page.url}")
        
        print("测试成功: 浏览器关闭后可以重新打开！")
        return True
        
    except Exception as e:
        print(f"测试失败: {str(e)}")
        return False
    finally:
        # 清理资源
        if automation.browser and automation.browser.is_connected():
            await automation.browser.close()
        if automation.playwright:
            await automation.playwright.stop()

if __name__ == "__main__":
    asyncio.run(test_browser_reopen())