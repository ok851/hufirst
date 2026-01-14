import requests
import json
import time

# 测试浏览器启动和关闭功能
def test_browser_close():
    # 1. 测试启用元素选择模式，这会启动浏览器
    enable_url = "http://127.0.0.1:5000/api/enable_element_selection"
    
    try:
        print("1. 测试启用元素选择模式...")
        enable_response = requests.post(enable_url, timeout=30)
        print(f"   响应状态码: {enable_response.status_code}")
        
        if enable_response.status_code == 200:
            print("   ✅ 元素选择模式已启用，浏览器已启动")
        else:
            print(f"   ❌ 启用元素选择模式失败: {enable_response.text}")
            return False
        
        # 等待2秒，确保浏览器完全启动
        time.sleep(2)
        
        # 2. 测试关闭浏览器
        close_url = "http://127.0.0.1:5000/api/close_browser"
        print("\n2. 测试关闭浏览器...")
        close_response = requests.post(close_url, timeout=30)
        print(f"   响应状态码: {close_response.status_code}")
        
        if close_response.status_code == 200:
            print("   ✅ 浏览器已成功关闭")
        else:
            print(f"   ❌ 关闭浏览器失败: {close_response.text}")
            return False
        
        print("\n🎉 测试通过，浏览器启动和关闭功能正常工作")
        return True
        
    except requests.exceptions.Timeout:
        print("\n❌ 请求超时")
        return False
    except requests.exceptions.RequestException as e:
        print(f"\n❌ 请求发生异常: {e}")
        return False

if __name__ == "__main__":
    success = test_browser_close()
    if success:
        print("\n所有测试通过！")
    else:
        print("\n测试失败！")
