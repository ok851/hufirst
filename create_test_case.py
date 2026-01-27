import requests
import json

# 创建测试用例
print("创建测试用例...")
case_data = {
    "name": "测试预期结果显示",
    "description": "测试运行历史记录中显示预期结果",
    "url": "https://www.baidu.com",
    "project_id": 1
}

case_response = requests.post("http://localhost:5000/api/cases", json=case_data)
case_result = case_response.json()
print(f"创建测试用例响应: {case_result}")

if case_result.get('success'):
    case_id = case_result.get('case_id')
    print(f"创建测试用例成功，ID: {case_id}")
    
    # 创建测试步骤 - 导航到百度首页
    step1_data = {
        "case_id": case_id,
        "action": "navigate",
        "input_value": "https://www.baidu.com",
        "description": "导航到百度首页"
    }
    
    step1_response = requests.post(f"http://localhost:5000/api/steps", json=step1_data)
    step1_result = step1_response.json()
    print(f"创建步骤1响应: {step1_result}")
    
    # 创建测试步骤 - 提取百度首页标题
    step2_data = {
        "case_id": case_id,
        "action": "text_compare",
        "selector_type": "css",
        "selector_value": "#su",
        "input_value": "百度一下",
        "description": "验证百度首页搜索按钮文本",
        "compare_type": "equals"
    }
    
    step2_response = requests.post(f"http://localhost:5000/api/steps", json=step2_data)
    step2_result = step2_response.json()
    print(f"创建步骤2响应: {step2_result}")
    
    # 运行测试用例
    print(f"\n运行测试用例 #{case_id}...")
    run_response = requests.post(f"http://localhost:5000/api/cases/{case_id}/run")
    run_result = run_response.json()
    print(f"运行测试用例响应: {run_result}")
    
    # 检查运行历史记录
    print("\n获取运行历史记录...")
    history_response = requests.get(f"http://localhost:5000/api/run-history?case_id={case_id}&page=1&page_size=5")
    history_data = history_response.json()
    
    print(f"响应状态码: {history_response.status_code}")
    if history_data.get('success'):
        print(f"获取到 {len(history_data.get('history', []))} 条运行记录")
        for i, record in enumerate(history_data.get('history', [])[:1]):
            print(f"\n记录 #{i+1}:")
            print(f"状态: {record.get('status')}")
            print(f"耗时: {record.get('duration')}秒")
            print(f"提取文本: {record.get('extracted_text')}")
            print(f"预期结果: {record.get('expected_text')}")
            print(f"运行时间: {record.get('created_at')}")
    else:
        print("获取运行历史记录失败:", history_data.get('error'))
else:
    print("创建测试用例失败:", case_result.get('error'))
