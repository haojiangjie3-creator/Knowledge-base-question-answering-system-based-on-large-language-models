import os
import json
import traceback
import time
from wxauto import WeChat
from project_database import ProjectDatabase
import matching_strategy
from document_extraction_strategy import extract_features_from_text
import requests  # 用于调用Ollama API
import random  # 用于随机选择表情

# 初始化数据库
db = ProjectDatabase(
    host="localhost",
    user="root",
    password="123456",
    database="sts"
)

# 配置项
DB_PATH = "F:\\1\\Software_trading_system\\db.json"
USER_PATH = "F:\\1\\Software_trading_system\\users.txt"
# 用于跟踪用户导入项目的状态
IMPORT_STATUS = {}  # 格式: {用户名: "等待描述"|"等待内容"}

# Ollama配置
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "deepseek-r1:1.7b"

# 表情符号增强亲和力
FRIENDLY_EMOJIS = ["😊", "🤗", "🌟", "💡", "✨", "👍", "👏", "🙌", "🌈", "🚀"]

# 系统功能说明
HELP_MESSAGE = """🌟 项目匹配助手使用指南 🌟

你好呀！我是你的项目匹配小助手~下面是我能帮你的：

1️⃣ 直接告诉我你的需求（比如："社区团购系统"），我会帮你找匹配的项目
2️⃣ 输入"项目导入"可以导入新项目到系统
3️⃣ 特殊命令：
   • 帮助：显示这个菜单
   • 项目列表：查看所有项目
   • 详情 [项目名]：查看项目详细信息

有什么问题随时问我哦！😊
"""

# 加载历史记录（确保初始化为字典）
DB = {}
try:
    if os.path.exists(DB_PATH):
        with open(DB_PATH, encoding="utf-8") as fp:
            DB = json.load(fp)
        # 确保数据结构正确（字典类型）
        if not isinstance(DB, dict):
            DB = {}
    print("历史记录加载完成")
except Exception as e:
    print(f"加载历史记录失败，重置为新字典：{e}")
    DB = {}

# 加载监听用户（带错误处理）
MONITOR_LIST = []
try:
    with open(USER_PATH, encoding="utf-8") as fp:
        MONITOR_LIST = [line.strip() for line in fp if line.strip()]
    print(f"已加载 {len(MONITOR_LIST)} 个监听用户")
except FileNotFoundError:
    print(f"警告：未找到用户列表 {USER_PATH}")
    MONITOR_LIST = ["文件传输助手"]  # 默认监听测试账号

# 初始化微信客户端
wx = WeChat()
for user in MONITOR_LIST:
    wx.AddListenChat(who=user)


def process_ai_reply(  ai_reply):
    """处理AI回复中的<think>标签"""
    if "</think>" in ai_reply:
        parts = ai_reply.split("</think>")
        if len(parts) >= 2:
            return parts[-1].strip()
    return ai_reply


def generate_ai_response(prompt, context=""):
    """使用Ollama的DeepSeek模型生成亲和回复"""
    try:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": f"{context}\n\n用户说: {prompt}\n\n请用友好、亲切、自然的语气回复:",
            "stream": False,
            "options": {
                "temperature": 0.7,
                "max_tokens": 500
            }
        }

        response = requests.post(OLLAMA_URL, json=payload)
        if response.status_code == 200:
            result = response.json()
            # 添加随机表情增强亲和力
            emoji = random.choice(FRIENDLY_EMOJIS)
            raw_reply = f"{emoji} {result['response'].strip()}"
            return process_ai_reply(raw_reply)
        else:
            print(f"Ollama API错误: {response.status_code} - {response.text}")
            return "🤔 我好像有点迷糊了，能再说一次吗？"
    except Exception as e:
        print(f"生成AI回复时出错: {str(e)}")
        return "⚠️ 系统暂时有点小问题，稍后再试哦~"


