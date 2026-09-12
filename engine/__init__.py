"""
业务流程驱动引擎 — 8阶段绩效评价审计流程
========================================
ponytail: 状态机模式，一个dict驱动全部业务流程
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Any, Optional
import json
import os
import sys
import urllib.request
import threading
from collections import deque

# ponytail: import once at the top
from regulations import (
    PERFORMANCE_INDEX_SYSTEM, WORKING_PAPER_TEMPLATES, REPORT_TEMPLATE,
    CLASSIFICATIONS, WORKFLOW_REFS, get_classification, list_classifications,
    get_classification_kit,
)
from engine.stages import WORKFLOWS, get_workflow

# 分阶段完整流程定义（每阶段含资料/法规/前置/指引/沟通/重点/成果）
STAGE_WORKFLOWS = WORKFLOWS

# ponytail: ring buffer, 100 entries, overwrite oldest
_trace = deque(maxlen=100)
# ponytail: 秒级时间戳 PID 会碰撞，用进程内序号兜底防同秒覆盖
_pid_seq = 0
# ponytail: 单写锁(RLock可重入, create_project外层+_save_projects内层), 防 evolve 后台线程并发写
_save_lock = threading.RLock()


def _log(action, pid, detail=""):
    _trace.append({
        "ts": datetime.now().isoformat(), "action": action, "pid": pid, "detail": detail
    })

# ponytail: stdlib urllib → LLM, zero-dependency. Falls back if no key set.
# v6.0: 双模型 — deepseek(默认,推理/生成) + zhipu GLM(备选/中文法规)。可直接调用，key从Hermes配置获取。
LLM_PROVIDERS = {
    "deepseek": {
        "base": os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        "key_envs": ["DEEPSEEK_API_KEY"],
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "deep_model": "deepseek-reasoner",  # 深度推理: 法规推理/勾稽验证/进化分析用
    },
    "zhipu": {
        "base": os.environ.get("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
        "key_envs": ["ZHIPU_API_KEY", "GLM_API_KEY", "ZAI_API_KEY"],
        "models": ["glm-5.2", "glm-4.6"],
    },
}


def _llm_key(provider: str) -> str | None:
    for env in LLM_PROVIDERS[provider]["key_envs"]:
        if os.environ.get(env):
            return os.environ[env]
    return None


def llm_status() -> dict:
    """返回双模型可用状态（前端AI面板用）"""
    return {
        pid: {
            "available": _llm_key(pid) is not None,
            "models": conf["models"],
        }
        for pid, conf in LLM_PROVIDERS.items()
    }


def _call_llm(system_prompt: str, user_prompt: str, provider: str = None,
              temperature: float = 0.3, max_tokens: int = 2000,
              deep: bool = False) -> str | None:
    """调用LLM。provider=None时按 deepseek→zhipu 顺序自动降级。
    deep=True 时用深度推理模型(deepseek-reasoner)，用于法规推理/勾稽验证等复杂逻辑。"""
    chain = [provider] if provider else ["deepseek", "zhipu"]
    for pid in chain:
        conf = LLM_PROVIDERS.get(pid)
        if not conf:
            continue
        api_key = _llm_key(pid)
        if not api_key:
            continue
        # ponytail: deep模型仅在配置了deep_model的provider上生效，降级时用普通模型
        model = conf.get("deep_model") if (deep and conf.get("deep_model")) else conf["models"][0]
        body = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature, "max_tokens": max_tokens
        }).encode()
        req = urllib.request.Request(
            f"{conf['base'].rstrip('/')}/chat/completions",
            data=body,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        )
        try:
            resp = json.loads(urllib.request.urlopen(req, timeout=90).read())
            content = resp["choices"][0]["message"]["content"]
            # ponytail: reasoner可能把token全部耗在思维链→content为空串→降级下一家
            if content and content.strip():
                return content
        except Exception as e:
            print(f"[engine] _call_llm({pid}) failed: {e}", file=sys.stderr)
    return None

# ═══════════════════════════════════════════════════════════
# 业务流程定义 — v6.0 从 engine/stages.py 加载（每阶段完整工作包）
# 保留旧名 PROCESS_STAGES 供现有代码引用
# ═══════════════════════════════════════════════════════════
PROCESS_STAGES = get_workflow("standard_8")


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
    source_doc: dict = field(default_factory=dict)   # v7: 导入的合同/约定书 原件+抽取结果
    summary: str = ""                                # v7: 结项一句话教训
    archived_at: str = ""                            # v7: 归档时间(空=未归档)
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
        """加载已保存的项目 — 逐条容错，坏项跳过，不整库丢弃"""
        path = self._get_project_file()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                import sys
                print(f"[engine] corrupt projects.json, resetting", file=sys.stderr)
                self._projects = {}
                self._save_projects()
                return
            import sys
            for pid, pdict in data.items():
                try:
                    self._projects[pid] = AuditProject(**pdict)
                except (KeyError, TypeError, ValueError):
                    print(f"[engine] skipping corrupt project {pid}", file=sys.stderr)

    def _save_projects(self):
        """保存项目到磁盘 — 原子写入防数据损坏，单写锁防并发丢更新"""
        import tempfile
        path = self._get_project_file()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with _save_lock:
            data = {pid: asdict(p) for pid, p in self._projects.items()}
            # ponytail: write temp+rename, avoids corruption on crash
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".json")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                os.replace(tmp, path)
            except Exception:
                os.unlink(tmp)
                raise

    # ═══════════════════════════════════════════
    # 进度统计（内部用）
    # ═══════════════════════════════════════════

    def _count_completed(self) -> int:
        return sum(1 for p in self._projects.values() if p.total_score > 0)

    def create_project(self, **kwargs) -> AuditProject:
        """创建新的审计项目"""
        global _pid_seq
        # ponytail: 类型校验（API 层只校验必填，这里兜底类型）
        kwargs["budget"] = float(kwargs.get("budget", 0) or 0)
        kwargs["year"] = int(kwargs.get("year", 2024) or 2024)
        with _save_lock:
            _pid_seq += 1
            pid = f"PA{datetime.now().strftime('%Y%m%d%H%M%S')}{_pid_seq:02d}"
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
            "checklist": next_stage.get("checklist") or next_stage.get("key_points", []),
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
            "checklist": current.get("checklist") or current.get("key_points", []),
            "outputs": current["outputs"],
            "estimated_time": current["estimated_time"]
        }

    def get_stage_detail(self, pid: str) -> dict:
        """获取当前阶段详情 — v6.0 含资料/法规/前置/指引/沟通/重点完整工作包"""
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

        # 兼容旧字段: key_points → checklist
        checklist = stage.get("checklist") or stage.get("key_points", [])

        return {
            "project": asdict(project),
            "current": {
                "stage_num": stage["stage"],
                "total": len(PROCESS_STAGES),
                "name": stage["name"],
                "description": stage["description"],
                "checklist": checklist,
                "materials_needed": stage.get("materials_needed", []),
                "regulations": stage.get("regulations", []),
                "prerequisites": stage.get("prerequisites", []),
                "guides": stage.get("guides", []),
                "comm_coord": stage.get("comm_coord", []),
                "key_points": stage.get("key_points", []),
                "outputs": stage["outputs"],
                "estimated_time": stage["estimated_time"]
            },
            "all_stages": all_stages,
            "progress": f"{project.current_stage}/{len(PROCESS_STAGES)}",
            "percent": min(100, round(project.current_stage / len(PROCESS_STAGES) * 100))  # completed(9/8) 不溢出
        }

    def submit_score(self, pid: str, dimension: str, score: float, evidence: str = "") -> dict:
        """提交评分"""
        project = self._projects.get(pid)
        if not project:
            return {"error": "项目不存在"}

        # ponytail: clamp score to valid range; reject unknown dimension (no silent max=100)
        dim_def = next((d for d in PERFORMANCE_INDEX_SYSTEM["dimensions"] if d["name"] == dimension), None)
        if dim_def is None:
            return {"error": f"未知评分维度: {dimension}"}
        max_score = dim_def["weight"]
        score = max(0, min(score, max_score))

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

        # 评级 — 法规语义 ≥min 命中（优≥90/良≥80/中≥60/差<60），闭区间会漏 89.5 等非整数
        for g in PERFORMANCE_INDEX_SYSTEM["scoring_rule"]["grades"]:
            if total >= g["min"]:
                project.grade = g["grade"]
                break

        project.updated_at = datetime.now().isoformat()
        self._save_projects()
        _log("calculate", pid, f"total={total} grade={project.grade}")
        self._maybe_evolve()  # ponytail: background LLM analysis every 3 scored projects

        # 勾稽自动校验 — 引用本项目实际使用的指标体系(分类不同则维度不同)
        from engine.reconcile import run_checks
        from regulations import _CLASSIFICATION_INDEX, _INDEX_MAP
        idx_key = _CLASSIFICATION_INDEX.get(self.classification_for(project) or "", "project")
        reconciliation = run_checks(project, _INDEX_MAP.get(idx_key))
        for f in reconciliation:
            _log("reconcile", pid, f"[{f['level']}] {f['check']}: {f['detail']}")

        return {
            "total_score": total,
            "grade": project.grade,
            "reconciliation": reconciliation,
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
        if severity not in ("高", "中", "低"):
            severity = "中"  # ponytail: 枚举兜底，不接收任意字符串
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

    def get_learned_patterns(self, project_type: str = None) -> dict:
        """ponytail: 聚合历史项目 + AI进化洞察 + v7归档知识包经验"""
        from collections import Counter
        issues, suggestions = [], []
        # v7: 结项归档的经验教训直接进池
        try:
            from engine.project_pack import learned_from_archive
            archived = learned_from_archive(project_type)
        except Exception:
            archived = []
        for p in self._projects.values():
            if project_type and p.project_type != project_type:
                continue
            if p.total_score > 0:
                for item in p.issues:
                    issues.append(item["issue"])
                for item in p.suggestions:
                    suggestions.append(item["suggestion"])
        result = {
            "common_issues": [{"text": k, "count": v} for k, v in Counter(issues).most_common(10)],
            "common_suggestions": [{"text": k, "count": v} for k, v in Counter(suggestions).most_common(10)],
            "total_projects_analyzed": sum(1 for p in self._projects.values() if p.total_score > 0)
        }
        if archived:
            result["archived_lessons"] = archived   # v7: 结项知识包提炼的经验
        evo = self._load_evolution()
        if evo:
            result["evolution"] = evo
        return result

    # ═══════════════════════════════════════════════
    #  阶段一产出: 全项目工作流程/方案/计划/人员调配
    # ═══════════════════════════════════════════════

    def get_full_workflow(self, pid: str) -> dict:
        """该项目全部工作流程(每阶段完整工作包)"""
        project = self._projects.get(pid)
        if not project:
            return {"error": "项目不存在"}
        stages = [{
            "stage": s["stage"], "name": s["name"], "description": s["description"],
            "estimated_time": s["estimated_time"],
            "prerequisites": s.get("prerequisites", []),
            "materials_needed": s.get("materials_needed", []),
            "regulations": s.get("regulations", []),
            "guides": s.get("guides", []),
            "comm_coord": s.get("comm_coord", []),
            "key_points": s.get("key_points", []),
            "outputs": s["outputs"],
            "status": project.stage_status.get(s["id"], "pending"),
        } for s in PROCESS_STAGES]
        total_days = self._estimate_total_days(stages)
        return {
            "project": {"id": project.id, "name": project.name, "org_name": project.org_name,
                        "project_type": project.project_type, "budget": project.budget, "year": project.year},
            "stages": stages,
            "total_estimated_days": total_days,
        }

    # ponytail: 简单启发式 — "x-y天"取y，锁定=基准人数
    _WORKER_BASE = {"负责人": 1, "项目经理": 1, "成员": 2}

    def _estimate_total_days(self, stages: list) -> int:
        days = 0
        for s in stages:
            t = s.get("estimated_time", "")
            if "天" in t:
                num = "".join(ch for ch in t if ch.isdigit() or ch == "-")
                days += int(num.split("-")[-1]) if num else 0
        return days

    def generate_work_plan(self, pid: str, start_date: str = None,
                           team_size: int = None) -> dict:
        """阶段一交付: 工作流程+实施方案+工作计划+人员调配 一键生成"""
        project = self._projects.get(pid)
        if not project:
            return {"error": "项目不存在"}

        cls = get_classification(self.classification_for(project))
        wf = self.get_full_workflow(pid)
        stages = wf["stages"]
        total_days = wf["total_estimated_days"] or 30

        # 人员调配 — 按预算规模分层
        budget = project.budget or 0
        if budget >= 5000:
            tier = {"组长": 1, "项目经理": 1, "财务专家": 2, "行业专家": 2, "数据分析员": 2, "助理": 2}
        elif budget >= 500:
            tier = {"组长": 1, "项目经理": 1, "财务专家": 1, "行业专家": 1, "数据分析员": 1, "助理": 1}
        else:
            tier = {"组长(兼项目经理)": 1, "财务专家": 1, "助理": 1}
        team = [{"role": r, "count": n, "duty": self._role_duty(r)} for r, n in tier.items()]
        team_total = sum(n for _, n in tier.items())
        if team_size and team_size != team_total:
            team.append({"role": "机动人员", "count": max(0, team_size - team_total), "duty": "按需支援各环节"})

        # 时间计划 — 从起始日按阶段顺序排期
        try:
            cur = datetime.strptime(start_date, "%Y-%m-%d") if start_date else datetime.now()
        except ValueError:
            cur = datetime.now()
        schedule = []
        for s in stages:
            t = s.get("estimated_time", "")
            nums = [int(x) for x in "".join(ch if ch.isdigit() else " " for ch in t).split()]
            dur = (nums[-1] if nums else 1)
            end = cur + timedelta(days=dur)
            schedule.append({
                "stage": s["stage"], "name": s["name"], "duration_days": dur,
                "start": cur.strftime("%Y-%m-%d"), "end": end.strftime("%Y-%m-%d"),
                "outputs": s["outputs"], "lead_role": self._stage_lead(s),
            })
            cur = end + timedelta(days=1)

        return {
            "project": {"id": project.id, "name": project.name, "org_name": project.org_name,
                        "year": project.year, "budget": project.budget,
                        "classification": cls["name"] if cls else project.project_type},
            "workflow_summary": [{"stage": s["stage"], "name": s["name"], "time": s["estimated_time"],
                                  "outputs": s["outputs"]} for s in stages],
            "implementation_plan": {
                "评价对象": f"{project.org_name} {project.name}",
                "评价范围": f"{project.year}年度资金 {project.budget}万元",
                "评价方法": ["文件检查", "访谈", "问卷调查", "现场观察", "数据分析", "文献检索"],
                "指标框架": "决策-过程-产出-效益四维(财预〔2020〕10号)" if (cls is None or cls["id"] == "project_expenditure") else (cls["name"] + "专用指标体系"),
                "评价依据": [r["name"] + "(" + r["doc_no"] + ")" for r in (cls["reg_basis"] if cls else [])] or ["财预〔2020〕10号", "中发〔2018〕34号"],
                "成果形式": cls["deliverables"] if cls else ["绩效评价报告", "评分工作底稿", "归档清单"],
            },
            "team": team,
            "schedule": schedule,
            "total_days": total_days,
            "end_date": cur.strftime("%Y-%m-%d"),
        }

    def classification_for(self, project) -> Optional[str]:
        """项目类型 → 分类id"""
        mapping = {
            "项目支出": "project_expenditure", "部门整体": "department_overall",
            "资产管理": "asset_performance", "单位自评": "self_evaluation",
            "成本绩效": "cost_performance", "政策评价": "policy_evaluation",
        }
        return mapping.get(project.project_type)

    def _role_duty(self, role: str) -> str:
        duties = {
            "组长": "总体把关，审定方案与报告，对接委托方高层",
            "组长(兼项目经理)": "总体把关+现场组织，审定方案与报告",
            "项目经理": "现场组织、进度控制、质量把关、对外沟通",
            "财务专家": "资金拨付/凭证检查/预算执行分析",
            "行业专家": "业务流程核查/产出质量鉴定/效益分析",
            "数据分析员": "问卷统计分析/数据交叉验证/图表制作",
            "助理": "资料收发整理/访谈记录/底稿归档",
        }
        return duties.get(role, "按项目组安排")

    def _stage_lead(self, stage: dict) -> str:
        lead_map = {"业务承接": "组长", "计划评价工作": "项目经理", "指标体系细化": "项目经理",
                    "数据收集与证据获取": "项目经理", "分析评分": "财务专家", "报告撰写与沟通": "组长",
                    "质量控制": "组长", "归档与后续": "助理"}
        return lead_map.get(stage["name"], "项目经理")

    def generate_stage1_docs(self, pid: str, start_date: str = None) -> dict:
        """阶段一一键产出: 方案+计划+人员调配(报告全文由 LLM 增强生成)"""
        plan = self.generate_work_plan(pid, start_date)
        if "error" in plan:
            return plan
        # LLM 增强: 生成方案正文要点（失败静默降级为结构化数据）
        system = "你是资深财政绩效评价专家。根据给定的项目信息和阶段安排，输出一份精炼的绩效评价实施方案要点(500字内)，包含: 评价思路、重点难点、创新点。直接输出文字。"
        user = json.dumps(plan["implementation_plan"], ensure_ascii=False) + "\n阶段安排:" + json.dumps(
            plan["workflow_summary"], ensure_ascii=False)
        insight = _call_llm(system, user[:6000], max_tokens=1200)
        plan["ai_brief"] = insight or "（LLM未配置，展示结构化要点）"
        _log("stage1_docs", pid, f"work plan generated, {plan['total_days']}days, team={sum(t['count'] for t in plan['team'])}")
        return plan

    # ═══════════════════════════════════════════════
    #  AI 自动进化引擎
    # ═══════════════════════════════════════════════

    def _load_evolution(self) -> dict | None:
        path = os.path.join(self.data_dir, "evolution.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return None  # 损坏 → 降级返回空，不 crash 调用方
        return None

    def evolve(self) -> dict:
        """ponytail: LLM分析全部已完成项目，自主生成权重调整/新指标/风险模式建议"""
        # ponytail: snapshot under GIL, then daemon thread uses copy only
        projects_snapshot = [
            p for p in self._projects.values() if p.total_score > 0
        ]
        if len(projects_snapshot) < 2:
            return {"error": "至少需要2个已完成项目", "projects": len(projects_snapshot)}

        summary = [{
            "name": p.name, "org_type": p.org_type, "project_type": p.project_type,
            "total_score": p.total_score, "grade": p.grade, "scores": p.scores,
            "issues": [i["issue"] for i in p.issues],
            "suggestions": [s["suggestion"] for s in p.suggestions]
        } for p in projects_snapshot]

        system = """你是绩效评价审计专家。分析历史项目数据，输出JSON：
{
  "weight_adjustments": [{"dimension": "...", "current_weight": N, "suggested_weight": N, "reason": "..."}],
  "new_indicators": [{"name": "...", "dimension": "...", "scoring_criteria": "..."}],
  "common_risk_patterns": [{"pattern": "...", "frequency": "高/中/低", "suggested_checklist": "..."}],
  "evolution_summary": "综合分析一段话"
}
只输出JSON。"""

        user = json.dumps(summary, ensure_ascii=False, indent=2)
        insight = _call_llm(system, user[:12000], deep=True)
        if not insight:
            return {"error": "LLM调用失败(deepseek/zhipu均不可用)。检查DEEPSEEK_API_KEY/ZHIPU_API_KEY。"}

        try:
            parsed = json.loads(insight)
        except json.JSONDecodeError:
            parsed = {"raw_insight": insight}

        import tempfile
        path = os.path.join(self.data_dir, "evolution.json")
        fd, tmp = tempfile.mkstemp(dir=self.data_dir, suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({
                    "generated_at": datetime.now().isoformat(),
                    "projects_analyzed": len(projects_snapshot),
                    "insights": parsed
                }, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
        except Exception:
            os.unlink(tmp)
            raise

        _log("evolve", "system", f"analyzed {len(projects_snapshot)} projects → evolution.json")
        return {"success": True, "projects_analyzed": len(projects_snapshot), "insights": parsed}

    def _maybe_evolve(self):
        """ponytail: 每3个新项目触发一次后台LLM进化"""
        completed = sum(1 for p in self._projects.values() if p.total_score > 0)
        if completed >= 3 and completed % 3 == 0:
            threading.Thread(target=self.evolve, daemon=True).start()

    def ai_consult(self, question: str, context: str = "", provider: str = None,
                   deep: bool = False) -> dict:
        """AI咨询: 直接调用 deepseek/zhipu 大模型回答绩效评价业务问题。
        deep=True 走 deepseek-reasoner 深度推理（法规适用/数据勾稽等复杂问题）。"""
        if not question or not question.strip():
            return {"error": "问题不能为空"}
        system = """你是资深财政绩效评价专家，精通财预〔2020〕10号、中发〔2018〕34号、成本预算绩效管理等。
