import warnings
import os
# 忽略所有警告
warnings.filterwarnings("ignore")
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import logging
logging.getLogger('transformers').setLevel(logging.ERROR)

# 然后再导入其他库
import matching_strategy
import pandas as pd

import time  # 用于限流等待
from document_extraction_strategy import extract_features_from_text
import matching_strategy  # 确保能导入 get_existing_projects 和 match_projects

# ================== 配置区 ==================
EXCEL_FILE = r"E:\xxf\供需匹配\用户需求汇总.xlsx"
SHEET_NAME = "Sheet1"
DEMAND_COLUMN = "用户需求"
TOTAL_TEST_CASES = 100


def evaluate_top1_accuracy():
    print("🚀 开始评估匹配系统 Top-1 准确率...")

    # 使用 matching_strategy 统一加载项目
    try:
        from matching_strategy import get_existing_projects, match_projects
    except ImportError as e:
        raise ImportError("请确保 matching_strategy.py 中有 get_existing_projects() 函数") from e

    existing_projects = get_existing_projects()
    if not existing_projects:
        raise ValueError("❌ 未能加载任何已有项目")

    print(f"✅ 共加载 {len(existing_projects)} 个已有项目\n")

    # 读取 Excel
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_NAME)
    except Exception as e:
        raise FileNotFoundError(f"无法读取 Excel 文件: {e}")

    correct_count = 0
    results = []

    # 记录开始时间
    start_time = time.time()

    # 遍历前 100 条需求
    for idx in range(min(TOTAL_TEST_CASES, len(df))):
        row_idx = idx + 1
        demand_text = str(df.iloc[idx][DEMAND_COLUMN]).strip()

        # 跳过空需求
        if not demand_text or pd.isna(demand_text):
            print(f"🟡 第 {row_idx} 行: 需求文本为空，跳过")
            results.append({
                "row": row_idx,
                "status": "empty",
                "top1_name": None,
                "expected_name": f"项目{idx+11}",
                "hit": 0
            })
            continue

        try:
            # ✅ 提取特征（调用你的 LLM 提取函数）
            print(f"🔍 第 {row_idx} 行: 正在提取特征...")
            features = extract_features_from_text(demand_text)

            # ✅ 关键：成功调用后，休眠 20 秒，确保不超过 RPM=3
            print(f"⏳ 第 {row_idx} 行: 请求完成，休眠 20 秒以避免限流...")
            time.sleep(20)

            # 检查是否提取到特征
            if not features:
                print(f"🟡 第 {row_idx} 行: 特征提取为空")
                results.append({
                    "row": row_idx,
                    "status": "no_features",
                    "top1_name": None,
                    "expected_name": f"项目{idx+1}",
                    "hit": 0
                })
                continue

            # 构造需求项目
            demand_project = {
                'id': 'demand',
                'name': f'用户需求_{row_idx}',
                'features': features
            }

            # 执行匹配
            matches = match_projects(demand_project, existing_projects)

            # 稳定排序：按得分降序，id 升序（防止顺序漂移）
            sorted_matches = sorted(matches.items(), key=lambda x: (-x[1], x[0]))
            top1_id = sorted_matches[0][0] if sorted_matches else None

            # 根据 top1_id 查找项目名称
            top1_project = next((p for p in existing_projects if p['id'] == top1_id), None)
            top1_name = top1_project['name'] if top1_project else None

            # 期望的项目名称
            expected_project_name = f"项目{idx + 1}"

            # 判断是否命中
            is_hit = (top1_name == expected_project_name)
            hit = 1 if is_hit else 0
            correct_count += hit

            # 记录结果
            results.append({
                "row": row_idx,
                "status": "success",
                "top1_name": top1_name,
                "expected_name": expected_project_name,
                "hit": hit
            })

            # 输出结果
            print(f"✅ 第{row_idx}行: 推荐 [{top1_name}] | 期望 [{expected_project_name}] | {'✅ 正确' if is_hit else '❌ 错误'}")

        except Exception as e:
            # 捕获所有异常（包括 API 429、网络错误等）
            print(f"❌ 第{row_idx}行 处理失败: {str(e)}")
            results.append({
                "row": row_idx,
                "status": "error",
                "top1_name": None,
                "expected_name": f"项目{idx+1}",
                "hit": 0
            })
            continue

    # === 最终统计 ===
    accuracy = correct_count / TOTAL_TEST_CASES
    elapsed = time.time() - start_time
    print("\n" + "="*60)
    print("📊 最终评估结果（Top-1 准确率）")
    print("="*60)
    print(f"共测试: {TOTAL_TEST_CASES} 个需求")
    print(f"正确数: {correct_count}")
    print(f"Top-1 准确率: {accuracy:.4f} ({correct_count}/100)")
    print(f"总耗时: {elapsed // 60:.0f} 分钟 {elapsed % 60:.0f} 秒")
    print("="*60)

    # 保存详细结果
    pd.DataFrame(results).to_csv('top1_evaluation_results.csv', index=False, encoding='utf-8-sig')
    print("📄 详细结果已保存至 'top1_evaluation_results_bge.csv'")

    return accuracy


# ============ 主程序 ============
if __name__ == "__main__":
    evaluate_top1_accuracy()