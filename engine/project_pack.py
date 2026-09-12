# -*- coding: utf-8 -*-
"""项目包引擎 — 导入立项 → 项目包聚合 → 结项知识沉淀。
全生命周期三段:
  1. import_source_doc: 合同/业务约定书 → 文本 → LLM抽取字段 → 预填项目(用户确认后创建)
  2. build_pack: 项目包 = 基本信息+适用法规+执行记录+成果+资料 全聚合
  3. archive_project: 结项 → LLM提炼经验教训 → data/knowledge_base.json (注入后续AI建议)
"""
import os, sys, json, tempfile
from datetime import datetime
from . import _call_llm, _log, engine

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB_PATH = os.path.join(ROOT, "data", "knowledge_base.json")


# ── 1. 导入合同/业务约定书 ──────────────────────────────

def _doc_to_text(path: str) -> str:
    """复用 convert_docs 的转换逻辑 (ponytail: 不再抽公共模块, 两处各30行)"""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        import fitz
        doc = fitz.open(path)
        text = "\n".join(page.get_text("text") for page in doc)
        doc.close()
        return text
    if ext in (".docx", ".doc"):
        from docx import Document
        return "\n".join(p.text for p in Document(path).paragraphs if p.text.strip())
    if ext in (".txt", ".md"):
        return open(path, encoding="utf-8", errors="replace").read()
    raise ValueError(f"不支持的格式: {ext} (支持 pdf/docx/txt/md)")


EXTRACT_SYSTEM = """你是财政绩效评价业务承接专家。从合同/业务约定书/实施方案文本中抽取项目要素，输出JSON(只输出JSON):
{"project_name": "评价项目名称", "org_name": "被评价单位全称", "org_type": "行政单位|事业单位|国有企业",
 "project_type": "项目支出|部门整体|单位自评|成本绩效|政策评价|资产管理",
 "budget": 数值(万元,提取不到填0), "year": 数值(评价年度), "commissioner": "委托方",
 "scope": "评价范围与内容(50字内)", "key_requirements": ["评价要求1", "要求2"],
 "confidence": "高|中|低"}
提取不到的字段填空字符串/0，不要编造。confidence=低 表示文本太短或非合同类文档。"""


def extract_project_fields(text: str) -> dict:
    """LLM抽取 → dict; 失败返回 {"error": ...}"""
    raw = _call_llm(EXTRACT_SYSTEM, text[:12000], max_tokens=1500, deep=True)
    if not raw:
        return {"error": "LLM抽取失败(deepseek/zhipu均不可用)"}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        import re
        m = re.search(r"\{.*\}", raw, re.S)
        try:
            return json.loads(m.group()) if m else {"error": "LLM返回非JSON", "raw": raw[:300]}
        except json.JSONDecodeError:
            return {"error": "LLM返回非JSON", "raw": raw[:300]}


def save_source_file(pid: str, filename: str, content: bytes) -> str:
    """合同原件存入项目包 outputs/<pid>/source/"""
    dest_dir = os.path.join(ROOT, "outputs", pid, "source")
    os.makedirs(dest_dir, exist_ok=True)
    safe = filename.replace("/", "_").replace("\\", "_")
    dest = os.path.join(dest_dir, safe)
    with open(dest, "wb") as f:
        f.write(content)
    return dest


def attach_source(pid: str, filepath: str, extracted: dict) -> dict:
    """把导入来源(原文路径+抽取结果+关键要求)记到项目上 — 项目包'资料来源'区块"""
    project = engine.get_project(pid)
    if not project:
        return {"error": "项目不存在"}
    project.source_doc = {
        "file": os.path.basename(filepath),
        "path": filepath,
        "imported_at": datetime.now().isoformat(),
        "extracted": extracted,
        "requirements": extracted.get("key_requirements", []),
    }
    project.updated_at = datetime.now().isoformat()
    engine._save_projects()
    _log("import", pid, f"source={os.path.basename(filepath)} conf={extracted.get('confidence')}")
    return {"success": True}


# ── 2. 项目包聚合 (全生命周期一个视图) ───────────────────

