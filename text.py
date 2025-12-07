from matching_strategy_weights import match_projects, get_existing_projects
from document_extraction_strategy import extract_features_from_text

existing_projects = get_existing_projects()
print(f"已有项目数: {len(existing_projects)}")

# 取两个明显不同的需求
demand1 = "我需要一个能监测心率并报警的老人手环系统"
demand2 = "我需要一个可以识别儿童画并生成3D模型的应用"

# 提取特征
features1 = extract_features_from_text(demand1)
features2 = extract_features_from_text(demand2)

# 构造项目
proj1 = {'id': 'demand1', 'name': '心率监测系统', 'features': features1}
proj2 = {'id': 'demand2', 'name': '儿童画3D', 'features': features2}

# 分别匹配
scores1 = match_projects(proj1, existing_projects)
scores2 = match_projects(proj2, existing_projects)

# 打印 Top-3
print("\nTop-3 for demand1:")
print(sorted(scores1.items(), key=lambda x: x[1], reverse=True)[:3])
print("\nTop-3 for demand2:")
print(sorted(scores2.items(), key=lambda x: x[1], reverse=True)[:3])
