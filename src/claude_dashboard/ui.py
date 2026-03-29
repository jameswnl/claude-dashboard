"""HTML/CSS/JS template for the dashboard UI."""


def get_html():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Claude Code Dashboard</title>
<style>
  :root {
    --bg: #0f1117;
    --surface: #1a1d27;
    --surface2: #232733;
    --border: #2d3140;
    --text: #e4e6ef;
    --text-dim: #8b8fa3;
    --accent: #d4a574;
    --accent2: #7c9dd4;
    --accent3: #8bc4a0;
    --search-bg: #1e2130;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
  }
  .header {
    padding: 24px 32px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
    position: sticky;
    top: 0;
    background: var(--bg);
    z-index: 100;
  }
  .header h1 {
    font-size: 22px;
    font-weight: 600;
    color: var(--accent);
    white-space: nowrap;
  }
  .header .stats {
    color: var(--text-dim);
    font-size: 14px;
  }
  .live-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--accent3);
    margin-right: 6px;
    animation: pulse 2s infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }
  .search-bar {
    flex: 1;
    min-width: 250px;
    max-width: 500px;
    margin-left: auto;
    display: flex;
    gap: 6px;
    align-items: center;
  }
  .search-input-wrap {
    flex: 1;
    position: relative;
  }
  .search-bar input {
    width: 100%;
    padding: 10px 32px 10px 16px;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: var(--search-bg);
    color: var(--text);
    font-size: 14px;
    outline: none;
    transition: border-color 0.2s;
  }
  .search-clear {
    position: absolute;
    right: 8px;
    top: 50%;
    transform: translateY(-50%);
    background: none;
    border: none;
    color: var(--text-dim);
    font-size: 16px;
    cursor: pointer;
    padding: 2px 6px;
    line-height: 1;
    display: none;
  }
  .search-clear:hover {
    color: var(--text);
  }
  .search-toggle {
    padding: 6px 8px;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: transparent;
    color: var(--text-dim);
    font-size: 12px;
    font-family: 'SF Mono', 'Fira Code', monospace;
    cursor: pointer;
    transition: background 0.15s, color 0.15s, border-color 0.15s;
    white-space: nowrap;
    line-height: 1;
  }
  .search-toggle:hover {
    color: var(--text);
    border-color: var(--text-dim);
  }
  .search-toggle.active {
    background: var(--accent2);
    color: var(--bg);
    border-color: var(--accent2);
  }
  .search-bar input:focus {
    border-color: var(--accent);
  }
  .search-bar input::placeholder {
    color: var(--text-dim);
  }
  .container {
    padding: 24px 32px;
    max-width: 1400px;
    margin: 0 auto;
  }
  .project-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
    grid-auto-rows: min-content;
    gap: 16px;
  }
  .project-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
    transition: border-color 0.2s, transform 0.15s;
    cursor: pointer;
  }
  .project-card:hover {
    border-color: var(--accent);
    transform: translateY(-2px);
  }
  .project-card.expanded {
    grid-column: 1 / -1;
  }
  .project-header {
    padding: 16px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .project-name {
    font-size: 16px;
    font-weight: 600;
    color: var(--accent2);
    font-family: 'SF Mono', 'Fira Code', monospace;
  }
  .session-count {
    background: var(--surface2);
    color: var(--text-dim);
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 12px;
    white-space: nowrap;
  }
  .project-sessions {
    display: none;
    border-top: 1px solid var(--border);
    max-height: 600px;
    overflow-y: auto;
  }
  .project-card.expanded .project-sessions {
    display: block;
  }
  .session-item {
    padding: 14px 20px;
    border-bottom: 1px solid var(--border);
    transition: background 0.15s;
  }
  .session-item:last-child {
    border-bottom: none;
  }
  .session-item:hover {
    background: var(--surface2);
  }
  .session-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
  }
  .session-date {
    font-size: 12px;
    color: var(--accent3);
    font-family: 'SF Mono', 'Fira Code', monospace;
  }
  .session-msgs {
    font-size: 11px;
    color: var(--text-dim);
  }
  .session-preview {
    font-size: 13px;
    color: var(--text-dim);
    line-height: 1.5;
    overflow: hidden;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }
  .session-all-messages {
    display: none;
    margin-top: 10px;
    padding: 10px 14px;
    background: var(--bg);
    border-radius: 8px;
    max-height: 300px;
    overflow-y: auto;
  }
  .session-item.show-messages .session-all-messages {
    display: block;
  }
  .session-all-messages .msg {
    padding: 6px 0;
    border-bottom: 1px solid var(--border);
    font-size: 12px;
    color: var(--text);
    line-height: 1.4;
  }
  .resume-btn {
    padding: 4px 12px;
    border-radius: 6px;
    border: 1px solid var(--accent2);
    background: transparent;
    color: var(--accent2);
    font-size: 11px;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
    white-space: nowrap;
  }
  .resume-btn:hover {
    background: var(--accent2);
    color: var(--bg);
  }
  .session-all-messages .msg:last-child {
    border-bottom: none;
  }
  .no-results {
    text-align: center;
    padding: 60px 20px;
    color: var(--text-dim);
    font-size: 16px;
  }
  .highlight {
    background: rgba(212, 165, 116, 0.3);
    border-radius: 2px;
    padding: 0 1px;
  }
  .memory-badge {
    display: inline-block;
    background: rgba(139, 196, 160, 0.2);
    color: var(--accent3);
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    margin-left: 8px;
    cursor: pointer;
  }
  .memory-section {
    display: none;
    border-top: 1px solid var(--border);
  }
  .project-card.show-memory .memory-section {
    display: block;
  }
  .memory-file {
    padding: 14px 20px;
    border-bottom: 1px solid var(--border);
  }
  .memory-file:last-child {
    border-bottom: none;
  }
  .memory-file-name {
    font-size: 13px;
    font-weight: 600;
    color: var(--accent3);
    font-family: 'SF Mono', 'Fira Code', monospace;
    margin-bottom: 8px;
  }
  .memory-file-content {
    font-size: 12px;
    color: var(--text-dim);
    line-height: 1.6;
    white-space: pre-wrap;
    background: var(--bg);
    padding: 12px 14px;
    border-radius: 8px;
    max-height: 400px;
    overflow-y: auto;
    font-family: 'SF Mono', 'Fira Code', monospace;
  }
  .tab-bar {
    display: flex;
    border-top: 1px solid var(--border);
    background: var(--surface2);
  }
  .tab-btn {
    flex: 1;
    padding: 8px 16px;
    font-size: 12px;
    color: var(--text-dim);
    background: none;
    border: none;
    cursor: pointer;
    text-align: center;
    transition: color 0.15s, background 0.15s;
    border-bottom: 2px solid transparent;
  }
  .tab-btn:hover {
    color: var(--text);
    background: var(--surface);
  }
  .tab-btn.active {
    color: var(--accent);
    border-bottom-color: var(--accent);
  }
  .claude-md-badge {
    display: inline-block;
    background: rgba(124, 157, 212, 0.2);
    color: var(--accent2);
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    margin-left: 8px;
  }
  .claude-md-section {
    display: none;
    border-top: 1px solid var(--border);
  }
  .project-card.show-claude-md .claude-md-section {
    display: block;
  }
  .refresh-btn {
    padding: 8px 16px;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: var(--surface2);
    color: var(--text-dim);
    font-size: 13px;
    cursor: pointer;
    transition: background 0.15s, color 0.15s, border-color 0.15s;
    white-space: nowrap;
  }
  .refresh-btn:hover {
    background: var(--surface);
    color: var(--text);
    border-color: var(--accent);
  }
  .refresh-btn.loading {
    opacity: 0.5;
    pointer-events: none;
  }
  .claude-md-content {
    font-size: 12px;
    color: var(--text-dim);
    line-height: 1.6;
    white-space: pre-wrap;
    background: var(--bg);
    padding: 14px 20px;
    max-height: 500px;
    overflow-y: auto;
    font-family: 'SF Mono', 'Fira Code', monospace;
  }
  .view-tabs {
    display: flex;
    gap: 0;
    padding: 0 32px;
    border-bottom: 1px solid var(--border);
    background: var(--bg);
  }
  .view-tab {
    padding: 10px 24px;
    font-size: 14px;
    color: var(--text-dim);
    background: none;
    border: none;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: color 0.15s;
  }
  .view-tab:hover {
    color: var(--text);
  }
  .view-tab.active {
    color: var(--accent);
    border-bottom-color: var(--accent);
  }
  .skills-summary {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
    flex-wrap: wrap;
  }
  .skills-summary-item {
    padding: 8px 16px;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--text-dim);
    font-size: 13px;
    cursor: pointer;
    transition: border-color 0.15s, color 0.15s;
    text-decoration: none;
  }
  .skills-summary-item:hover {
    border-color: var(--accent);
    color: var(--text);
  }
  .skills-summary-count {
    color: var(--accent);
    font-weight: 600;
    margin-right: 4px;
  }
  .skills-section {
    margin-bottom: 24px;
  }
  .skills-section-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--accent);
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
  }
  .skills-group {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    margin-bottom: 12px;
    overflow: hidden;
  }
  .skills-group-header {
    padding: 12px 20px;
    font-size: 14px;
    font-weight: 600;
    color: var(--accent2);
    font-family: 'SF Mono', 'Fira Code', monospace;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .skills-group-header:hover {
    background: var(--surface2);
  }
  .skills-group-count {
    background: var(--surface2);
    color: var(--text-dim);
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 11px;
  }
  .skills-group-body {
    display: none;
    border-top: 1px solid var(--border);
  }
  .skills-group.expanded .skills-group-body {
    display: block;
  }
  .skill-item {
    padding: 12px 20px;
    border-bottom: 1px solid var(--border);
  }
  .skill-item:last-child {
    border-bottom: none;
  }
  .skill-name {
    font-size: 13px;
    font-weight: 600;
    color: var(--accent3);
    font-family: 'SF Mono', 'Fira Code', monospace;
    margin-bottom: 6px;
  }
  .skill-content {
    font-size: 12px;
    color: var(--text-dim);
    line-height: 1.5;
    white-space: pre-wrap;
    background: var(--bg);
    padding: 10px 14px;
    border-radius: 8px;
    max-height: 200px;
    overflow-y: auto;
    font-family: 'SF Mono', 'Fira Code', monospace;
  }
</style>
</head>
<body>

<div class="header">
  <h1><span class="live-dot"></span>Claude Code Dashboard</h1>
  <span class="stats" id="stats"></span>
  <div class="search-bar">
    <div class="search-input-wrap">
      <input type="text" id="search" placeholder="Search projects, sessions, memory, CLAUDE.md..." autofocus>
      <button class="search-clear" id="search-clear" title="Clear search">&times;</button>
    </div>
    <button class="search-toggle" id="toggle-case" title="Case sensitive">Aa</button>
    <button class="search-toggle" id="toggle-word" title="Full word match">W</button>
  </div>
  <button class="refresh-btn" id="refresh" title="Refresh data">Refresh</button>
</div>

<div class="view-tabs">
  <button class="view-tab active" id="view-projects">Projects</button>
  <button class="view-tab" id="view-skills">Skills</button>
</div>

<div class="container" id="projects-view">
  <div class="project-grid" id="grid"></div>
  <div class="no-results" id="no-results" style="display:none">No matching projects or sessions found.</div>
</div>

<div class="container" id="skills-view" style="display:none">
  <div id="skills-content"></div>
</div>

<script>
let DATA = [];
let SKILLS = {};
let currentVersion = 0;
let caseSensitive = false;
let fullWord = false;
let currentView = 'projects';

const grid = document.getElementById('grid');
const searchInput = document.getElementById('search');
const statsEl = document.getElementById('stats');
const noResults = document.getElementById('no-results');
const toggleCase = document.getElementById('toggle-case');
const toggleWord = document.getElementById('toggle-word');

toggleCase.addEventListener('click', () => {
  caseSensitive = !caseSensitive;
  toggleCase.classList.toggle('active', caseSensitive);
  render(searchInput.value);
});
toggleWord.addEventListener('click', () => {
  fullWord = !fullWord;
  toggleWord.classList.toggle('active', fullWord);
  render(searchInput.value);
});

function escapeHtml(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function searchMatch(text, query) {
  if (!query) return false;
  const flags = caseSensitive ? '' : 'i';
  const escaped = query.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');
  const pattern = fullWord ? '\\\\b' + escaped + '\\\\b' : escaped;
  return new RegExp(pattern, flags).test(text);
}

function highlightText(text, query) {
  if (!query) return escapeHtml(text);
  const escaped = escapeHtml(text);
  const flags = caseSensitive ? 'g' : 'gi';
  const escapedQ = query.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');
  const pattern = fullWord ? '\\\\b(' + escapedQ + ')\\\\b' : '(' + escapedQ + ')';
  const re = new RegExp(pattern, flags);
  return escaped.replace(re, '<span class="highlight">$1</span>');
}

function render(query) {
  grid.innerHTML = '';
  let visibleCount = 0;
  const q = query || '';
  const hasQuery = q.length > 0;

  const totalSessions = DATA.reduce((s, p) => s + p.sessions.length, 0);
  statsEl.textContent = DATA.length + ' projects | ' + totalSessions + ' sessions';

  DATA.forEach((project, pi) => {
    const nameMatch = !hasQuery || searchMatch(project.name, q);
    const matchingSessions = project.sessions.filter(s => {
      if (!hasQuery) return true;
      return searchMatch(s.first_message, q)
        || s.user_messages.some(m => searchMatch(m, q))
        || searchMatch(s.started, q);
    });

    const memoryMatch = hasQuery && project.memory_files && project.memory_files.some(
      mf => searchMatch(mf.content, q) || searchMatch(mf.name, q)
    );
    const claudeMdMatch = hasQuery && project.claude_md && searchMatch(project.claude_md, q);

    if (!nameMatch && matchingSessions.length === 0 && !memoryMatch && !claudeMdMatch) return;
    visibleCount++;

    const sessionsToShow = hasQuery ? matchingSessions : project.sessions;
    const hasMemory = project.memory_files && project.memory_files.length > 0;
    const hasClaudeMd = !!project.claude_md;
    const hasTabs = hasMemory || hasClaudeMd;

    const card = document.createElement('div');
    card.className = 'project-card';
    card.innerHTML = `
      <div class="project-header">
        <span class="project-name">${highlightText(project.name, q)}</span>
        <span>
          ${hasClaudeMd ? '<span class="claude-md-badge">CLAUDE.md</span>' : ''}
          ${hasMemory ? '<span class="memory-badge">' + project.memory_files.length + ' memory</span>' : ''}
          <span class="session-count">${sessionsToShow.length} session${sessionsToShow.length !== 1 ? 's' : ''}</span>
        </span>
      </div>
      ${hasTabs ? `<div class="tab-bar">
        <button class="tab-btn active" data-tab="sessions">Sessions</button>
        ${hasMemory ? '<button class="tab-btn" data-tab="memory">Memory</button>' : ''}
        ${hasClaudeMd ? '<button class="tab-btn" data-tab="claude-md">CLAUDE.md</button>' : ''}
      </div>` : ''}
      <div class="project-sessions">
        ${sessionsToShow.map((s, si) => `
          <div class="session-item" data-si="${si}">
            <div class="session-meta">
              <span class="session-date">${escapeHtml(s.started)}</span>
              <span class="session-msgs">${s.message_count} message${s.message_count !== 1 ? 's' : ''}</span>
              <button class="resume-btn" data-session-id="${escapeHtml(s.id)}" data-dirname="${escapeHtml(project.dirname)}">Resume</button>
            </div>
            <div class="session-preview">${highlightText(s.first_message, q)}</div>
            <div class="session-all-messages">
              ${s.user_messages.map(m => `<div class="msg">${highlightText(m, q)}</div>`).join('')}
            </div>
          </div>
        `).join('')}
      </div>
      ${hasMemory ? `<div class="memory-section">
        ${project.memory_files.map(mf => `
          <div class="memory-file">
            <div class="memory-file-name">${highlightText(mf.name, q)}</div>
            <div class="memory-file-content">${highlightText(mf.content, q)}</div>
          </div>
        `).join('')}
      </div>` : ''}
      ${hasClaudeMd ? `<div class="claude-md-section">
        <div class="claude-md-content">${highlightText(project.claude_md, q)}</div>
      </div>` : ''}
    `;

    card.querySelector('.project-header').addEventListener('click', () => {
      card.classList.toggle('expanded');
    });

    card.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const tab = btn.dataset.tab;
        card.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        card.classList.remove('show-memory', 'show-claude-md');
        const sessionsDiv = card.querySelector('.project-sessions');
        if (tab === 'memory') {
          card.classList.add('show-memory');
          sessionsDiv.style.display = 'none';
        } else if (tab === 'claude-md') {
          card.classList.add('show-claude-md');
          sessionsDiv.style.display = 'none';
        } else {
          sessionsDiv.style.display = 'block';
        }
      });
    });

    card.querySelectorAll('.session-item').forEach(el => {
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        el.classList.toggle('show-messages');
      });
    });

    card.querySelectorAll('.resume-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const sessionId = btn.dataset.sessionId;
        const dirname = btn.dataset.dirname;
        btn.textContent = 'Opening...';
        try {
          const resp = await fetch('/api/resume', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({session_id: sessionId, dirname: dirname})
          });
          const result = await resp.json();
          if (!result.ok) alert('Failed to open terminal: ' + (result.error || 'unknown error'));
        } catch (err) {
          alert('Failed to resume session: ' + err.message);
        }
        btn.textContent = 'Resume';
      });
    });

    if (hasQuery) {
      card.classList.add('expanded');
      const sessionsDiv = card.querySelector('.project-sessions');
      if (matchingSessions.length === 0 && (memoryMatch || claudeMdMatch)) {
        const bestTab = memoryMatch ? 'memory' : 'claude-md';
        if (bestTab === 'memory') card.classList.add('show-memory');
        else card.classList.add('show-claude-md');
        if (sessionsDiv) sessionsDiv.style.display = 'none';
        card.querySelectorAll('.tab-btn').forEach(b => {
          b.classList.toggle('active', b.dataset.tab === bestTab);
        });
      }
    }

    grid.appendChild(card);
  });

  noResults.style.display = visibleCount === 0 ? 'block' : 'none';
}

