// projects.js — 项目列表

async function init() {
    const projects = await API('/api/projects');
    const el = document.getElementById('projectList');
    if (!projects || projects.length === 0) {
        el.innerHTML = '<div class="empty-state">暂无项目，点击上方按钮创建</div>';
        return;
    }
    const gradeColors = { '优': '#22c55e', '良': '#3b82f6', '中': '#f59e0b', '差': '#ef4444' };
    el.innerHTML = projects.map(p => `
        <div class="project-item">
            <div class="proj-info">
                <a href="/workflow/${p.id}" class="proj-name">${p.name}</a>
                <div class="proj-meta">${p.org_name} | ${p.org_type} | ${p.current_stage}/${p.total_stages}阶段 | ${new Date(p.created_at).toLocaleDateString()}</div>
                <div class="progress-bar-container" style="margin-top:.5rem">
                    <div class="progress-bar" style="width:${p.percent}%"></div>
                </div>
            </div>
            <div class="proj-score">
                <div class="score">${p.total_score ? p.total_score.toFixed(1) : '-'}</div>
                <small>${p.grade || '未评级'}</small>
            </div>
            <div>
                <a href="/pack?pid=${p.id}" class="btn btn-sm btn-secondary">📦 项目包</a>
                <a href="/scoring/${p.id}" class="btn btn-sm btn-secondary">评分</a>
                <a href="/report/${p.id}" class="btn btn-sm btn-primary">报告</a>
            </div>
        </div>
    `).join('');
}

init();
