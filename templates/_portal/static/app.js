'use strict';

// ── State ─────────────────────────────────────────────────────────
let _agents  = [];
let _tasks   = { open: [], closed: [] };
let _chatWs  = null;
let _cycleWs = null;
let _office  = null;  // IsometricOffice instance

// ── Boot ──────────────────────────────────────────────────────────
async function init() {
  await loadCompany();
  await Promise.all([loadTeam(), loadStats(), loadRecent(), loadTasks()]);
  loadBriefings();
  connectChat();

  // Init isometric office AFTER team loaded, then start
  _initOffice();
  if (_office && _agents.length > 0) {
    _office.setAgents(_agents);
    _office.start();
  }

  // Navigation
  document.querySelectorAll('.nav-item').forEach(function(el) {
    el.addEventListener('click', function() {
      var page = el.dataset.page;
      document.querySelectorAll('.nav-item').forEach(function(n) { n.classList.remove('active'); });
      el.classList.add('active');
      document.querySelectorAll('.page').forEach(function(p) { p.classList.remove('active'); });
      var target = document.getElementById('page-' + page);
      if (target) target.classList.add('active');
    });
  });

  // Run cycle button
  document.getElementById('run-cycle-btn').addEventListener('click', runCycle);

  // Chat
  document.getElementById('chat-send').addEventListener('click', sendChat);
  document.getElementById('chat-input').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') sendChat();
  });

  // Tasks
  document.getElementById('add-task-btn').addEventListener('click', toggleAddTask);
  document.getElementById('save-task-btn').addEventListener('click', saveTask);
  document.getElementById('cancel-task-btn').addEventListener('click', toggleAddTask);
}

// ── API helpers ───────────────────────────────────────────────────
async function api(url, opts) {
  var res = await fetch(url, opts || {});
  if (!res.ok) throw new Error('HTTP ' + res.status);
  return res.json();
}

// ── Company info ──────────────────────────────────────────────────
async function loadCompany() {
  var c = await api('/api/company');
  var name = c.name || 'Company';
  document.getElementById('company-name').textContent    = name;
  document.getElementById('company-type').textContent    = c.type || '';
  document.getElementById('workspace-name').textContent  = name;
  document.getElementById('welcome-name').textContent    = name;
  document.title = name + ' — Portal';
}

// ── Isometric Office ─────────────────────────────────────────────
function _initOffice() {
  var canvas = document.getElementById('office-canvas');
  if (!canvas || typeof IsometricOffice === 'undefined') return;
  var wrap = canvas.parentElement;
  canvas.width  = wrap.clientWidth  || 700;
  canvas.height = 320;
  _office = new IsometricOffice(canvas, function(agent) {
    // Agent clicked → show in chat panel + switch to team page if desired
    showAgentCard(agent.id);
    var input = document.getElementById('chat-input');
    input.value = '';
    input.placeholder = agent.id.replace(/_/g,' ') + ' คุณมีอะไรจะรายงานไหม?';
  });
  // Agents loaded later in loadTeam()
  window.addEventListener('resize', function() {
    canvas.width = wrap.clientWidth || 700;
    if (_office) _office.resize(canvas.width, canvas.height);
  });
}

// ── Team ──────────────────────────────────────────────────────────
async function loadTeam() {
  var data = await api('/api/team');
  _agents = data.agents || [];
  document.getElementById('agent-count').textContent = 'ทีม AI · ' + _agents.length + ' คน';

  // Team grid
  var grid = document.getElementById('team-grid');
  grid.innerHTML = _agents.map(function(a) {
    var skills = (a.responsibilities || []).slice(0,3).map(function(r) {
      return '<div class="skill-row" style="font-size:12px;color:var(--text-muted);margin-top:4px">• ' + r.slice(0,50) + '</div>';
    }).join('');
    var tierColor = a.model_tier === 'critical' ? 'var(--yellow)' : a.model_tier === 'reasoning' ? 'var(--purple-l)' : 'var(--cyan)';
    return '<div class="team-card" onclick="selectAgent(\'' + a.id + '\')">' +
      '<span class="team-card-tier" style="color:' + tierColor + '">' + (a.model_tier || '') + '</span>' +
      '<img class="team-card-avatar" src="/static/sprites/' + a.sprite + '.png" alt="' + a.role + '"/>' +
      '<div class="team-card-name">' + a.id.replace(/_/g,' ') + '</div>' +
      '<div class="team-card-role">' + a.role + '</div>' +
      '<div class="team-card-status"><span class="status-dot"></span> กำลังทำงาน</div>' +
      skills +
    '</div>';
  }).join('');

  // Chat agent avatars
  var chatAgents = document.getElementById('chat-agents');
  chatAgents.innerHTML = '<div class="chat-agent-avatar" title="เลขา"><span style="font-size:18px">&#x1F4BC;</span></div>' +
    _agents.map(function(a) {
      return '<div class="chat-agent-avatar" title="' + a.role + '" onclick="showAgentCard(\'' + a.id + '\')">' +
        '<img src="/static/sprites/' + a.sprite + '.png" alt="' + a.role + '" style="width:100%;height:auto"/>' +
      '</div>';
    }).join('');

  // Populate task agent selector
  var sel = document.getElementById('task-agent');
  sel.innerHTML = _agents.map(function(a) {
    return '<option value="' + a.id + '">' + a.role + '</option>';
  }).join('');
}

