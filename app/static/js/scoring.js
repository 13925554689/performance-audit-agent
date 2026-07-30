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
    gridEl = document.getElementById('scoringGrid');
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
        </div>
        <button class="btn btn-primary" style="margin-top:1rem" onclick="submitAllScores()">🔄 重新计算</button>
    `;
}

function updateInputs() {
    // 回填已有评分
    for (const [dim, score] of Object.entries(scores)) {
        // ponytail: just update the score object, inputs are per-dimension
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
