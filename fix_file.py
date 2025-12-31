# 修复playwright_automation.py文件，删除重复的代码
with open(r'D:\mkst_baixiang\Python_Code\NewUITestPlatform\playwright_automation.py', 'r') as f:
    content = f.read()
    
# 找到需要保留的内容的结束位置
# 我们只需要保留到第一个sync_get_selected_element函数定义结束
end_pos = content.find('def sync_get_selected_element():') + len('def sync_get_selected_element():\n    async def run():\n        return await automation.get_selected_element()\n    return worker.execute(run)')

# 创建新的内容，只保留到结束位置
new_content = content[:end_pos]

# 写入修复后的内容
with open(r'D:\mkst_baixiang\Python_Code\NewUITestPlatform\playwright_automation.py', 'w') as f:
    f.write(new_content)

print("文件修复完成")
