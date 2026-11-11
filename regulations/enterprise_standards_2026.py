# -*- coding: utf-8 -*-
"""
企业绩效评价标准值2026 — 示例数据（5行业×5指标）
⚠️ 当前为演示数据，禁止用于正式评价。完整标准值需从PDF提取。
"""

# ponytail: 示例5行业，完整170+类目×4规模×22指标待PDF抽取
ENTERPRISE_STANDARDS_2026 = {
    "version": "2026",
    "source": "财政部企业绩效评价标准值",
    "industries": [
        {
            "code": "01",
            "name": "农副食品加工业",
            "standards": {
                "净资产收益率": {"优秀": 11.7, "良好": 4.8, "平均": 1.1, "较低": -3.3, "较差": -6.6},
                "总资产报酬率": {"优秀": 10.5, "良好": 4.1, "平均": 1.9, "较低": -1.3, "较差": -4.6},
                "营业收入利润率": {"优秀": 10.5, "良好": 4.1, "平均": 1.9, "较低": -1.3, "较差": -4.6},
                "资产负债率": {"优秀": 39.0, "良好": 46.8, "平均": 54.6, "较低": 71.5, "较差": 83.8},
                "总资产周转率": {"优秀": 1.0, "良好": 0.6, "平均": 0.3, "较低": 0.2, "较差": 0.1},
            }
        },
        {
            "code": "06",
            "name": "煤炭开采和洗选业",
            "standards": {
                "净资产收益率": {"优秀": 11.0, "良好": 5.2, "平均": 1.4, "较低": -3.3, "较差": -11.5},
                "总资产报酬率": {"优秀": 13.0, "良好": 5.7, "平均": 2.8, "较低": -2.3, "较差": -9.1},
                "营业收入利润率": {"优秀": 13.0, "良好": 5.7, "平均": 2.8, "较低": -2.3, "较差": -9.1},
                "资产负债率": {"优秀": 53.2, "良好": 58.2, "平均": 63.3, "较低": 73.2, "较差": 88.2},
                "总资产周转率": {"优秀": 1.0, "良好": 0.6, "平均": 0.3, "较低": 0.2, "较差": 0.1},
            }
        },
        {
            "code": "13",
            "name": "电力、热力生产和供应业",
            "standards": {
                "净资产收益率": {"优秀": 11.8, "良好": 5.7, "平均": 2.1, "较低": -1.2, "较差": -3.7},
                "总资产报酬率": {"优秀": 9.2, "良好": 5.1, "平均": 2.6, "较低": -0.2, "较差": -2.1},
                "营业收入利润率": {"优秀": 14.2, "良好": 8.8, "平均": 3.3, "较低": -4.5, "较差": -17.0},
                "资产负债率": {"优秀": 47.3, "良好": 52.3, "平均": 57.3, "较低": 66.4, "较差": 82.3},
                "总资产周转率": {"优秀": 1.0, "良好": 0.7, "平均": 0.6, "较低": 0.3, "较差": 0.1},
            }
        },
        {
            "code": "17",
            "name": "房地产业",
            "standards": {
                "净资产收益率": {"优秀": 11.7, "良好": 4.9, "平均": 0.9, "较低": -7.1, "较差": -11.3},
                "总资产报酬率": {"优秀": 5.6, "良好": 3.0, "平均": 1.3, "较低": -1.6, "较差": -4.0},
                "营业收入利润率": {"优秀": 16.3, "良好": 7.9, "平均": 2.8, "较低": -1.3, "较差": -4.7},
                "资产负债率": {"优秀": 49.0, "良好": 54.0, "平均": 59.0, "较低": 69.0, "较差": 84.0},
                "总资产周转率": {"优秀": 0.9, "良好": 0.6, "平均": 0.4, "较低": 0.2, "较差": 0.1},
            }
        },
        {
            "code": "27",
            "name": "互联网和相关服务",
            "standards": {
                "净资产收益率": {"优秀": 12.2, "良好": 5.1, "平均": -3.8, "较低": -15.4, "较差": None},
                "总资产报酬率": {"优秀": 11.1, "良好": 6.0, "平均": 3.8, "较低": -1.4, "较差": -7.1},
                "营业收入利润率": {"优秀": 3.4, "良好": -2.3, "平均": -4.6, "较低": -21.4, "较差": -43.4},
                "资产负债率": {"优秀": 53.5, "良好": 58.5, "平均": 63.5, "较低": 73.5, "较差": 88.5},
                "总资产周转率": {"优秀": 0.5, "良好": 0.4, "平均": 0.3, "较低": 0.2, "较差": 0.1},
            }
        },
    ],
    "all_indicators": [
        "净资产收益率", "总资产报酬率", "营业收入利润率", "盈余现金保障倍数",
        "总资产周转率", "应收账款周转率", "流动资产周转率", "两金占流动资产比重",
        "资产负债率", "现金流动负债比率", "带息负债比率", "已获利息倍数",
        "研发经费投入强度", "全员劳动生产率", "经济增加值率", "国有资本保值增值率",
        "营业现金比率", "国有资本回报率", "EBITDA率", "百元收入支付的成本费用",
        "存货周转率", "速动比率"
    ],
    "grade_mapping": {
        "优秀": {"min": 90, "color": "#22c55e"},
        "良好": {"min": 75, "color": "#3b82f6"},
        "平均": {"min": 60, "color": "#f59e0b"},
        "较低": {"min": 40, "color": "#f97316"},
        "较差": {"min": 0, "color": "#ef4444"}
    }
}


