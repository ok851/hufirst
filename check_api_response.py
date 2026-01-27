import requests

# 测试用例ID
case_id = 38

# 获取运行历史记录
print("获取运行历史记录...")
history_response = requests.get(f"http://localhost:5000/api/run-history?case_id={case_id}&page=1&page_size=5")
history_data = history_response.json()

print(f"响应状态码: {history_response.status_code}")
print(f"响应内容: {history_data}")

if history_data.get('success'):
    print(f"获取到 {len(history_data.get('history', []))} 条运行记录")
    for i, record in enumerate(history_data.get('history', [])):
        print(f"\n记录 #{i+1}:")
        print(f"ID: {record.get('id')}")
        print(f"状态: {record.get('status')}")
        print(f"耗时: {record.get('duration')}秒")
        print(f"提取文本: {record.get('extracted_text')}")
        print(f"预期结果: {record.get('expected_text')}")
        print(f"错误信息: {record.get('error')}")
        print(f"运行时间: {record.get('created_at')}")
else:
    print("获取运行历史记录失败:", history_data.get('error'))

# 获取指定运行记录的详情
print("\n获取指定运行记录的详情...")
if history_data.get('success') and history_data.get('history'):
    record_id = history_data.get('history')[0].get('id')
    detail_response = requests.get(f"http://localhost:5000/api/run-history/{record_id}")
    detail_data = detail_response.json()
    print(f"响应状态码: {detail_response.status_code}")
    print(f"响应内容: {detail_data}")
