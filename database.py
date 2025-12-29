import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any

class Database:
    def __init__(self, db_path: str = "test_cases.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建测试用例表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                target_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建测试脚本表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_scripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER,
                name TEXT NOT NULL,
                steps TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (case_id) REFERENCES test_cases (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_test_case(self, name: str, description: str = "", target_url: str = "") -> int:
        """创建测试用例"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO test_cases (name, description, target_url) VALUES (?, ?, ?)",
            (name, description, target_url)
        )
        case_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return case_id
    
    def get_test_case(self, case_id: int) -> Dict[str, Any]:
        """获取测试用例"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM test_cases WHERE id = ?", (case_id,))
        row = cursor.fetchone()
        
        if row:
            return {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'target_url': row[3],
                'created_at': row[4]
            }
        
        conn.close()
        return None
    
    def get_all_test_cases(self) -> List[Dict[str, Any]]:
        """获取所有测试用例"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM test_cases ORDER BY created_at DESC")
        rows = cursor.fetchall()
        
        cases = []
        for row in rows:
            cases.append({
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'target_url': row[3],
                'created_at': row[4]
            })
        
        conn.close()
        return cases
    
    def create_test_script(self, case_id: int, name: str, steps: List[Dict[str, Any]] = None) -> int:
        """创建测试脚本"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        steps_json = json.dumps(steps or [], ensure_ascii=False)
        cursor.execute(
            "INSERT INTO test_scripts (case_id, name, steps) VALUES (?, ?, ?)",
            (case_id, name, steps_json)
        )
        script_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return script_id
    
    def get_test_script(self, script_id: int) -> Dict[str, Any]:
        """获取测试脚本"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM test_scripts WHERE id = ?", (script_id,))
        row = cursor.fetchone()
        
        if row:
            return {
                'id': row[0],
                'case_id': row[1],
                'name': row[2],
                'steps': json.loads(row[3]) if row[3] else [],
                'created_at': row[4]
            }
        
        conn.close()
        return None
    
    def get_scripts_by_case(self, case_id: int) -> List[Dict[str, Any]]:
        """根据用例ID获取所有脚本"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM test_scripts WHERE case_id = ? ORDER BY created_at DESC", (case_id,))
        rows = cursor.fetchall()
        
        scripts = []
        for row in rows:
            scripts.append({
                'id': row[0],
                'case_id': row[1],
                'name': row[2],
                'steps': json.loads(row[3]) if row[3] else [],
                'created_at': row[4]
            })
        
        conn.close()
        return scripts
    
    def update_test_case(self, case_id: int, name: str = None, description: str = None, target_url: str = None) -> bool:
        """更新测试用例"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 构建更新语句和参数
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        
        if target_url is not None:
            updates.append("target_url = ?")
            params.append(target_url)
        
        if not updates:
            conn.close()
            return False
        
        query = f"UPDATE test_cases SET {', '.join(updates)} WHERE id = ?"
        params.append(case_id)
        
        cursor.execute(query, params)
        success = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        return success
    
    def delete_test_case(self, case_id: int) -> bool:
        """删除测试用例及其相关脚本"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 删除与该用例相关的所有脚本
        cursor.execute("DELETE FROM test_scripts WHERE case_id = ?", (case_id,))
        
        # 删除测试用例
        cursor.execute("DELETE FROM test_cases WHERE id = ?", (case_id,))
        
        success = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        return success
    
    def update_test_script_steps(self, script_id: int, steps: List[Dict[str, Any]]) -> bool:
        """更新测试脚本步骤"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        steps_json = json.dumps(steps, ensure_ascii=False)
        cursor.execute(
            "UPDATE test_scripts SET steps = ? WHERE id = ?",
            (steps_json, script_id)
        )
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def update_test_script(self, script_id: int, name: str = None, case_id: int = None) -> bool:
        """更新测试脚本"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 构建更新语句和参数
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        
        if case_id is not None:
            updates.append("case_id = ?")
            params.append(case_id)
        
        if not updates:
            conn.close()
            return False
        
        query = f"UPDATE test_scripts SET {', '.join(updates)} WHERE id = ?"
        params.append(script_id)
        
        cursor.execute(query, params)
        success = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        return success
    
    def delete_test_script(self, script_id: int) -> bool:
        """删除测试脚本"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 删除测试脚本
        cursor.execute("DELETE FROM test_scripts WHERE id = ?", (script_id,))
        
        success = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        return success
    
    def get_all_test_scripts(self) -> List[Dict[str, Any]]:
        """获取所有测试脚本"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM test_scripts ORDER BY created_at DESC")
        rows = cursor.fetchall()
        
        scripts = []
        for row in rows:
            scripts.append({
                'id': row[0],
                'case_id': row[1],
                'name': row[2],
                'steps': json.loads(row[3]) if row[3] else [],
                'created_at': row[4]
            })
        
        conn.close()
        return scripts
