"""勾稽自动校验引擎 — 纯函数, 无第三方依赖。
检查: ①指标体系权重完整性(静态) ②评分与总分级勾稽(动态) ③评级与总分一致性。
用法: run_checks(project, index_system) → findings 列表; engine.calculate_final_score 已自动挂接。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # ponytail: 直跑自检用
from regulations import PERFORMANCE_INDEX_SYSTEM


def _grade_of(total: float, scoring_rule: dict) -> str:
    # 与 engine.calculate_final_score 同算法: ≥min 命中
    for g in scoring_rule["grades"]:
        if total >= g["min"]:
            return g["grade"]
    return ""


def run_checks(project, index_system: dict = None) -> list:
    """project 需有 .scores/.total_score/.grade 属性。返回 [{level, check, detail}]"""
    idx = index_system or PERFORMANCE_INDEX_SYSTEM
    dims = idx["dimensions"]
    rule = idx.get("scoring_rule") or PERFORMANCE_INDEX_SYSTEM["scoring_rule"]
    findings = []

    # 1. 指标体系权重完整性 (静态, 每次全查)
    dim_sum = sum(d["weight"] for d in dims)
    if dim_sum != rule["max_score"]:
        findings.append({"level": "ERROR", "check": "维度权重合计",
                         "detail": f"{len(dims)}维度合计{dim_sum}分 ≠ 满分{rule['max_score']}分"})
    for d in dims:
        s = sum(i["weight"] for i in d.get("indices", []))
        if s != d["weight"]:
            findings.append({"level": "ERROR", "check": f"维度[{d['name']}]二级指标合计",
                             "detail": f"合计{s}分 ≠ 维度权重{d['weight']}分"})
        for i in d.get("indices", []):
            subs = i.get("sub_indices")
            if subs:
                ss = sum(x["weight"] for x in subs)
                if ss != i["weight"]:
                    findings.append({"level": "ERROR", "check": f"指标[{i['id']} {i['name']}]三级指标合计",
                                     "detail": f"合计{ss}分 ≠ 指标权重{i['weight']}分"})

    # 2. 评分勾稽 (动态)
    scores = project.scores or {}
    if not scores:
        return findings
    known = {d["name"] for d in dims}
    for name in scores:
        if name not in known:
            findings.append({"level": "WARN", "check": "未知评分维度",
                             "detail": f"[{name}]不在当前指标体系内, 不计入总分"})
    for d in dims:
        v = scores.get(d["name"])
        if v is not None and v > d["weight"]:
            findings.append({"level": "ERROR", "check": f"维度[{d['name']}]超权重",
                             "detail": f"得分{v} > 权重{d['weight']}"})
    ssum = sum(v for k, v in scores.items() if k in known)
    total = project.total_score
    if not total:
        findings.append({"level": "WARN", "check": "总分未计算",
                         "detail": "已录维度分但未执行最终计算"})
        return findings
    if abs(ssum - total) > 0.01:
        findings.append({"level": "ERROR", "check": "总分勾稽",
                         "detail": f"维度分合计{ssum} ≠ 存储总分{total}(评分后未重新计算)"})
    if total > rule["max_score"]:
        findings.append({"level": "ERROR", "check": "总分上限",
                         "detail": f"总分{total} > 满分{rule['max_score']}"})
    expect = _grade_of(total, rule)
    if project.grade and project.grade != expect:
        findings.append({"level": "ERROR", "check": "评级勾稽",
                         "detail": f"存储评级[{project.grade}] ≠ 总分{total}应对应[{expect}]"})
    return findings


if __name__ == "__main__":
    # 自检: 坏数据必须报错, 好数据必须干净
    from types import SimpleNamespace as NS
    bad = NS(scores={"决策": 20, "过程": 22}, total_score=87, grade="良")   # 决策超权重+总分不符
    errs = [f for f in run_checks(bad) if f["level"] == "ERROR"]
    assert any("超权重" in f["check"] for f in errs) and any("总分勾稽" in f["check"] for f in errs), errs
    good = NS(scores={"决策": 13, "过程": 22, "产出": 27, "效益": 25}, total_score=87, grade="良")
    assert not [f for f in run_checks(good) if f["level"] == "ERROR"], run_checks(good)
    print(f"OK: 坏数据捕获{len(errs)}项ERROR, 好数据0项 — 勾稽引擎自检通过")