def generate_match_reply(demand: str, matches: list, projects: list) -> str:
    if not matches:
        # 使用AI生成更友好的无结果回复
        ai_reply = generate_ai_response(
            f"用户需求: {demand}，但没有找到匹配项目",
            "你是一个友好的项目匹配助手，现在用户的需求没有匹配的项目，请用温暖鼓励的语气回复用户，并给出改进建议"
        )
        return ai_reply

    # 准备匹配结果信息 - 确保包含匹配度数据
    match_info = []
    for idx, (pid, score) in enumerate(matches, 1):
        proj = next((p for p in projects if p['id'] == pid), None)
        if proj:
            features = "\n".join(f"   - {f}" for f in proj['features'][:3])
            # 确保匹配度信息被包含在输出中
            match_info.append(
                f"{idx}. {proj['name']}（匹配度：{score:.0%}）\n"
                f"主要功能：\n{features}"
            )

    # 使用AI生成更友好的结果回复
    match_text = "\n\n".join(match_info)

    # 改进提示词，确保AI包含所有匹配信息
    ai_reply = generate_ai_response(
        f"用户需求: {demand}\n\n匹配结果:\n{match_text}",
        "你是一个友好的项目匹配助手，请用自然、亲切的语言向用户介绍这些匹配结果，"
        "确保包含所有提供的项目名称、匹配度和主要功能信息，"
        "并建议用户可以通过'详情 项目名'查看详细信息"
    )

    return ai_reply


def save_chat_history(chat_user, user_msg, system_msg):
    """统一保存聊天记录的函数"""
    try:
        # 确保用户历史记录存在（初始化列表）
        if chat_user not in DB:
            DB[chat_user] = []
        # 添加用户消息和系统回复
        DB[chat_user].append({
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "user": user_msg,
            "system": system_msg
        })
        # 写入文件
        with open(DB_PATH, "w", encoding="utf-8") as fp:
            json.dump(DB, fp, ensure_ascii=False, indent=2)
        print(f"已保存 [{chat_user}] 的聊天记录")
    except Exception as e:
        print(f"保存聊天记录失败：{e}")


# 处理项目导入流程
def handle_project_import(chat_user, chat_win, message):
    global IMPORT_STATUS

    # 检查当前状态
    status = IMPORT_STATUS.get(chat_user)

    # 如果用户刚发送"项目导入"且没有处于导入流程中
    if message == "项目导入" and (not status or status not in ["等待描述", "等待内容"]):
        # 使用更友好的提示语
        reply = "🌟 太好了！请简单描述一下你的项目（例如：'一个电商平台管理系统'）"
        chat_win.SendMsg(reply)
        IMPORT_STATUS[chat_user] = "等待描述"
        # 保存记录
        save_chat_history(chat_user, message, reply)
        return True

    # 如果处于等待项目描述状态
    elif status == "等待描述":
        # 保存项目名称/描述
        project_desc = message
        # 使用更友好的提示语
        reply = "📝 很棒的项目想法！现在请发送项目的详细内容，我会帮你提取关键特征~"
        chat_win.SendMsg(reply)
        # 更新状态，同时保存临时信息
        IMPORT_STATUS[chat_user] = {
            "status": "等待内容",
            "description": project_desc
        }
        # 保存记录
        save_chat_history(chat_user, message, reply)
        return True

    # 如果处于等待项目内容状态
    elif status and isinstance(status, dict) and status["status"] == "等待内容":
        try:
            # 提取项目特征
            project_features = extract_features_from_text(message)

            # 保存到数据库（使用正确的参数名和顺序）
            project_id = db.add_project(
                project_name=status["description"],  # 项目名称
                document_path="user_input",  # 标记为用户输入（非文件）
                features=project_features  # 特征列表
            )

            if project_id:  # add_project成功时返回项目ID，失败返回None
                # 使用AI生成更友好的成功回复
                ai_reply = generate_ai_response(
                    f"用户成功导入了项目: {status['description']}",
                    "你是一个友好的助手，用户刚刚成功导入了项目，请用热情鼓励的语气祝贺用户，并表达期待帮助他匹配项目"
                )
                reply = ai_reply
            else:
                reply = "😔 项目导入好像出了点问题，再试一次好吗？"

        except Exception as e:
            print(f"项目导入数据库时出错: {str(e)}")
            # 使用更友好的错误提示
            reply = "😟 处理项目时出了点小状况，稍后再试试？"

        chat_win.SendMsg(reply)
        # 清除导入状态
        if chat_user in IMPORT_STATUS:
            del IMPORT_STATUS[chat_user]
        # 保存记录
        save_chat_history(chat_user, message, reply)
        return True

    return False


