// workflow.js — 业务流程页面 v6.0
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
        <div class="org-info">${p.org_name} | ${p.org_type} | ${p.project_type} | 预算:${p.budget}万元 | ${p.year}年
            <a href="/workplan/${PID}" style="margin-left:.5rem">📅 工作计划 →</a></div>
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
    renderStageDetail(res.current);

    // Jump select
    const sel = document.getElementById('jumpStage');
    if (!sel.options.length) {
        res.all_stages.forEach(s => {
            sel.innerHTML += `<option value="${s.stage}">${s.stage}. ${s.name}</option>`;
        });
    }
    sel.value = '';

    loadPaperTemplates();
    if (Object.keys(p.scores).length > 0) showScorePreview(p);
}

function renderStageDetail(cur) {
    document.getElementById('stageName').textContent = `第${cur.stage_num}阶段: ${cur.name}`;
    document.getElementById('stageDesc').textContent = cur.description;
    document.getElementById('stageTime').textContent = `⏱ ${cur.estimated_time}`;
    document.getElementById('stageProgress').textContent = `${cur.stage_num}/${cur.total}`;

    // 检查清单/工作重点
    document.getElementById('checklist').innerHTML = (cur.checklist || []).map(c =>
        `<li>${c}</li>`).join('');

    // 阶段成果
    document.getElementById('outputList').innerHTML = (cur.outputs || []).map(o =>
        `<li>📄 ${o}</li>`).join('');

    // v6.0 六大工作包区块
    const extra = document.getElementById('stageExtras');
    extra.innerHTML = `
        ${renderListCard('📥 前置条件', (cur.prerequisites || []).map(x => `⚡ ${x}`))}
        ${renderListCard('📁 该阶段需要的资料', (cur.materials_needed || []).map(x => `📎 ${x}`))}
        ${renderRegCard(cur.regulations || [])}
        ${renderListCard('🧭 具体执行操作指引', (cur.guides || []).map((g, i) => `<b>${i + 1}.</b> ${g}`), 'guide-list')}
        ${renderCommCard(cur.comm_coord || [])}
        ${renderListCard('⭐ 本阶段工作重点', (cur.key_points || []).map(x => `❗ ${x}`), 'key-list')}
    `;
}

function renderListCard(title, items, cls = '') {
    if (!items.length) return '';
    return `<div class="card">
        <h3>${title}</h3>
        <ul class="checklist ${cls}">${items.map(x => `<li>${x}</li>`).join('')}</ul>
    </div>`;
}

function renderRegCard(regs) {
    if (!regs.length) return '';
    return `<div class="card">
        <h3>⚖️ 本阶段依据法规</h3>
        <ul class="checklist">${regs.map(r =>
            `<li><b>${r.name}</b>（${r.doc_no}）<br><small style="color:#666">要点: ${r.key}</small></li>`
        ).join('')}</ul>
    </div>`;
}

function renderCommCard(comms) {
    if (!comms.length) return '';
    return `<div class="card">
        <h3>💬 沟通与协调事项</h3>
        ${comms.map(c => `
            <div class="comm-item" style="border-left:3px solid var(--primary,#1a56db);padding:.4rem .8rem;margin:.5rem 0;background:var(--gray-50,#f8fafc);border-radius:4px">
                <div><b>${c.timing}</b> <span style="color:#888">↔ ${c.parties}</span> <span class="badge">${c.channel}</span></div>
                <div style="font-size:.85rem;margin-top:.25rem">${c.points}</div>
            </div>`).join('')}
    </div>`;
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
    }).then(() => init()).catch(err => alert('跳转失败: ' + err.message));
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