const searchClear = document.getElementById('search-clear');
searchInput.addEventListener('input', (e) => {
  searchClear.style.display = e.target.value ? 'block' : 'none';
  render(e.target.value);
  if (currentView === 'skills') renderSkills(e.target.value);
});
searchClear.addEventListener('click', () => {
  searchInput.value = '';
  searchClear.style.display = 'none';
  render('');
  if (currentView === 'skills') renderSkills('');
  searchInput.focus();
});

// View switching
const viewProjects = document.getElementById('view-projects');
const viewSkills = document.getElementById('view-skills');
const projectsView = document.getElementById('projects-view');
const skillsView = document.getElementById('skills-view');

viewProjects.addEventListener('click', () => {
  currentView = 'projects';
  viewProjects.classList.add('active');
  viewSkills.classList.remove('active');
  projectsView.style.display = '';
  skillsView.style.display = 'none';
});
viewSkills.addEventListener('click', () => {
  currentView = 'skills';
  viewSkills.classList.add('active');
  viewProjects.classList.remove('active');
  projectsView.style.display = 'none';
  skillsView.style.display = '';
  renderSkills(searchInput.value);
});

function renderSkillGroup(title, skills, query) {
  const filtered = query
    ? skills.filter(s => searchMatch(s.name, query) || searchMatch(s.content, query))
    : skills;
  if (filtered.length === 0) return '';
  return filtered.map(s => `
    <div class="skill-item">
      <div class="skill-name">/${highlightText(s.name, query)}</div>
      <div class="skill-content">${highlightText(s.content, query)}</div>
    </div>
  `).join('');
}