function selectAgent(id) {
  document.querySelectorAll('.team-card').forEach(function(c) { c.classList.remove('selected'); });
  var idx = _agents.findIndex(function(a) { return a.id === id; });
  if (idx >= 0) document.querySelectorAll('.team-card')[idx].classList.add('selected');
  showAgentCard(id);
}

function showAgentCard(id) {
  var a = _agents.find(function(x) { return x.id === id; });
  if (!a) return;
  document.getElementById('active-agent-card').classList.remove('hidden');
  document.getElementById('active-agent-img').src          = '/static/sprites/' + a.sprite + '.png';
  document.getElementById('active-agent-name').textContent = a.id.replace(/_/g,' ');
  document.getElementById('active-agent-role').textContent = a.role;
}

// ── Stats ─────────────────────────────────────────────────────────
async function loadStats() {
  var s = await api('/api/stats');
  document.getElementById('st-obs').textContent   = s.observations || 0;
  document.getElementById('st-dec').textContent   = s.decisions    || 0;
  document.getElementById('st-tasks').textContent = s.open_tasks   || 0;
  document.getElementById('st-briefs').textContent = s.briefs      || 0;
}

// ── Recent activity feed ──────────────────────────────────────────
async function loadRecent() {
  var data = await api('/api/recent');
  var feed = document.getElementById('activity-feed');
  var entries = data.entries || [];
  if (!entries.length) return;
  feed.innerHTML = entries.map(function(e) {
    var ts = e.ts ? e.ts.split('T')[0] : '';
    return '<div class="activity-item">' +
      '<span class="activity-agent">' + e.agent + '</span>' +
      '<span class="activity-body">' + e.body.slice(0,100) + '</span>' +
      '<span class="activity-ts">' + ts + '</span>' +
    '</div>';
  }).join('');
}

// ── Tasks ─────────────────────────────────────────────────────────
async function loadTasks() {
  _tasks = await api('/api/tasks');
  renderTasks();
  var badge = document.getElementById('badge-tasks');
  badge.textContent = (_tasks.open || []).length || '';
}

function renderTasks() {
  renderTaskList('tasks-open', _tasks.open || [], false);
  renderTaskList('tasks-closed', _tasks.closed || [], true);
}

function renderTaskList(elId, items, closed) {
  var el = document.getElementById(elId);
  if (!items.length) {
    el.innerHTML = '<div style="color:var(--text-muted);font-size:13px;padding:12px">ไม่มีงาน</div>';
    return;
  }
  el.innerHTML = items.map(function(t) {
    var priClass = t.priority === 'high' ? 'high' : t.priority === 'low' ? 'low' : 'medium';
    var priText  = t.priority === 'high' ? 'สำคัญมาก' : t.priority === 'low' ? 'ต่ำ' : 'ปกติ';
    return '<div class="task-item' + (closed ? ' closed' : '') + '">' +
      '<div class="task-check' + (closed ? ' checked' : '') + '" onclick="toggleTask(\'' + t.id + '\')">' + (closed ? '✓' : '') + '</div>' +
      '<span class="task-title">' + t.title + '</span>' +
      '<span class="task-meta">' + (t.assigned || '') + '</span>' +
      '<span class="task-priority ' + priClass + '">' + priText + '</span>' +
    '</div>';
  }).join('');
}

async function toggleTask(id) {
  await api('/api/tasks/' + id + '/done', { method: 'PATCH' });
  await loadTasks();
}

function toggleAddTask() {
  var form = document.getElementById('add-task-form');
  form.classList.toggle('hidden');
  if (!form.classList.contains('hidden')) {
    document.getElementById('task-title').focus();
  }
}

async function saveTask() {
  var title  = document.getElementById('task-title').value.trim();
  var agent  = document.getElementById('task-agent').value;
  var prio   = document.getElementById('task-priority').value;
  if (!title) return;
  await api('/api/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: title, assigned_to: agent, priority: prio }),
  });
  document.getElementById('task-title').value = '';
  document.getElementById('add-task-form').classList.add('hidden');
  await loadTasks();
}

// ── Briefings ─────────────────────────────────────────────────────
async function loadBriefings() {
  var data = await api('/api/briefings');
  var list = document.getElementById('briefings-list');
  var dates = data.briefings || [];
  if (!dates.length) {
    list.innerHTML = '<div class="briefing-item">ยังไม่มีรายงาน</div>';
    return;
  }
  list.innerHTML = dates.map(function(d) {
    return '<div class="briefing-item" onclick="loadBrief(\'' + d + '\')">' + d + '</div>';
  }).join('');
}

