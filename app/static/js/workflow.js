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

    // v7.2: 已导入记录展示
    const rec = cur.records || { files: [], notes: [] };
    document.getElementById('stageRecords').innerHTML = `
        ${rec.files.length ? `<b>已上传 (${rec.files.length}):</b>` + rec.files.map(f =>
            `<span class="badge" style="margin:.15rem">📎 ${esc(f.name)} (${Math.round(f.size / 1024)}KB)</span>`).join('') : ''}
        ${rec.notes.length ? `<div style="margin-top:.5rem"><b>已记录 (${rec.notes.length}):</b>` + rec.notes.map(n =>
            `<div class="comm-item" style="border-left:3px solid #0ea5e9;padding:.4rem .8rem;margin:.4rem 0;background:#f8fafc;border-radius:4px"><b>${{ comm: '💬沟通', prereq: '⚡前置', note: '📝备注' }[n.type] || '📝备注'}</b> <small style="color:#888">${(n.at || '').slice(0, 16)}</small><div style="font-size:.9rem">${esc(n.text)}</div></div>`).join('') + '</div>' : ''}
        ${!rec.files.length && !rec.notes.length ? '<span style="color:#94a3b8">本阶段暂无导入记录</span>' : ''}
    `;
}

// ── v7.2: 阶段资料导入 + 记录 + AI调整 ──
function currentStageId() {
    const s = (projectData?.all_stages || []).find(x => x.is_current);
    return s ? s.id : null;
}

async function uploadStageFile() {
    const input = document.getElementById('stageFile');
    const sid = currentStageId();
    if (!input.files[0] || !sid) { alert('请选择文件'); return; }
    const fd = new FormData(); fd.append('file', input.files[0]);
    const res = await fetch(`/api/projects/${PID}/stages/${sid}/upload`, { method: 'POST', body: fd });
    const data = await res.json();
    if (data.error) { alert(data.error); return; }
    input.value = '';
    init();
}

async function saveStageNote() {
    const sid = currentStageId();
    const text = document.getElementById('noteText').value.trim();
    if (!sid || !text) { alert('请填写记录内容'); return; }
    const res = await API(`/api/projects/${PID}/stages/${sid}/note`, { method: 'POST',
        body: JSON.stringify({ type: document.getElementById('noteType').value, text }) });
    if (res.error) { alert(res.error); return; }
    document.getElementById('noteText').value = '';
    init();
}

async function runAdjustPlan() {
    const box = document.getElementById('adjustResult');
    box.innerHTML = '<div class="spinner"></div> AI分析中(约20-40秒)...';
    const res = await API(`/api/projects/${PID}/adjust-plan`, { method: 'POST' });
    if (res.error) { box.innerHTML = `<p style="color:#ef4444">❌ ${res.error}</p>`; return; }
    const stageName = id => ((projectData?.all_stages || []).find(s => s.id === id) || {}).name || id;
    box.innerHTML = res.changes.length ? `
        <div style="background:#fffbeb;border-left:3px solid #f59e0b;padding:.8rem;border-radius:6px">
            <b>🆕 ${esc(res.focus)}</b> (${(res.ts || '').slice(0, 16)})
            ${res.changes.map(c => `<div style="margin:.5rem 0;padding:.4rem .6rem;background:#fff;border-radius:4px">
                <b>${esc(stageName(c.stage_id))}:</b> ${esc(c.change)}
                <br><small style="color:#666">依据: ${esc(c.reason)}</small></div>`).join('')}
            <button class="btn btn-primary" style="margin-top:.5rem" onclick="applyAdjustments(this)">✔ 应用到本项目工作流</button>
            <small style="color:#92400e;margin-left:.5rem">应用后写入对应阶段操作指引(项目级, 可留痕追溯)</small>
        </div>` : `<p style="color:#059669">✅ ${esc(res.focus || 'AI分析完成')}: 后续流程无需调整。</p>`;
}

async function applyAdjustments(btn) {
    if (!confirm('将AI调整写入本项目工作流模板？(幂等, 不影响全局模板)')) return;
    btn.disabled = true; btn.textContent = '应用中...';
    const res = await API(`/api/projects/${PID}/apply-adjustments`, { method: 'POST' });
    if (res.error) { alert(res.error); btn.disabled = false; btn.textContent = '✔ 应用到本项目工作流'; return; }
    alert(`已应用 ${res.applied.length} 条调整到对应阶段指引`);
    init();
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
