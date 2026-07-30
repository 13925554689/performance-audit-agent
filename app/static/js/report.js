// report.js — 报告页面

async function init() {
    const proj = await API(`/api/projects/${PID}`);
    document.getElementById('projectHeader').innerHTML = `
        <h2>${proj.project.name}</h2>
        <div class="org-info">${proj.project.org_name} | ${proj.project.org_type}</div>
    `;
}

async function generateReport() {
    const btn = document.getElementById('btnGenerate');
    btn.disabled = true;
    btn.textContent = '⏳ 生成中...';

    // 先计算分数
    await API(`/api/projects/${PID}/calculate`, { method: 'POST' });

    const report = await API(`/api/projects/${PID}/report`, { method: 'POST' });
    renderReport(report);
    btn.disabled = false;
    btn.textContent = '🔄 重新生成报告';
}

function renderReport(report) {
    const container = document.getElementById('reportContainer');
    container.style.display = 'block';

    const gradeColors = { '优': '#22c55e', '良': '#3b82f6', '中': '#f59e0b', '差': '#ef4444' };

    let html = `<h1>${report.title}</h1>
    <p style="text-align:center;color:#999">生成时间: ${new Date(report.generated_at).toLocaleString()}</p>`;

    for (const [section, content] of Object.entries(report.sections)) {
        html += `<div class="report-section"><h3>${section}</h3>`;

        if (typeof content === 'object' && !Array.isArray(content)) {
            html += '<table>';
            for (const [k, v] of Object.entries(content)) {
                let display = typeof v === 'object' ? JSON.stringify(v, null, 2) : v;
                html += `<tr><th style="width:150px">${k}</th><td>${display}</td></tr>`;
            }
            html += '</table>';
        } else if (Array.isArray(content)) {
            if (content.length === 0) {
                html += '<p style="color:#999">暂无记录</p>';
            } else {
                html += content.map(item => {
                    if (typeof item === 'string') return `<div class="issue-item">${item}</div>`;
                    return `<div class="issue-item">
                        ${item.severity ? `<span class="severity-${item.severity === '高' ? 'high' : 'mid'}">[${item.severity}]</span> ` : ''}
                        ${item.issue || item.suggestion || JSON.stringify(item)}
                    </div>`;
                }).join('');
            }
        } else {
            html += `<p>${content || '无'}</p>`;
        }

        html += '</div>';
    }

    container.innerHTML = html;
}

init();
