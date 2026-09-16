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
from .stages import get_workflow
_PROCESS_STAGES = get_workflow("standard_8")

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


def _safe_pid_dir(pid: str) -> str:
    """ponytail: pid必须严格是PA+数字, 防URL注入穿越outputs目录(全部文件写入共用)"""
    import re
    if not re.fullmatch(r"PA\d{16,18}", pid or ""):
        raise ValueError(f"非法项目编号: {pid!r}")
    return os.path.join(ROOT, "outputs", pid)


def _safe_filename(filename: str) -> str:
    # ponytail: strip path/ADS chars; NTFS reserved names (CON/NUL) skip — uploads always carry real extensions
    return filename.replace(":", "_").replace("/", "_").replace("\\", "_")


def save_source_file(pid: str, filename: str, content: bytes) -> str:
    """合同原件存入项目包 outputs/<pid>/source/"""
    dest_dir = os.path.join(_safe_pid_dir(pid), "source")
    os.makedirs(dest_dir, exist_ok=True)
    safe = _safe_filename(filename)
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
    pdir = _safe_pid_dir(pid)
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
        try:
            created.append(_import_one(extracted, f))
        except Exception as e:   # ponytail: 单份失败不拖垮整批, 逐份报告
            created.append({"filename": f["filename"], "error": f"{type(e).__name__}: {e}"})
    return {"success": True, "created": created,
            "ok": sum(1 for c in created if c.get("pid"))}


def _import_one(extracted: dict, f: dict) -> dict:
    """learn_and_create 内层: 单份文件抽取+建项+入库。抛异常由外层捕获。"""
    ext = os.path.splitext(f["filename"])[1].lower()
    if ext not in (".pdf", ".docx", ".doc", ".txt", ".md"):
        return {"filename": f["filename"], "error": f"不支持的格式: {ext}"}
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
        return {"filename": f["filename"], "error": "文本过少(可能为扫描件)"}
    extracted = dict(extracted or {})
    fields = extract_project_fields(text)
    fields.update({k: v for k, v in extracted.items() if v})   # 手填覆盖LLM
    if fields.get("error"):
        return {"filename": f["filename"], "error": fields["error"]}
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
    return {"filename": f["filename"], "pid": pid,
            "name": proj.name, "confidence": fields.get("confidence")}


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

    out = os.path.join(_safe_pid_dir(pid), "deliverables", f"归档报告_{pid}.docx")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    doc.save(out)
    return {"success": True, "path": out}


# ── 2.5 阶段资料导入与流程自适应 (v7.2) ──────────────────

def stage_upload(pid: str, stage_id: str, filename: str, content: bytes) -> dict:
    """阶段资料/沟通记录/前置情况文件导入 → 存 outputs/<pid>/stages/<stage_id>/ 并记入stage_records"""
    project = engine.get_project(pid)
    if not project:
        return {"error": "项目不存在"}
    stage_ids = {s["id"] for s in _PROCESS_STAGES}
    if stage_id not in stage_ids:
        return {"error": f"未知阶段: {stage_id}"}
    safe = _safe_filename(filename)
    dest = os.path.join(_safe_pid_dir(pid), "stages", stage_id)
    os.makedirs(dest, exist_ok=True)
    path = os.path.join(dest, safe)
    with open(path, "wb") as f:
        f.write(content)
    rec = project.stage_records.setdefault(stage_id, {"files": [], "notes": []})
    rec["files"].append({"name": safe, "size": len(content), "at": datetime.now().isoformat()})
    project.updated_at = datetime.now().isoformat()
    engine._save_projects()
    _log("stage_upload", pid, f"{stage_id} ← {safe}")
    return {"success": True, "file": safe}


def stage_note(pid: str, stage_id: str, note_type: str, text: str) -> dict:
    """文字记录: 沟通协调过程与结果 / 前置条件落实情况 / 其他备注 (note_type: comm|prereq|note)"""
    project = engine.get_project(pid)
    if not project:
        return {"error": "项目不存在"}
    stage_ids = {s["id"] for s in _PROCESS_STAGES}
    if stage_id not in stage_ids:
        return {"error": f"未知阶段: {stage_id}"}
    if not text or not text.strip():
        return {"error": "内容不能为空"}
    rec = project.stage_records.setdefault(stage_id, {"files": [], "notes": []})
    rec["notes"].append({"type": note_type, "text": text.strip()[:2000],
                         "at": datetime.now().isoformat()})
    project.updated_at = datetime.now().isoformat()
    engine._save_projects()
    _log("stage_note", pid, f"{stage_id} [{note_type}] {len(text)}字")
    return {"success": True}


ADJUST_SYSTEM = """你是绩效评价项目管理专家。项目执行中导入了新资料/出现新情况，分析其对后续阶段的影响。
后续阶段定义: {stages}
只输出JSON: {{"focus": "10字概括新情况", "changes": [{{"stage_id": "阶段id", "change": "调整建议(30字内)", "reason": "依据(40字内)"}}]}}
只列确需调整的阶段(0-4个)，依据只能来自给定资料，不编造。无实质影响则changes为空数组。"""


