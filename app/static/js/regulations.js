// regulations.js — 法规库页面

async function init() {
    await Promise.all([
        loadRegulations(),
        loadIndexSystem('project'),
        loadEvidenceMethods(),
        loadCases()
    ]);
}

async function loadRegulations(keyword = '') {
    const url = keyword ? `/api/regulations?keyword=${encodeURIComponent(keyword)}` : '/api/regulations';
    const regs = await API(url);
    document.getElementById('regList').innerHTML = regs.map(r => `
        <div class="reg-card">
            <h4>${r.name} <span style="font-weight:normal;font-size:.8rem;color:#999">${r.doc_no}</span></h4>
            <div class="reg-meta">${r.issuer} | ${r.level} | ${r.category} | ${r.effective_date}</div>
            <ul class="reg-points">
                ${r.key_content.map(k => `<li>${k}</li>`).join('')}
            </ul>
        </div>
    `).join('');
}

function searchRegs() {
    loadRegulations(document.getElementById('searchInput').value);
}

let currentTab = 'project';

async function switchTab(tab) {
    currentTab = tab;
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');
    loadIndexSystem(tab);
}

async function loadIndexSystem(category) {
    const idx = await API(`/api/index-system?category=${category}`);
    document.getElementById('indexSystem').innerHTML = `
        <p style="margin-bottom:.5rem;color:var(--gray-700)">依据: ${idx.based_on || '财预〔2020〕10号'} | 总分: ${idx.scoring_rule.max_score}分</p>
        ${idx.dimensions.map(dim => `
            <div class="reg-card">
                <h4>📌 ${dim.name} (权重: ${dim.weight}分)</h4>
                <ul class="reg-points">
                    ${(dim.indices || []).map(idx => `
                        <li><strong>${idx.id || ''} ${idx.name}</strong> (${idx.weight}分)
                            ${idx.sub_indices ? '<ul>' + idx.sub_indices.map(sub =>
                                `<li>${sub.id} ${sub.name} (${sub.weight}分) — ${sub.criteria || ''}</li>`
                            ).join('') + '</ul>' : ''}
                            ${idx.criteria ? ` — ${idx.criteria}` : ''}
                        </li>
                    `).join('')}
                </ul>
            </div>
        `).join('')}
    `;
}

async function loadEvidenceMethods() {
    const methods = await API('/api/evidence-methods');
    document.getElementById('evidenceMethods').innerHTML = `<div class="paper-grid">` +
        methods.map(m => `
            <div class="paper-item" style="text-align:left;cursor:default">
                <strong>${m.name}</strong>
                <p style="font-size:.8rem;color:#666">${m.desc}</p>
                <small style="color:var(--primary)">工具: ${m.tools.join(', ')}</small><br>
                <small>产出: ${m.output}</small>
            </div>
        `).join('') + '</div>';
}

async function loadCases() {
    const cases = await API('/api/cases');
    document.getElementById('caseList').innerHTML = cases.map(c => `
        <div class="reg-card">
            <h4>${c.name} <span style="font-weight:normal;font-size:.8rem;color:#999">${c.org} | ${c.year}年 | 预算${c.budget}万元</span></h4>
            <p style="font-size:.85rem;margin:.25rem 0">
                总得分: <strong style="font-size:1.1rem">${c.total_score}</strong>分 | 评级: <strong>${c.grade}</strong>
            </p>
            <p style="font-size:.8rem;color:var(--success)">✅ 亮点: ${c.highlights.join('；')}</p>
            <p style="font-size:.8rem;color:var(--warning)">⚠️ 问题: ${c.issues.join('；')}</p>
            <p style="font-size:.8rem;color:var(--primary)">💡 建议: ${c.suggestions.join('；')}</p>
        </div>
    `).join('');
}

init();
