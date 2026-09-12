// scoring.js — 评分页面

let indexSystem = null;
let projectData = null;
let scores = {};

async function init() {
    const [proj, idx] = await Promise.all([
        API(`/api/projects/${PID}`),
        API('/api/index-system?category=project')
    ]);
    projectData = proj;
    indexSystem = idx;

    document.getElementById('projectHeader').innerHTML = `
        <h2>${proj.project.name}</h2>
        <div class="org-info">${proj.project.org_name} | 当前评分: ${proj.project.total_score || '未计算'} | ${proj.project.grade || '未评级'}</div>
    `;

    renderScoringGrid();
    if (proj.project.scores) {
        scores = { ...proj.project.scores };
        updateInputs();
    }
    renderIssues();
    renderSuggestions();
}

function renderScoringGrid() {
    const grid = document.getElementById('scoringGrid');
    const colors = ['#1a56db', '#7c3aed', '#059669', '#d97706'];

    grid.innerHTML = indexSystem.dimensions.map((dim, di) => `
        <div class="score-card">
            <div class="score-card-header" style="background:${colors[di % 4]}">
                ${dim.name} (权重: ${dim.weight}分)
            </div>
            <div class="score-card-body">
                ${(dim.indices || []).map(idx => `
                    <div style="margin-bottom:.5rem;padding:.5rem;background:var(--gray-50);border-radius:4px">
                        <strong>${idx.id} ${idx.name}</strong> (权重${idx.weight}分)
                        ${idx.sub_indices ? idx.sub_indices.map(sub => `
                            <div class="score-input-row">
                                <label title="${sub.criteria || ''}">${sub.id} ${sub.name}</label>
                                <input type="number" class="score-val"
                                    id="score_${sub.id}" min="0" max="${sub.weight}"
                                    step="0.5" onchange="onScoreChange('${dim.name}', this)">
                                <span class="max-score">/${sub.weight}</span>
                            </div>
                        `).join('') : `
                            <div class="score-input-row">
                                <label title="${idx.criteria || ''}">${idx.name}</label>
                                <input type="number" class="score-val"
                                    id="score_${idx.id}" min="0" max="${idx.weight}"
                                    step="0.5" onchange="onScoreChange('${dim.name}', this)">
                                <span class="max-score">/${idx.weight}</span>
                            </div>
                        `}
                    </div>
                `).join('')}
            </div>
        </div>
    `).join('');
}

function onScoreChange(dim, input) {
    const dimScores = [];
    const gridEl = document.getElementById('scoringGrid');
    // 找出当前维度的所有输入
    const dimCards = gridEl.querySelectorAll('.score-card');
    dimCards.forEach(card => {
        const header = card.querySelector('.score-card-header');
        if (header && header.textContent.includes(dim)) {
            card.querySelectorAll('.score-val').forEach(inp => {
                dimScores.push(parseFloat(inp.value) || 0);
            });
        }
    });
    const total = dimScores.reduce((a, b) => a + b, 0);
    scores[dim] = total;
}

async function submitAllScores() {
    for (const [dim, score] of Object.entries(scores)) {
        await API(`/api/projects/${PID}/score`, {
            method: 'POST',
            body: JSON.stringify({ dimension: dim, score: score })
        });
    }
    const result = await API(`/api/projects/${PID}/calculate`, { method: 'POST' });
    showResult(result);
}