async function loadBrief(date) {
  document.querySelectorAll('.briefing-item').forEach(function(el) {
    el.classList.toggle('active', el.textContent === date);
  });
  var data = await api('/api/briefings/' + date);
  document.getElementById('brief-view').textContent = data.content || '';
}

// ── Secretary Chat ────────────────────────────────────────────────
function connectChat() {
  var proto = location.protocol === 'https:' ? 'wss' : 'ws';
  _chatWs = new WebSocket(proto + '://' + location.host + '/ws/chat');

  _chatWs.onmessage = function(e) {
    var data = JSON.parse(e.data);
    if (data.type === 'secretary') {
      appendBubble('secretary', 'เลขา', data.response, data.ts, data.tasks || []);
      // Refresh tasks
      loadTasks();
    }
  };

  _chatWs.onclose = function() {
    setTimeout(connectChat, 2000);
  };
}

function sendChat() {
  var input = document.getElementById('chat-input');
  var msg   = input.value.trim();
  if (!msg || !_chatWs || _chatWs.readyState !== WebSocket.OPEN) return;
  appendBubble('user', 'CEO', msg, now());
  input.value = '';
  _chatWs.send(JSON.stringify({ message: msg }));
}

function appendBubble(type, sender, text, ts, tasks) {
  var msgs = document.getElementById('chat-messages');
  var div  = document.createElement('div');
  div.className = 'chat-bubble ' + type;

  var senderEl = '';
  if (type !== 'user' && type !== 'system') {
    senderEl = '<div class="bubble-sender">' + sender + '</div>';
  }

  var taskChips = '';
  if (tasks && tasks.length) {
    taskChips = '<div class="task-chips">' +
      tasks.map(function(t) {
        return '<span class="task-chip">&#x1F4CC; ' + t.title + ' → ' + (t.assigned_to || '') + '</span>';
      }).join('') +
    '</div>';
  }

  div.innerHTML = senderEl +
    '<div>' + text + '</div>' +
    taskChips +
    (ts ? '<div class="bubble-ts">' + ts + '</div>' : '');

  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

// ── Daily Cycle ───────────────────────────────────────────────────
function runCycle() {
  var btn = document.getElementById('run-cycle-btn');
  btn.disabled = true;
  btn.textContent = '⏳ กำลังรัน...';

  var log = document.createElement('div');
  log.className = 'cycle-log visible';
  document.getElementById('activity-feed').before(log);

  var proto = location.protocol === 'https:' ? 'wss' : 'ws';
  _cycleWs = new WebSocket(proto + '://' + location.host + '/ws/cycle');

  _cycleWs.onmessage = function(e) {
    var msg = JSON.parse(e.data);
    if (msg.type === 'agent') {
      // Update office character state
      if (_office) {
        // Mark previous agent done
        var idx = _agents.findIndex(function(a) { return a.id === msg.agent; });
        if (idx > 0) _office.setAgentState(_agents[idx-1].id, 'done');
        _office.setAgentState(msg.agent, 'working');
      }
      appendCycleLog(log, '[' + msg.agent + '] ' + msg.summary, '');
      appendBubble('agent-update', msg.agent, msg.agent + ': ' + msg.summary, now(), []);
    } else if (msg.type === 'done') {
      if (_office) _agents.forEach(function(a) { _office.setAgentState(a.id, 'done'); });
      appendCycleLog(log, 'เสร็จสิ้น cycle วันที่ ' + msg.date, 'done');
      btn.disabled = false;
      btn.textContent = '▶ รัน Daily Cycle';
      // Reset to idle after 3s
      setTimeout(function() {
        if (_office) _agents.forEach(function(a) { _office.setAgentState(a.id, 'idle'); });
      }, 3000);
      loadStats(); loadRecent(); loadTasks(); loadBriefings();
      if (_cycleWs) { _cycleWs.close(); _cycleWs = null; }
    } else if (msg.type === 'error') {
      if (_office) _agents.forEach(function(a) { _office.setAgentState(a.id, 'idle'); });
      appendCycleLog(log, 'ERROR: ' + msg.message, 'err');
      btn.disabled = false;
      btn.textContent = '▶ รัน Daily Cycle';
    }
  };
}

function appendCycleLog(el, text, cls) {
  var line = document.createElement('div');
  line.className = 'cycle-log-line' + (cls ? ' cycle-log-' + cls : '');
  line.textContent = text;
  el.appendChild(line);
  el.scrollTop = el.scrollHeight;
}

// ── Utils ─────────────────────────────────────────────────────────
function now() {
  var d = new Date();
  return d.getHours() + ':' + String(d.getMinutes()).padStart(2, '0');
}

// ── Start ─────────────────────────────────────────────────────────
init().catch(function(err) { console.error('Portal init error:', err); });
