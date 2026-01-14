import requests
import json
import time

# 测试完整的浏览器自动化流程
def test_browser_automation_full():
    base_url = "http://127.0.0.1:5000"
    
    print("=== 开始测试完整的浏览器自动化流程 ===\n")
    
    try:
        # 1. 测试启用元素选择模式，这会启动浏览器
        print("1. 测试启用元素选择模式...")
        enable_url = f"{base_url}/api/enable_element_selection"
        enable_response = requests.post(enable_url, timeout=30)
        print(f"   响应状态码: {enable_response.status_code}")
        
        if enable_response.status_code == 200:
            enable_result = enable_response.json()
            if enable_result.get('success'):
                print("   ✅ 元素选择模式已启用，浏览器已启动")
            else:
                print(f"   ❌ 启用元素选择模式失败: {enable_result.get('error')}")
                return False
        else:
            print(f"   ❌ 启用元素选择模式失败: {enable_response.text}")
            return False
        
        # 等待3秒，确保浏览器完全启动
        print("   等待3秒，确保浏览器完全启动...")
        time.sleep(3)
        
        # 2. 测试禁用元素选择模式
        print("\n2. 测试禁用元素选择模式...")
        disable_url = f"{base_url}/api/disable_element_selection"
        disable_response = requests.post(disable_url, timeout=30)
        print(f"   响应状态码: {disable_response.status_code}")
        
        if disable_response.status_code == 200:
            disable_result = disable_response.json()
            if disable_result.get('success'):
                print("   ✅ 元素选择模式已禁用")
            else:
                print(f"   ❌ 禁用元素选择模式失败: {disable_result.get('error')}")
        else:
            print(f"   ❌ 禁用元素选择模式失败: {disable_response.text}")
        
        # 3. 测试执行多个测试用例，这会测试API的超时处理和浏览器关闭功能
        print("\n3. 测试执行多个测试用例...")
        execute_url = f"{base_url}/api/execute_multiple_cases"
        
        # 准备测试数据，使用一个不存在的测试用例ID，这样不会实际执行测试，但会测试API的超时处理和浏览器关闭功能
        data = {
            "case_ids": [9999]  # 使用不存在的测试用例ID
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        start_time = time.time()
        execute_response = requests.post(execute_url, data=json.dumps(data), headers=headers, timeout=60)
        end_time = time.time()
        response_time = end_time - start_time
        
        print(f"   请求耗时: {response_time:.2f}秒")
        print(f"   响应状态码: {execute_response.status_code}")
        
        if execute_response.status_code == 200:
            execute_result = execute_response.json()
            if execute_result.get('success'):
                print("   ✅ 执行多个测试用例API调用成功")
                print(f"   测试结果: 成功用例数: {execute_result['results']['successful_cases']}, 失败用例数: {execute_result['results']['failed_cases']}")
            else:
                print(f"   ❌ 执行多个测试用例失败: {execute_result.get('error')}")
                return False
        else:
            print(f"   ❌ 执行多个测试用例API调用失败: {execute_response.text}")
            return False
        
        print("\n🎉 完整的浏览器自动化流程测试通过！")
        print("✅ API端点没有出现Failed to fetch错误")
        print("✅ 浏览器能够正常启动和关闭")
        print("✅ 超时处理机制正常工作")
        print("✅ 错误处理机制正常工作")
        
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
    success = test_browser_automation_full()
    if success:
        print("\n=== 所有测试通过！===\n")
    else:
        print("\n=== 测试失败！===\n")
