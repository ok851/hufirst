import sqlite3

# 连接到数据库
conn = sqlite3.connect('test_cases.db')
cursor = conn.cursor()

# 查询测试步骤表的结构
print("测试步骤表结构:")
cursor.execute("PRAGMA table_info(test_steps)")
columns = cursor.fetchall()
for column in columns:
    print(f"列名: {column[1]}, 类型: {column[2]}")

print("\n" + "-" * 80 + "\n")

# 查询前20条测试步骤数据
print("测试步骤数据:")
print("ID\tCaseID\tAction\t\tSelectorType\tSelectorValue\tInputValue")
print("-" * 100)

cursor.execute('''
    SELECT id, case_id, action, selector_type, selector_value, input_value 
    FROM test_steps 
    LIMIT 20
''')
rows = cursor.fetchall()

for row in rows:
    # 格式化输出，确保对齐
    id_val = row[0]
    case_id = row[1]
    action = row[2]
    selector_type = row[3] if row[3] else ''
    selector_value = row[4] if row[4] else ''
    input_value = row[5] if row[5] else ''
    
    print(f"{id_val}\t{case_id}\t{action}\t\t{selector_type}\t\t{selector_value[:20]}\t\t{input_value[:20]}")

# 关闭数据库连接
conn.close()