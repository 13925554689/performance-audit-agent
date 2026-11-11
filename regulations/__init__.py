"""
绩效评价法规库 — 内置法规、指标体系、评分标准和案例
==================================================
ponytail: 纯Python dict，不用DB，够用且零依赖
"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

# 学习成果合并: 分类体系 + 2024/2025最新法规案例
from regulations.classification import (
    CLASSIFICATIONS, WORKFLOW_REFS, get_classification,
    list_classifications, search_classifications,
)
from regulations.knowledge_update import (
    EXTRA_REGULATIONS, EXTRA_CASES, COST_PERFORMANCE_KB, PLAN_REVIEW_CHECKLIST,
    AUDIT_GUIDE_KB, COST_ANALYSIS_TEMPLATES_KB,
)
from regulations.enterprise_standards_2026 import (
    ENTERPRISE_STANDARDS_2026, get_industry_standard, score_indicator, batch_score,
)
from regulations.pre_evaluation import (
    PRE_EVALUATION_KB, get_evaluation_indicators, get_report_template,
)

# ═══════════════════════════════════════════════════════════
# 1. 法规清单
# ═══════════════════════════════════════════════════════════
REGULATIONS = [
    {
        "id": "R001",
        "name": "项目支出绩效评价管理办法",
        "issuer": "财政部",
        "doc_no": "财预〔2020〕10号",
        "level": "部门规章",
        "category": "财政支出",
        "effective_date": "2020-02-25",
        "key_content": [
            "绩效评价分为单位自评、部门评价和财政评价三种方式",
            "评价指标体系：决策、过程、产出、效益四个维度",
            "产出、效益指标权重不低于60%",
            "评价结果：优(≥90)、良(≥80)、中(≥60)、差(<60)",
            "单位自评指标权重：预算执行率10%、产出50%、效益30%、满意度10%"
        ],
        "full_text_ref": "财预〔2020〕10号 全文"
    },
    {
        "id": "R002",
        "name": "行政事业性国有资产管理条例",
        "issuer": "国务院",
        "doc_no": "国务院令第738号",
        "level": "行政法规",
        "category": "国有资产",
        "effective_date": "2021-04-01",
        "key_content": [
            "建立国有资产绩效管理制度，科学设立评价指标体系",
            "资产配置、使用、处置全过程管理",
            "绩效评价结果作为资产配置的重要依据",
            "财政部门-主管部门-行政事业单位三级监管体系"
        ],
        "full_text_ref": "国务院令第738号 全文"
    },
    {
        "id": "R003",
        "name": "会计师事务所财政支出绩效评价业务指引",
        "issuer": "中国注册会计师协会",
        "doc_no": "会协〔2015〕征求意见稿",
        "level": "行业指引",
        "category": "绩效评价",
        "effective_date": "2015-01",
        "key_content": [
            "7章完整覆盖：概述→承接→计划→实施→IT环境→报告→质量控制",
            "6种证据收集方法：文件检查、文献检索、问卷、访谈、研讨会、观察",
            "4类证据：实物证据、口头证据、书面证据、分析性证据",
            "评价指标原则：相关性、重要性、可比性、系统性、经济性",
            "事前/事中/事后三类评价"
        ],
        "full_text_ref": "会计师事务所财政支出绩效评价业务指引"
    },
    {
        "id": "R004",
        "name": "中央行政事业单位资产管理绩效考评办法(试行)",
        "issuer": "国家机关事务管理局",
        "doc_no": "国管资〔2012〕204号",
        "level": "部门规章",
        "category": "国有资产",
        "effective_date": "2012-07-01",
        "key_content": [
            "资产管理效果、资产管理规范、资产管理基础工作三大维度",
            "34个评分点+2个加分项(实践创新/理论创新)",
            "部门自评→集中评审→反馈沟通→结果应用四步流程"
        ],
        "full_text_ref": "国管资〔2012〕204号 全文"
    },
    {
        "id": "R005",
        "name": "中共中央 国务院关于全面实施预算绩效管理的意见",
        "issuer": "中共中央、国务院",
        "doc_no": "中发〔2018〕34号",
        "level": "中央文件",
        "category": "预算绩效",
        "effective_date": "2018-09-01",
        "key_content": [
            "构建全方位预算绩效管理格局",
            "建立全过程预算绩效管理链条",
            "完善全覆盖预算绩效管理体系",
            "硬化预算绩效管理约束"
        ],
        "full_text_ref": "中发〔2018〕34号 全文"
    }
]

# 合并学习成果: 2024/2025最新法规（CASE_LIBRARY 在下方第5节后合并）
REGULATIONS = REGULATIONS + EXTRA_REGULATIONS


# ═══════════════════════════════════════════════════════════
# 2. 绩效评价指标体系（财预〔2020〕10号框架）
# ═══════════════════════════════════════════════════════════
PERFORMANCE_INDEX_SYSTEM = {
    "name": "项目支出绩效评价指标体系",
    "scoring_rule": {
        "max_score": 100,
        "grades": [
            {"grade": "优", "min": 90, "max": 100, "color": "#22c55e"},
            {"grade": "良", "min": 80, "max": 89, "color": "#3b82f6"},
            {"grade": "中", "min": 60, "max": 79, "color": "#f59e0b"},
            {"grade": "差", "min": 0, "max": 59, "color": "#ef4444"}
        ]
    },
    "dimensions": [
        {
            "name": "决策",
            "weight": 15,
            "indices": [
                {"id": "A1", "name": "项目立项", "weight": 8, "sub_indices": [
                    {"id": "A11", "name": "立项依据充分性", "weight": 4, "type": "定性",
                     "criteria": "项目是否符合国家政策、部门职能和实际需求"},
                    {"id": "A12", "name": "立项程序规范性", "weight": 4, "type": "定性",
                     "criteria": "项目是否按规定程序申报、审批"}
                ]},
                {"id": "A2", "name": "绩效目标", "weight": 4, "sub_indices": [
                    {"id": "A21", "name": "绩效目标合理性", "weight": 2, "type": "定性",
                     "criteria": "目标是否与实际工作内容相关，预期产出和效果是否符合正常业绩水平"},
                    {"id": "A22", "name": "绩效指标明确性", "weight": 2, "type": "定性",
                     "criteria": "指标是否清晰、细化、可衡量"}
                ]},
                {"id": "A3", "name": "资金投入", "weight": 3, "sub_indices": [
                    {"id": "A31", "name": "预算编制科学性", "weight": 3, "type": "定性",
                     "criteria": "预算编制是否经过科学论证，资金额度与年度目标是否匹配"}
                ]}
            ]
        },
        {
            "name": "过程",
            "weight": 25,
            "indices": [
                {"id": "B1", "name": "资金管理", "weight": 10, "sub_indices": [
                    {"id": "B11", "name": "预算执行率", "weight": 5, "type": "定量",
                     "criteria": "实际支出/预算金额×100%，≥95%满分"},
                    {"id": "B12", "name": "资金使用合规性", "weight": 5, "type": "定性",
                     "criteria": "是否符合国家财经法规，是否存在截留、挤占、挪用"}
                ]},
                {"id": "B2", "name": "组织实施", "weight": 15, "sub_indices": [
                    {"id": "B21", "name": "管理制度健全性", "weight": 5, "type": "定性",
                     "criteria": "财务和业务管理制度是否健全"},
                    {"id": "B22", "name": "制度执行有效性", "weight": 5, "type": "定性",
                     "criteria": "是否遵守相关法律法规和制度规定"},
                    {"id": "B23", "name": "项目监管有效性", "weight": 5, "type": "定性",
                     "criteria": "是否为保障项目质量采取了必要的监督检查"}
                ]}
            ]
        },
        {
            "name": "产出",
            "weight": 30,
            "indices": [
                {"id": "C1", "name": "产出数量", "weight": 10, "type": "定量",
                 "criteria": "实际完成率=实际产出数/计划产出数×100%"},
                {"id": "C2", "name": "产出质量", "weight": 10, "type": "定量",
                 "criteria": "质量达标率=质量达标产出数/实际产出数×100%"},
                {"id": "C3", "name": "产出时效", "weight": 5, "type": "定量",
                 "criteria": "完成及时性，计划完成时间内完成"},
                {"id": "C4", "name": "产出成本", "weight": 5, "type": "定量",
                 "criteria": "成本节约率，实际成本是否控制在预算内"}
            ]
        },
        {
            "name": "效益",
            "weight": 30,
            "indices": [
                {"id": "D1", "name": "经济效益", "weight": 8, "type": "定性",
                 "criteria": "项目实施产生的直接或间接经济效益"},
                {"id": "D2", "name": "社会效益", "weight": 8, "type": "定性",
                 "criteria": "项目实施产生的社会影响和公众受益程度"},
                {"id": "D3", "name": "生态效益", "weight": 4, "type": "定性",
                 "criteria": "项目实施对生态环境的影响"},
                {"id": "D4", "name": "可持续影响", "weight": 5, "type": "定性",
                 "criteria": "项目后续运行及成效发挥的可持续性"},
                {"id": "D5", "name": "满意度", "weight": 5, "type": "定量",
                 "criteria": "服务对象对项目实施的满意程度"}
            ]
        }
    ]
}

# ═══════════════════════════════════════════════════════════
# 3. 行政事业单位国有资产绩效评价指标体系
# ═══════════════════════════════════════════════════════════
ASSET_PERFORMANCE_INDEX = {
    "name": "行政事业单位国有资产管理绩效评价指标体系",
    "based_on": "国管资〔2012〕204号",
    "scoring_rule": PERFORMANCE_INDEX_SYSTEM["scoring_rule"],
    "dimensions": [
        {
            "name": "资产管理效果",
            "weight": 40,
            "indices": [
                {"id": "E1", "name": "人均资产占有情况", "weight": 8},
                {"id": "E2", "name": "固定资产增长率", "weight": 6},
                {"id": "E3", "name": "资产调剂利用率", "weight": 10},
                {"id": "E4", "name": "资产配置费用节约率", "weight": 6},
                {"id": "E5", "name": "公车运行费用", "weight": 5},
                {"id": "E6", "name": "资产保值增值率", "weight": 5}
            ]
        },
        {
            "name": "资产管理规范",
            "weight": 35,
            "indices": [
                {"id": "F1", "name": "资产配置规范", "weight": 10},
                {"id": "F2", "name": "资产使用规范", "weight": 10},
                {"id": "F3", "name": "资产处置规范", "weight": 10},
                {"id": "F4", "name": "资产收益管理规范", "weight": 5}
            ]
        },
        {
            "name": "资产管理基础工作",
            "weight": 25,
            "indices": [
                {"id": "G1", "name": "管理制度建设", "weight": 8},
                {"id": "G2", "name": "领导重视程度", "weight": 5},
                {"id": "G3", "name": "机构人员设置", "weight": 5},
                {"id": "G4", "name": "资产信息卡片库建设", "weight": 7}
            ]
        }
    ]
}

# ═══════════════════════════════════════════════════════════
# 2b. 部门整体支出绩效评价指标体系 (履职效能50+管理效率50)
#     依据: 部门整体支出绩效评价共性指标体系框架(2024年度)
# ═══════════════════════════════════════════════════════════
DEPARTMENT_INDEX_SYSTEM = {
    "name": "部门整体支出绩效评价指标体系",
    "based_on": "部门整体支出绩效评价共性指标体系框架(2024年度)",
    "scoring_rule": PERFORMANCE_INDEX_SYSTEM["scoring_rule"],
    "dimensions": [
        {
            "name": "履职效能",
            "weight": 50,
            "indices": [
                {"id": "H1", "name": "整体效能", "weight": 50, "sub_indices": [
                    {"id": "H11", "name": "产出指标完成情况", "weight": 15, "type": "定量",
                     "criteria": "部门整体绩效目标产出指标(数量/质量/时效)完成率"},
                    {"id": "H12", "name": "效益指标完成情况", "weight": 15, "type": "定量",
                     "criteria": "部门整体绩效目标效益指标(社会/生态/可持续)完成率"},
                    {"id": "H13", "name": "专项资金绩效完成情况", "weight": 20, "type": "定量",
                     "criteria": "主管部门管理的专项资金绩效目标实现程度"},
                ]}
            ]
        },
        {
            "name": "管理效率",
            "weight": 50,
            "indices": [
                {"id": "I1", "name": "预算编制", "weight": 3, "type": "定性",
                 "criteria": "事前绩效评估应评尽评；绩效目标随预算同步编制"},
                {"id": "I2", "name": "预算执行", "weight": 4, "type": "定量",
                 "criteria": "季度执行率得分=(季度进度/序时进度)×1分×4季度+全年平均执行率×2分；结转结余率"},
                {"id": "I3", "name": "信息公开", "weight": 4, "type": "定性",
                 "criteria": "预决算公开合规性2分+绩效信息公开2分"},
                {"id": "I4", "name": "绩效管理", "weight": 15, "type": "定性",
                 "criteria": "绩效管理制度建设+事前评估+双监控+自评质量+结果应用+整改闭环"},
                {"id": "I5", "name": "采购管理", "weight": 10, "type": "定性",
                 "criteria": "采购计划执行率+合同签订备案及时性(2个工作日内)+中小企业采购份额"},
                {"id": "I6", "name": "资产管理", "weight": 10, "type": "定性",
                 "criteria": "账-卡-物相符+资产利用率+资产年报质量"},
                {"id": "I7", "name": "运行成本", "weight": 4, "type": "定量",
                 "criteria": "日常公用经费控制率+'三公'经费控制率，落实过紧日子要求"},
            ]
        }
    ]
}

# ═══════════════════════════════════════════════════════════
# 2c. 单位自评指标框架 (财预〔2020〕10号第十四条权重)
# ═══════════════════════════════════════════════════════════
SELF_EVAL_INDEX = {
    "name": "项目支出绩效自评指标框架",
    "based_on": "财预〔2020〕10号(单位自评权重)",
    "scoring_rule": PERFORMANCE_INDEX_SYSTEM["scoring_rule"],
    "dimensions": [
        {"name": "预算执行率", "weight": 10, "indices": [
            {"id": "J1", "name": "预算执行率", "weight": 10, "type": "定量",
             "criteria": "实际支出/预算金额×100%；执行率<60%需专项说明"}]},
        {"name": "产出指标", "weight": 50, "indices": [
            {"id": "J2", "name": "产出数量完成率", "weight": 15, "type": "定量", "criteria": "实际/计划×100%"},
            {"id": "J3", "name": "产出质量达标率", "weight": 15, "type": "定量", "criteria": "达标产出/实际产出×100%"},
            {"id": "J4", "name": "产出时效符合率", "weight": 10, "type": "定量", "criteria": "按时完成产出/计划产出×100%"},
            {"id": "J5", "name": "产出成本控制率", "weight": 10, "type": "定量", "criteria": "实际成本/预算成本×100%"}]},
        {"name": "效益指标", "weight": 40, "indices": [
            {"id": "J6", "name": "经济效益实现程度", "weight": 12, "type": "定性", "criteria": "对照绩效目标效益值"},
            {"id": "J7", "name": "社会效益实现程度", "weight": 12, "type": "定性", "criteria": "对照绩效目标效益值"},
            {"id": "J8", "name": "生态效益/可持续影响", "weight": 8, "type": "定性", "criteria": "对照绩效目标效益值"},
            {"id": "J9", "name": "服务对象满意度", "weight": 8, "type": "定量", "criteria": "满意度调查≥85%满分"}]},
    ]
}

# ═══════════════════════════════════════════════════════════
# 2d. 成本绩效分析指标框架 (成本要素+定额对标)
# ═══════════════════════════════════════════════════════════
COST_EVAL_INDEX = {
    "name": "成本绩效分析评价指标框架",
    "based_on": "上海/北京成本预算绩效管理实践",
    "scoring_rule": PERFORMANCE_INDEX_SYSTEM["scoring_rule"],
    "dimensions": [
        {"name": "成本合理性", "weight": 40, "indices": [
            {"id": "K1", "name": "成本要素完整性", "weight": 10, "type": "定性", "criteria": "人/机/料/法/环五要素无遗漏"},
            {"id": "K2", "name": "单位成本对标偏差", "weight": 20, "type": "定量", "criteria": "实际单位成本/行业基线×100%，≥120%需专项说明"},
            {"id": "K3", "name": "成本数据可靠性", "weight": 10, "type": "定性", "criteria": "近3年数据+≥3家单位交叉验证"}]},
        {"name": "作业效能", "weight": 30, "indices": [
            {"id": "K4", "name": "作业定额符合度", "weight": 15, "type": "定量", "criteria": "实际作业量/定额作业量"},
            {"id": "K5", "name": "人员配置效率", "weight": 15, "type": "定量", "criteria": "实际配置/标准配置(劳动定额)"}]},
        {"name": "标准建设", "weight": 30, "indices": [
            {"id": "K6", "name": "定额标准科学性", "weight": 15, "type": "定性", "criteria": "测算方法透明+专家论证通过"},
            {"id": "K7", "name": "绩效基线可用性", "weight": 15, "type": "定性", "criteria": "基线可量化、可监控、可应用于预算"}]},
    ]
}

# 分类 → 指标体系映射
_INDEX_MAP = {
    "project": PERFORMANCE_INDEX_SYSTEM,
    "asset": ASSET_PERFORMANCE_INDEX,
    "department": DEPARTMENT_INDEX_SYSTEM,
    "selfeval": SELF_EVAL_INDEX,
    "cost": COST_EVAL_INDEX,
}

# 分类id → 指标key
_CLASSIFICATION_INDEX = {
    "project_expenditure": "project",
    "department_overall": "department",
    "self_evaluation": "selfeval",
    "cost_performance": "cost",
    "policy_evaluation": "project",
    "asset_performance": "asset",
}

# ═══════════════════════════════════════════════════════════
# 4. 审计证据收集方法
#    v6.0: 按业务指引原文修正为7种(文件检查/文献分析/问卷调查/访谈/研讨会/焦点小组/观察)
# ═══════════════════════════════════════════════════════════
EVIDENCE_METHODS = [
    {"id": "M1", "name": "文件检查", "desc": "查阅项目立项、招投标、合同、验收等文件；对资金收支活动做合规性检查(独立核算/专款专用/原始凭证合规)",
     "tools": ["文件清单", "抽样表"], "output": "文件检查记录表",
     "pros": "反映全面历史信息、不干扰日常工作", "cons": "耗时、信息可能不完整、仅限已存在数据"},
    {"id": "M2", "name": "文献分析", "desc": "查阅相关文献、研究历史资料，评估内容可靠性(客观性/多方位描述)",
     "tools": ["法规库", "行业数据库"], "output": "文献检索记录"},
    {"id": "M3", "name": "问卷调查", "desc": "从人群或组织收集详细信息；可函证/网上调查/电话核实，需抽样设计和计算机加工",
     "tools": ["问卷模板", "统计分析表"], "output": "问卷调查分析报告",
     "pros": "匿名、成本低、易比较、可获大量数据", "cons": "反馈可能不认真、措辞影响回应、需抽样专家"},
    {"id": "M4", "name": "访谈", "desc": "计划及调查阶段获取文件/意见/想法，证实其他渠道数据；从非结构化到结构化；访谈前需策划，双人记录",
     "tools": ["访谈提纲", "访谈记录模板"], "output": "访谈纪要",
     "pros": "信息全面深入、建立关系、灵活", "cons": "耗时长、难分析比较、成本高"},
    {"id": "M5", "name": "研讨会", "desc": "各阶段均可召开；获取专业领域了解/讨论成功经验与改进措施/通报不同观点",
     "tools": ["会议方案", "纪要模板"], "output": "研讨会纪要"},
    {"id": "M6", "name": "焦点小组", "desc": "选定人员集中讨论某主题，收集定性信息；从受益人/利益相关方获取执行情况与项目影响信息",
     "tools": ["引导提纲", "记录表"], "output": "焦点小组记录",
     "pros": "快捷可靠获取共同印象、短期获取广泛深入信息", "cons": "难分析成员反应、协调员需保密"},
    {"id": "M7", "name": "现场观察", "desc": "深入了解操作运行方式、测试观点及信息对比；拍照编号留档",
     "tools": ["观察清单", "拍照记录"], "output": "现场观察记录表",
     "pros": "观察实际发生情况、灵活", "cons": "行为解释难、可能影响被观察者、成本高"},
]

# ═══════════════════════════════════════════════════════════
# 5. 案例库
# ═══════════════════════════════════════════════════════════
CASE_LIBRARY = [
    {
        "id": "C001",
        "name": "国资监管政策实施效果稽核与评价项目",
        "org": "国务院国资委",
        "year": 2025,
        "budget": 63.00,  # 万元
        "dimensions_score": {
            "决策": 15, "过程": 25, "产出": 30, "效益": 30
        },
        "total_score": 89,
        "grade": "良",
        "highlights": [
            "绩效目标明确，指标设置完整",
            "稽核团队经验丰富，深入央企现场检查",
            "提出的建议被采纳转化为制度举措"
        ],
        "issues": ["部分指标量化不足"],
        "suggestions": ["加强绩效指标量化设计"]
    },
    {
        "id": "C002",
        "name": "数据运营项目绩效评价",
        "org": "上海市大数据中心",
        "year": 2021,
        "budget": 2500.00,
        "dimensions_score": {"决策": 11.4, "过程": 17.6, "产出": 30, "效益": 30},
        "total_score": 89,
        "grade": "良",
        "highlights": ["数据归集超额完成", "分类共享机制完善", "产出100%达标"],
        "issues": ["绩效目标合理性不足(30%得分率)", "预算编制科学性不足(25%得分率)"],
        "suggestions": ["事前加强绩效目标论证", "预算编制增加测算依据"]
    },
    {
        "id": "C003",
        "name": "馆所文献购置费绩效评价",
        "org": "上海图书馆",
        "year": 2017,
        "budget": 3500.00,
        "dimensions_score": {"决策": 15, "过程": 22, "产出": 28, "效益": 27},
        "total_score": 92,
        "grade": "优",
        "highlights": [
            "战略目标与城市定位高度吻合",
            "预算执行规范",
            "效益显著，读者满意度高"
        ],
        "issues": ["预算编制与实际单价有偏差"],
        "suggestions": ["提高预算编制的精准度"]
    }
]

# 合并学习成果: 2024/2025最新案例
CASE_LIBRARY = CASE_LIBRARY + EXTRA_CASES

# ═══════════════════════════════════════════════════════════
# 6. 审计工作底稿模板
# ═══════════════════════════════════════════════════════════
WORKING_PAPER_TEMPLATES = {
    "WP01_计划审计工作": {
        "name": "计划审计工作底稿",
        "sections": ["审计目标", "审计范围", "审计依据", "重要性水平", "审计风险", "审计策略", "时间安排", "人员分工"],
        "auto_fill": ["审计依据", "时间安排"]
    },
    "WP02_了解被评价单位": {
        "name": "了解被评价单位底稿",
        "sections": ["单位基本情况", "组织架构", "主要职能", "财务状况", "内控制度", "前期审计发现"]
    },
    "WP03_风险评估": {
        "name": "风险评估工作底稿",
        "sections": ["风险识别", "风险分析", "风险应对", "风险矩阵"]
    },
    "WP04_决策评价": {
        "name": "决策评价工作底稿",
        "sections": ["立项依据", "程序合规性", "绩效目标", "预算编制"]
    },
    "WP05_过程评价": {
        "name": "过程评价工作底稿",
        "sections": ["预算执行", "资金使用合规性", "管理制度", "制度执行", "项目监管"]
    },
    "WP06_产出评价": {
        "name": "产出评价工作底稿",
        "sections": ["产出数量", "产出质量", "产出时效", "产出成本"]
    },
    "WP07_效益评价": {
        "name": "效益评价工作底稿",
        "sections": ["经济效益", "社会效益", "生态效益", "可持续影响", "满意度"]
    },
    "WP08_评分汇总": {
        "name": "评分汇总工作底稿",
        "sections": ["各维度评分", "总分计算", "评级结果", "主要结论"]
    }
}

# ═══════════════════════════════════════════════════════════
# 7. 审计报告模板
# ═══════════════════════════════════════════════════════════
REPORT_TEMPLATE = {
    "sections": [
        "一、项目基本情况",
        "二、绩效评价工作开展情况",
        "三、绩效评价指标体系",
        "四、绩效目标实现程度",
        "五、存在问题及原因分析",
        "六、评价结论及建议",
        "七、其他需要说明的问题"
    ],
    "appendix": [
        "附件1：绩效评价指标体系及评分表",
        "附件2：问卷调查分析报告",
        "附件3：访谈纪要",
        "附件4：现场照片"
    ]
}


def search_regulations(keyword: str) -> list:
    """搜索法规库"""
    results = []
    keyword_lower = keyword.lower()
    for reg in REGULATIONS:
        text = f"{reg['name']} {reg['issuer']} {' '.join(reg['key_content'])}"
        if keyword_lower in text.lower():
            results.append(reg)
    return results


def get_index_system(category: str = "project") -> dict:
    """获取指标体系 — project/asset/department/selfeval/cost 五套"""
    return _INDEX_MAP.get(category, PERFORMANCE_INDEX_SYSTEM)


def get_case(case_id: str = None) -> list:
    """获取案例"""
    if case_id:
        for c in CASE_LIBRARY:
            if c["id"] == case_id:
                return [c]
    return CASE_LIBRARY


def get_classification_kit(cid: str) -> dict:
    """分类工作包: 分类信息 + 对应指标体系 + 沟通模板 + 成果清单"""
    c = get_classification(cid)
    if not c:
        return {"error": f"未知分类: {cid}"}
    idx_key = _CLASSIFICATION_INDEX.get(cid, "project")
    return {
        "classification": c,
        "index_system": _INDEX_MAP[idx_key],
        "workflow": WORKFLOW_REFS[c["workflow_ref"]],
    }
