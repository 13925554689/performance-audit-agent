"""端到端功能验证脚本"""
import urllib.request, json, sys

BASE = "http://localhost:5199"

def api(path, method="GET", body=None):
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(
        f"{BASE}{path}", data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method=method
    )
    resp = urllib.request.urlopen(req, timeout=10)
    return json.loads(resp.read())

# 1. 创建项目
p = api("/api/projects", "POST", {
    "name": "2024年度信息化建设经费绩效评价",
    "org_name": "XX市数据管理局",
    "org_type": "事业单位",
    "project_type": "项目支出",
    "budget": 500.0,
    "year": 2024
})
pid = p["project_id"]
print(f"✅ 1. 创建项目: {pid}")

# 2. 推进全部8阶段
for _ in range(7):
    api(f"/api/projects/{pid}/advance", "POST")
detail = api(f"/api/projects/{pid}")
print(f"✅ 2. 业务流程: {detail['progress']} ({detail['percent']}%) — 当前: {detail['current']['name']}")

# 3. 评分
for dim, score in [("决策", 13.0), ("过程", 22.0), ("产出", 27.0), ("效益", 25.0)]:
    api(f"/api/projects/{pid}/score", "POST", {"dimension": dim, "score": score})
result = api(f"/api/projects/{pid}/calculate", "POST")
print(f"✅ 3. 评分: 总分{result['total_score']}分 | 评级「{result['grade']}」")

# 4. 问题与建议
api(f"/api/projects/{pid}/issue", "POST", {"issue": "部分绩效指标量化不足", "severity": "中"})
api(f"/api/projects/{pid}/suggestion", "POST", {"suggestion": "加强事前绩效目标论证"})
proj = api(f"/api/projects/{pid}")
print(f"✅ 4. 问题: {len(proj['project']['issues'])}条 | 建议: {len(proj['project']['suggestions'])}条")

# 5. 生成底稿
paper = api(f"/api/projects/{pid}/working-paper", "POST", {"paper_type": "WP08_评分汇总"})
print(f"✅ 5. 底稿: {paper['paper_name']} — {len(paper['sections'])}章节")

# 6. 生成报告
report = api(f"/api/projects/{pid}/report", "POST")
print(f"✅ 6. 报告: {report['title']}")
for section in report["sections"]:
    print(f"   ✓ {section}")

# 7. 法规库
regs = api("/api/regulations")
idx = api("/api/index-system")
cases = api("/api/cases")
templates = api("/api/paper-templates")
print(f"✅ 7. 知识库: {len(regs)}部法规 | {len(idx['dimensions'])}维度 | {len(cases)}案例 | {len(templates)}底稿模板")

print("\n" + "=" * 50)
print("🎉 全部验证通过！绩效评价审计智能体运行正常")
print(f"   访问: http://localhost:5199")
print("=" * 50)
