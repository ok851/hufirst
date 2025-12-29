import requests
import time

# 手动交互测试 - 测试滚动等操作的录制
def test_manual_interaction():
    base_url = "http://127.0.0.1:5000"
    
    print("开始测试录制功能 - 请按以下步骤手动操作:")
    print("1. 启动录制")
    print("2. 在打开的浏览器中进行以下操作:")
    print("   - 滚动页面")
    print("   - 点击一些元素")
    print("   - 在输入框中输入文本（如果有的话）")
    print("3. 等待程序自动停止录制并显示结果")
    print()
    
    # 1. 启动录制
    print("1. 启动录制...")
    start_response = requests.post(f"{base_url}/api/start_recording", json={"url": "https://www.baidu.com"})
    start_result = start_response.json()
    print(f"启动录制响应: {start_result}")
    
    if start_result.get('success'):
        print("\n录制启动成功！")
        print("请在浏览器中进行一些操作，如滚动、点击等...")
        time.sleep(15)  # 等待足够长的时间以便手动操作
        
        # 2. 停止录制
        print("\n2. 停止录制...")
        stop_response = requests.post(f"{base_url}/api/stop_recording")
        result = stop_response.json()
        print(f"停止录制响应: {result}")
        
        if result.get('success'):
            steps = result.get('steps', [])
            print(f"\n录制到 {len(steps)} 个步骤:")
            
            action_types = {}
            for i, step in enumerate(steps):
                action = step.get('action', 'unknown')
                if action not in action_types:
                    action_types[action] = 0
                action_types[action] += 1
                
                print(f"  步骤 {i+1}: {step}")
                
                # 特别显示滚动操作的详细信息
                if action == 'scroll':
                    scroll_pos = step.get('scrollPosition')
                    if scroll_pos:
                        print(f"    → 滚动到位置 X: {scroll_pos.get('x', 0)}, Y: {scroll_pos.get('y', 0)}")
            
            print(f"\n操作统计:")
            for action_type, count in action_types.items():
                print(f"  {action_type} 操作: {count} 次")
                
            if 'scroll' in action_types:
                print(f"\n✅ 恭喜！成功录制了 {action_types['scroll']} 次滚动操作！")
            else:
                print(f"\n⚠️  未检测到滚动操作，请确保在浏览器中进行了滚动操作。")
                
        else:
            print("停止录制失败")
    else:
        print("启动录制失败")

if __name__ == "__main__":
    test_manual_interaction()