回答要专业、具体、可操作，引用法规文号，按条目组织。"""
        user = (f"背景: {context}\n" if context else "") + f"问题: {question}"
        answer = _call_llm(system, user[:8000], provider=provider,
                           max_tokens=2500 if not deep else 4000, deep=deep)
        if not answer:
            return {"error": "LLM调用失败(deepseek/zhipu均不可用)"}
        used = provider or "deepseek"
        _log("ai_consult", "system", f"provider={used} deep={deep} q={question[:40]}")
        return {"success": True, "provider": used, "deep": deep,
                "question": question, "answer": answer}

    def ai_score_suggest(self, pid: str) -> dict:
        """AI辅助评分建议: 基于项目信息和已有问题清单，给出各维度评分建议和理由"""
        project = self._projects.get(pid)
        if not project:
            return {"error": "项目不存在"}
        system = """你是财政绩效评价专家。根据项目信息和建议问题清单，输出JSON(只输出JSON):
{"suggestions": [{"dimension": "决策/过程/产出/效益", "suggested_score": N, "max_score": N, "reason": "..."}],
 "risk_flags": ["需要现场重点核实的事项"]}
dimension必须恰好是这四个。"""
        user = json.dumps({
            "项目": project.name, "单位": project.org_name, "类型": project.org_type,
            "预算": project.budget, "年度": project.year,
            "已录入问题": [i["issue"] for i in project.issues],
            "历史同类项目常见问题": self.get_learned_patterns().get("common_issues", [])[:5],
            "归档项目经验教训": self.get_learned_patterns(project.project_type).get("archived_lessons", [])[:3],
        }, ensure_ascii=False)
        raw = _call_llm(system, user, max_tokens=1500)
        if not raw:
            return {"error": "LLM调用失败"}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            # 宽松提取JSON块
            import re
            m = re.search(r"\{.*\}", raw, re.S)
            try:
                parsed = json.loads(m.group()) if m else {"raw": raw}
            except json.JSONDecodeError:
                parsed = {"raw": raw}
        _log("ai_score_suggest", pid, "score suggestions generated")
        return {"success": True, "suggestions": parsed.get("suggestions", parsed.get("raw", [])),
                "risk_flags": parsed.get("risk_flags", [])}

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
            # 与 calculate_final_score 同算法：≥min 命中（避免 89.5 等非整数落空）
            for g in PERFORMANCE_INDEX_SYSTEM["scoring_rule"]["grades"]:
                if total_score >= g["min"]:
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
