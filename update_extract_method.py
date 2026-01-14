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

if start_line is not None and end_line is not None:
    # Define the new method content as a list of lines
    new_method_lines = [
        '    async def extract_element_text(self, selector: str) -> str:\n',
        '        """提取特定元素的文本"""\n',
        '        if self.page is None:\n',
        '            raise Exception("浏览器未启动")\n',
        '        \n',
        '        # 内部辅助函数：提取输入框的值\n',
        '        async def extract_input_value(element):\n',
        '            try:\n',
        '                text = await element.input_value()\n',
        '                return text if text else ""\n',
        '            except:\n',
        '                try:\n',
        '                    text = await element.get_attribute("value")\n',
        '                    return text if text else ""\n',
        '                except:\n',
        '                    return ""\n',
        '        \n',
        '        # 内部辅助函数：提取普通元素的内容\n',
        '        async def extract_element_content(element):\n',
        '            try:\n',
        '                text = await element.inner_text()\n',
        '                return text if text else ""\n',
        '            except:\n',
        '                try:\n',
        '                    text = await element.text_content()\n',
        '                    return text if text else ""\n',
        '                except:\n',
        '                    return ""\n',
        '        \n',
        '        # 内部辅助函数：从Shadow DOM中提取文本\n',
        '        async def extract_from_shadow_dom(selector):\n',
        '            try:\n',
        '                text = await self.page.evaluate(f\'\'\'\n',
        '                    (selector) => {{\n',
        '                        function searchInShadowDOM(root) {{\n',
        '                            const element = root.querySelector(selector);\n',
        '                            if (element) {{\n',
        '                                if (element.tagName === "INPUT" || element.tagName === "TEXTAREA") {{\n',
        '                                    return element.value || element.getAttribute("value") || "";\n',
        '                                }}\n',
        '                                return element.innerText || element.textContent || "";\n',
        '                            }}\n',
        '                            const shadowHosts = root.querySelectorAll("*");\n',
        '                            for (const host of shadowHosts) {{\n',
        '                                if (host.shadowRoot) {{\n',
        '                                    const result = searchInShadowDOM(host.shadowRoot);\n',
        '                                    if (result) return result;\n',
        '                                }}\n',
        '                            }}\n',
        '                            return "";\n',
        '                        }}\n',
        '                        return searchInShadowDOM(document);\n',
        '                    }}\n',
        '                \'\'\', selector)\n',
        '                return text if text else ""\n',
        '            except:\n',
        '                return ""\n',
        '        \n',
        '        # 内部辅助函数：从iframe中提取文本\n',
        '        async def extract_from_iframe(selector):\n',
        '            try:\n',
        '                frames = self.page.frames\n',
        '                for frame in frames:\n',
        '                    async def extract_from_specific_iframe(frame, selector):\n',
        '                        try:\n',
        '                            element = frame.locator(selector)\n',
        '                            count = await element.count()\n',
        '                            if count > 0:\n',
        '                                element = element.first\n',
        '                                tag_name = await element.evaluate("el => el.tagName.toLowerCase()")\n',
        '                                if tag_name in ["input", "textarea"]:\n',
        '                                    return await extract_input_value(element)\n',
        '                                return await extract_element_content(element)\n',
        '                            for child_frame in frame.child_frames():\n',
        '                                text = await extract_from_specific_iframe(child_frame, selector)\n',
        '                                if text: return text\n',
        '                            return ""\n',
        '                        except:\n',
        '                            return ""\n',
        '                    \n',
        '                    try:\n',
        '                        text = await extract_from_specific_iframe(frame, selector)\n',
        '                        if text: return text\n',
        '                    except: pass\n',
        '                return ""\n',
        '            except:\n',
        '                return ""\n',
        '        \n',
        '        # 内部辅助函数：处理特殊DOM结构\n',
        '        async def handle_special_dom(selector):\n',
        '            shadow_dom_text = await extract_from_shadow_dom(selector)\n',
        '            if shadow_dom_text: return shadow_dom_text\n',
        '            iframe_text = await extract_from_iframe(selector)\n',
        '            if iframe_text: return iframe_text\n',
        '            return ""\n',
        '        \n',
        '        try:\n',
        '            # 1. 快速定位元素，不使用复杂的等待机制\n',
        '            element = self.page.locator(selector)\n',
        '            \n',
        '            # 2. 检查元素是否存在\n',
        '            count = await element.count()\n',
        '            if count == 0:\n',
        '                # 尝试处理特殊DOM结构\n',
        '                return await handle_special_dom(selector)\n',
        '            \n',
        '            # 3. 获取第一个匹配元素\n',
        '            element = element.first\n',
        '            \n',
        '            # 4. 尝试获取元素标签名，判断元素类型\n',
        '            try:\n',
        '                tag_name = await element.evaluate("el => el.tagName.toLowerCase()")\n',
        '                \n',
        '                # 对于输入框类型，使用input_value()\n',
        '                if tag_name in ["input", "textarea"]:\n',
        '                    return await extract_input_value(element)\n',
        '            except:\n',
        '                pass\n',
        '            \n',
        '            # 5. 对于非输入框元素，使用inner_text()\n',
        '            return await extract_element_content(element)\n',
        '        except Exception as e:\n',
        '            # 6. 特殊DOM结构处理：尝试处理Shadow DOM和iframe\n',
        '            return await handle_special_dom(selector)\n',
        '\n'
    ]
    
    # Replace the old method with the new one
    new_lines = lines[:start_line] + new_method_lines + lines[end_line:]
    
    # Write the updated content back to the file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print(f"Successfully updated extract_element_text method from line {start_line+1} to {end_line}")
else:
    print("Could not find the extract_element_text method or the _validate_selector method")
    if start_line is None:
        print("extract_element_text method not found")
    if end_line is None:
        print("_validate_selector method not found after extract_element_text")