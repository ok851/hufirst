import sqlite3

# 连接数据库
conn = sqlite3.connect('test_cases.db')
cursor = conn.cursor()

# 向run_history表添加expected_text字段
try:
    cursor.execute('ALTER TABLE run_history ADD COLUMN expected_text TEXT DEFAULT ""')
    print("成功向run_history表添加expected_text字段")
except Exception as e:
    print(f"添加字段时出错: {e}")

# 关闭连接
conn.commit()
conn.close()