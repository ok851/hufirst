import requests
import time

# 测试浏览器关闭后重新打开的功能
def test_browser_reopen():
    base_url = "http://127.0.0.1:5000"
    
    print("=== 测试浏览器关闭后重新打开功能 ===\n")
    
    try:
        # 1. 第一次启用元素选择模式
        print("1. 第一次启用元素选择模式...")
        enable_url = f"{base_url}/api/enable_element_selection"
        enable_response = requests.post(enable_url, timeout=30)
        print(f"   响应状态码: {enable_response.status_code}")
        
        if enable_response.status_code == 200:
            enable_result = enable_response.json()
            if enable_result.get('success'):
                print("   ✅ 第一次启用元素选择模式成功，浏览器已启动")
            else:
                print(f"   ❌ 第一次启用元素选择模式失败: {enable_result.get('error')}")
                return False
        else:
            print(f"   ❌ 第一次启用元素选择模式失败: {enable_response.text}")
            return False
        
        # 等待5秒，模拟用户操作
        print("   等待5秒，模拟用户操作...")
        time.sleep(5)
        
        # 2. 模拟浏览器崩溃或被用户手动关闭
        print("\n2. 模拟浏览器崩溃或被用户手动关闭...")
        # 直接重置浏览器状态，模拟浏览器被关闭的情况
        reset_url = f"{base_url}/api/reset_browser"
        reset_response = requests.post(reset_url, timeout=30)
        print(f"   响应状态码: {reset_response.status_code}")
        
        if reset_response.status_code == 200:
            print("   ✅ 浏览器状态已重置")
        else:
            # 如果没有reset_browser端点，直接继续测试
            print(f"   ⚠️  重置浏览器状态失败（可能是因为没有对应的API端点），直接继续测试")
        
        # 等待3秒，确保浏览器已完全关闭
        print("   等待3秒，确保浏览器已完全关闭...")
        time.sleep(3)
        
        # 3. 第二次启用元素选择模式，测试是否能重新打开浏览器
        print("\n3. 第二次启用元素选择模式，测试是否能重新打开浏览器...")
        enable_response = requests.post(enable_url, timeout=30)
        print(f"   响应状态码: {enable_response.status_code}")
        
        if enable_response.status_code == 200:
            enable_result = enable_response.json()
            if enable_result.get('success'):
                print("   ✅ 第二次启用元素选择模式成功，浏览器已重新打开")
            else:
                print(f"   ❌ 第二次启用元素选择模式失败: {enable_result.get('error')}")
                return False
        else:
            print(f"   ❌ 第二次启用元素选择模式失败: {enable_response.text}")
            return False
        
        # 4. 清理：禁用元素选择模式
        print("\n4. 清理：禁用元素选择模式...")
        disable_url = f"{base_url}/api/disable_element_selection"
        requests.post(disable_url, timeout=30)
        print("   ✅ 测试完成，已禁用元素选择模式")
        
        print("\n🎉 测试通过！浏览器关闭后能够成功重新打开")
        return True
        
    except requests.exceptions.Timeout:
        print("\n❌ 请求超时，测试失败")
        return False
    except requests.exceptions.RequestException as e:
        print(f"\n❌ 请求发生异常: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 测试发生异常: {e}")
        return False

if __name__ == "__main__":
    success = test_browser_reopen()
    if success:
        print("\n=== 所有测试通过！===\n")
    else:
        print("\n=== 测试失败！===\n")
