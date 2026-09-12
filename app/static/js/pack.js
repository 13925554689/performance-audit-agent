// pack.js — 项目导入抽取 + 项目包视图 + 结项归档
const URLP = new URLSearchParams(location.search);
let pendingExtract = null, pendingFile = null;

// ── 导入抽取 ──
const drop = document.getElementById('drop');
const fileInput = document.getElementById('fileInput');
drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('drag'); });
drop.addEventListener('dragleave', () => drop.classList.remove('drag'));
drop.addEventListener('drop', e => { e.preventDefault(); drop.classList.remove('drag'); const fs = e.dataTransfer.files; if (fs.length > 1) batchImport(fs); else if (fs[0]) extractFile(fs[0]); });
fileInput.addEventListener('change', () => { const fs = fileInput.files; if (fs.length > 1) batchImport(fs); else if (fs[0]) extractFile(fs[0]); });

async function extractFile(file) {
    document.getElementById('extractResult').innerHTML = '<div class="spinner"></div> 上传并抽取中...';
    const fd = new FormData(); fd.append('file', file);
    const res = await fetch('/api/import/extract', { method: 'POST', body: fd });
    const data = await res.json();
    if (data.error) { document.getElementById('extractResult').innerHTML = `<p style="color:#ef4444">❌ ${data.error}</p>`; return; }
    pendingExtract = data; pendingFile = file;
    renderExtract(data);
}

function renderExtract(d) {
    document.getElementById('extractResult').innerHTML = `
        <div style="background:#f0fdf4;border-left:3px solid #22c55e;padding:.8rem;border-radius:6px">
            <b>✅ 抽取结果（请核对后确认立项）</b> <span class="tag">置信度: ${d.confidence || '?'}</span>
            <div class="kv"><b>项目名称</b><span>${esc(d.project_name)}</span></div>
            <div class="kv"><b>被评价单位</b><span>${esc(d.org_name)}</span></div>
            <div class="kv"><b>单位类型</b><span>${esc(d.org_type)}</span></div>
            <div class="kv"><b>评价类型</b><span>${esc(d.project_type)}</span></div>
            <div class="kv"><b>预算(万元)</b><span>${d.budget || 0}</span></div>
            <div class="kv"><b>年度</b><span>${d.year || ''}</span></div>
            <div class="kv"><b>委托方</b><span>${esc(d.commissioner)}</span></div>
            <div class="kv"><b>评价范围</b><span>${esc(d.scope)}</span></div>
            ${(d.key_requirements || []).length ? `<div style="margin:.5rem 0 .2rem"><b>关键要求:</b> ${d.key_requirements.map(r => `<span class="tag">${esc(r)}</span>`).join('')}</div>` : ''}
            <div style="margin-top:.8rem">
                <button class="btn btn-primary" onclick="confirmCreate()">✅ 确认无误，创建项目并归档原件</button>
                <button class="btn btn-secondary" onclick="document.getElementById('extractResult').innerHTML=''">取消</button>
            </div>
        </div>`;
}

async function confirmCreate() {
    const d = pendingExtract;
    const res = await API('/api/projects', { method: 'POST', body: JSON.stringify({
        name: d.project_name || d._filename, org_name: d.org_name || '待补充',
        org_type: d.org_type || '事业单位', project_type: d.project_type || '项目支出',
        budget: parseFloat(d.budget) || 0, year: parseInt(d.year) || new Date().getFullYear(),
    })});
    if (res.error) { alert(res.error); return; }
    const pid = res.project_id;
    // 原件正式入库
    const fd = new FormData(); fd.append('file', pendingFile);
    fd.append('extracted', JSON.stringify(d));
    await fetch(`/api/projects/${pid}/import-source`, { method: 'POST', body: fd });
    location.href = `/pack?pid=${pid}`;
}

// ── 多文件批量导入 ──
async function batchImport(files) {
    if (!files || !files.length) return;
    if (files.length > 20) { alert('单次最多20份，请分批导入'); return; }
    document.getElementById('extractResult').innerHTML =
        `<div class="spinner"></div> 批量抽取中(每份需AI解析, 共${files.length}份, 约${files.length * 20}~${files.length * 60}秒)...`;
    const fd = new FormData();
    [...files].forEach(f => fd.append('files', f));
    const res = await fetch('/api/import/batch', { method: 'POST', body: fd });
    const data = await res.json();
    if (data.error) { document.getElementById('extractResult').innerHTML = `<p style="color:#ef4444">❌ ${data.error}</p>`; return; }
    document.getElementById('extractResult').innerHTML = `
        <div style="background:#f0fdf4;border-left:3px solid #22c55e;padding:.8rem;border-radius:6px">
            <b>✅ 批量导入完成: 成功 ${data.ok}/${data.created.length} 份</b>
            ${data.created.map(c => c.pid
                ? `<div class="kv"><b>${esc(c.filename)}</b><span><a href="/pack?pid=${c.pid}">📦 ${esc(c.name)}</a> (置信度:${c.confidence || '?'})</span></div>`
                : `<div class="kv"><b>${esc(c.filename)}</b><span style="color:#ef4444">❌ ${esc(c.error)}</span></div>`).join('')}
        </div>`;
}

// ── 归档报告导出 word ──
function exportArchiveReport() {
    const pid = URLP.get('pid');
    if (!pid) return;
    window.location.href = `/api/projects/${pid}/archive-report`;
}