# 主消息处理循环
while True:
    try:
        listen_dict = wx.GetListenMessage()
        for chat_win, message_list in listen_dict.items():
            chat_user = chat_win.who
            messages = [msg.content for msg in message_list if msg.type == "friend"]
            if not messages:
                continue

            latest_msg = messages[-1].strip()
            print(f"\n收到 [{chat_user}] 消息：{latest_msg}")

            # 先检查是否是项目导入流程
            if handle_project_import(chat_user, chat_win, latest_msg):
                continue  # 项目导入相关消息已处理并保存

            # 处理帮助请求
            if latest_msg.lower() in ["你好", "帮助", "help", "？", "hi", "hello"]:
                # 添加随机欢迎语
                greetings = ["你好呀！", "嗨~", "很高兴见到你！", "欢迎回来！"]
                greeting = random.choice(greetings)
                reply = f"{greeting}{random.choice(FRIENDLY_EMOJIS)}\n\n{HELP_MESSAGE}"
                chat_win.SendMsg(reply)
                save_chat_history(chat_user, latest_msg, reply)
                continue

            # 处理项目列表请求
            if latest_msg == "项目列表":
                projects = db.get_all_projects()
                if projects:
                    # 使用更友好的列表格式
                    reply = "📋 这是我找到的所有项目：\n" + "\n".join(
                        f"{idx}. {p['project_name']}" for idx, p in enumerate(projects, 1)
                    )
                    reply += f"\n\n想了解哪个项目的详情？告诉我吧~ {random.choice(FRIENDLY_EMOJIS)}"
                else:
                    reply = f"📋 目前还没有项目呢，要不要导入一个？{random.choice(FRIENDLY_EMOJIS)}"
                chat_win.SendMsg(reply)
                save_chat_history(chat_user, latest_msg, reply)
                continue

            # 处理详情查询
            if latest_msg.startswith("详情 "):
                project_name = latest_msg[3:].strip()
                features = db.get_project_features(project_name)
                if features:
                    # 使用AI生成更友好的项目详情介绍
                    features_text = "\n".join(f"- {f}" for f in features)
                    ai_reply = generate_ai_response(
                        f"用户请求项目详情: {project_name}\n项目功能:\n{features_text}",
                        "你是一个友好的项目助手，请用生动有趣的语言向用户介绍这个项目的功能和特点"
                    )
                    reply = ai_reply
                else:
                    reply = f"🤔 没找到项目 '{project_name}'，确定名字没错吗？"
                chat_win.SendMsg(reply)
                save_chat_history(chat_user, latest_msg, reply)
                continue

            # 处理普通需求匹配
            features = extract_features_from_text(latest_msg)
            demand_project = {
                'id': 'demand',
                'name': '用户需求',
                'features': features
            }

            # 获取已有项目
            all_projects = db.get_all_projects()
            existing_projects = []
            for p in all_projects:
                feats = db.get_project_features(p['project_name'])
                existing_projects.append({
                    'id': p['project_id'],
                    'name': p['project_name'],
                    'features': feats or []
                })

            # 执行匹配
            matches = matching_strategy.match_projects(demand_project, existing_projects)
            sorted_matches = sorted(matches.items(), key=lambda x: x[1], reverse=True)[:3]  # 取Top3

            # 生成并发送回复
            reply = generate_match_reply(latest_msg, sorted_matches, existing_projects)
            chat_win.SendMsg(reply)
            # 保存记录
            save_chat_history(chat_user, latest_msg, reply)

    except Exception as e:
        error_msg = f"处理消息时出错：{str(e)}"
        print(error_msg)
        traceback.print_exc()
        try:
            # 使用更友好的错误提示
            emoji = random.choice(FRIENDLY_EMOJIS)
            chat_win.SendMsg(f"😅 哎呀，系统打了个小盹儿~{emoji}\n稍等一下，马上回来！")
            # 即使出错也保存错误记录
            save_chat_history(chat_user, latest_msg, "⚠️ 系统暂时不可用，请稍后再试")
        except:
            pass

    time.sleep(1)