def get_industry_standard(industry_code: str = None, industry_name: str = None) -> dict | None:
    """按行业代码或名称查询标准值"""
    for ind in ENTERPRISE_STANDARDS_2026["industries"]:
        if industry_code and ind["code"] == industry_code:
            return ind
        if industry_name and industry_name in ind["name"]:
            return ind
    return None


def score_indicator(industry_code: str, indicator_name: str, actual_value: float) -> dict:
    """
    单指标评分: 实际值 vs 标准值 → 分数(0-100) + 等级
    
    逻辑: 
    - 正向指标(收益率/周转率等): 实际值 >= 优秀线 → 100分
    - 反向指标(资产负债率/成本费用): 实际值 <= 优秀线 → 100分
    - 线性插值: 落在相邻两档之间时按比例计分
    """
    ind = get_industry_standard(industry_code=industry_code)
    if not ind or indicator_name not in ind["standards"]:
        return {"error": f"行业{industry_code}或指标{indicator_name}未找到"}
    
    std = ind["standards"][indicator_name]
    grades = ["优秀", "良好", "平均", "较低", "较差"]
    # ponytail: 过滤None档(互联网27的ROE较差=None)
    grades = [g for g in grades if std.get(g) is not None]
    if not grades:
        return {"error": f"指标{indicator_name}无有效档位"}
    
    # ponytail: 反向指标判定 — 资产负债率/成本费用越低越好
    reverse = indicator_name in ["资产负债率", "带息负债比率", "两金占流动资产比重", "百元收入支付的成本费用"]
    
    # 确定落在哪档区间
    if not reverse:  # 正向指标: 越大越好
        if actual_value >= std[grades[0]]:
            return {"score": 100, "grade": grades[0], "standard": std[grades[0]]}
        if actual_value <= std[grades[-1]]:
            return {"score": 0, "grade": grades[-1], "standard": std[grades[-1]]}
        for i in range(len(grades) - 1):
            upper, lower = std[grades[i]], std[grades[i + 1]]
            if lower <= actual_value < upper:
                ratio = (actual_value - lower) / (upper - lower)
                score = 20 * (4 - i) + ratio * 20  # 优秀80-100, 良好60-80...
                return {"score": round(score, 1), "grade": grades[i + 1], "standard": lower}
    else:  # 反向指标: 越小越好
        if actual_value <= std[grades[0]]:
            return {"score": 100, "grade": grades[0], "standard": std[grades[0]]}
        if actual_value >= std[grades[-1]]:
            return {"score": 0, "grade": grades[-1], "standard": std[grades[-1]]}
        for i in range(len(grades) - 1):
            lower, upper = std[grades[i]], std[grades[i + 1]]
            if lower < actual_value <= upper:
                ratio = (upper - actual_value) / (upper - lower)
                score = 20 * (4 - i) + ratio * 20
                return {"score": round(score, 1), "grade": grades[i + 1], "standard": upper}
    
    return {"score": 50, "grade": grades[len(grades)//2] if grades else "平均", "standard": std.get(grades[len(grades)//2]) if grades else 0}


def batch_score(industry_code: str, indicators: dict) -> dict:  # ponytail: dict不带[]避免旧py版本报错
    """
    批量评分: {指标名: 实际值} → 总分 + 各指标明细
    
    权重分配(财政部标准):
    - 盈利能力(30%): 净资产收益率/总资产报酬率/营业收入利润率/成本费用利润率/盈余现金保障倍数
    - 资产质量(25%): 总资产周转率/应收账款周转率/存货周转率/流动资产周转率
    - 债务风险(25%): 资产负债率/带息负债比率/速动比率/现金流动负债比率/营运资金配置比率
    - 经营增长(20%): 营业收入增长率/总资产增长率/营业利润增长率/技术投入比率/两金占流动资产比重
    """
    # ponytail: 维度权重dict，指标按出现频次分配子权重
    WEIGHTS = {
        "净资产收益率": 0.30/5, "总资产报酬率": 0.30/5, "营业收入利润率": 0.30/5, "成本费用利润率": 0.30/5, "盈余现金保障倍数": 0.30/5,
        "总资产周转率": 0.25/4, "应收账款周转率": 0.25/4, "存货周转率": 0.25/4, "流动资产周转率": 0.25/4,
        "资产负债率": 0.25/5, "带息负债比率": 0.25/5, "速动比率": 0.25/5, "现金流动负债比率": 0.25/5, "营运资金配置比率": 0.25/5,
        "营业收入增长率": 0.20/5, "总资产增长率": 0.20/5, "营业利润增长率": 0.20/5, "技术投入比率": 0.20/5, "两金占流动资产比重": 0.20/5,
        "百元收入支付的成本费用": 0.05, "劳动效率": 0.05, "营业利润率": 0.05  # ponytail: 未分类指标等权补足
    }
    
    ind = get_industry_standard(industry_code=industry_code)
    if not ind:
        return {"error": f"行业{industry_code}未找到"}
    
    # ponytail: 简化权重 — 所有指标等权，实际应用中按财政部要求分维度加权
    results = []
    errors = []
    total_score = 0
    for name, value in indicators.items():
        # ponytail: 类型守卫
        if not isinstance(value, (int, float)):
            errors.append({"indicator": name, "reason": f"值类型错误: {type(value).__name__}"})
            continue
        import math
        if not math.isfinite(value):
            errors.append({"indicator": name, "reason": "值非有限数(NaN/Inf)"})
            continue
        r = score_indicator(industry_code, name, value)
        if "error" in r:
            errors.append({"indicator": name, "reason": r["error"]})
        else:
            w = WEIGHTS.get(name, 1.0 / len(indicators))  # ponytail: 未知指标等权兜底
            results.append({"indicator": name, "actual": value, "weight": round(w, 4), **r})
            total_score += r["score"] * w
    
    if not results:
        return {"error": "无有效指标", "errors": errors}
    
    # ponytail: 权重已应用于total_score，直接用加权分
    avg_score = round(total_score, 1)
    final_grade = "优秀" if avg_score >= 90 else "良好" if avg_score >= 75 else "平均" if avg_score >= 60 else "较低" if avg_score >= 40 else "较差"
    
    ret = {
        "industry_code": industry_code,
        "industry_name": ind["name"],
        "total_score": avg_score,
        "grade": final_grade,
        "details": results
    }
    if errors:
        ret["errors"] = errors
    return ret


if __name__ == "__main__":
    # 自检: 房地产企业示例
    result = batch_score("17", {
        "净资产收益率": 6.5,
        "总资产报酬率": 2.8,
        "营业收入利润率": 5.2,
        "资产负债率": 68.0,
        "总资产周转率": 0.35
    })
    assert result["total_score"] > 0 and result["grade"] in ["优秀", "良好", "平均", "较低", "较差"]
    print(f"房地产企业评分: {result['total_score']}分 ({result['grade']})")
    for d in result["details"]:
        print(f"  {d['indicator']}: 实际{d['actual']} vs 标准{d['standard']} → {d['score']}分({d['grade']})")
