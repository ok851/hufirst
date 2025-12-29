from playwright.sync_api import sync_playwright
import time
import json

def test_browser_automation():
    """测试浏览器自动化功能"""
    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # 访问页面
        page.goto("https://www.baidu.com")
        print("已访问百度首页")
        
        # 等待页面加载
        page.wait_for_load_state("networkidle")
        
        # 测试搜索功能
        search_input = page.locator("#kw")  # 百度搜索框ID
        search_input.fill("Playwright 测试")
        print("已输入搜索内容")
        
        # 点击搜索按钮
        search_button = page.locator("#su")  # 百度搜索按钮ID
        search_button.click()
        print("已点击搜索按钮")
        
        # 等待搜索结果加载
        page.wait_for_load_state("networkidle")
        
        # 获取搜索结果数量
        results = page.locator(".result").count()
        print(f"找到 {results} 个搜索结果")
        
        # 等待几秒查看结果
        time.sleep(3)
        
        # 关闭浏览器
        browser.close()
        print("浏览器已关闭")

if __name__ == "__main__":
    test_browser_automation()