async function showResult(result) {
    const card = document.getElementById('resultCard');
    card.style.display = 'block';

    const gradeColors = { '优': '#22c55e', '良': '#3b82f6', '中': '#f59e0b', '差': '#ef4444' };
    card.querySelector('#resultSummary').innerHTML = `
        <div class="big-score">${result.total_score.toFixed(1)}</div>
        <div class="grade" style="background:${gradeColors[result.grade]}20;color:${gradeColors[result.grade]}">
            ${result.grade}
        </div>
        <div style="margin-top:.5rem;text-align:left">
            ${(result.dimensions || []).map(d =>
                `<div class="dimension-bar">
                    <span style="width:80px">${d.name}:</span>
                    <div class="dim-bar-track">
                        <div class="dim-bar-fill" style="width:${(d.score/d.weight*100).toFixed(0)}%;background:${gradeColors[result.grade]}"></div>
                    </div>
                    <span>${d.score}/${d.weight}</span>
                </div>`
            ).join('')}
            ${(result.reconciliation || []).length ? `
            <div style="margin-top:.75rem;background:#fffbeb;border-left:3px solid #f59e0b;padding:.5rem .8rem;border-radius:6px">
                <b>🔍 勾稽校验 (${result.reconciliation.length}项提示)</b>
                ${result.reconciliation.map(f => `<div style="margin:.25rem 0;font-size:.9rem">
                    <span style="color:${f.level === 'ERROR' ? '#ef4444' : '#f59e0b'};font-weight:bold">[${f.level}]</span>
                    ${f.check}: ${f.detail}</div>`).join('')}
            </div>` : `
            <div style="margin-top:.75rem;background:#f0fdf4;border-left:3px solid #22c55e;padding:.4rem .8rem;border-radius:6px;font-size:.9rem">
                ✅ 勾稽校验通过：维度分合计=总分、评级与总分一致、无超权重
            </div>`}
        </div>
        <button class="btn btn-primary" style="margin-top:1rem" onclick="submitAllScores()">🔄 重新计算</button>
        <button class="btn btn-secondary" style="margin-top:1rem" onclick="aiSuggest()">🤖 AI评分建议</button>
        <div id="aiSuggestBox" style="margin-top:.75rem;text-align:left"></div>
    `;
}

async function aiSuggest() {
    const box = document.getElementById('aiSuggestBox');
    box.innerHTML = '<div class="spinner"></div> AI分析中(DeepSeek)...';
    const res = await API(`/api/projects/${PID}/ai-score-suggest`, { method: 'POST' });
    if (res.error) { box.innerHTML = `<p style="color:#ef4444">❌ ${res.error}</p>`; return; }
    const list = Array.isArray(res.suggestions) ? res.suggestions : [];
    box.innerHTML = `
        <div style="background:#f0f9ff;border-left:3px solid #1a56db;padding:.6rem .9rem;border-radius:6px">
            <b>🤖 AI评分建议</b>
            ${list.map(s => `<div style="margin:.4rem 0">
                <b>${s.dimension}</b>: 建议 ${s.suggested_score}/${s.max_score} 分 — ${s.reason || ''}</div>`).join('') || '<p>' + JSON.stringify(res.suggestions).slice(0, 400) + '</p>'}
            ${(res.risk_flags || []).length ? '<b>⚠️ 风险提示:</b><ul style="margin:.3rem 0 0 1.2rem">' +
                res.risk_flags.map(r => `<li>${r}</li>`).join('') + '</ul>' : ''}
        </div>`;
}

function updateInputs() {
    // 回填已保存评分到维度卡片头部（后端只存维度总分，不存子指标明细）
    for (const [dim, score] of Object.entries(scores)) {
        const header = Array.from(document.querySelectorAll('.score-card-header'))
            .find(h => h.textContent.includes(dim));
        if (header && !header.querySelector('.saved-score')) {
            const span = document.createElement('span');
            span.className = 'saved-score';
            span.style.cssText = 'float:right;font-weight:normal;font-size:.85rem;color:#e2e8f0;background:rgba(255,255,255,.15);padding:0 .4rem;border-radius:4px';
            span.textContent = `已保存: ${score} 分`;
            header.appendChild(span);
        }
    }
}

async function addIssue() {
    const input = document.getElementById('issueInput');
    const sev = document.getElementById('issueSeverity');
    if (!input.value) return;
    await API(`/api/projects/${PID}/issue`, {
        method: 'POST',
        body: JSON.stringify({ issue: input.value, severity: sev.value })
    });
    input.value = '';
    renderIssues();
}

async function addSuggestion() {
    const input = document.getElementById('suggestionInput');
    if (!input.value) return;
    await API(`/api/projects/${PID}/suggestion`, {
        method: 'POST',
        body: JSON.stringify({ suggestion: input.value })
    });
    input.value = '';
    renderSuggestions();
}

async function renderIssues() {
    const proj = await API(`/api/projects/${PID}`);
    const el = document.getElementById('issueList');
    el.innerHTML = (proj.project.issues || []).map(i =>
        `<li><span class="severity-${i.severity === '高' ? 'high' : 'mid'}">[${i.severity}]</span> ${i.issue}</li>`
    ).join('');
}

async function renderSuggestions() {
    const proj = await API(`/api/projects/${PID}`);
    const el = document.getElementById('suggestionList');
    el.innerHTML = (proj.project.suggestions || []).map(s =>
        `<li>💡 ${s.suggestion}</li>`
    ).join('');
}

init();
