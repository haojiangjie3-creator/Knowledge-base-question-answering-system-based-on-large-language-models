from typing import *
 
import os
import json
from pathlib import Path
 
from openai import OpenAI

from tenacity import retry, stop_after_attempt

client = OpenAI(
    base_url="https://api.moonshot.cn/v1",
    api_key="sk-GxbZYybCAKP1XwGpbNsFL4WhORrYHmyRBIiTVILon4gHb4GM",
)
 
 
def upload_files(files: List[str]) -> List[Dict[str, Any]]:
    """
    upload_files 会将传入的文件（路径）全部通过文件上传接口 '/v1/files' 上传，并获取上传后的
    文件内容生成文件 messages。每个文件会是一个独立的 message，这些 message 的 role 均为
    system，Kimi 大模型会正确识别这些 system messages 中的文件内容。
 
    :param files: 一个包含要上传文件的路径的列表，路径可以是绝对路径也可以是相对路径，请使用字符串
        的形式传递文件路径。
    :return: 一个包含了文件内容的 messages 列表，请将这些 messages 加入到 Context 中，
        即请求 `/v1/chat/completions` 接口时的 messages 参数中。
    """
    messages = []
    print(f"开始上传文件: {files}")
 

    for file in files:
        try:
            print(f"正在上传文件: {file}")
            file_object = client.files.create(file=Path(file), purpose="file-extract")
            print(f"文件上传成功，ID: {file_object.id}")
            
            print("正在获取文件内容...")
            file_content = client.files.content(file_id=file_object.id).text
            print(f"文件内容获取成功，长度: {len(file_content)}")
            
            messages.append({
                "role": "system",
                "content": file_content,
            })
        except Exception as e:
            print(f"处理文件 {file} 时出错: {e}")
            raise
 
    return messages
 
@retry(stop=stop_after_attempt(3))
def extract_features_from_document(document_path: str) -> List[str]:
    """
    从需求文档中提取功能点，包括明确提到的功能和隐含的功能。
    
    :param document_path: 需求文档的路径
    :return: 功能点列表
    """
    print(f"开始处理文档: {document_path}")
    
    try:
        file_messages = upload_files(files=[document_path])
        print("文件上传完成，开始提取特征...")
        
        messages = [
            *file_messages,
            {
                "role": "system",
                "content": "你是一个专业的需求分析师。请仔细分析这个需求文档，并提取出所有功能点。"
                          "包括：\n"
                          "1. 文档中明确提到的功能\n"
                          "2. 文档中隐含的、但为了实现主要功能所必需的功能\n"
                          "3. 每个功能点都应该简洁明了，使用动词+名词的形式描述\n"
                          "请直接返回功能点列表，每行一个功能点，不要包含任何其他格式或说明。"
            },
            {
                "role": "user",
                "content": "请提取这个需求文档中的所有功能点，包括明确的和隐含的。"
            }
        ]
        
        print("正在调用API提取特征...")
        completion = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messages,
        )
        print("API调用完成，正在处理结果...")
        

        content = completion.choices[0].message.content.strip()
        
        # 按行分割、清理特征
        features = []
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith(('```', 'json', '功能点', '列表', '包括', '明确', '隐含')):
                # 移除可能的序号和特殊字符
                line = line.lstrip('0123456789.- ')
                line = line.strip('"\'[]{}')
                if line:
                    features.append(line)
        
        print(f"成功提取特征，数量: {len(features)}")
        print("提取的特征:")
        for i, feature in enumerate(features, 1):
            print(f"{i}. {feature}")
            
        return features
    except Exception as e:
        print(f"提取特征时出错: {e}")
        raise

def extract_features_from_text(text: str) -> List[str]:
    """
    从自然语言描述中提取功能点，包括明确和隐含功能。
    :param text: 项目描述文本
    :return: 功能点列表
    """
    print(f"开始处理文本: {text[:30]}...")
    try:
        messages = [
            {
                "role": "system",
                "content": "你是一个专业的需求分析师。请仔细分析下面的项目描述，并提取出所有功能点。"
                           "包括：\n"
                           "1. 描述中明确提到的功能\n"
                           "2. 描述中隐含的、但为了实现主要功能所必需的功能\n"
                           "3. 每个功能点都应该简洁明了，使用动词+名词的形式描述\n"
                           "请直接返回功能点列表，每行一个功能点，不要包含任何其他格式或说明。"
            },
            {
                "role": "user",
                "content": text
            }
        ]
        print("正在调用API提取特征...")
        completion = client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=messages,
        )
        print("API调用完成，正在处理结果...")
        content = completion.choices[0].message.content.strip()
        features = []
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith(('```', 'json', '功能点', '列表', '包括', '明确', '隐含')):
                line = line.lstrip('0123456789.- ')
                line = line.strip('"\'[]{}')
                if line:
                    features.append(line)
        print(f"成功提取特征，数量: {len(features)}")
        print("提取的特征:")
        for i, feature in enumerate(features, 1):
            print(f"{i}. {feature}")
        return features
    except Exception as e:
        print(f"提取特征时出错: {e}")
        raise

def main():
    document_path = r"/exist_document/已有项目2.docx"  # 替换为实际的需求文档路径
    try:
        features = extract_features_from_document(document_path)
        print("提取的功能点：")
        for feature in features:
            print(f"- {feature}")
    except Exception as e:
        print(f"处理文档时出错: {e}")
 
 
if __name__ == '__main__':
    main()
 