def build_pack(pid: str) -> dict:
    """项目包: 基本信息/适用法规与知识库/全过程执行/成果/资料/总结"""
    from regulations import get_classification_kit, _CLASSIFICATION_INDEX, _INDEX_MAP
    project = engine.get_project(pid)
    if not project:
        return {"error": "项目不存在"}

    # 适用法规: 分类 → 法规库+指标体系+流程 (classification kit 现成)
    cid = engine.classification_for(project) or ""
    kit = get_classification_kit(cid) if cid else None

    # 全过程执行记录
    stages = [{
        "stage": s["stage"], "name": s["name"], "status": project.stage_status.get(s["id"], "pending"),
    } for s in __import__("engine", fromlist=["PROCESS_STAGES"]).PROCESS_STAGES]

    # 项目资料: 上传原件 + 生成的成果文件
    pdir = os.path.join(ROOT, "outputs", pid)
    files = []
    for sub in ("source", "deliverables"):
        d = os.path.join(pdir, sub)
        if os.path.isdir(d):
            files += [{"name": f, "section": sub, "size": os.path.getsize(os.path.join(d, f))}
                      for f in os.listdir(d)]

    return {
        "basic": {"id": project.id, "name": project.name, "org_name": project.org_name,
                  "org_type": project.org_type, "project_type": project.project_type,
                  "budget": project.budget, "year": project.year,
                  "created_at": project.created_at, "source_doc": getattr(project, "source_doc", None)},
        "regulations": {"kit": kit, "index_name": _INDEX_MAP[
            _CLASSIFICATION_INDEX.get(cid, "project")]["name"] if cid else "项目支出通用指标体系"},
        "execution": {"stages": stages, "current_stage": project.current_stage,
                      "percent": min(100, round(project.current_stage / len(stages) * 100)),
                      "scores": project.scores, "total_score": project.total_score, "grade": project.grade},
        "findings": {"issues": project.issues, "suggestions": project.suggestions,
                     "evidence": project.evidence_files},
        "files": files,
        "summary": project.summary if getattr(project, "summary", None) else None,
        "archived": bool(getattr(project, "archived_at", None)),
    }


# ── 3. 结项 → 知识沉淀 ─────────────────────────────────

ARCHIVE_SYSTEM = """你是绩效评价知识管理专家。分析这个已完成项目的全量数据，提炼可复用经验，输出JSON(只输出JSON):
{"issue_patterns": ["该类项目高发问题模式(带场景条件)"],
 "effective_practices": ["证明有效的做法"],
 "template_tips": ["报告/底稿/沟通的模板要点"],
 "indicator_insights": ["指标与权重设置的心得"],
 "one_line_lesson": "一句话核心教训"}
只从给定数据提炼，不编造数据中不存在的内容。"""


def archive_project(pid: str) -> dict:
    """结项归档: 项目包 → LLM提纯 → knowledge_base.json → 后续项目AI建议自动引用"""
    project = engine.get_project(pid)
    if not project:
        return {"error": "项目不存在"}
    if project.total_score <= 0:
        return {"error": "项目未完成评分，不能结项归档"}

    pack = build_pack(pid)
    user = json.dumps({
        "项目": pack["basic"], "评分": pack["execution"]["scores"],
        "总分": project.total_score, "评级": project.grade,
        "问题": [i["issue"] for i in project.issues],
        "建议": [s["suggestion"] for s in project.suggestions],
        "分类": pack["regulations"]["index_name"],
    }, ensure_ascii=False)
    raw = _call_llm(ARCHIVE_SYSTEM, user[:10000], max_tokens=2000, deep=True)
    lessons = {"raw": raw[:2000]} if not raw else _safe_json(raw)

    entry = {
        "pid": pid, "name": project.name, "org_type": project.org_type,
        "project_type": project.project_type, "year": project.year,
        "scores": project.scores, "total_score": project.total_score, "grade": project.grade,
        "lessons": lessons, "archived_at": datetime.now().isoformat(),
    }
    kb = load_knowledge_base()
    kb = [e for e in kb if e["pid"] != pid] + [entry]   # ponytail: 重归档=覆盖
    tmp_fd, tmp = tempfile.mkstemp(dir=os.path.dirname(KB_PATH) if os.path.isdir(os.path.dirname(KB_PATH)) else ROOT, suffix=".json")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(kb, f, ensure_ascii=False, indent=2)
        os.replace(tmp, KB_PATH)
    except Exception:
        os.unlink(tmp)
        raise

    project.archived_at = datetime.now().isoformat()
    project.summary = lessons.get("one_line_lesson", "")
    engine._save_projects()
    _log("archive", pid, f"grade={project.grade} lessons={len(lessons)}")
    return {"success": True, "lessons": lessons, "kb_size": len(kb)}


def _safe_json(raw: str) -> dict:
    import re
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.S)
        try:
            return json.loads(m.group()) if m else {"raw": raw[:2000]}
        except json.JSONDecodeError:
            return {"raw": raw[:2000]}


def load_knowledge_base() -> list:
    if os.path.exists(KB_PATH):
        try:
            return json.load(open(KB_PATH, encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
    return []


def learned_from_archive(project_type: str = None) -> list:
    """给 get_learned_patterns / ai_score_suggest 用的归档经验"""
    kb = load_knowledge_base()
    if project_type:
        kb = [e for e in kb if e.get("project_type") == project_type]
    return [e["lessons"] for e in kb if e.get("lessons")]
