'use strict';

// Company name from URL path
const COMPANY = window.location.pathname.split('/').pop();

// State
let ws         = null;
let isRunning  = false;
let startTime  = null;
let timerID    = null;
let _agents    = [];

// DOM refs
const runBtn = document.getElementById('run-btn');

// ── Character image — 1.png to 11.png, assigned by agent index ──
function charSVG(tier, state, role, agentIndex) {
  var num = ((agentIndex || 0) % 11) + 1;   // cycles 1–11
  var cls = state || 'idle';
  return '<img class="char-sprite-img ' + cls + '" src="/static/sprites/' + num + '.png" alt="' + (role || 'agent') + '">';
}

// ── Boot ─────────────────────────────────────────────────
async function init() {
  document.title = COMPANY.toUpperCase() + ' — Dashboard';
  document.getElementById('hdr-name').textContent = COMPANY.toUpperCase();
  updateClock();
  setInterval(updateClock, 60000);

  const [status, agentData] = await Promise.all([
    api('/api/companies/' + COMPANY),
    api('/api/companies/' + COMPANY + '/agents'),
  ]);

  _agents = agentData.agents || [];
  document.getElementById('hdr-type').textContent =
    (status.template || '') + ' - ' + (status.mode || 'paper') + ' - ' + (status.risk_level || 'low');

  renderPipelineDots(_agents);
  _agents.forEach(function(a) { });  // init state
  renderTeamStatus(_agents);
  renderWorkspaces(_agents);
  renderAgentCards(_agents);
  renderPipelineLog(_agents);
  updateStats(status, _agents);

  runBtn.disabled = false;
  runBtn.addEventListener('click', onRun);
}

// ── Pipeline dots ─────────────────────────────────────────
function renderPipelineDots(agents) {
  const wrap = document.getElementById('pipe-agents-dots');
  wrap.innerHTML = agents.map(function(a) {
    return '<div class="pipe-dot" id="pdot-' + a.id + '"></div>';
  }).join('');
}

// ── Team Status (left panel) ──────────────────────────────
function renderTeamStatus(agents) {
  var list = document.getElementById('agent-status-list');
  list.innerHTML = agents.map(function(a, i) {
    return '<div class="agent-status-row" id="arow-' + a.id + '">' +
      '<div class="agent-mini-sprite">' + charSVG(a.model_tier, 'idle', a.role, i) + '</div>' +
      '<div class="agent-mini-info">' +
        '<div class="agent-mini-name">' + a.id.replace(/_/g, ' ') + '</div>' +
        '<div class="agent-mini-state" id="astate-' + a.id + '">IDLE</div>' +
      '</div>' +
      '<div class="dot dot-grey" id="adot-' + a.id + '"></div>' +
    '</div>';
  }).join('');
}

// ── Workspace panels (center) ────────────────────────────
function renderWorkspaces(agents) {
  var grid = document.getElementById('workspaces');
  grid.innerHTML = agents.map(function(a, i) {
    return '<div class="workspace-panel" id="ws-' + a.id + '">' +
      '<div class="ws-header">' +
        '<span class="ws-title">' + a.role.toUpperCase() + '</span>' +
        '<div class="ws-status-area">' +
          '<span class="ws-status-text" id="wsstatus-' + a.id + '">IDLE</span>' +
          '<div class="dot dot-grey" id="wsdot-' + a.id + '"></div>' +
        '</div>' +
      '</div>' +
      '<div class="ws-char-center" id="wschar-' + a.id + '">' +
        charSVG(a.model_tier, 'idle', a.role, i) +
      '</div>' +
      '<div class="ws-output" id="wsout-' + a.id + '">Waiting for cycle...</div>' +
    '</div>';
  }).join('');
}

