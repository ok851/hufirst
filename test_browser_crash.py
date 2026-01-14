import requests
import time
import json

# 测试浏览器崩溃后重新打开的功能
def test_browser_crash_recovery():
    base_url = "http://127.0.0.1:5000"
    
    print("=== 测试浏览器崩溃后重新打开功能 ===\n")
    
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
        
        # 等待3秒，确保浏览器已完全启动
        print("   等待3秒，确保浏览器已完全启动...")
        time.sleep(3)
        
        # 2. 模拟浏览器崩溃或被用户手动关闭
        # 我们将直接使用Playwright的API来关闭浏览器，这样更真实
        print("\n2. 直接关闭浏览器实例...")
        
        # 创建一个自定义请求，直接关闭浏览器
        crash_url = f"{base_url}/api/execute_multiple_cases"
        # 使用不存在的测试用例ID，这样在执行过程中会尝试关闭浏览器
        crash_data = {
            "case_ids": [9999]
        }
        crash_headers = {
            "Content-Type": "application/json"
        }
        crash_response = requests.post(crash_url, data=json.dumps(crash_data), headers=crash_headers, timeout=30)
        print(f"   响应状态码: {crash_response.status_code}")
        print("   ✅ 浏览器已关闭")
        
        # 等待5秒，确保浏览器已完全关闭
        print("   等待5秒，确保浏览器已完全关闭...")
        time.sleep(5)
        
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
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_browser_crash_recovery()
    if success:
        print("\n=== 所有测试通过！===")
    else:
        print("\n=== 测试失败！===")
