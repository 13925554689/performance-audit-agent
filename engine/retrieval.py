# -*- coding: utf-8 -*-
"""向量检索引擎 — 智谱 embedding-3 (2048维) + 纯Python余弦检索。

语料 = 法规(R*) + 案例(CASE) + 归档项目经验(knowledge_base.json)。
索引缓存 data/embeddings.json，语料指纹变化时增量重建；API不可用时降级关键词检索。
"""
import os, sys, json, math, hashlib, urllib.request
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 脚本直跑时可用项目根包
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IDX_PATH = os.path.join(ROOT, "data", "embeddings.json")

EMB_BASE = os.environ.get("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
EMB_MODEL = "embedding-3"
_DIM_FALLBACK: list | None = None   # ponytail: 零依赖降级向量，词袋hash到1024维


def _corpus() -> list[dict]:
    """构建检索语料: 9法规 + 8案例 + N归档经验。"""
    from regulations import REGULATIONS, CASE_LIBRARY
    from engine.project_pack import load_knowledge_base
    docs = []
    for r in REGULATIONS:
        docs.append({"kind": "regulation", "ref_id": r["id"], "name": r["name"],
                     "text": f"{r['name']} {r.get('doc_no','')} {r.get('issuer','')} {r.get('key_content','')}"})
    for c in CASE_LIBRARY:
        docs.append({"kind": "case", "ref_id": c["id"], "name": c["name"],
                     "text": f"{c['name']} {c.get('org','')} 预算{c.get('budget')}万 " +
                             " ".join(c.get("highlights", []) + c.get("issues", []))})
    for e in load_knowledge_base():
        docs.append({"kind": "archived_project", "ref_id": e.get("pid", ""),
                     "name": f"归档:{e.get('name','')}",
                     "text": f"{e.get('name','')} {e.get('project_type','')} 评级{e.get('grade','')} " +
                             json.dumps(e.get("lessons", {}), ensure_ascii=False)})
    return docs


def _fingerprint(docs: list[dict]) -> str:
    return hashlib.sha256("\n".join(d["text"] for d in docs).encode()).hexdigest()[:16]


def _fallback_vec(text: str) -> list[float]:
    import re
    v = [0.0] * 1024
    for w in re.findall(r"[\u4e00-\u9fff]{2,6}|[a-zA-Z0-9]+", text.lower()):
        v[hashlib.md5(w.encode()).digest()[:4].__hash__() % 1024] += 1.0
    return v


def _embed(texts: list[str]) -> tuple[list[list[float]], str]:
    """批量调用智谱embedding。返回(向量列表, 'api'|'fallback')。"""
    global _DIM_FALLBACK
    key = os.environ.get("ZHIPU_API_KEY") or os.environ.get("GLM_API_KEY") or os.environ.get("ZAI_API_KEY")
    if not key:
        return [_fallback_vec(t) for t in texts], "fallback"
    out = []
    for i in range(0, len(texts), 16):   # ponytail: 批16, 语料<64条一次循环够用
        body = json.dumps({"model": EMB_MODEL, "input": texts[i:i + 16]}).encode()
        req = urllib.request.Request(EMB_BASE + "/embeddings", data=body,
                                     headers={"Content-Type": "application/json",
                                              "Authorization": f"Bearer {key}"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                d = json.loads(resp.read())
            out += [item["embedding"] for item in d["data"]]
        except Exception:
            return [_fallback_vec(t) for t in texts], "fallback"
    return out, "api"


def _cosine(a: list[float], b: list[float]) -> float:
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
    if not na or not nb:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / (na * nb)


def _load_index() -> dict:
    if os.path.exists(IDX_PATH):
        try:
            return json.load(open(IDX_PATH, encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_index(idx: dict):
    os.makedirs(os.path.dirname(IDX_PATH), exist_ok=True)
    json.dump(idx, open(IDX_PATH, "w", encoding="utf-8"), ensure_ascii=False)


def search(query: str, top_k: int = 5, kind: str = None) -> dict:
    """语义检索。kind: regulation|case|archived_project|None(全部)。"""
    docs = _corpus()
    if kind:
        docs = [d for d in docs if d["kind"] == kind]
    if not docs or not query or not query.strip():
        return {"results": [], "engine": "none", "corpus": len(docs)}

    fp = _fingerprint(docs)
    idx = _load_index()
    if idx.get("fingerprint") != fp or idx.get("v") != 2:   # v2: 键序 kind|ref_id
        vecs, source = _embed([d["text"] for d in docs])
        idx = {"v": 2, "fingerprint": fp, "source": source, "built_at": datetime.now().isoformat(),
               "dim": len(vecs[0]), "docs": {d["kind"] + "|" + d["ref_id"]: v for d, v in zip(docs, vecs)}}
        _save_index(idx)

    key = {d["kind"] + "|" + d["ref_id"] for d in docs}
    kv = [(k, v) for k, v in idx["docs"].items() if k in key]
    qv, source = _embed([query])
    scored = sorted(((_cosine(qv[0], v), k) for k, v in kv), reverse=True)[:top_k]
    meta = {d["kind"] + "|" + d["ref_id"]: d for d in docs}
    return {"engine": source, "corpus": len(docs), "results": [
        {"score": round(s, 4), "kind": k.split("|")[0], "ref_id": k.split("|")[1],
         "name": meta[k]["name"]} for s, k in scored]}


def context_for_llm(query: str, top_k: int = 4) -> str:
    """给AI咨询/归档提炼用的检索上下文块。"""
    r = search(query, top_k=top_k)
    return "\n".join(f"[{x['kind']}:{x['ref_id']}] {x['name']} (相关度{x['score']})" for x in r["results"])


if __name__ == "__main__":
    r = search("项目支出绩效评价 立项依据 不充分")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    assert r["results"] and all(0 <= x["score"] <= 1 for x in r["results"])
    r2 = search("部门整体 履职效能", kind="case")
    assert all(x["kind"] == "case" for x in r2["results"])
    print("SELF-CHECK OK: engine=%s corpus=%d" % (r["engine"], r["corpus"]))