// ── Agent cards (right panel) ────────────────────────────
function renderAgentCards(agents) {
  const col = document.getElementById('agent-cards');
  col.innerHTML = agents.map(function(a) {
    return '<div class="agent-card" id="ac-' + a.id + '">' +
      '<div class="ac-header">' +
        '<span class="ac-title">' + a.id.replace(/_/g, ' ').toUpperCase() + ' AGENT</span>' +
        '<span class="ac-tier">' + a.model_tier.toUpperCase() + '</span>' +
        '<div class="dot dot-grey" id="acdot-' + a.id + '"></div>' +
      '</div>' +
      '<div class="ac-content" id="acco-' + a.id + '">Standby...</div>' +
    '</div>';
  }).join('');
}

// ── Pipeline log (right bottom) ──────────────────────────
function renderPipelineLog(agents) {
  const steps = document.getElementById('pipeline-steps');
  steps.innerHTML = agents.map(function(a) {
    return '<div class="pipe-log-row" id="plog-' + a.id + '">' +
      '<span class="pipe-log-name">' + a.id.replace(/_/g, ' ').toUpperCase() + '</span>' +
      '<span class="pipe-log-icon wait" id="plogicon-' + a.id + '">&#x25A1;</span>' +
    '</div>';
  }).join('');
}

// ── Set agent UI state ────────────────────────────────────
// state: 'idle' | 'working' | 'done'
function setAgentState(agentId, state, output) {
  var dotClass  = state === 'working' ? 'dot-green pulsing' : state === 'done' ? 'dot-yellow' : 'dot-grey';
  var stateText = state === 'working' ? 'WORKING...' : state === 'done' ? 'DONE' : 'IDLE';
  var wsClass   = state === 'working' ? 'working' : state === 'done' ? 'done' : '';

  // Status row (left)
  var row = document.getElementById('arow-' + agentId);
  if (row) row.className = 'agent-status-row ' + wsClass;
  setDot('adot-' + agentId, dotClass);
  setDot('wsdot-' + agentId, dotClass);
  setDot('acdot-' + agentId, dotClass);

  var stateEl = document.getElementById('astate-' + agentId);
  if (stateEl) {
    stateEl.textContent = stateText;
    stateEl.className = 'agent-mini-state ' + state;
  }

  // Pipeline dot
  var pdot = document.getElementById('pdot-' + agentId);
  if (pdot) pdot.className = 'pipe-dot' + (state === 'working' ? ' active' : '');

  // Workspace panel
  var ws = document.getElementById('ws-' + agentId);
  if (ws) ws.className = 'workspace-panel ' + wsClass;

  // Update ws-status-text
  var wsStatusText = document.getElementById('wsstatus-' + agentId);
  if (wsStatusText) {
    wsStatusText.textContent = stateText;
    wsStatusText.className = 'ws-status-text ' + state;
  }

  // Update character sprite state (re-render with new state class)
  var charDiv = document.getElementById('wschar-' + agentId);
  if (charDiv) {
    var agentIndex = _agents.findIndex(function(a) { return a.id === agentId; });
    var agentData  = agentIndex >= 0 ? _agents[agentIndex] : null;
    if (agentData) charDiv.innerHTML = charSVG(agentData.model_tier, state, agentData.role, agentIndex);
  }

  // Output text
  if (output) {
    var outEl = document.getElementById('wsout-' + agentId);
    if (outEl) { outEl.textContent = output; outEl.className = 'ws-output active'; }
    var accoEl = document.getElementById('acco-' + agentId);
    if (accoEl) { accoEl.textContent = output; accoEl.className = 'ac-content active'; }
  }

  // Agent card
  var ac = document.getElementById('ac-' + agentId);
  if (ac) ac.className = 'agent-card ' + wsClass;

  // Pipeline log icon
  var plogicon = document.getElementById('plogicon-' + agentId);
  if (plogicon) {
    plogicon.className = 'pipe-log-icon ' + state;
    plogicon.innerHTML = state === 'done' ? '&#x2713;' : state === 'working' ? '&#x25BA;' : '&#x25A1;';
  }

  // All systems label
  var anyWorking = _agents.some(function(a) { return document.getElementById('astate-' + a.id) && document.getElementById('astate-' + a.id).textContent === 'WORKING...'; });
  var sys = document.getElementById('all-systems');
  if (sys) {
    if (state === 'working') {
      sys.className = 'all-systems active';
      sys.innerHTML = '<span class="dot dot-green pulsing"></span> ALL SYSTEMS OPERATIONAL';
    } else if (_agents.every(function(a) { var el = document.getElementById('astate-' + a.id); return el && el.textContent === 'DONE'; })) {
      sys.className = 'all-systems';
      sys.innerHTML = '<span class="dot dot-yellow"></span> CYCLE COMPLETE';
    }
  }
}

