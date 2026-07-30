"""
业务流程驱动引擎 — 8阶段绩效评价审计流程
========================================
ponytail: 状态机模式，一个dict驱动全部业务流程
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Optional
import json
import os
from collections import deque

# ponytail: import once at the top
from regulations import (
    PERFORMANCE_INDEX_SYSTEM, WORKING_PAPER_TEMPLATES, REPORT_TEMPLATE
)

# ponytail: ring buffer, 100 entries, overwrite oldest
_trace = deque(maxlen=100)


def _log(action, pid, detail=""):
    _trace.append({
        "ts": datetime.now().isoformat(), "action": action, "pid": pid, "detail": detail
    })

# ═══════════════════════════════════════════════════════════
# 8阶段业务流程定义
# ═══════════════════════════════════════════════════════════
PROCESS_STAGES = [
    {
        "stage": 1, "id": "acceptance", "name": "业务承接",
        "description": "确认业务委托、签订约定书、明确评价对象和范围",
        "outputs": ["业务约定书", "委托方需求确认单"],
        "checklist": [
            "被评价单位是否认可并理解其责任",
            "评价人员是否具备专业胜任能力",
            "是否存在独立性威胁",
            "是否已签订业务约定书"
        ],
        "estimated_time": "1-2天"
    },
    {
        "stage": 2, "id": "planning", "name": "计划评价工作",
        "description": "了解项目背景、设计评价指标体系、编制评价方案",
        "outputs": ["绩效评价工作方案", "评价指标体系表", "时间进度安排表"],
        "checklist": [
            "是否已充分了解项目背景和政策依据",
            "评价指标体系是否覆盖决策-过程-产出-效益四维度",
            "指标权重是否合理(产出+效益≥60%)",
            "是否确定了数据收集方法和抽样方案",
            "评价方案是否经委托方确认"
        ],
        "estimated_time": "3-5天"
    },
    {
        "stage": 3, "id": "indicators", "name": "指标体系设计",
        "description": "根据项目特点细化三级/四级指标，设定评分标准和权重",
        "outputs": ["绩效评价指标体系(细化版)", "评分标准表", "数据采集表"],
        "checklist": [
            "指标是否符合相关性、重要性、可比性、系统性、经济性原则",
            "定量指标是否明确计算公式",
            "定性指标是否有明确的评分档次",
            "评分标准是否可操作"
        ],
        "estimated_time": "2-3天"
    },
    {
        "stage": 4, "id": "data_collection", "name": "数据收集与证据获取",
        "description": "通过文件检查、访谈、问卷、观察、数据分析等方式收集证据",
        "outputs": ["文件检查记录表", "访谈纪要", "问卷分析报告", "现场观察记录", "数据分析底稿"],
        "checklist": [
            "是否覆盖全部6种证据收集方法(适用时)",
            "证据是否满足可靠性、相关性、充分性",
            "是否对关键数据进行了交叉验证",
            "是否保留了证据来源记录"
        ],
        "estimated_time": "5-10天"
    },
    {
        "stage": 5, "id": "analysis", "name": "分析评分",
        "description": "对照指标体系逐项评分，汇总各维度得分，形成初步评价结论",
        "outputs": ["评分工作底稿", "评分汇总表", "问题清单", "初步评价结论"],
        "checklist": [
            "每项评分是否有充分证据支持",
            "加减分理由是否明确记录",
            "各维度得分是否合理",
            "是否进行了组内复核"
        ],
        "estimated_time": "3-5天"
    },
    {
        "stage": 6, "id": "reporting", "name": "报告撰写与沟通",
        "description": "撰写绩效评价报告，与被评价单位沟通，修改完善",
        "outputs": ["绩效评价报告(征求意见稿)", "沟通记录", "反馈意见处理表"],
        "checklist": [
            "报告是否包含全部7个章节",
            "结论是否有充分证据支持",
            "建议是否具有可操作性",
            "是否已与被评价单位充分沟通",
            "反馈意见是否妥善处理"
        ],
        "estimated_time": "5-7天"
    },
    {
        "stage": 7, "id": "quality_control", "name": "质量控制",
        "description": "组内复核、部门复核、独立复核三级质量控制",
        "outputs": ["复核记录表", "质量评价表"],
        "checklist": [
            "是否完成三级复核",
            "复核意见是否已处理",
            "报告是否满足完整性、准确性、客观性、说服力、逻辑清晰要求",
            "底稿归档是否完整"
        ],
        "estimated_time": "2-3天"
    },
    {
        "stage": 8, "id": "archiving", "name": "归档与后续",
        "description": "整理底稿、归档电子/纸质档案、跟踪整改建议落实情况",
        "outputs": ["归档清单", "底稿索引表", "后续跟踪计划"],
        "checklist": [
            "底稿是否按索引编号归档",
            "电子档案是否备份",
            "是否制定了后续跟踪计划"
        ],
        "estimated_time": "1-2天"
    }
]


@dataclass
class AuditProject:
    """审计项目状态"""
    id: str
    name: str
    org_name: str  # 被评价单位
    org_type: str  # 行政单位 / 事业单位 / 国有企业
    project_type: str  # 项目支出 / 部门整体 / 资产管理
    budget: float
    year: int
    current_stage: int = 1
    stage_status: dict = field(default_factory=dict)  # {stage_id: "pending"|"in_progress"|"completed"}
    scores: dict = field(default_factory=dict)  # {dimension: score}
    total_score: float = 0.0
    grade: str = ""
    issues: list = field(default_factory=list)
    suggestions: list = field(default_factory=list)
    evidence_files: list = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.stage_status:
            self.stage_status = {s["id"]: "pending" for s in PROCESS_STAGES}
            self.stage_status["acceptance"] = "in_progress"


class ProcessEngine:
    """业务流程驱动引擎"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self._projects: dict[str, AuditProject] = {}
        self._load_projects()

    def _get_project_file(self) -> str:
        return os.path.join(self.data_dir, "projects.json")

    def _load_projects(self):
        """加载已保存的项目"""
        path = self._get_project_file()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for pid, pdict in data.items():
                    self._projects[pid] = AuditProject(**pdict)
            except (json.JSONDecodeError, KeyError, TypeError):
                # ponytail: corrupt file → skip, log to stderr
                import sys
                print(f"[engine] corrupt projects.json, resetting", file=sys.stderr)
                self._projects = {}
                self._save_projects()

    def _save_projects(self):
        """保存项目到磁盘"""
        path = self._get_project_file()
        data = {pid: asdict(p) for pid, p in self._projects.items()}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def create_project(self, **kwargs) -> AuditProject:
        """创建新的审计项目"""
        pid = f"PA{datetime.now().strftime('%Y%m%d%H%M%S')}"
        project = AuditProject(id=pid, **kwargs)
        self._projects[pid] = project
        self._save_projects()
        _log("create", pid, f"{kwargs.get('name','?')} @{kwargs.get('org_name','?')}")
        return project

    def get_project(self, pid: str) -> Optional[AuditProject]:
        return self._projects.get(pid)

    def list_projects(self) -> list:
        return list(self._projects.values())

    def advance_stage(self, pid: str) -> dict:
        """推进到下一阶段"""
        project = self._projects.get(pid)
        if not project:
            return {"error": "项目不存在"}

        current = project.current_stage
        if current > len(PROCESS_STAGES):
            return {"error": "项目已完成全部阶段"}

        current_stage = PROCESS_STAGES[current - 1]

        # ponytail: if on last stage, complete it instead of advancing
        if current == len(PROCESS_STAGES):
            project.stage_status[current_stage["id"]] = "completed"
            project.current_stage = current + 1  # beyond last stage = done
            project.updated_at = datetime.now().isoformat()
            self._save_projects()
            _log("complete", pid, f"stage {current}/8 done: {current_stage['name']}")
            return {
                "success": True, "current_stage": project.current_stage,
                "stage_name": f"{current_stage['name']} ✅ 已完成",
                "stage_id": current_stage["id"], "checklist": [],
                "outputs": [], "estimated_time": "已完成",
                "stage_num": project.current_stage,
                "total_stages": len(PROCESS_STAGES),
                "progress": f"全部完成! ({len(PROCESS_STAGES)}/{len(PROCESS_STAGES)})",
                "completed": True
            }

        # 完成当前阶段
        project.stage_status[current_stage["id"]] = "completed"

        # 进入下一阶段
        project.current_stage = current + 1
        next_stage = PROCESS_STAGES[current]
        project.stage_status[next_stage["id"]] = "in_progress"
        project.updated_at = datetime.now().isoformat()
        self._save_projects()
        _log("advance", pid, f"stage {current}→{current+1}: {current_stage['name']}→{next_stage['name']}")

        return {
            "success": True,
            "current_stage": project.current_stage,
            "stage_name": next_stage["name"],
            "stage_id": next_stage["id"],
            "checklist": next_stage["checklist"],
            "outputs": next_stage["outputs"],
            "estimated_time": next_stage["estimated_time"],
            "stage_num": project.current_stage,
            "total_stages": len(PROCESS_STAGES),
            "progress": f"{project.current_stage}/{len(PROCESS_STAGES)}"
        }

    def go_to_stage(self, pid: str, stage: int) -> dict:
        """跳转到指定阶段"""
        project = self._projects.get(pid)
        if not project:
            return {"error": "项目不存在"}
        if stage < 1 or stage > len(PROCESS_STAGES):
            return {"error": f"阶段号应在1-{len(PROCESS_STAGES)}之间"}

        project.current_stage = stage
        for i, s in enumerate(PROCESS_STAGES):
            if i + 1 < stage:
                project.stage_status[s["id"]] = "completed"
            elif i + 1 == stage:
                project.stage_status[s["id"]] = "in_progress"
            else:
                project.stage_status[s["id"]] = "pending"

        project.updated_at = datetime.now().isoformat()
        self._save_projects()

        current = PROCESS_STAGES[stage - 1]
        return {
            "success": True,
            "current_stage": stage,
            "stage_name": current["name"],
            "stage_id": current["id"],
            "checklist": current["checklist"],
            "outputs": current["outputs"],
            "estimated_time": current["estimated_time"]
        }

    def get_stage_detail(self, pid: str) -> dict:
        """获取当前阶段详情"""
        project = self._projects.get(pid)
        if not project:
            return {"error": "项目不存在"}

        # ponytail: handle completed state (current_stage > len)
        completed = project.current_stage > len(PROCESS_STAGES)
        stage_idx = min(project.current_stage, len(PROCESS_STAGES)) - 1
        stage = PROCESS_STAGES[stage_idx]
        all_stages = [
            {
                "stage": s["stage"],
                "id": s["id"],
                "name": s["name"],
                "status": project.stage_status.get(s["id"], "pending"),
                "is_current": s["stage"] == project.current_stage
            }
            for s in PROCESS_STAGES
        ]

        return {
            "project": asdict(project),
            "current": {
                "stage_num": stage["stage"],
                "total": len(PROCESS_STAGES),
                "name": stage["name"],
                "description": stage["description"],
                "checklist": stage["checklist"],
                "outputs": stage["outputs"],
                "estimated_time": stage["estimated_time"]
            },
            "all_stages": all_stages,
            "progress": f"{project.current_stage}/{len(PROCESS_STAGES)}",
            "percent": round(project.current_stage / len(PROCESS_STAGES) * 100)
        }

    def submit_score(self, pid: str, dimension: str, score: float, evidence: str = "") -> dict:
        """提交评分"""
        project = self._projects.get(pid)
        if not project:
            return {"error": "项目不存在"}

        project.scores[dimension] = score
        project.evidence_files.append({
            "dimension": dimension,
            "score": score,
            "evidence": evidence,
            "timestamp": datetime.now().isoformat()
        })
        project.updated_at = datetime.now().isoformat()
        self._save_projects()
        _log("score", pid, f"{dimension}={score}")
        return {"success": True, "dimension": dimension, "score": score}

    def calculate_final_score(self, pid: str) -> dict:
        """计算最终得分和评级"""
        project = self._projects.get(pid)
        if not project:
            return {"error": "项目不存在"}

        total = sum(project.scores.values())
        project.total_score = total

        # 评级
        for g in PERFORMANCE_INDEX_SYSTEM["scoring_rule"]["grades"]:
            if g["min"] <= total <= g["max"]:
                project.grade = g["grade"]
                break

        project.updated_at = datetime.now().isoformat()
        self._save_projects()
        _log("calculate", pid, f"total={total} grade={project.grade}")

        return {
            "total_score": total,
            "grade": project.grade,
            "scores": project.scores,
            "dimensions": [
                {"name": d["name"], "weight": d["weight"], "score": project.scores.get(d["name"], 0)}
                for d in PERFORMANCE_INDEX_SYSTEM["dimensions"]
            ]
        }

    def add_issue(self, pid: str, issue: str, severity: str = "中") -> dict:
        """添加问题"""
        project = self._projects.get(pid)
        if not project:
            return {"error": "项目不存在"}
        project.issues.append({
            "issue": issue,
            "severity": severity,
            "timestamp": datetime.now().isoformat()
        })
        self._save_projects()
        return {"success": True, "issue_count": len(project.issues)}

    def add_suggestion(self, pid: str, suggestion: str) -> dict:
        """添加建议"""
        project = self._projects.get(pid)
        if not project:
            return {"error": "项目不存在"}
        project.suggestions.append({
            "suggestion": suggestion,
            "timestamp": datetime.now().isoformat()
        })
        self._save_projects()
        return {"success": True, "suggestion_count": len(project.suggestions)}

    def generate_working_paper(self, pid: str, paper_type: str) -> dict:
        """生成工作底稿"""
        project = self._projects.get(pid)
        if not project:
            return {"error": "项目不存在"}

        template = WORKING_PAPER_TEMPLATES.get(paper_type, {})
        if not template:
            return {"error": f"未知底稿类型: {paper_type}"}

        # 自动填充
        paper = {
            "project_id": project.id,
            "project_name": project.name,
            "org_name": project.org_name,
            "paper_type": paper_type,
            "paper_name": template["name"],
            "sections": template["sections"],
            "generated_at": datetime.now().isoformat(),
            "content": {}
        }

        # 根据评分自动填充内容
        if paper_type == "WP08_评分汇总":
            paper["content"] = {
                "各维度评分": project.scores,
                "总分": project.total_score,
                "评级": project.grade,
                "主要问题": project.issues,
                "建议": project.suggestions
            }

        _log("paper", pid, paper_type)
        return paper

    def generate_report(self, pid: str) -> dict:
        """生成绩效评价报告"""
        project = self._projects.get(pid)
        if not project:
            return {"error": "项目不存在"}

        total_score = project.total_score or sum(project.scores.values())
        grade = project.grade
        if not grade:
            for g in PERFORMANCE_INDEX_SYSTEM["scoring_rule"]["grades"]:
                if g["min"] <= total_score <= g["max"]:
                    grade = g["grade"]
                    break

        # ponytail: strip redundant "绩效评价" suffix from project name
        name_clean = project.name
        if name_clean.endswith('绩效评价'):
            name_clean = name_clean[:-4]
        if f"{project.year}年度" not in name_clean:
            name_clean = f"{project.year}年度{name_clean}"
        report = {
            "title": f"{project.org_name}{name_clean}绩效评价报告",
            "generated_at": datetime.now().isoformat(),
            "sections": {
                "一、项目基本情况": {
                    "项目名称": project.name,
                    "被评价单位": project.org_name,
                    "单位类型": project.org_type,
                    "评价类型": project.project_type,
                    "预算金额": f"{project.budget}万元",
                    "评价年度": project.year
                },
                "二、绩效评价工作开展情况": {
                    "评价方法": ["文件检查", "访谈", "问卷调查", "现场观察", "数据分析"],
                    "评价过程": [
                        f"第{s['stage']}阶段-{s['name']}: {project.stage_status.get(s['id'], '未开始')}"
                        for s in PROCESS_STAGES
                    ],
                    "数据收集方式": "综合运用文件查阅、实地调研、问卷访谈等方式"
                },
                "三、绩效评价指标体系": {
                    "框架": "决策-过程-产出-效益 四维框架",
                    "总分": 100,
                    "指标层级": "一级指标4个，二级指标若干，三级指标若干",
                    "权重分配": {
                        d["name"]: f"{d['weight']}分"
                        for d in PERFORMANCE_INDEX_SYSTEM["dimensions"]
                    },
                    "评分标准": "优(≥90)、良(≥80)、中(≥60)、差(<60)"
                },
                "四、绩效目标实现程度": {
                    "各维度得分": project.scores,
                    "总得分": total_score,
                    "评级": grade,
                    "产出完成情况": "待补充实际数据",
                    "效益实现情况": "待补充实际数据"
                },
                "五、存在问题及原因分析": project.issues,
                "六、评价结论及建议": {
                    "总体结论": f"该项目绩效评价总得分{total_score}分，评级为「{grade}」。",
                    "建议": project.suggestions
                },
                "七、其他需要说明的问题": "无"
            }
        }

        _log("report", pid, f"title={report['title']}")
        return report


# 单例
engine = ProcessEngine(data_dir=os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"))


def get_trace():
    """返回最近100条数据流日志"""
    return list(_trace)
