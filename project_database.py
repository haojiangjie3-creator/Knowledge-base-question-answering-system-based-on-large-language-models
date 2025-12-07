import mysql.connector
from mysql.connector import Error
from typing import List, Dict, Optional
from pathlib import Path
from document_extraction_strategy import extract_features_from_document

class ProjectDatabase:
    def save_chat_record(self, user_id: str, user_input: str, bot_response: str) -> bool:
        """保存聊天记录到数据库"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO chat_records 
                (user_id, user_input, bot_response, timestamp) 
                VALUES (%s, %s, %s, NOW())
            """, (user_id, user_input, bot_response))
            self.connection.commit()
            return True
        except Error as e:
            print(f"保存聊天记录时出错: {e}")
            self.connection.rollback()
            return False

    def __init__(self, host: str = "localhost", user: str = "root", password: str = "123456", database: str = "project_features"):
        """
        初始化数据库连接
        :param host: 数据库主机地址
        :param user: 数据库用户名
        :param password: 数据库密码
        :param database: 数据库名称
        """
        self.connection = None
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.connect()
        # self.create_tables()

    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password
            )
            if self.connection.is_connected():
                cursor = self.connection.cursor()
                # 创建数据库（如果不存在）
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
                cursor.execute(f"USE {self.database}")
                print("成功连接到MySQL数据库")
        except Error as e:
            print(f"连接数据库时出错: {e}")

    def clean_features(self, features: List[str]) -> List[str]:
        cleaned_features = []
        
        for feature in features:
            feature = feature.strip()
            
            # 跳过空行
            if not feature:
                continue
            
            # 清理特征文本，但保留引号
            feature = feature.strip().rstrip(',')
            
            # 跳过特殊标记和说明文本
            if any(skip in feature for skip in [
                "```",
                "json",
                "功能点",
                "列表",
                "包括",
                "明确",
                "隐含"
            ]):
                continue
            
            # 确保特征有引号
            if not (feature.startswith('"') and feature.endswith('"')):
                feature = f'"{feature}"'
            
            # 只保留有效的特征
            if len(feature) > 3 and not feature.startswith("~$"):
                cleaned_features.append(feature)
        
        return cleaned_features

    def add_project(self, project_name: str, document_path: str, features: List[str]) -> Optional[int]:
        try:
            cursor = self.connection.cursor()
            
            # 清理特征列表
            cleaned_features = self.clean_features(features)
            print(f"清理后的特征数量: {len(cleaned_features)}")
            
            # 插入项目信息
            cursor.execute("""
                INSERT INTO projects (project_name, document_path)
                VALUES (%s, %s)
            """, (project_name, document_path))
            
            project_id = cursor.lastrowid
            
            # 插入特征信息
            for feature in cleaned_features:
                cursor.execute("""
                    INSERT INTO features (project_id, feature_text, feature_type)
                    VALUES (%s, %s, %s)
                """, (project_id, feature, 'explicit'))
            
            self.connection.commit()
            return project_id
        except Error as e:
            print(f"添加项目时出错: {e}")
            self.connection.rollback()
            return None

    def get_project_features(self, project_name: str) -> Optional[List[str]]:
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT f.feature_text
                FROM features f
                JOIN projects p ON f.project_id = p.project_id
                WHERE p.project_name = %s
            """, (project_name,))
            
            features = [row[0] for row in cursor.fetchall()]
            return features
        except Error as e:
            print(f"获取项目特征时出错: {e}")
            return None

    def get_all_projects(self) -> List[Dict]:
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT p.project_id, p.project_name, p.document_path, 
                       COUNT(f.feature_id) as feature_count
                FROM projects p
                LEFT JOIN features f ON p.project_id = f.project_id
                GROUP BY p.project_id
            """)
            
            return cursor.fetchall()
        except Error as e:
            print(f"获取项目列表时出错: {e}")
            return []

    def update_project_features(self, project_name: str, features: List[str]) -> bool:
        try:
            cursor = self.connection.cursor()
            
            # 获取项目ID
            cursor.execute("SELECT project_id FROM projects WHERE project_name = %s", (project_name,))
            result = cursor.fetchone()
            if not result:
                return False
            
            project_id = result[0]
            
            # 删除旧特征
            cursor.execute("DELETE FROM features WHERE project_id = %s", (project_id,))
            
            # 插入新特征
            for feature in features:
                cursor.execute("""
                    INSERT INTO features (project_id, feature_text, feature_type)
                    VALUES (%s, %s, %s)
                """, (project_id, feature, 'explicit'))
            
            self.connection.commit()
            return True
        except Error as e:
            print(f"更新项目特征时出错: {e}")
            self.connection.rollback()
            return False

    def import_existing_projects(self, project_dir: str):
        print(f"开始扫描目录: {project_dir}")
        for file_path in Path(project_dir).glob("*.docx"):
            # 排除临时文件（以~$开头的文件）
            if file_path.name.startswith("~$"):
                print(f"跳过临时文件: {file_path}")
                continue
                
            print(f"正在处理文件: {file_path}")
            project_name = file_path.stem
            print(f"提取特征中...")
            try:
                features = extract_features_from_document(str(file_path))
                print(f"成功提取特征，数量: {len(features)}")
                print("正在保存到数据库...")
                self.add_project(project_name, str(file_path), features)
                print(f"项目 {project_name} 导入完成")
            except Exception as e:
                print(f"处理文件 {file_path} 时出错: {e}")

    def close(self):
        """关闭数据库连接"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("数据库连接已关闭")

def main():
    db = ProjectDatabase(
        host="localhost",
        user="root",
        password="123456",
        database="sts"
    )
    

    # 导入已有项目
    project_dir = r"/exist_document"
    print(f"\n开始导入项目，项目目录: {project_dir}")
    db.import_existing_projects(project_dir)
    
    # 获取所有项目信息
    projects = db.get_all_projects()
    print("\n已导入的项目：")
    for project in projects:
        print(f"\n项目：{project['project_name']}")
        print(f"特征数量：{project['feature_count']}")
        
        # 获取项目特征
        features = db.get_project_features(project['project_name'])
        if features:
            print("特征列表：")
            for feature in features:
                print(f"  - {feature}")
    
    db.close()

if __name__ == "__main__":
    main() 