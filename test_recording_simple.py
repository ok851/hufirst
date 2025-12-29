import requests
import time

# 测试录制功能 - 简化版
def test_recording_simple():
    base_url = "http://127.0.0.1:5000"
    
    print("开始测试录制功能...")
    
    # 1. 启动录制
    print("1. 启动录制...")
    start_response = requests.post(f"{base_url}/api/start_recording", json={"url": "https://www.baidu.com"})
    start_result = start_response.json()
    print(f"启动录制响应: {start_result}")
    
    if start_result.get('success'):
        print("录制启动成功，等待几秒钟以便进行一些操作...")
        time.sleep(8)  # 等待更长时间，以便手动进行一些操作，如滚动、点击等
        
        # 2. 停止录制
        print("2. 停止录制...")
        stop_response = requests.post(f"{base_url}/api/stop_recording")
        result = stop_response.json()
        print(f"停止录制响应: {result}")
        
        if result.get('success'):
            steps = result.get('steps', [])
            print(f"录制到 {len(steps)} 个步骤:")
            scroll_count = 0
            click_count = 0
            fill_count = 0
            navigate_count = 0
            other_count = 0
            
            for i, step in enumerate(steps):
                print(f"  步骤 {i+1}: {step}")
                
                # 统计不同类型的步骤
                action = step.get('action')
                if action == 'scroll':
                    scroll_count += 1
                    print(f"    - 滚动位置: {step.get('scrollPosition')}")
                elif action == 'click':
                    click_count += 1
                elif action == 'fill':
                    fill_count += 1
                elif action == 'navigate':
                    navigate_count += 1
                else:
                    other_count += 1
            
            print(f"\n操作统计:")
            print(f"  滚动操作: {scroll_count}")
            print(f"  点击操作: {click_count}")
            print(f"  输入操作: {fill_count}")
            print(f"  导航操作: {navigate_count}")
            print(f"  其他操作: {other_count}")
        else:
            print("停止录制失败")
    else:
        print("启动录制失败")

if __name__ == "__main__":
    test_recording_simple()