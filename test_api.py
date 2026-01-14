import requests
import json

# 测试API是否正常工作
try:
    response = requests.get('http://localhost:5000/api/projects')
    print(f"API响应状态码: {response.status_code}")
    print(f"响应头: {json.dumps(dict(response.headers), indent=2)}")
    print(f"响应内容: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"API测试失败: {e}")