function setDot(id, cls) {
  var el = document.getElementById(id);
  if (el) el.className = 'dot ' + cls;
}

// ── Run Cycle ─────────────────────────────────────────────
function onRun() {
  if (isRunning) return;
  isRunning = true;
  startTime = Date.now();
  runBtn.disabled = true;

  _agents.forEach(function(a) { setAgentState(a.id, 'idle', 'Running...'); });
  document.getElementById('st-status').textContent = 'RUNNING';
  if (timerID) clearInterval(timerID);
  timerID = setInterval(updateRuntime, 1000);

  var proto = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(proto + '://' + location.host + '/ws/' + COMPANY + '/run');
  ws.onmessage = function(e) { handleMsg(JSON.parse(e.data)); };
  ws.onerror   = function() { finishRun(); };
  ws.onclose   = function() { if (isRunning) finishRun(); };
}

function handleMsg(msg) {
  if (msg.type === 'agent') {
    var idx = _agents.findIndex(function(a) { return a.id === msg.agent; });
    if (idx > 0) setAgentState(_agents[idx - 1].id, 'done');
    setAgentState(msg.agent, 'working', msg.summary || 'Working...');
  } else if (msg.type === 'brief') {
    _agents.forEach(function(a) { setAgentState(a.id, 'done'); });
  } else if (msg.type === 'done') {
    document.getElementById('st-status').textContent = 'SUCCESS';
    finishRun();
    refreshStats();
  } else if (msg.type === 'error') {
    document.getElementById('st-status').textContent = 'ERROR';
    _agents.forEach(function(a) { setAgentState(a.id, 'idle'); });
    finishRun();
  }
}

function finishRun() {
  isRunning = false;
  runBtn.disabled = false;
  clearInterval(timerID);
  if (ws) { ws.close(); ws = null; }
}

// ── Stats ─────────────────────────────────────────────────
async function refreshStats() {
  var s = await api('/api/companies/' + COMPANY);
  updateStats(s, _agents);
}

function updateStats(status, agents) {
  document.getElementById('st-agents').textContent  = agents.length + '/' + agents.length + ' ONLINE';
  document.getElementById('st-obs').textContent     = (status.memory && status.memory.observations) || 0;
  document.getElementById('st-dec').textContent     = (status.memory && status.memory.decisions)    || 0;
  if (!isRunning) document.getElementById('st-status').textContent = status.last_run ? 'STANDBY' : 'READY';
}

// ── Runtime timer ─────────────────────────────────────────
function updateRuntime() {
  if (!startTime) return;
  var s   = Math.floor((Date.now() - startTime) / 1000);
  var m   = Math.floor(s / 60);
  var sec = s % 60;
  document.getElementById('st-runtime').textContent = m + 'm ' + sec + 's';
}

// ── Clock ─────────────────────────────────────────────────
function updateClock() {
  var now  = new Date();
  var h    = String(now.getHours()).padStart(2, '0');
  var min  = String(now.getMinutes()).padStart(2, '0');
  var ampm = now.getHours() >= 12 ? 'PM' : 'AM';
  document.getElementById('hdr-time').textContent = h + ':' + min + ' ' + ampm;
}

// ── Fetch ─────────────────────────────────────────────────
async function api(url) {
  var res = await fetch(url);
  if (!res.ok) throw new Error('HTTP ' + res.status);
  return res.json();
}

// ── Start ─────────────────────────────────────────────────
init().catch(function(err) { console.error('Dashboard error:', err); });