def adjust_plan(pid: str) -> dict:
    """AI根据该项目已导入的全部资料+记录 → 对后续阶段流程给出调整建议"""
    project = engine.get_project(pid)
    if not project:
        return {"error": "项目不存在"}
    if project.current_stage > len(_PROCESS_STAGES):
        return {"error": "项目已完成全部阶段，无可调整的后续流程"}
    stages_desc = "; ".join(f"{s['stage']}.{s['name']}({s['id']})" for s in _PROCESS_STAGES)
    # 语料: 导入资料清单 + 沟通/前置记录 + 项目概况
    corpus = [f"项目: {project.name} | {project.project_type} | 预算{project.budget}万 | 第{project.current_stage}阶段"]
    for s in _PROCESS_STAGES:
        rec = project.stage_records.get(s["id"])
        if rec:
            corpus.append(f"阶段{s['stage']}({s['name']}) 已导入文件: {', '.join(f['name'] for f in rec['files']) or '无'}")
            corpus += [f"  记录[{n['type']}]: {n['text'][:300]}" for n in rec["notes"]]
    if getattr(project, "source_doc", {}).get("requirements"):
        corpus.append("合同关键要求: " + "; ".join(project.source_doc["requirements"]))
    if len(corpus) <= 1:
        return {"error": "尚无导入资料或记录，先在各阶段导入资料/填写沟通记录后再试"}
    # ponytail: 不用deep=True — reasoner把max_tokens烧在思维链导致JSON截断, 结构化短输出chat足够
    raw = _call_llm(ADJUST_SYSTEM.format(stages=stages_desc), "\n".join(corpus)[:12000],
                    max_tokens=1500, deep=False)
    if not raw:
        return {"error": "LLM调用失败(deepseek/zhipu均不可用)"}
    parsed = _safe_json(raw)
    if "changes" not in parsed:
        return {"error": "LLM返回非JSON", "raw": str(parsed)[:300]}
    valid_ids = {s["id"] for s in _PROCESS_STAGES}
    parsed["changes"] = [c for c in parsed["changes"] if c.get("stage_id") in valid_ids][:4]
    parsed["ts"] = datetime.now().isoformat()
    project.plan_adjustments.append(parsed)   # 留痕: 项目包可追溯每次调整
    project.updated_at = datetime.now().isoformat()
    engine._save_projects()
    _log("adjust_plan", pid, f"focus={parsed.get('focus','?')} changes={len(parsed['changes'])}")
    return parsed


def pending_adjustments(pid: str) -> list:
    """该阶段未处理的调整建议(推进阶段时前端提示用) — 全部已注入, 仅供展示"""
    project = engine.get_project(pid)
    if not project or not project.plan_adjustments:
        return []
    cur = project.current_stage
    return [a for a in project.plan_adjustments
            if any(c.get("stage_id") == _PROCESS_STAGES[min(cur, 8) - 1]["id"] for c in a.get("changes", []))]


def apply_adjustments(pid: str) -> dict:
    """AI调整建议 → 改写本项目工作流模板(项目级覆盖, 不动全局stages.py)。

    每个 change 追加到该阶段: guides/key_points 去重后加"🔧AI调整:"前缀条目,
    同时在 stage_status 同级记录 applied_adjustments 留痕。返回逐条应用结果。
    """
    project = engine.get_project(pid)
    if not project or not project.plan_adjustments:
        return {"error": "无可应用的调整建议"}
    # 项目级流程覆盖: 写入project.flow_overrides, get_stage_detail/begin优先读取
    applied, seen = [], set()
    for a in project.plan_adjustments:
        if a.get("applied"):
            continue   # 已应用过的批次跳过(幂等)
        for c in a.get("changes", []):
            sid, change, reason = c.get("stage_id"), c.get("change", ""), c.get("reason", "")
            if not sid or not change or (sid, change) in seen:
                continue
            seen.add((sid, change))
            ov = project.flow_overrides.setdefault(sid, {"guides": [], "key_points": [], "applied_at": ""})
            entry = f"🔧AI调整: {change}（依据: {reason}）"
            target = ov["guides"]   # 调整建议本质是执行动作 → 进操作指引
            if entry not in target:
                target.append(entry)
            ov["applied_at"] = datetime.now().isoformat()
            applied.append({"stage_id": sid, "entry": entry})
        a["applied"] = True
    if not applied:
        return {"error": "调整建议均已应用过"}
    project.updated_at = datetime.now().isoformat()
    engine._save_projects()
    _log("apply_adjustments", pid, f"applied={len(applied)}")
    return {"success": True, "applied": applied}


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
    raw = _call_llm(ARCHIVE_SYSTEM, user[:10000], max_tokens=3000, deep=False)  # ponytail: JSON输出禁reasoner(思维链吃max_tokens致截断), llm-output-verification §8
    if not raw:
        return {"error": "LLM调用失败(deepseek/zhipu均不可用)，未落知识库，请稍后重试"}  # ponytail: 审查P2 — 畸形lessons不进KB污染学习池
    lessons = _safe_json(raw)
    if "one_line_lesson" not in lessons:
        return {"error": "LLM返回结构异常，未落知识库，请重试", "raw": str(lessons)[:200]}

    entry = {
        "pid": pid, "name": project.name, "org_type": project.org_type,
        "project_type": project.project_type, "year": project.year,
        "scores": project.scores, "total_score": project.total_score, "grade": project.grade,
        "lessons": lessons, "archived_at": datetime.now().isoformat(),
    }
    from engine import _save_lock
    with _save_lock:   # ponytail: 复用engine同一把锁, 防并发归档read-modify-write丢条目
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
