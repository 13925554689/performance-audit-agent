// workflow.js — 业务流程页面
// ponytail: fetch + DOM, no frameworks

let projectData = null;

async function init() {
    const res = await API(`/api/projects/${PID}`);
    if (res.error) { alert(res.error); return; }
    projectData = res;

    // Header
    const p = res.project;
    document.getElementById('projectHeader').innerHTML = `
        <h2>${p.name}</h2>
        <div class="org-info">${p.org_name} | ${p.org_type} | ${p.project_type} | 预算:${p.budget}万元 | ${p.year}年</div>
    `;

    // Progress
    document.getElementById('progressBar').style.width = res.percent + '%';
    document.getElementById('progressText').textContent = `进度: ${res.progress} (${res.percent}%)`;

    // Stage nav pills
    const nav = document.getElementById('stageNav');
    nav.innerHTML = res.all_stages.map(s => {
        let cls = s.status === 'completed' ? 'completed' :
                  s.is_current ? 'current' : 'pending';
        return `<span class="stage-pill ${cls}" onclick="jumpTo(${s.stage})">${s.stage}. ${s.name}</span>`;
    }).join('');

    // Stage detail
    const cur = res.current;
    document.getElementById('stageName').textContent = `第${cur.stage_num}阶段: ${cur.name}`;
    document.getElementById('stageDesc').textContent = cur.description;
    document.getElementById('stageTime').textContent = `⏱ ${cur.estimated_time}`;
    document.getElementById('stageProgress').textContent = `${cur.stage_num}/${cur.total}`;

    // Checklist
    document.getElementById('checklist').innerHTML = cur.checklist.map(c =>
        `<li>${c}</li>`).join('');

    // Outputs
    document.getElementById('outputList').innerHTML = cur.outputs.map(o =>
        `<li>📄 ${o}</li>`).join('');

    // Jump select
    const sel = document.getElementById('jumpStage');
    res.all_stages.forEach(s => {
        sel.innerHTML += `<option value="${s.stage}">${s.stage}. ${s.name}</option>`;
    });
    sel.value = '';

    // Paper templates
    loadPaperTemplates();

    // Score preview if available
    if (Object.keys(p.scores).length > 0) {
        showScorePreview(p);
    }
}

async function loadPaperTemplates() {
    const templates = await API('/api/paper-templates');
    const grid = document.getElementById('paperGrid');
    grid.innerHTML = Object.entries(templates).map(([k, v]) =>
        `<div class="paper-item" onclick="generatePaper('${k}')">📝 ${v}</div>`
    ).join('');
}

async function advanceStage() {
    const res = await API(`/api/projects/${PID}/advance`, { method: 'POST' });
    if (res.error) { alert(res.error); return; }
    init();
}

function jumpTo(stage) {
    if (!confirm(`跳转到第${stage}阶段？`)) return;
    API(`/api/projects/${PID}/go-to-stage`, {
        method: 'POST',
        body: JSON.stringify({ stage })
    }).then(() => init());
}

async function generatePaper(paperType) {
    const res = await API(`/api/projects/${PID}/working-paper`, {
        method: 'POST',
        body: JSON.stringify({ paper_type: paperType })
    });
    alert('底稿已生成:\n' + JSON.stringify(res, null, 2));
}

function showScorePreview(p) {
    const el = document.getElementById('scorePreview');
    el.style.display = 'block';
    el.querySelector('#scoreContent').innerHTML = `
        <p>总得分: <strong>${p.total_score || '未计算'}</strong> | 评级: <strong>${p.grade || '未评级'}</strong></p>
        <p>各维度得分: ${JSON.stringify(p.scores)}</p>
    `;
}

init();
