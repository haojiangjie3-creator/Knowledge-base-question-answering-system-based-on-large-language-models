import pandas as pd
import time  # 用于限流等待
from document_extraction_strategy import extract_features_from_text
import matching_strategy  # 确保能导入 get_existing_projects 和 match_projects

# ================== 配置区 ==================
EXCEL_FILE = r"E:\xxf\供需匹配\用户需求汇总.xlsx"
SHEET_NAME = "Sheet1"
DEMAND_COLUMN = "用户需求"
TOTAL_TEST_CASES = 100
TOP_K = 1  # ← 可灵活调整 Top-K


def evaluate_topk_accuracy():
    print(f"🚀 开始评估匹配系统 Top-{TOP_K} 准确率...")

    # 使用 matching_strategy 统一加载项目
    try:
        from matching_strategy import get_existing_projects, match_projects
    except ImportError as e:
        raise ImportError("请确保 matching_strategy.py 中有 get_existing_projects() 和 match_projects() 函数") from e

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

    # 遍历前 TOTAL_TEST_CASES 条需求
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
                "top3_names": "",
                "expected_name": f"项目{idx+1}",
                "hit": 0
            })
            continue

        try:
            # ✅ 提取特征（调用你的 LLM 提取函数）
            print(f"🔍 第 {row_idx} 行: 正在提取特征...")
            features = extract_features_from_text(demand_text)

            # ✅ 限流：休眠 20 秒（假设 RPM=3）
            print(f"⏳ 第 {row_idx} 行: 请求完成，休眠 20 秒以避免限流...")
            time.sleep(10)

            # 检查是否提取到特征
            if not features:
                print(f"🟡 第 {row_idx} 行: 特征提取为空")
                results.append({
                    "row": row_idx,
                    "status": "no_features",
                    "top1_name": None,
                    "top3_names": "",
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

            # 执行匹配（返回所有项目得分）
            matches = match_projects(demand_project, existing_projects)

            # 稳定排序：按得分降序，id 升序（防止顺序漂移）
            sorted_matches = sorted(matches.items(), key=lambda x: (-x[1], x[0]))

            # 获取 Top-K 项目 ID
            topk_ids = [pid for pid, _ in sorted_matches[:TOP_K]]

            # 将 ID 转为项目名称
            topk_names = []
            for pid in topk_ids:
                proj = next((p for p in existing_projects if p['id'] == pid), None)
                if proj:
                    topk_names.append(proj['name'])

            # 期望的项目名称（根据你的设定：第 i 行对应“项目i”）
            expected_project_name = f"项目{idx + 1}"

            # 判断是否命中：期望项目是否在 Top-K 中
            is_hit = expected_project_name in topk_names
            hit = 1 if is_hit else 0
            correct_count += hit

            # 记录结果
            results.append({
                "row": row_idx,
                "status": "success",
                "top1_name": topk_names[0] if topk_names else None,
                "top3_names": "; ".join(topk_names),
                "expected_name": expected_project_name,
                "hit": hit
            })

            # 输出结果
            topk_str = "; ".join(topk_names) if topk_names else "无结果"
            status_icon = "✅ 正确" if is_hit else "❌ 错误"
            print(f"✅ 第{row_idx}行: Top-{TOP_K} [{topk_str}] | 期望 [{expected_project_name}] | {status_icon}")

        except Exception as e:
            # 捕获所有异常（包括 API 429、网络错误等）
            print(f"❌ 第{row_idx}行 处理失败: {str(e)}")
            results.append({
                "row": row_idx,
                "status": "error",
                "top1_name": None,
                "top3_names": "",
                "expected_name": f"项目{idx+1}",
                "hit": 0
            })
            continue

    # === 最终统计 ===
    accuracy = correct_count / TOTAL_TEST_CASES
    elapsed = time.time() - start_time
    print("\n" + "="*60)
    print(f"📊 最终评估结果（Top-{TOP_K} 准确率）")
    print("="*60)
    print(f"共测试: {TOTAL_TEST_CASES} 个需求")
    print(f"命中数: {correct_count}")
    print(f"Top-{TOP_K} 准确率: {accuracy:.4f} ({correct_count}/{TOTAL_TEST_CASES})")
    print(f"总耗时: {int(elapsed // 60)} 分钟 {int(elapsed % 60)} 秒")
    print("="*60)

    # 保存详细结果
    output_file = f'top{TOP_K}_evaluation_results.csv'
    pd.DataFrame(results).to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"📄 详细结果已保存至 '{output_file}'")

    return accuracy


# ============ 主程序 ============
if __name__ == "__main__":
    evaluate_topk_accuracy()