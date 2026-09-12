"""
绩效评价审计智能体 — Flask 主应用
"""
from flask import Flask, render_template, request, jsonify, send_file
from datetime import datetime
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import engine, PROCESS_STAGES, get_trace, llm_status
from regulations import (
    REGULATIONS, PERFORMANCE_INDEX_SYSTEM, ASSET_PERFORMANCE_INDEX,
    EVIDENCE_METHODS, CASE_LIBRARY, WORKING_PAPER_TEMPLATES,
    search_regulations, get_index_system, get_case,
    list_classifications, get_classification_kit, search_classifications,
    COST_PERFORMANCE_KB, PLAN_REVIEW_CHECKLIST,
)

app = Flask(__name__)
# ponytail: env var or random, single-user local
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", os.urandom(24).hex())

# ═══════════════════════════════════════════════
# 路由 — 页面
# ═══════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/projects")
def projects_page():
    return render_template("projects.html")


@app.route("/workflow/<pid>")
def workflow_page(pid):
    project = engine.get_project(pid)
    if not project:
        return "项目不存在", 404
    return render_template("workflow.html", pid=pid)


@app.route("/scoring/<pid>")
def scoring_page(pid):
    project = engine.get_project(pid)
    if not project:
        return "项目不存在", 404
    return render_template("scoring.html", pid=pid)


@app.route("/report/<pid>")
def report_page(pid):
    return render_template("report.html", pid=pid)


@app.route("/workplan/<pid>")
def workplan_page(pid):
    project = engine.get_project(pid)
    if not project:
        return "项目不存在", 404
    return render_template("workplan.html", pid=pid)


@app.route("/regulations")
def regulations_page():
    return render_template("regulations.html")


@app.route("/classifications")
def classifications_page():
    return render_template("classifications.html")


@app.route("/ai")
def ai_page():
    return render_template("ai.html")


# ═══════════════════════════════════════════════
# API — 项目
# ═══════════════════════════════════════════════

@app.route("/api/projects", methods=["GET"])
def api_list_projects():
    projects = engine.list_projects()
    return jsonify([{
        "id": p.id, "name": p.name, "org_name": p.org_name,
        "org_type": p.org_type, "current_stage": p.current_stage,
        "total_stages": len(PROCESS_STAGES),
        "percent": min(100, round(p.current_stage / len(PROCESS_STAGES) * 100)),
        "total_score": p.total_score, "grade": p.grade,
        "created_at": p.created_at
    } for p in projects])


@app.route("/api/projects", methods=["POST"])
def api_create_project():
    data = request.json or {}
    required = ["name", "org_name", "org_type", "project_type"]
    for f in required:
        if f not in data:
            return jsonify({"error": f"缺少必填字段: {f}"}), 400
    project = engine.create_project(
        name=data["name"], org_name=data["org_name"],
        org_type=data["org_type"], project_type=data["project_type"],
        budget=float(data.get("budget", 0)),
        year=int(data.get("year", 2024))
    )
    return jsonify({"success": True, "project_id": project.id})


@app.route("/api/projects/<pid>", methods=["GET"])
def api_get_project(pid):
    result = engine.get_stage_detail(pid)
    return jsonify(result)


# ═══════════════════════════════════════════
# API — 流程
# ═══════════════════════════════════════════

@app.route("/api/projects/<pid>/advance", methods=["POST"])
def api_advance_stage(pid):
    result = engine.advance_stage(pid)
    return jsonify(result)


@app.route("/api/projects/<pid>/go-to-stage", methods=["POST"])
def api_go_to_stage(pid):
    data = request.json
    result = engine.go_to_stage(pid, data.get("stage", 1))
    return jsonify(result)


@app.route("/api/stages", methods=["GET"])
def api_get_stages():
    return jsonify(PROCESS_STAGES)


# ═══════════════════════════════════════════
# API — 评分
# ═══════════════════════════════════════════

@app.route("/api/projects/<pid>/score", methods=["POST"])
def api_submit_score(pid):
    data = request.json or {}
    dim = data.get("dimension", "")
    score = float(data.get("score", 0))
    if not dim:
        return jsonify({"error": "缺少 dimension 字段"}), 400
    result = engine.submit_score(pid, dim, score, data.get("evidence", ""))
    return jsonify(result)


@app.route("/api/projects/<pid>/calculate", methods=["POST"])
def api_calculate_score(pid):
    result = engine.calculate_final_score(pid)
    return jsonify(result)


@app.route("/api/projects/<pid>/issue", methods=["POST"])
def api_add_issue(pid):
    data = request.json or {}
    issue = data.get("issue", "").strip()
    if not issue:
        return jsonify({"error": "缺少 issue 字段"}), 400
    result = engine.add_issue(pid, issue, data.get("severity", "中"))
    return jsonify(result)


@app.route("/api/projects/<pid>/suggestion", methods=["POST"])
def api_add_suggestion(pid):
    data = request.json or {}
    suggestion = data.get("suggestion", "").strip()
    if not suggestion:
        return jsonify({"error": "缺少 suggestion 字段"}), 400
    result = engine.add_suggestion(pid, suggestion)
    return jsonify(result)


# ═══════════════════════════════════════════
# API — 底稿与报告
# ═══════════════════════════════════════════

@app.route("/api/projects/<pid>/working-paper", methods=["POST"])
def api_generate_working_paper(pid):
    data = request.json
    result = engine.generate_working_paper(pid, data.get("paper_type", "WP01_计划审计工作"))
    return jsonify(result)


@app.route("/api/projects/<pid>/report", methods=["POST"])
def api_generate_report(pid):
    result = engine.generate_report(pid)
    return jsonify(result)


