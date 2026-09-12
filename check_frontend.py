# -*- coding: utf-8 -*-
"""前端静态自检: 引用的JS文件存在 + PID变量 + 分类页/AI页接口字段"""
import os, re

ok = True
for f in os.listdir("app/templates"):
    if not f.endswith(".html"):
        continue
    html = open(os.path.join("app/templates", f), encoding="utf-8").read()
    for m in re.findall(r'src="(/static/js/[^"]+)"', html):
        p = os.path.join("app", "static", "js", os.path.basename(m))
        if not os.path.exists(p):
            print(f"[FAIL] {f}: 缺少 {m}")
            ok = False
    if "{{ pid }}" in html or "{{pid}}" in html:
        if "const PID" not in html and "PID =" not in html:
            print(f"[FAIL] {f}: 引用pid但未定义PID")
            ok = False

# workflow.js 用到的新字段必须由 engine 提供
import sys
sys.path.insert(0, ".")
from engine import engine, PROCESS_STAGES
need = ["materials_needed", "regulations", "prerequisites", "guides", "comm_coord", "key_points", "outputs"]
missing = [k for k in need if k not in PROCESS_STAGES[0]]
if missing:
    print("[FAIL] PROCESS_STAGES 缺字段:", missing)
    ok = False

print("PASS: 前端静态自检通过" if ok else "FAIL")
