Software_trading_system/
│
├── app.py                        # 主程序入口，负责后端服务的启动与路由
├── project_database.py           # 数据库操作相关代码，封装了对项目数据库的增删查改
├── matching_strategy.py          # 项目需求与现有项目的匹配算法实现
├── document_extraction_strategy.py # 文档内容提取与处理策略
├── readme.txt                    # 项目说明文档（本文件）
│
├── database/
│   └── sts.sql                   # 数据库结构及初始化SQL脚本
│
├── uploads/                      # 上传的需求文档存放目录
│   └── *.docx                    # 用户上传的需求文档
│
├── exist_document/              (测试用) # 已有项目文档存放目录
│   └── *.docx                    # 已有项目的相关文档
│
├── demand_document/              （测试用）# 需求文档样例或历史需求文档
│   └── *.docx                    # 需求文档样例
│
├── frontend/                     # 前端页面相关文件
│   ├── index.html                # 前端主页面
│   ├── main.js                   # 前端逻辑脚本
│   └── style.css                 # 前端样式表
│
└── __pycache__/                  # Python缓存文件夹（可忽略）


matching_strategy.py中模型路径需要修改，自行下载text2vec-base-chinese模型，更换路径即可
各个数据库连接的密码需要修改
调用的是kimi的模型，api有请求上限，一分钟内请求不能多于三次，导入新项目需要请求两次，演示的时候记得控制一下请求量，后续要求响应速度的话升级pro套餐可以解决。
直接运行app.py即可



