import sqlite3

# 连接数据库
conn = sqlite3.connect('test_cases.db')
cursor = conn.cursor()

# 向test_steps表添加compare_type字段
try:
    cursor.execute('ALTER TABLE test_steps ADD COLUMN compare_type TEXT DEFAULT "equals"')
    print("成功向test_steps表添加compare_type字段")
except Exception as e:
    print(f"添加字段时出错: {e}")

# 关闭连接
conn.commit()
conn.close()