// ── 项目包视图 ──
async function loadPack() {
    const pid = URLP.get('pid'); if (!pid) return;
    const pack = await API(`/api/projects/${pid}/pack`);
    if (pack.error) { document.getElementById('packTitle').textContent = `(${pack.error})`; return; }
    document.getElementById('packCard').style.display = 'block';
    const b = pack.basic;
    document.getElementById('packTitle').textContent = `— ${b.name}`;
    const sd = b.source_doc || {};
    document.getElementById('packBasic').innerHTML = [
        kv('项目编号', b.id), kv('项目名称', b.name), kv('被评价单位', b.org_name),
        kv('单位类型', b.org_type), kv('评价类型', b.project_type),
        kv('预算', `${b.budget}万元`), kv('年度', b.year), kv('创建时间', (b.created_at || '').slice(0, 10)),
        sd.file ? kv('📎 立项依据', sd.file) : '',
    ].join('');
    const regs = pack.regulations;
    document.getElementById('packRegs').innerHTML = regs.kit ? `
        <div class="kv"><b>指标体系</b><span>${esc(regs.index_name)}</span></div>
        <div class="kv"><b>评价流程</b><span>${esc(regs.kit.workflow || '')}</span></div>
        ${(regs.kit.classification.reg_basis || []).map(r => `<span class="tag">⚖️ ${esc(r.name)}</span>`).join('')}
        <div style="margin-top:.4rem"><a href="/classifications">→ 查看分类工作包</a></div>`
        : '<p>未匹配分类，使用项目支出通用体系</p>';
    const ex = pack.execution;
    const color = s => ({ completed: '#22c55e', in_progress: '#f59e0b' }[s] || '#cbd5e1');
    document.getElementById('packExec').innerHTML = `
        <div class="kv"><b>进度</b><span>${ex.percent}% (第${ex.current_stage}阶段)</span></div>
        ${ex.scores && Object.keys(ex.scores).length ? `<div class="kv"><b>得分</b><span>${ex.total_score}分 ${ex.grade ? `「${ex.grade}」` : ''}</span></div>` : ''}
        ${ex.stages.map(s => `<div style="font-size:.9rem;padding:.15rem 0"><span class="stage-dot" style="background:${color(s.status)}"></span>${s.stage}. ${esc(s.name)} — ${s.status === 'completed' ? '✅完成' : s.status === 'in_progress' ? '🔶进行中' : '⚪未开始'}</div>`).join('')}`;
    document.getElementById('packFiles').innerHTML = pack.files.length
        ? pack.files.map(f => `<div class="kv"><b>${f.section === 'source' ? '📥原件' : '📤成果'}</b><span>${esc(f.name)} (${(f.size / 1024).toFixed(0)}KB)</span></div>`).join('')
        : '<p style="color:#94a3b8;font-size:.9rem">暂无文件（评分/报告页生成的成果将出现在此）</p>';
    const fd2 = pack.findings;
    document.getElementById('packFindings').innerHTML =
        (fd2.issues.length ? `<b>⚠️ 问题 ${fd2.issues.length}条:</b>` + fd2.issues.map(i => `<div class="lesson">• ${esc(i.issue)} <span class="tag">${i.severity}</span></div>`).join('') : '') +
        (fd2.suggestions.length ? `<b style="display:block;margin-top:.5rem">💡 建议 ${fd2.suggestions.length}条:</b>` + fd2.suggestions.map(s => `<div class="lesson">• ${esc(s.suggestion)}</div>`).join('') : '') +
        (!fd2.issues.length && !fd2.suggestions.length ? '<p style="color:#94a3b8;font-size:.9rem">暂无记录</p>' : '');
    // 链接 + 归档按钮状态
    ['lnkWorkflow', 'lnkScoring', 'lnkWorkplan', 'lnkReport'].forEach((id, i) =>
        document.getElementById(id).href = ['/workflow/', '/scoring/', '/workplan/', '/report/'][i] + pid);
    const btn = document.getElementById('btnArchive');
    if (pack.archived) { btn.disabled = true; btn.textContent = '🎓 已归档'; }
    btn.disabled = btn.disabled || ex.total_score <= 0;
    if (ex.total_score <= 0 && !pack.archived) btn.title = '需先完成评分计算';
}

function kv(k, v) { return `<div class="kv"><b>${k}</b><span>${v == null || v === '' ? '—' : esc(String(v))}</span></div>`; }

async function doArchive() {
    const pid = URLP.get('pid');
    if (!confirm('结项归档后项目进入知识库，AI将提炼经验教训用于后续项目。确认？')) return;
    const box = document.getElementById('archiveResult');
    box.innerHTML = '<div class="spinner"></div> AI提炼中(deepseek推理)...';
    const res = await API(`/api/projects/${pid}/archive`, { method: 'POST' });
    if (res.error) { box.innerHTML = `<p style="color:#ef4444">❌ ${res.error}</p>`; return; }
    const l = res.lessons || {};
    box.innerHTML = `<div style="background:#f0fdf4;border:1px solid #22c55e;border-radius:8px;padding:1rem">
        <b>✅ 已归档 → 系统知识库 (共${res.kb_size}个项目包)</b>
        ${l.one_line_lesson ? `<div class="lesson"><b>核心教训:</b> ${esc(l.one_line_lesson)}</div>` : ''}
        ${[['issue_patterns', '高发问题模式'], ['effective_practices', '有效做法'], ['template_tips', '模板要点'], ['indicator_insights', '指标心得']]
            .map(([k, t]) => (l[k] || []).length ? `<b style="display:block;margin:.5rem 0 .2rem">${t}:</b>` + l[k].map(x => `<div class="lesson">• ${esc(x)}</div>`).join('') : '').join('')}
        <p style="font-size:.9rem;color:#059669;margin-top:.5rem">经验已注入AI评分建议与学习模式，后续同类项目自动受益。</p>
    </div>`;
    document.getElementById('btnArchive').disabled = true;
    document.getElementById('btnArchive').textContent = '🎓 已归档';
}

function esc(s) { return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }
loadPack();
