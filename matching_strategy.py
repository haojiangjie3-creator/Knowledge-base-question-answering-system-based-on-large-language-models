import numpy as np
from text2vec import SentenceModel
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from project_database import ProjectDatabase
from document_extraction_strategy import extract_features_from_document

from rank_bm25 import BM25Okapi
import jieba

model_path = r"F:\conda_envs\r1\text2vec-base-chinese"
model = SentenceModel(model_path)

# 提前下载到指定目录，避免每次从 HF 拉取
# MODEL_PATH = r"D:\models\BAAI\bge-large-zh-v1.5"

#print("正在加载 BGE 模型（可能首次需下载）...")
#model = SentenceTransformer(
#    'BAAI/bge-large-zh-v1.5',
#    cache_folder=MODEL_PATH  # 指定缓存路径
#)
#print("模型加载完成 ✅")

db = ProjectDatabase(
    host="localhost",
    user="root",
    password="123456",
    database="sts"
)

def bm25_similarity(demand_text, corpus_texts):
    """计算 BM25 相似度（稀疏匹配部分）"""
    # 对项目特征分词
    tokenized_corpus = [list(jieba.cut(text)) for text in corpus_texts]
    bm25 = BM25Okapi(tokenized_corpus)

    query_tokens = list(jieba.cut(demand_text))
    scores = bm25.get_scores(query_tokens)
    # 标准化 (0~1)
    scores = np.array(scores)
    if scores.max() > 0:
        scores = scores / scores.max()
    return scores

def print_matching_details(demand_feature, existing_features, similarities):
    """打印单个需求特征与所有已有特征的匹配详情"""
    print(f"\n需求特征: {demand_feature}")
    print("与已有特征的相似度:")
    for existing_feature, similarity in zip(existing_features, similarities):
        print(f"  - {existing_feature}: {similarity:.4f}")

def match_projects(demand_project, existing_projects):
    """匹配需求项目与已有项目"""
    print("\n=== 开始项目匹配 ===")
    print(f"需求项目特征数量: {len(demand_project['features'])}")

    # 1. 向量化需求项目的所有功能
    print("\n正在向量化需求项目特征...")
    demand_vectors = model.encode(demand_project["features"])
    # demand_vectors = model.encode(demand_project["features"], normalize_embeddings=True)

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
        # existing_vectors = model.encode(project["features"], normalize_embeddings=True)

        # --- 稠密匹配部分 ---
        # 3. 计算需求功能与已有功能的相似度矩阵
        similarity_matrix = cosine_similarity(demand_vectors, existing_vectors)
        dense_score = similarity_matrix.max(axis=1).mean()

        # 4. 对每个需求功能，找到其在已有功能中的最大相似度
        max_sim_per_demand_feature = similarity_matrix.max(axis=1)

        # 稀疏匹配
        demand_text = " ".join(demand_project["features"])
        project_texts = [" ".join(p["features"]) for p in existing_projects]
        bm25_scores = bm25_similarity(demand_text, project_texts)

        # 稀疏分数对应当前项目
        sparse_score = bm25_scores[existing_projects.index(project)]
        dense_score = max_sim_per_demand_feature.mean()

        # 混合
        alpha = 0.76
        hybrid_score = alpha * dense_score + (1 - alpha) * sparse_score
        project_scores[project["id"]] = hybrid_score

        # ========== 新增阈值过滤 ==========
        #THRESHOLD = 0.35  # 可调参数，建议 0.5 ~ 0.7
        # 小于阈值的视为“未匹配”，得分为 0
        #max_sim_per_demand_feature = np.where(max_sim_per_demand_feature >= THRESHOLD,
        #                                      max_sim_per_demand_feature,
        #                                      0.0)
        # =================================

        # 打印每个需求特征的匹配详情
        for i, (demand_feature, max_sim) in enumerate(zip(demand_project["features"], max_sim_per_demand_feature)):
            print(f"\n需求特征 {i+1}: {demand_feature}")
            print(f"最大相似度: {max_sim:.4f}")

            # 找出最相似的特征
            best_match_idx = similarity_matrix[i].argmax()
            best_match_feature = project["features"][best_match_idx]
            print(f"最匹配的已有特征: {best_match_feature}")

        # 5. 聚合得分（用平均值）
        #final_score = max_sim_per_demand_feature.mean()
        #project_scores[project["id"]] = final_score
        #print(f"\n项目 {project['id']} 的最终匹配得分: {final_score:.4f}")

        # === 新增：稀疏（BM25）得分 + 混合得分 ===
        dense_score = max_sim_per_demand_feature.mean()  # 稠密得分
        # 稀疏部分在混合检索逻辑里计算好，这里用 sparse_score 变量
        # hybrid_score = alpha * dense_score + (1 - alpha) * sparse_score

        print(f"\n项目 {project['id']} 的得分构成：")
        print(f"  稀疏得分 (BM25)：{sparse_score:.4f}")
        print(f"  稠密得分 (Embedding)：{dense_score:.4f}")
        print(f"  融合得分 (Hybrid)：{hybrid_score:.4f}")
        print("-" * 40)

    return project_scores

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

    demand_document_path = "F:\\1\\Software_trading_system\\demand_document\\我需要APP开发1.docx"
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

    project_scores = match_projects(demand_project, existing_projects)

    sorted_projects = sorted(project_scores.items(), key=lambda item: item[1], reverse=True)

    print("\n=== 最终匹配结果 ===")
    for project_id, score in sorted_projects:
        project_name = next((p["name"] for p in existing_projects if p["id"] == project_id), "未知项目")
        print(f"项目: {project_name} (ID: {project_id})")
        print(f"匹配得分: {score:.4f}")
        print("-" * 50)

def get_existing_projects():
    existing_projects = []
    projects = db.get_all_projects()
    for project in projects:
        features = db.get_project_features(project['project_name'])
        existing_projects.append({
            "id": project['project_id'],
            "name": project['project_name'],  # 必须保留 name 字段
            "features": features or []
        })
    return existing_projects

if __name__ == "__main__":
    main()
    # 调试输出前 15 个项目名称
    for i, p in enumerate(get_existing_projects()[:15]):
        print(f"{i + 1:02d}. {p['name']}")
