// 展示已有项目（支持搜索和分页）
let projectPage = 1;
let projectKeyword = '';
const PROJECT_PAGE_SIZE = 4;
function loadProjects(keyword = '', page = 1) {
    projectKeyword = keyword;
    projectPage = page;
    fetch(`/api/projects_search?q=${encodeURIComponent(keyword)}&page=${page}&page_size=${PROJECT_PAGE_SIZE}`)
        .then(res => res.json())
        .then(data => {
            const list = document.getElementById('project-list');
            const pagination = document.getElementById('project-pagination');
            list.innerHTML = '';
            pagination.innerHTML = '';
            if (!data.projects || data.projects.length === 0) {
                list.innerHTML = '<div style="color:#888;padding:24px;">未找到相关项目</div>';
                return;
            }
            data.projects.forEach(proj => {
                const card = document.createElement('div');
                card.className = 'project-card';
                card.innerHTML = `
                    <div class="project-card-title">${proj.name || proj.project_name}</div>
                    <div class="project-card-info">特征数量：${proj.feature_count || 0}</div>
                    <div class="project-card-info">文档：${proj.document_path ? proj.document_path.split(/[\\/]/).pop() : '无'}</div>
                `;
                card.onclick = () => showProjectDetail(proj);
                list.appendChild(card);
            });
            // 分页栏
            const totalPages = Math.ceil(data.total / data.page_size);
            if (totalPages > 1) {
                const prevBtn = document.createElement('button');
                prevBtn.textContent = '上一页';
                prevBtn.disabled = data.page === 1;
                prevBtn.onclick = () => loadProjects(projectKeyword, data.page - 1);
                pagination.appendChild(prevBtn);
                for (let i = 1; i <= totalPages; i++) {
                    const btn = document.createElement('button');
                    btn.textContent = i;
                    if (i === data.page) btn.className = 'active';
                    btn.onclick = () => loadProjects(projectKeyword, i);
                    pagination.appendChild(btn);
                }
                const nextBtn = document.createElement('button');
                nextBtn.textContent = '下一页';
                nextBtn.disabled = data.page === totalPages;
                nextBtn.onclick = () => loadProjects(projectKeyword, data.page + 1);
                pagination.appendChild(nextBtn);
            }
        });
}

// 弹窗展示项目详情
function showProjectDetail(proj) {
    // 获取项目详细特征
    fetch(`/api/project_detail?project_id=${proj.project_id}`)
        .then(res => res.json())
        .then(detail => {
            document.getElementById('modal-title').textContent = '项目详情';
            // 构建特征列表（默认只显示前5条）
            const features = detail.features || [];
            const showCount = 5;
            let featureHtml = '';
            if (features.length <= showCount) {
                featureHtml = `<ul>${features.map(f => `<li>${f}</li>`).join('')}</ul>`;
            } else {
                featureHtml = `<ul id="feature-list">${features.slice(0, showCount).map(f => `<li>${f}</li>`).join('')}</ul>` +
                    `<button id="toggle-features" class="toggle-btn">展开更多</button>`;
            }
            document.getElementById('modal-details').innerHTML = `
                <div class="modal-table-scroll">
                <table class="detail-table">
                  <tr><th>项目名称</th><td>${detail.project_name}</td></tr>
                  <tr><th>项目ID</th><td>${detail.project_id}</td></tr>
                  <tr><th>文档路径</th><td>${detail.document_path}</td></tr>
                  <tr><th>特征数量</th><td>${features.length}</td></tr>
                  <tr><th>特征列表</th><td>${featureHtml}</td></tr>
                </table>
                </div>
            `;
            document.getElementById('project-modal').style.display = 'flex';
            // 展开/收起逻辑
            const toggleBtn = document.getElementById('toggle-features');
            if (toggleBtn) {
                let expanded = false;
                toggleBtn.onclick = function() {
                    expanded = !expanded;
                    const list = document.getElementById('feature-list');
                    if (expanded) {
                        list.innerHTML = features.map(f => `<li>${f}</li>`).join('');
                        toggleBtn.textContent = '收起';
                    } else {
                        list.innerHTML = features.slice(0, showCount).map(f => `<li>${f}</li>`).join('');
                        toggleBtn.textContent = '展开更多';
                    }
                };
            }
        });
}

// 关闭弹窗
document.getElementById('close-modal').onclick = function() {
    document.getElementById('project-modal').style.display = 'none';
};
// 点击遮罩关闭
document.getElementById('project-modal').onclick = function(e) {
    if (e.target === this) this.style.display = 'none';
};

// 导入新项目选项卡切换
const tabUpload = document.getElementById('tab-upload');
const tabText = document.getElementById('tab-text');
const uploadPanel = document.getElementById('upload-panel');
const textPanel = document.getElementById('text-panel');

tabUpload.onclick = function() {
    tabUpload.classList.add('active');
    tabText.classList.remove('active');
    uploadPanel.style.display = '';
    textPanel.style.display = 'none';
};
tabText.onclick = function() {
    tabText.classList.add('active');
    tabUpload.classList.remove('active');
    uploadPanel.style.display = 'none';
    textPanel.style.display = '';
};

// 导入项目
document.getElementById('import-form').onsubmit = function(e) {
    e.preventDefault();
    const formData = new FormData();
    if (uploadPanel.style.display !== 'none') {
        const fileInput = uploadPanel.querySelector('input[type="file"]');
        if (!fileInput.files.length) {
            document.getElementById('import-msg').textContent = '请先选择要上传的Word文档';
            return;
        }
        formData.append('file', fileInput.files[0]);
    } else {
        const text = textPanel.querySelector('textarea').value.trim();
        if (!text) {
            document.getElementById('import-msg').textContent = '请输入项目描述';
            return;
        }
        formData.append('text', text);
    }
    fetch('/api/import_project', {
        method: 'POST',
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById('import-msg').textContent = data.msg;
        loadProjects();
    });
};

// 匹配项目
document.getElementById('match-form').onsubmit = function(e) {
    e.preventDefault();
    const query = e.target.query.value;
    fetch('/api/match', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({query})
    })
    .then(res => res.json())
    .then(data => {
        // 匹配过程日志
        if (data.log) {
            document.getElementById('match-log').textContent = data.log;
            document.getElementById('match-log-container').style.display = '';
        } else {
            document.getElementById('match-log-container').style.display = 'none';
        }
        // 匹配结果表格
        const list = document.getElementById('match-result');
        list.innerHTML = '';
        if (data.result && data.result.length > 0) {
            let cards = data.result.map(item => `
                <div class="match-card" data-pid="${item.project_id}">
                    <div class="match-title">${item.name}</div>
                    <div class="match-score">匹配度：${(item.score*100).toFixed(1)}%</div>
                </div>
            `).join('');
            list.innerHTML = cards;
            // 绑定点击事件（卡片整体可点）
            Array.from(list.querySelectorAll('.match-card')).forEach(card => {
                card.onclick = function(e) {
                    const pid = card.getAttribute('data-pid');
                    showProjectDetail({ project_id: pid });
                };
            });
        } else {
            list.innerHTML = '<li>未找到匹配项目</li>';
        }
    });
};

// 搜索框事件
const searchInput = document.getElementById('project-search-input');
searchInput.oninput = function() {
    loadProjects(this.value.trim(), 1); // 搜索时重置到第一页
};

// 合并window.onload逻辑，保证loadProjects和其它初始化都能执行
const oldOnload = window.onload;
window.onload = function() {
    if (oldOnload) oldOnload();
    loadProjects();
};