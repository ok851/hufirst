import requests
import time

# 测试用例ID
case_id = 25

# 运行测试用例
print(f"开始运行测试用例 #{case_id}...")
start_time = time.time()

response = requests.post(f"http://localhost:5000/api/cases/{case_id}/run")

end_time = time.time()
duration = round(end_time - start_time, 2)

print(f"运行完成，耗时: {duration}秒")
print(f"响应状态码: {response.status_code}")
print(f"响应内容: {response.json()}")

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
