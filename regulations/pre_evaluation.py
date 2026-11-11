# -*- coding: utf-8 -*-
"""事前绩效评估 — 三维度(必要性/可行性/绩效性) + 两模式(非竞争/竞争)"""

PRE_EVALUATION_KB = {
    "dimensions": {
        "necessity": {"name": "必要性", "key": "要不要设立", "focus": ["立项依据", "现实需求", "重复建设", "替代方案"]},
        "feasibility": {"name": "可行性", "key": "能不能落地", "focus": ["实施方案", "决策程序", "资金保障", "风险防控"]},
        "performance": {"name": "绩效性", "key": "值不值得投", "focus": ["投入经济性", "目标合理性", "预算科学性"]}
    },
    "methods": {
        "factor": "因素分析法 — 内外部因素权重打分",
        "cost_benefit": "成本效益分析法 — 预期效益vs预算投入",
        "comparison": "比较法 — 同类/往期项目横纵向对比",
        "public": "公众评判法 — 受益对象调研",
        "expert": "专家咨询法 — 行业专家书面意见"
    },
    "modes": {
        "non_competitive": {
            "name": "非竞争性模式",
            "scenario": "无子项目竞争、预算固定",
            "process": ["必要性评估", "可行性评估", "绩效性评估"],
            "indicators": [
                {"dim": "必要性", "items": ["立项依据充分性", "需求迫切性", "财政支持合理性", "重复建设判断"]},
                {"dim": "可行性", "items": ["决策程序合规性", "实施方案成熟度", "资金保障程度", "组织管理能力", "风险防控水平"]},
                {"dim": "绩效性", "items": ["绩效目标合理性", "预算编制科学性", "投入产出匹配度", "可持续影响"]}
            ]
        },
        "competitive": {
            "name": "竞争性模式",
            "scenario": "多主体申报、资金择优分配",
            "process": ["筛选判定(必要性一票否决)", "评分排序(必要性60+可行性40)", "预算调整(单价/工程量优化)"],
            "indicators": ["政策符合性", "需求真实性", "方案可行性", "预算合理性", "绩效目标合理性", "组织保障能力", "风险可控性", "示范引领性"]
        }
    },
    "report_structure": {
        "project": ["摘要", "项目概况", "评估开展情况", "评估分析(三维度)", "总体结论", "预算安排建议", "绩效目标调整建议", "附件"],
        "policy": ["摘要", "政策概况", "评估开展情况", "评估分析(三维度)", "总体结论", "预算安排建议", "绩效目标调整建议", "附件"]
    },
    "result_application": ["预算安排依据", "项目调整依据", "政策完善依据", "项目库建设依据"],
    "workflow": ["前期准备", "材料审核", "现场调研/专家论证", "指标评分", "形成报告", "结果反馈与应用"],
    "key_principles": ["先评估后预算", "问题导向(要不要/能不能/值不值)", "客观公正", "定量定性结合", "闭环管理"]
}


def get_evaluation_indicators(mode: str = "non_competitive") -> list:
    """获取评估指标 — 竞争/非竞争两套"""
    # ponytail: 直接取KB字典，无需ORM
    return PRE_EVALUATION_KB["modes"].get(mode, {}).get("indicators", [])


def get_report_template(eval_type: str = "project") -> list:
    """获取报告框架 — 项目/政策两套"""
    return PRE_EVALUATION_KB["report_structure"].get(eval_type, [])


if __name__ == "__main__":
    # 自检
    assert len(PRE_EVALUATION_KB["dimensions"]) == 3
    assert len(PRE_EVALUATION_KB["modes"]) == 2
    indicators = get_evaluation_indicators("non_competitive")
    assert len(indicators) == 3  # 三维度
    print(f"✓ 事前评估知识库: 3维度 × 2模式 × 5方法")
    for dim in PRE_EVALUATION_KB["dimensions"].values():
        print(f"  - {dim['name']}: {dim['key']}")
