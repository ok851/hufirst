import requests
import time

# 测试录制功能
def test_recording():
    base_url = "http://127.0.0.1:5000"
    
    print("开始测试录制功能...")
    
    # 1. 启动录制
    print("1. 启动录制...")
    start_response = requests.post(f"{base_url}/api/start_recording", json={"url": "https://www.baidu.com"})
    start_result = start_response.json()
    print(f"启动录制响应: {start_result}")
    
    if start_result.get('success'):
        print("录制启动成功，等待几秒钟以便进行一些操作...")
        time.sleep(5)  # 等待一段时间，以便可以手动进行一些操作
        
        # 2. 执行一些操作，如滚动页面
        print("2. 执行一些操作，如滚动页面...")
        scroll_response = requests.post(f"{base_url}/api/scroll", json={"direction": "down", "pixels": 300})
        print(f"滚动操作响应: {scroll_response.json()}")
        time.sleep(1)
        
        # 再次滚动
        scroll_response2 = requests.post(f"{base_url}/api/scroll", json={"direction": "down", "pixels": 500})
        print(f"第二次滚动操作响应: {scroll_response2.json()}")
        time.sleep(1)
        
        # 3. 停止录制
        print("3. 停止录制...")
        stop_response = requests.post(f"{base_url}/api/stop_recording")
        result = stop_response.json()
        print(f"停止录制响应: {result}")
        
        if result.get('success'):
            steps = result.get('steps', [])
            print(f"录制到 {len(steps)} 个步骤:")
            for i, step in enumerate(steps):
                print(f"  步骤 {i+1}: {step}")
                
                # 检查是否包含滚动步骤
                if step.get('action') == 'scroll':
                    print(f"    - 滚动位置: {step.get('scrollPosition')}")
        else:
            print("停止录制失败")
    else:
        print("启动录制失败")

if __name__ == "__main__":
    test_recording()