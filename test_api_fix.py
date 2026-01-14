import requests
import json
import time

# 测试执行多个测试用例的API端点
def test_execute_multiple_cases():
    url = "http://127.0.0.1:5000/api/execute_multiple_cases"
    
    # 准备测试数据，使用一个不存在的测试用例ID，这样不会实际执行测试，但会测试API的超时处理和浏览器关闭功能
    data = {
        "case_ids": [9999]  # 使用不存在的测试用例ID
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        print("开始测试API端点...")
        start_time = time.time()
        
        # 发送请求，设置超时时间为60秒
        response = requests.post(url, data=json.dumps(data), headers=headers, timeout=60)
        
        end_time = time.time()
        response_time = end_time - start_time
        
        print(f"请求耗时: {response_time:.2f}秒")
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("响应内容:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print("✅ API请求成功，没有出现Failed to fetch错误")
            return True
        else:
            print(f"❌ API请求失败，状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
            return False
    except requests.exceptions.Timeout:
        print("❌ API请求超时")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ API请求发生异常: {e}")
        return False

if __name__ == "__main__":
    success = test_execute_multiple_cases()
    if success:
        print("\n🎉 测试通过，修复后的API端点能正常工作")
    else:
        print("\n❌ 测试失败，API端点仍有问题")
