# -*- coding: utf-8 -*-
"""
企业绩效评价标准值2026集成测试
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from regulations import ENTERPRISE_STANDARDS_2026, get_industry_standard, batch_score

def test_standards_loaded():
    """标准值加载验证"""
    assert len(ENTERPRISE_STANDARDS_2026["industries"]) == 5
    assert len(ENTERPRISE_STANDARDS_2026["all_indicators"]) == 22
    print("✓ 标准值加载: 5行业 × 22指标")

def test_industry_query():
    """行业查询"""
    coal = get_industry_standard(industry_code="06")
    assert coal["name"] == "煤炭开采和洗选业"
    assert "净资产收益率" in coal["standards"]
    print("✓ 行业查询: 煤炭开采和洗选业")

def test_scoring():
    """评分逻辑"""
    result = batch_score("17", {
        "净资产收益率": 6.5,
        "总资产报酬率": 2.8,
        "营业收入利润率": 5.2,
        "资产负债率": 68.0,
        "总资产周转率": 0.35
    })
    assert result["industry_name"] == "房地产业"
    assert 0 <= result["total_score"] <= 100
    assert result["grade"] in ["优秀", "良好", "平均", "较低", "较差"]
    print(f"✓ 评分计算: {result['industry_name']} {result['total_score']}分 ({result['grade']})")
    for d in result["details"]:
        print(f"  - {d['indicator']}: {d['actual']} → {d['score']}分({d['grade']})")

def test_retrieval_integration():
    """检索引擎集成"""
    from engine.retrieval import search
    r = search("企业绩效评价 标准值 行业对标")
    found = any(x["ref_id"] == "enterprise_standards_2026" for x in r["results"])
    assert found, "企业标准值未入检索语料"
    print("✓ 检索集成: 企业标准值2026已入语料")

def test_api_integration():
    """API接口可用性"""
    from app.app import app
    with app.test_client() as client:
        # GET 标准值列表
        resp = client.get("/api/enterprise-standards-2026")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["version"] == "2026"
        print("✓ API接口: GET /api/enterprise-standards-2026")
        
        # GET 单个行业
        resp = client.get("/api/enterprise-standards-2026?industry=17")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["name"] == "房地产业"
        print("✓ API接口: GET /api/enterprise-standards-2026?industry=17")
        
        # POST 评分
        resp = client.post("/api/enterprise-score", json={
            "industry_code": "17",
            "indicators": {
                "净资产收益率": 6.5,
                "总资产报酬率": 2.8
            }
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert "total_score" in data
        print(f"✓ API接口: POST /api/enterprise-score → {data['total_score']}分")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  企业绩效评价标准值2026集成测试")
    print("="*60 + "\n")
    
    test_standards_loaded()
    test_industry_query()
    test_scoring()
    test_retrieval_integration()
    test_api_integration()
    
    print("\n" + "="*60)
    print("  全部测试通过 ✓")
    print("="*60 + "\n")
