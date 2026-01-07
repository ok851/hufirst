import sqlite3

# 连接数据库
conn = sqlite3.connect('test_cases.db')
cursor = conn.cursor()

# 检查test_cases表结构
print("test_cases表结构:")
cursor.execute('PRAGMA table_info(test_cases);')
for row in cursor.fetchall():
    print(row)

# 检查test_cases表数据
print("\ntest_cases表数据:")
cursor.execute('SELECT * FROM test_cases LIMIT 5;')
for row in cursor.fetchall():
    print(row)

# 关闭连接
conn.close()