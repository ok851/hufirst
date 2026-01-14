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
    elif start_line is not None and 'async def' in line and 'extract_element_text' not in line:
        end_line = i
        break

if start_line is None or end_line is None:
    print("Could not find the extract_element_text method")
    exit(1)

# Define the new method content with enhanced debugging and selector handling
new_method_lines = [
    '    async def extract_element_text(self, selector: str, selector_type: str = "css") -> str:\n',
    '        """提取特定元素的文本，支持CSS选择器和XPath选择器"""\n',
    '        if self.page is None:\n',
    '            raise Exception("浏览器未启动")\n',
    '        \n',
    '        uat_logger.info(f"📝 [TEXT_EXTRACT_DEBUG] 开始提取文本，选择器: {selector}, 选择器类型: {selector_type}")\n',
    '        \n',
    '        # 构建完整的选择器，与click_element方法保持一致\n',
    '        full_selector = selector\n',
    '        if selector_type == "xpath":\n',
    '            full_selector = f"xpath={selector}"\n',
    '        elif not full_selector.startswith("xpath=") and (full_selector.startswith("//") or full_selector.startswith("/")):\n',
    '            # 自动识别XPath\n',
    '            full_selector = f"xpath={full_selector}"\n',
    '        \n',
    '        uat_logger.info(f"📝 [TEXT_EXTRACT_DEBUG] 构建的完整选择器: {full_selector}")\n',
    '        \n',
    '        try:\n',
    '            # 等待元素可见，增加成功概率\n',
    '            uat_logger.info(f"📝 [TEXT_EXTRACT_DEBUG] 等待元素可见")\n',
    '            await self.page.wait_for_selector(full_selector, state="visible", timeout=5000)\n',
    '            await self.page.wait_for_selector(full_selector, state="enabled", timeout=5000)\n',
    '            \n',
    '            # 使用Playwright的locator方法获取元素\n',
    '            uat_logger.info(f"📝 [TEXT_EXTRACT_DEBUG] 使用locator获取元素")\n',
    '            element = self.page.locator(full_selector)\n',
    '            \n',
    '            # 检查元素是否存在\n',
    '            count = await element.count()\n',
    '            uat_logger.info(f"📝 [TEXT_EXTRACT_DEBUG] 找到元素数量: {count}")\n',
    '            if count == 0:\n',
    '                uat_logger.warning(f"📝 [TEXT_EXTRACT_DEBUG] 未找到元素")\n',
    '                return ""\n',
    '            \n',
    '            # 获取第一个匹配元素\n',
    '            element = element.first\n',
    '            \n',
    '            # 获取元素的标签名，判断元素类型\n',
    '            tag_name = await element.evaluate("el => el.tagName.toLowerCase()")\n',
    '            uat_logger.info(f"📝 [TEXT_EXTRACT_DEBUG] 元素标签名: {tag_name}")\n',
    '            \n',
    '            # 针对不同元素类型使用合适的提取方法\n',
    '            extracted_text = ""\n',
    '            if tag_name in ["input", "textarea"]:\n',
    '                uat_logger.info(f"📝 [TEXT_EXTRACT_DEBUG] 输入框元素，使用input_value()提取")\n',
    '                try:\n',
    '                    extracted_text = await element.input_value()\n',
    '                    uat_logger.info(f"📝 [TEXT_EXTRACT_DEBUG] input_value()提取结果: \'{extracted_text}")\n',
    '                except Exception as e:\n',
    '                    uat_logger.warning(f"📝 [TEXT_EXTRACT_DEBUG] input_value()失败: {e}")\n',
    '                    try:\n',
    '                        extracted_text = await element.get_attribute("value")\n',
    '                        uat_logger.info(f"📝 [TEXT_EXTRACT_DEBUG] get_attribute(\"value\")提取结果: \'{extracted_text}")\n',
    '                    except Exception as e2:\n',
    '                        uat_logger.warning(f"📝 [TEXT_EXTRACT_DEBUG] get_attribute(\"value\")失败: {e2}")\n',
    '            else:\n',
    '                uat_logger.info(f"📝 [TEXT_EXTRACT_DEBUG] 普通元素，使用inner_text()提取")\n',
    '                try:\n',
    '                    extracted_text = await element.inner_text()\n',
    '                    uat_logger.info(f"📝 [TEXT_EXTRACT_DEBUG] inner_text()提取结果: \'{extracted_text}")\n',
    '                except Exception as e:\n',
    '                    uat_logger.warning(f"📝 [TEXT_EXTRACT_DEBUG] inner_text()失败: {e}")\n',
    '                    try:\n',
    '                        extracted_text = await element.text_content()\n',
    '                        uat_logger.info(f"📝 [TEXT_EXTRACT_DEBUG] text_content()提取结果: \'{extracted_text}")\n',
    '                    except Exception as e2:\n',
    '                        uat_logger.warning(f"📝 [TEXT_EXTRACT_DEBUG] text_content()失败: {e2}")\n',
    '            \n',
    '            # 确保返回的文本不为None\n',
    '            result = extracted_text if extracted_text is not None else ""\n',
    '            uat_logger.info(f"📝 [TEXT_EXTRACT_DEBUG] 最终提取结果: \'{result}")\n',
    '            return result\n',
    '        except Exception as e:\n',
    '            # 详细记录异常信息\n',
    '            uat_logger.error(f"📝 [TEXT_EXTRACT_DEBUG] 提取文本时出错: {str(e)}")\n',
    '            print(f"提取元素文本时出错: {str(e)}")\n',
    '            return ""\n',
    '\n'
]

# Replace the old method with the new one
new_lines = lines[:start_line] + new_method_lines + lines[end_line:]

# Write the updated content back to the file
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"Successfully updated extract_element_text method with enhanced debugging and selector handling")
print(f"Method updated from line {start_line+1} to {end_line}")