function renderSkills(query) {
  const container = document.getElementById('skills-content');
  const q = query || '';
  const hasQuery = q.length > 0;
  let sectionsHtml = '';

  const userCount = SKILLS.user ? SKILLS.user.length : 0;
  const projectSkillCount = SKILLS.projects ? SKILLS.projects.reduce((s, p) => s + p.skills.length, 0) : 0;
  const pluginSkillCount = SKILLS.plugins ? SKILLS.plugins.reduce((s, p) => s + p.skills.length, 0) : 0;

  // Summary bar
  let summaryItems = [];
  if (userCount > 0) summaryItems.push(`<a class="skills-summary-item" href="#skills-user"><span class="skills-summary-count">${userCount}</span>User</a>`);
  if (projectSkillCount > 0) summaryItems.push(`<a class="skills-summary-item" href="#skills-projects"><span class="skills-summary-count">${projectSkillCount}</span>Project</a>`);
  if (pluginSkillCount > 0) summaryItems.push(`<a class="skills-summary-item" href="#skills-plugins"><span class="skills-summary-count">${pluginSkillCount}</span>Plugin</a>`);
  const summaryHtml = summaryItems.length > 0 ? `<div class="skills-summary">${summaryItems.join('')}</div>` : '';

  // User skills
  if (userCount > 0) {
    const items = renderSkillGroup('User', SKILLS.user, q);
    if (items) {
      sectionsHtml += `<div class="skills-section" id="skills-user">
        <div class="skills-section-title">User Skills <span style="color:var(--text-dim);font-size:13px;font-weight:400">(${userCount})</span></div>
        <div class="skills-group expanded">
          <div class="skills-group-body" style="display:block">${items}</div>
        </div>
      </div>`;
    }
  }

  // Project skills
  if (SKILLS.projects && SKILLS.projects.length > 0) {
    let projectsHtml = '';
    SKILLS.projects.forEach(p => {
      const items = renderSkillGroup(p.name, p.skills, q);
      if (items || !hasQuery) {
        projectsHtml += `<div class="skills-group">
          <div class="skills-group-header">
            <span>${highlightText(p.name, q)}</span>
            <span class="skills-group-count">${p.skills.length} skill${p.skills.length !== 1 ? 's' : ''}</span>
          </div>
          <div class="skills-group-body">${items || renderSkillGroup(p.name, p.skills, '')}</div>
        </div>`;
      }
    });
    if (projectsHtml) {
      sectionsHtml += `<div class="skills-section" id="skills-projects">
        <div class="skills-section-title">Project Skills <span style="color:var(--text-dim);font-size:13px;font-weight:400">(${projectSkillCount} across ${SKILLS.projects.length} projects)</span></div>
        ${projectsHtml}
      </div>`;
    }
  }

  // Plugin skills
  if (SKILLS.plugins && SKILLS.plugins.length > 0) {
    let pluginsHtml = '';
    SKILLS.plugins.forEach(p => {
      const items = renderSkillGroup(p.name, p.skills, q);
      if (items || !hasQuery) {
        pluginsHtml += `<div class="skills-group">
          <div class="skills-group-header">
            <span>${highlightText(p.name, q)}</span>
            <span class="skills-group-count">${p.skills.length} skill${p.skills.length !== 1 ? 's' : ''}</span>
          </div>
          <div class="skills-group-body">${items || renderSkillGroup(p.name, p.skills, '')}</div>
        </div>`;
      }
    });
    if (pluginsHtml) {
      sectionsHtml += `<div class="skills-section" id="skills-plugins">
        <div class="skills-section-title">Plugin Skills <span style="color:var(--text-dim);font-size:13px;font-weight:400">(${pluginSkillCount} across ${SKILLS.plugins.length} plugins)</span></div>
        ${pluginsHtml}
      </div>`;
    }
  }

  container.innerHTML = (summaryHtml + sectionsHtml) || '<div class="no-results">No skills found.</div>';

  // Add click handlers for group headers
  container.querySelectorAll('.skills-group-header').forEach(header => {
    header.addEventListener('click', () => {
      header.parentElement.classList.toggle('expanded');
    });
  });

  // Smooth scroll for summary links
  container.querySelectorAll('.skills-summary-item').forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const target = document.querySelector(link.getAttribute('href'));
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
}

async function fetchData() {
  const resp = await fetch('/api/data');
  const result = await resp.json();
  if (result.version !== currentVersion) {
    currentVersion = result.version;
    DATA = result.data;
    SKILLS = result.skills || {};
    render(searchInput.value);
    if (currentView === 'skills') renderSkills(searchInput.value);
  }
}

// Manual refresh
const refreshBtn = document.getElementById('refresh');
refreshBtn.addEventListener('click', async () => {
  refreshBtn.classList.add('loading');
  refreshBtn.textContent = 'Refreshing...';
  try {
    await fetch('/api/refresh', { method: 'POST' });
    await fetchData();
  } catch (e) {}
  refreshBtn.classList.remove('loading');
  refreshBtn.textContent = 'Refresh';
});

// Initial load
fetchData();
</script>
</body>
</html>"""
