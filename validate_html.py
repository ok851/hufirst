from bs4 import BeautifulSoup

# 读取HTML文件
with open('templates/create_case_v2.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

try:
    # 使用BeautifulSoup解析HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    print("HTML解析成功，没有明显的语法错误。")
    
    # 检查特定部分
    title_modal = soup.find('div', id='titleModal')
    if title_modal:
        print("找到titleModal元素。")
        
        # 检查有问题的部分
        problematic_div = title_modal.find('div', class_='flex justify-between items-center mb-4')
        if problematic_div:
            print("找到有问题的div元素。")
            h3 = problematic_div.find('h3')
            button = problematic_div.find('button')
            
            if h3:
                print(f"h3元素内容: {h3.text.strip()}")
            else:
                print("未找到h3元素。")
            
            if button:
                print(f"button元素: 类型={button.get('type')}, 类={button.get('class')}")
                i_tag = button.find('i')
                if i_tag:
                    print(f"i元素: 类={i_tag.get('class')}")
                else:
                    print("未找到i元素。")
            else:
                print("未找到button元素。")
        else:
            print("未找到有问题的div元素。")
    else:
        print("未找到titleModal元素。")
        
except Exception as e:
    print(f"HTML解析错误: {e}")
