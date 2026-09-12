# -*- coding: utf-8 -*-
"""项目包引擎 — 导入立项 → 项目包聚合 → 结项知识沉淀。
全生命周期三段:
  1. import_source_doc: 合同/业务约定书 → 文本 → LLM抽取字段 → 预填项目(用户确认后创建)
  2. build_pack: 项目包 = 基本信息+适用法规+执行记录+成果+资料 全聚合
  3. archive_project: 结项 → LLM提炼经验教训 → data/knowledge_base.json (注入后续AI建议)
"""
import os, json, tempfile
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


def learn_and_create(extracted: dict, files: list[dict]) -> dict:
    """批量导入: 依次LLM抽取每份文件 → 用户确认后一次性建N个项目(原件各自入库)。

    files: [{filename, bytes}]。extracted 可含 {name, org_name, org_type, project_type,
    budget, year} 覆盖LLM抽取值(单文件模式用)。
    """
    from . import engine
    created = []
    for f in files:
        import tempfile
        ext = os.path.splitext(f["filename"])[1].lower()
        if ext not in (".pdf", ".docx", ".doc", ".txt", ".md"):
            created.append({"filename": f["filename"], "error": f"不支持的格式: {ext}"})
            continue
        fd, tmp = tempfile.mkstemp(suffix=ext)
        os.close(fd)  # ponytail: Windows mkstemp句柄不关会锁文件
        try:
            with open(tmp, "wb") as fh:
                fh.write(f["bytes"])
            text = _doc_to_text(tmp)
        finally:
            try:
                os.unlink(tmp)
            except PermissionError:
                pass
        if len(text.strip()) < 50:
            created.append({"filename": f["filename"], "error": "文本过少(可能为扫描件)"})
            continue
        extracted = dict(extracted or {})
        fields = extract_project_fields(text)
        fields.update({k: v for k, v in extracted.items() if v})   # 手填覆盖LLM
        if fields.get("error"):
            created.append({"filename": f["filename"], "error": fields["error"]})
            continue
        proj = engine.create_project(
            name=fields.get("project_name") or os.path.splitext(f["filename"])[0],
            org_name=fields.get("org_name") or "待补充",
            org_type=fields.get("org_type") or "事业单位",
            project_type=fields.get("project_type") or "项目支出",
            budget=float(fields.get("budget") or 0),
            year=int(fields.get("year") or datetime.now().year),
        )
        pid = proj.id
        path = save_source_file(pid, f["filename"], f["bytes"])
        attach_source(pid, path, fields)
        created.append({"filename": f["filename"], "pid": pid,
                        "name": proj.name, "confidence": fields.get("confidence")})
    return {"success": True, "created": created,
            "ok": sum(1 for c in created if c.get("pid"))}


def export_archive_report(pid: str) -> dict:
    """结项归档报告导出 word: 项目包全量数据 → docx (python-docx)。"""
    pack = build_pack(pid)
    if pack.get("error"):
        return pack
    project = engine.get_project(pid)
    from docx import Document
    from docx.shared import Pt
    doc = Document()
    doc.styles["Normal"].font.name = "宋体"
    doc.styles["Normal"].font.size = Pt(12)

    def h(t, lv=1):
        doc.add_heading(t, level=lv)

    def p(t, bold=False):
        para = doc.add_paragraph()
        run = para.add_run(str(t)) if t not in (None, "") else para.add_run("—")
        run.bold = bold

    def table(rows: list[list], header: bool = True):
        if not rows:
            return
        t = doc.add_table(rows=len(rows), cols=len(rows[0]))
        t.style = "Table Grid"
        for i, row in enumerate(rows):
            for j, v in enumerate(row):
                t.cell(i, j).text = str(v) if v not in (None, "") else "—"
        if header:
            for j, v in enumerate(rows[0]):
                t.cell(0, j).paragraphs[0].runs[0].bold = True

    b, ex, regs, fd = pack["basic"], pack["execution"], pack["regulations"], pack["findings"]
    sd = b.get("source_doc") or {}
    h(f"绩效评价项目结项归档报告 — {b['name']}", 0)
    p(f"项目编号: {b['id']}    生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}", bold=True)

    h("一、项目基本信息")
    table([["项目名称", b["name"], "被评价单位", b["org_name"]],
           ["单位类型", b["org_type"], "评价类型", b["project_type"]],
           ["预算(万元)", b["budget"], "评价年度", b["year"]],
           ["立项依据", sd.get("file", "—"), "导入时间", (sd.get("imported_at") or "—")[:10]],
           ["结项归档", (getattr(project, "archived_at", None) or "未归档")[:10],
            "AI一句话教训", getattr(project, "summary", None) or "—"]])

    h("二、适用法规与指标体系")
    if regs.get("kit"):
        p("指标体系: " + str(regs.get("index_name")))
        p("评价流程: " + str(regs["kit"].get("workflow") or "—"))
        p("适用法规: " + "; ".join(r["name"] for r in regs["kit"]["classification"]["reg_basis"]))
    else:
        p("未匹配分类，使用项目支出通用指标体系")

    h("三、全过程执行记录")
    rows = [["阶段", "名称", "状态"]]
    rows += [[str(s["stage"]), s["name"], {"completed": "完成", "in_progress": "进行中"}.get(s["status"], "未开始")] for s in ex["stages"]]
    table(rows)
    p(f"当前进度: 第{ex['current_stage']}阶段 ({ex['percent']}%)", bold=True)

    h("四、评分结果")
    if ex["scores"] and sum(1 for v in ex["scores"].values() if v):
        table([["维度", "得分"]] + [[k, v] for k, v in ex["scores"].items()] +
              [["总分", ex["total_score"]], ["评级", ex["grade"] or "—"]])
    else:
        p("未评分")

    h("五、发现与建议")
    if fd["issues"]:
        table([["严重度", "问题"]] + [[i["severity"], i["issue"]] for i in fd["issues"]])
    if fd["suggestions"]:
        table([["建议"]] + [[s["suggestion"]] for s in fd["suggestions"]])
    if not fd["issues"] and not fd["suggestions"]:
        p("无记录")

    h("六、资料清单")
    if pack["files"]:
        table([["类别", "文件", "大小(KB)"]] +
              [[{"source": "立项原件", "deliverables": "成果文件"}.get(f["section"], f["section"]),
                f["name"], round(f["size"] / 1024)] for f in pack["files"]])
    else:
        p("无")

    h("七、归档经验(AI提炼)" if pack["archived"] else "七、归档经验(未归档)")
    from engine.project_pack import load_knowledge_base
    entry = next((e for e in load_knowledge_base() if e.get("pid") == pid), None)
    if entry:
        l = entry.get("lessons", {})
        for key, title in (("issue_patterns", "高发问题模式"), ("effective_practices", "有效做法"),
                           ("template_tips", "模板要点"), ("indicator_insights", "指标心得")):
            for x in (l.get(key) or []):
                p("• " + str(x))
        p("核心教训: " + str(l.get("one_line_lesson", "—")), bold=True)
    else:
        p("项目未归档或无提炼结果。可先在项目包页执行「结项归档」。")

    out = os.path.join(ROOT, "outputs", pid, "deliverables", f"归档报告_{pid}.docx")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    doc.save(out)
    return {"success": True, "path": out}


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