# ═══════════════════════════════════════════
# API — 法规库
# ═══════════════════════════════════════════

@app.route("/api/regulations", methods=["GET"])
def api_regulations():
    keyword = request.args.get("keyword", "")
    if keyword:
        return jsonify(search_regulations(keyword))
    return jsonify(REGULATIONS)


@app.route("/api/index-system", methods=["GET"])
def api_index_system():
    category = request.args.get("category", "project")
    return jsonify(get_index_system(category))


@app.route("/api/evidence-methods", methods=["GET"])
def api_evidence_methods():
    return jsonify(EVIDENCE_METHODS)


@app.route("/api/cases", methods=["GET"])
def api_cases():
    case_id = request.args.get("id")
    return jsonify(get_case(case_id))


@app.route("/api/paper-templates", methods=["GET"])
def api_paper_templates():
    templates = {k: v["name"] for k, v in WORKING_PAPER_TEMPLATES.items()}
    return jsonify(templates)


@app.route("/api/learn/patterns", methods=["GET"])
def api_learn_patterns():
    """ponytail: 从历史项目聚合学习 — 常见问题+建议"""
    project_type = request.args.get("project_type")
    return jsonify(engine.get_learned_patterns(project_type))


@app.route("/api/learn/evolve", methods=["POST"])
def api_learn_evolve():
    """ponytail: 手动触发LLM进化分析"""
    result = engine.evolve()
    return jsonify(result)


@app.route("/api/trace", methods=["GET"])
def api_trace():
    """数据流跟踪日志 — 最近100条操作记录"""
    return jsonify(get_trace())


# ═══════════════════════════════════════════════
# API — 分类体系 (v6.0)
# ═══════════════════════════════════════════════

@app.route("/api/classifications", methods=["GET"])
def api_classifications():
    keyword = request.args.get("keyword", "")
    if keyword:
        return jsonify(search_classifications(keyword))
    return jsonify(list_classifications())


@app.route("/api/classifications/<cid>", methods=["GET"])
def api_classification_kit(cid):
    """分类工作包: 法规库+流程+沟通模板+成果+指标体系"""
    return jsonify(get_classification_kit(cid))


@app.route("/api/cost-performance-kb", methods=["GET"])
def api_cost_kb():
    """成本预算绩效管理知识库（上海模式/濮阳八步/零基预算/真实核减案例）"""
    return jsonify(COST_PERFORMANCE_KB)


@app.route("/api/plan-review-checklist", methods=["GET"])
def api_plan_review():
    """方案质量评审自查清单（17条常见缺陷+必备要素）"""
    return jsonify(PLAN_REVIEW_CHECKLIST)


# ═══════════════════════════════════════════════
# API — 阶段一产出: 流程/方案/计划/人员 (v6.0)
# ═══════════════════════════════════════════════

@app.route("/api/projects/<pid>/full-workflow", methods=["GET"])
def api_full_workflow(pid):
    """该项目全部工作流程 — 每阶段: 资料/法规/前置/操作/沟通/重点/成果"""
    return jsonify(engine.get_full_workflow(pid))


@app.route("/api/projects/<pid>/work-plan", methods=["GET", "POST"])
def api_work_plan(pid):
    """一键生成: 工作流程+实施方案+工作计划+人员调配"""
    data = request.json or {} if request.is_json else {}
    start_date = data.get("start_date") or request.args.get("start_date")
    team_size = data.get("team_size") or request.args.get("team_size", type=int)
    return jsonify(engine.generate_work_plan(pid, start_date=start_date, team_size=team_size))


@app.route("/api/projects/<pid>/stage1-docs", methods=["POST"])
def api_stage1_docs(pid):
    """阶段一一键产出(含AI方案要点)"""
    data = request.json or {}
    return jsonify(engine.generate_stage1_docs(pid, start_date=data.get("start_date")))


# ═══════════════════════════════════════════════
# API — AI 大模型 (v6.0: deepseek + zhipu GLM)
# ═══════════════════════════════════════════════

@app.route("/api/ai/status", methods=["GET"])
def api_ai_status():
    return jsonify(llm_status())


@app.route("/api/ai/consult", methods=["POST"])
def api_ai_consult():
    data = request.json or {}
    return jsonify(engine.ai_consult(
        data.get("question", ""),
        context=data.get("context", ""),
        provider=data.get("provider"),
    ))


@app.route("/api/projects/<pid>/ai-score-suggest", methods=["POST"])
def api_ai_score_suggest(pid):
    return jsonify(engine.ai_score_suggest(pid))


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  绩效评价审计智能体 — Performance Evaluation Audit Agent v6.0")
    print("=" * 60)
    print(f"  法规库: {len(REGULATIONS)}部法规 | 分类体系: {len(list_classifications())}类")
    print(f"  案例库: {len(CASE_LIBRARY)}个案例")
    print(f"  业务流程: {len(PROCESS_STAGES)}阶段(每阶段完整工作包)")
    print(f"  底稿模板: {len(WORKING_PAPER_TEMPLATES)}个")
    ai = llm_status()
    print(f"  AI模型: deepseek({'✓' if ai['deepseek']['available'] else '✗'}) + zhipu GLM({'✓' if ai['zhipu']['available'] else '✗'})")
    print(f"\n  访问: http://localhost:5199")
    print("=" * 60 + "\n")
    # ponytail: debug 默认开(本地开发)；生产设 FLASK_DEBUG=0 关闭(禁用Werkzeug调试器RCE面)
    app.run(host="127.0.0.1", port=5199, debug=os.environ.get("FLASK_DEBUG", "1") == "1")
