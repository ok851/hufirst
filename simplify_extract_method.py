import re

# Read the file content
file_path = r'd:\mkst_baixiang\Python_Code\NewUITestPlatform\playwright_automation.py'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the start and end lines of the extract_element_text method
start_line = None
end_line = None
for i, line in enumerate(lines):
    if 'async def extract_element_text(self, selector: str) -> str:' in line:
        start_line = i
    elif start_line is not None and 'async def _validate_selector' in line:
        end_line = i
        break

if start_line is None or end_line is None:
    print("Could not find the extract_element_text method or the _validate_selector method")
    exit(1)

# Define the simplified and improved method
new_method_lines = [
    '    async def extract_element_text(self, selector: str) -> str:\n',
    '        """提取特定元素的文本，支持CSS选择器和XPath选择器"""\n',
    '        if self.page is None:\n',
    '            raise Exception("浏览器未启动")\n',
    '        \n',
    '        try:\n',
    '            # 1. 直接使用Playwright的locator，它原生支持CSS和XPath\n',
    '            #    Playwright会自动识别XPath（以//开头或包含xpath=前缀）\n',
    '            element = self.page.locator(selector)\n',
    '            \n',
    '            # 2. 快速检查元素是否存在\n',
    '            count = await element.count()\n',
    '            if count == 0:\n',
    '                # 尝试简单的重试机制\n',
    '                await asyncio.sleep(0.5)\n',
    '                count = await element.count()\n',
    '                if count == 0:\n',
    '                    return ""\n',
    '            \n',
    '            # 3. 获取第一个匹配元素\n',
    '            element = element.first\n',
    '            \n',
    '            # 4. 尝试获取元素标签名，判断元素类型\n',
    '            tag_name = await element.evaluate("el => el.tagName.toLowerCase()")\n',
    '            \n',
    '            # 5. 针对不同元素类型使用合适的提取方法\n',
    '            if tag_name in ["input", "textarea"]:\n',
    '                # 输入框类型，使用input_value()直接获取值\n',
    '                try:\n',
    '                    return await element.input_value()\n',
    '                except:\n',
    '                    # 失败时尝试获取value属性\n',
    '                    try:\n',
    '                        value = await element.get_attribute("value")\n',
    '                        return value if value is not None else ""\n',
    '                    except:\n',
    '                        return ""\n',
    '            else:\n',
    '                # 普通元素，优先使用inner_text()获取可见文本\n',
    '                try:\n',
    '                    return await element.inner_text()\n',
    '                except:\n',
    '                    # 失败时尝试使用text_content()获取所有文本\n',
    '                    try:\n',
    '                        return await element.text_content()\n',
    '                    except:\n',
    '                        return ""\n',
    '        except Exception as e:\n',
    '            # 简化异常处理，确保返回空字符串而不是崩溃\n',
    '            print(f"提取元素文本时出错: {str(e)}")\n',
    '            return ""\n',
    '\n'
]

# Replace the old method with the new one
new_lines = lines[:start_line] + new_method_lines + lines[end_line:]

# Write the updated content back to the file
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"Successfully simplified and improved extract_element_text method")
