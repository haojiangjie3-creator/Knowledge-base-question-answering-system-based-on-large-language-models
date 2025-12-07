from sentence_transformers import SentenceTransformer
from project_database import ProjectDatabase
from document_extraction_strategy import extract_features_from_document
import numpy as np
from text2vec import SentenceModel
from sklearn.metrics.pairwise import cosine_similarity

model_path = "F:\\conda_envs\\r1\\text2vec-base-chinese"
model = SentenceModel(model_path)

db = ProjectDatabase(
    host="localhost",
    user="root",
    password="123456",
    database="sts"
)

# ================== 关键词权重配置 ==================
CORE_TECH_KEYWORDS = {
    '智能', '自动', '识别', '分析', '学习', '推荐', '生成', '预测',
    '监控', '监测', '管理', '安全', '支付', '交易', '加密', '同步',
    '备份', '恢复', '集成', '算法', '模型', '深度', '数据', '实时'
}

BASIC_FUNCTION_KEYWORDS = {
    '提供', '支持', '实现', '记录', '查看', '设置', '配置', '保存',
    '导入', '导出', '编辑', '调整', '创建', '添加', '搜索', '筛选',
    '分类', '整理', '计算', '统计', '展示', '上传', '下载'
}

UX_KEYWORDS = {
    '界面', '教程', '帮助', '分享', '社区', '美化', '预览', '展示',
    '提醒', '通知', '友好', '简洁', '文档', '说明', '引导'
}

# ================== 软阈值配置 ==================
SOFT_THRESHOLD = 0.35  # 阈值：低于此值的相似度会被惩罚
PENALTY_FACTOR = 0.5  # 惩罚因子：低于阈值的相似度乘以这个系数


def precise_keyword_weights(features):
    """基于真实数据特征的精准权重分配"""
    weights = []

    for feature in features:
        # 统计各类关键词
        core_terms = [word for word in CORE_TECH_KEYWORDS if word in feature]
        basic_terms = [word for word in BASIC_FUNCTION_KEYWORDS if word in feature]
        ux_terms = [word for word in UX_KEYWORDS if word in feature]

        # 精准权重逻辑
        if len(core_terms) >= 3:
            weight = 0.9  # 多个核心技术词
        elif len(core_terms) == 2:
            weight = 0.8  # 两个核心技术词
        elif len(core_terms) == 1:
            if len(basic_terms) >= 1:
                weight = 0.7  # 技术+功能组合
            else:
                weight = 0.6  # 纯技术词
        elif len(basic_terms) >= 3:
            weight = 0.5  # 多个基础功能
        elif len(basic_terms) == 2:
            weight = 0.4  # 两个基础功能
        elif len(basic_terms) == 1:
            weight = 0.35  # 单个基础功能
        elif len(ux_terms) >= 1:
            weight = 0.3  # 用户体验相关
        else:
            weight = 0.4  # 默认权重

        weights.append(weight)

    # 归一化
    total = sum(weights)
    if total > 0:
        normalized_weights = [w / total for w in weights]
        print(f"特征权重分配: {normalized_weights}")
        return normalized_weights
    else:
        default_weights = [1 / len(features)] * len(features)
        print(f"使用默认权重: {default_weights}")
        return default_weights


def apply_soft_threshold(similarities, threshold=SOFT_THRESHOLD, penalty=PENALTY_FACTOR):
    """
    应用软阈值处理
    - 高于阈值的相似度：完全保留
    - 低于阈值的相似度：按惩罚因子衰减
    """
    adjusted_similarities = np.where(
        similarities >= threshold,
        similarities,  # 高于阈值：完全保留
        similarities * penalty  # 低于阈值：按惩罚因子衰减
    )

    # 打印调整详情
    original_mean = similarities.mean()
    adjusted_mean = adjusted_similarities.mean()
    print(f"软阈值处理: {threshold} | 惩罚因子: {penalty}")
    print(f"相似度均值: {original_mean:.4f} → {adjusted_mean:.4f}")

    return adjusted_similarities


def print_matching_details(demand_feature, existing_features, similarities, adjusted_similarities=None):
    """打印匹配详情，包含软阈值处理前后的对比"""
    print(f"\n需求特征: {demand_feature}")
    print("与已有特征的相似度:")
    for i, (existing_feature, similarity) in enumerate(zip(existing_features, similarities)):
        if adjusted_similarities is not None:
            adjusted = adjusted_similarities[i]
            marker = "⚠️" if similarity < SOFT_THRESHOLD else "✅"
            print(f"  {marker} {existing_feature}: {similarity:.4f} → {adjusted:.4f}")
        else:
            print(f"  - {existing_feature}: {similarity:.4f}")


