// 绩效评价审计智能体 — 全局脚本
// ponytail: vanilla JS, no frameworks

const API = (path, opts = {}) => fetch(path, {
    headers: { 'Content-Type': 'application/json', ...opts.headers },
    ...opts
}).then(r => r.json());

// 流程时间线
async function loadTimeline() {
    const stages = await API('/api/stages');
    const el = document.getElementById('processTimeline');
    if (!el) return;
    el.innerHTML = stages.map(s =>
        `<div class="timeline-item">
            <div class="stage-num">${s.stage}</div>
            <div>${s.name}</div>
            <small style="color:#999">${s.estimated_time}</small>
        </div>`).join('');
}

// 创建项目
function showCreateModal() {
    document.getElementById('createModal').classList.add('active');
}
function closeModal() {
    document.getElementById('createModal').classList.remove('active');
}

document.addEventListener('DOMContentLoaded', () => {
    loadTimeline();

    const form = document.getElementById('createForm');
    if (form) {
        form.onsubmit = async (e) => {
            e.preventDefault();
            const data = Object.fromEntries(new FormData(form));
            data.budget = parseFloat(data.budget);
            data.year = parseInt(data.year);
            const res = await API('/api/projects', {
                method: 'POST',
                body: JSON.stringify(data)
            });
            if (res.success) {
                closeModal();
                window.location.href = `/workflow/${res.project_id}`;
            }
        };
    }
});

// 加载案例
async function loadCases() {
    const cases = await API('/api/cases');
    alert(cases.map(c =>
        `${c.name}(${c.org},${c.year}年) — 得分${c.total_score}分 「${c.grade}」\n亮点:${c.highlights.join(';')}`
    ).join('\n\n'));
}