def match_projects(demand_project, existing_projects):
    """匹配需求项目与已有项目（使用软阈值）"""
    print("\n=== 开始项目匹配（软阈值方案） ===")
    print(f"软阈值配置: 阈值={SOFT_THRESHOLD}, 惩罚因子={PENALTY_FACTOR}")
    print(f"需求项目特征数量: {len(demand_project['features'])}")

    # 1. 向量化需求项目的所有功能
    print("\n正在向量化需求项目特征...")
    demand_vectors = model.encode(demand_project["features"])

    # 计算特征权重
    weights = precise_keyword_weights(demand_project["features"])

    project_scores = {}
    for project in existing_projects:
        if not project["features"]:
            print(f"\n项目 {project['id']} 没有特征，跳过")
            project_scores[project["id"]] = 0
            continue

        print(f"\n正在匹配项目 {project['id']}")
        print(f"项目特征数量: {len(project['features'])}")

        # 2. 向量化当前已有项目的所有功能
        existing_vectors = model.encode(project["features"])

        # 3. 计算需求功能与已有功能的相似度矩阵
        similarity_matrix = cosine_similarity(demand_vectors, existing_vectors)

        # 4. 对每个需求功能，找到其在已有功能中的最大相似度
        max_sim_per_demand_feature = similarity_matrix.max(axis=1)

        # 🔥 核心修改：应用软阈值处理
        adjusted_similarities = apply_soft_threshold(max_sim_per_demand_feature)

        # 打印匹配详情（包含调整前后对比）
        for i, (demand_feature, original_sim, adjusted_sim) in enumerate(
                zip(demand_project["features"], max_sim_per_demand_feature, adjusted_similarities)
        ):
            print(f"\n需求特征 {i + 1}: {demand_feature}")
            print(f"原始最大相似度: {original_sim:.4f}")
            print(f"调整后相似度: {adjusted_sim:.4f}")

            if original_sim < SOFT_THRESHOLD:
                print("⚠️  低于阈值，已应用惩罚")

            # 找出最相似的特征
            best_match_idx = similarity_matrix[i].argmax()
            best_match_feature = project["features"][best_match_idx]
            print(f"最匹配的已有特征: {best_match_feature}")

        # 使用调整后的相似度计算加权平均
        if sum(weights) > 0:
            final_score = np.average(adjusted_similarities, weights=weights)
        else:
            final_score = adjusted_similarities.mean()

        project_scores[project["id"]] = final_score
        print(f"\n项目 {project['id']} 的最终匹配得分: {final_score:.4f}")

    return project_scores


def evaluate_soft_threshold_effect(demand_project, existing_projects_sample):
    """评估软阈值效果"""
    print("\n" + "=" * 60)
    print("软阈值效果评估")
    print("=" * 60)

    demand_vectors = model.encode(demand_project["features"])
    weights = precise_keyword_weights(demand_project["features"])

    for project in existing_projects_sample[:3]:  # 评估前3个项目
        print(f"\n评估项目: {project['id']}")

        existing_vectors = model.encode(project["features"])
        similarity_matrix = cosine_similarity(demand_vectors, existing_vectors)
        max_sim_per_demand_feature = similarity_matrix.max(axis=1)

        # 计算三种方案的得分
        # 1. 无阈值
        no_threshold_score = np.average(max_sim_per_demand_feature, weights=weights)

        # 2. 硬阈值（原来的方案）
        hard_threshold_sim = np.where(max_sim_per_demand_feature >= 0.5, max_sim_per_demand_feature, 0.0)
        hard_threshold_score = np.average(hard_threshold_sim, weights=weights)

        # 3. 软阈值（新方案）
        soft_threshold_sim = apply_soft_threshold(max_sim_per_demand_feature)
        soft_threshold_score = np.average(soft_threshold_sim, weights=weights)

        print(f"  无阈值得分: {no_threshold_score:.4f}")
        print(f"  硬阈值得分: {hard_threshold_score:.4f}")
        print(f"  软阈值得分: {soft_threshold_score:.4f}")

        # 统计低于阈值的特征数量
        low_sim_count = (max_sim_per_demand_feature < SOFT_THRESHOLD).sum()
        total_count = len(max_sim_per_demand_feature)
        print(f"  低于阈值特征: {low_sim_count}/{total_count} ({low_sim_count / total_count * 100:.1f}%)")


def main():
    print("正在获取现有项目...")
    existing_projects = []
    projects = db.get_all_projects()
    for project in projects:
        features = db.get_project_features(project['project_name'])
        if features:
            existing_projects.append({
                "id": project['project_id'],
                "name": project['project_name'],
                "features": features
            })

    print(f"成功获取 {len(existing_projects)} 个现有项目")

    demand_document_path = "E:\\project\\Software_trading_system\\demand_document\\我需要APP开发1.docx"
    print(f"\n正在处理需求文档: {demand_document_path}")

    features = extract_features_from_document(demand_document_path)
    if not features:
        raise Exception("需求项目特征提取失败")

    project_name = f"demand_{demand_document_path.split('/')[-1].split('.')[0]}"
    project_id = db.add_project(project_name, demand_document_path, features)

    if not project_id:
        raise Exception("需求项目处理失败")

    demand_project = {
        "id": project_id,
        "name": project_name,
        "features": features
    }

    # 可选：评估软阈值效果
    if len(existing_projects) >= 3:
        evaluate_soft_threshold_effect(demand_project, existing_projects[:3])

    # 执行匹配
    project_scores = match_projects(demand_project, existing_projects)

    sorted_projects = sorted(project_scores.items(), key=lambda item: item[1], reverse=True)

    print("\n=== 最终匹配结果（软阈值方案） ===")
    for rank, (project_id, score) in enumerate(sorted_projects[:10], 1):
        project_name = next((p["name"] for p in existing_projects if p["id"] == project_id), "未知项目")
        print(f"排名 {rank}: {project_name} (ID: {project_id})")
        print(f"匹配得分: {score:.4f}")
        print("-" * 50)


def get_existing_projects():
    existing_projects = []
    projects = db.get_all_projects()
    for project in projects:
        features = db.get_project_features(project['project_name'])
        existing_projects.append({
            "id": project['project_id'],
            "name": project['project_name'],
            "features": features or []
        })
    return existing_projects


if __name__ == "__main__":
    main()