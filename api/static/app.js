'use strict';

// ── State ────────────────────────────────────────────────────────
let ws         = null;
let runningFor = null;

// ── DOM ──────────────────────────────────────────────────────────
const newBtn       = document.getElementById('new-btn');
const modal        = document.getElementById('modal');
const cancelBtn    = document.getElementById('cancel-btn');
const generateBtn  = document.getElementById('generate-btn');
const modalError   = document.getElementById('modal-error');
const pathPreview  = document.getElementById('path-preview');
const botSprite    = document.getElementById('bot-sprite');
const botStatus    = document.getElementById('bot-status');
const botMsg       = document.getElementById('bot-msg');
const companyList  = document.getElementById('company-list');
const briefPanel   = document.getElementById('brief-panel');
const briefContent = document.getElementById('brief-content');
const briefLabel   = document.getElementById('brief-company-label');
const logLines     = document.getElementById('log-lines');

// selected values for team size + work style
let selectedSize  = 0;   // 0 = AUTO
let selectedStyle = 'balanced';

// ── Boot ─────────────────────────────────────────────────────────
async function init() {
  await refresh();

  newBtn.addEventListener('click', openModal);
  cancelBtn.addEventListener('click', closeModal);
  generateBtn.addEventListener('click', onGenerate);
  document.getElementById('brief-close').addEventListener('click', () => briefPanel.classList.add('hidden'));

  // toggle buttons
  document.getElementById('size-group').addEventListener('click', e => {
    if (!e.target.dataset.val) return;
    selectedSize = parseInt(e.target.dataset.val);
    document.querySelectorAll('#size-group .btn-option').forEach(b => b.classList.toggle('active', b.dataset.val == e.target.dataset.val));
  });
  document.getElementById('style-group').addEventListener('click', e => {
    if (!e.target.dataset.val) return;
    selectedStyle = e.target.dataset.val;
    document.querySelectorAll('#style-group .btn-option').forEach(b => b.classList.toggle('active', b.dataset.val === e.target.dataset.val));
  });

  // live path preview
  const nameInput   = document.getElementById('inp-name');
  const outdirInput = document.getElementById('inp-outdir');
  const updatePreview = () => {
    const n = nameInput.value.trim().toLowerCase();
    const d = outdirInput.value.trim();
    pathPreview.textContent = (n && d) ? `→ ${d}\\${n}` : '';
  };
  nameInput.addEventListener('input', updatePreview);
  outdirInput.addEventListener('input', updatePreview);
}

// ── Data ─────────────────────────────────────────────────────────
async function refresh() {
  const data = await api('/api/companies');
  const list = data.companies || [];
  renderRegistry(list);
  document.getElementById('fs-total').textContent      = list.length;
  document.getElementById('registry-count').textContent = list.length;
}

// ── Registry ──────────────────────────────────────────────────────
function renderRegistry(companies) {
  if (!companies.length) {
    companyList.innerHTML = `
      <div class="empty-msg">
        No companies yet.<br/>
        Click <strong>GENERATE COMPANY</strong> to create your first AI company.
      </div>`;
    return;
  }
  companyList.innerHTML = '';
  companies.forEach(c => companyList.appendChild(buildCard(c)));
}

function buildCard(c) {
  const div      = document.createElement('div');
  const missing  = c.exists === false;
  const isRun    = runningFor === c.name;
  const lastRun  = c.last_run || 'never';

  div.className = `company-card${missing ? ' missing' : ''}${isRun ? ' running' : ''}`;
  div.id        = `card-${c.name}`;

  div.innerHTML = `
    <div class="card-header">
      <span class="card-icon">&#x1F4E6;</span>
      <span class="card-name">${c.name}</span>
      <div class="card-actions">
        <button class="btn-run" onclick="onRun('${c.name}')" ${isRun || missing ? 'disabled' : ''}>&#x25B6; RUN</button>
        <button class="btn-info" onclick="onBrief('${c.name}')">&#x1F4C4;</button>
        <button class="btn-del"  onclick="onDelete('${c.name}')">&#x1F5D1;</button>
      </div>
    </div>
    <div class="card-meta">
      <span>&#x1F4CB; ${c.template} &nbsp;|&nbsp; created ${c.created_at} &nbsp;|&nbsp; last run: ${lastRun}</span>
      ${missing ? '<span style="color:var(--red)">&#x26A0; Folder not found</span>' : ''}
    </div>
    <div class="card-path">${c.path}</div>
    <div class="card-status${isRun ? ' running' : ''}" id="cstatus-${c.name}">
      ${isRun ? 'RUNNING...' : (missing ? 'MISSING' : 'IDLE')}
    </div>`;
  return div;
}

// ── Run Cycle (existing company) ──────────────────────────────────
function onRun(name) {
  if (runningFor) return;
  runningFor = name;
  briefPanel.classList.add('hidden');
  setBotState('working', 'Running cycle...');
  addLog(`> Running cycle for '${name}'...`, 'info');
  setCardStatus(name, 'RUNNING...', 'running');
  disableRunBtns(true);

  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${proto}://${location.host}/ws/${name}/run`);
  ws.onmessage = e => handleRunMsg(name, JSON.parse(e.data));
  ws.onerror   = () => { addLog('> Connection error', 'error'); finishRun(name); };
  ws.onclose   = () => { if (runningFor) finishRun(name); };
}

function handleRunMsg(name, msg) {
  if (msg.type === 'agent') {
    addLog(`  [${msg.agent}] ${msg.summary || ''}`, 'agent');
    setBotMsg(`[${msg.agent}] ${msg.summary || ''}`);
  } else if (msg.type === 'brief') {
    showBrief(name, msg.content || '');
    addLog('  [brief] saved', 'done');
  } else if (msg.type === 'done') {
    addLog(`> Cycle complete (${msg.date})`, 'done');
    setBotState('done', 'Cycle complete!');
    setTimeout(() => setBotState('idle', ''), 2000);
    finishRun(name);
    refresh();
  } else if (msg.type === 'error') {
    addLog(`> ERROR: ${msg.message}`, 'error');
    setBotState('idle', '');
    finishRun(name);
  }
}

function finishRun(name) {
  setCardStatus(name, 'IDLE', '');
  disableRunBtns(false);
  runningFor = null;
  if (ws) { ws.close(); ws = null; }
}

function disableRunBtns(disabled) {
  document.querySelectorAll('.btn-run').forEach(b => b.disabled = disabled);
}

// ── Generate new company ──────────────────────────────────────────
function onGenerate() {
  const description = document.getElementById('inp-desc').value.trim();
  const name        = document.getElementById('inp-name').value.trim().toLowerCase();
  const outputDir   = document.getElementById('inp-outdir').value.trim();

  if (!description) { showModalErr('Please describe your company'); return; }
  if (!name)        { showModalErr('Company name is required'); return; }
  if (!outputDir)   { showModalErr('Output directory is required'); return; }

  generateBtn.disabled    = true;
  generateBtn.textContent = '⚡ GENERATING...';
  modalError.classList.add('hidden');
  setBotState('working', 'Connecting to Claude...');
  addLog(`> Generating '${name}' with Claude...`, 'info');
  closeModal();

  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const genWs = new WebSocket(`${proto}://${location.host}/ws/factory/generate`);

  genWs.onopen = () => {
    genWs.send(JSON.stringify({
      description,
      name,
      output_dir:  outputDir,
      agent_count: selectedSize,
      work_style:  selectedStyle,
      risk_level:  'low',
    }));
  };

  genWs.onmessage = e => {
    const msg = JSON.parse(e.data);
    if (msg.type === 'step') {
      addLog(`  ${msg.message}`, 'info');
      setBotMsg(msg.message);
    } else if (msg.type === 'done') {
      const agentNames = (msg.agents || []).join(', ');
      addLog(`> Created: ${msg.path}`, 'done');
      addLog(`  Type: ${msg.company_type} | Agents: ${agentNames}`, 'done');
      setBotState('done', `Done! ${msg.company_type}`);
      setTimeout(() => setBotState('idle', ''), 2500);
      refresh();
    } else if (msg.type === 'error') {
      addLog(`> ERROR: ${msg.message}`, 'error');
      setBotState('idle', '');
    }
  };

  genWs.onclose = () => {
    generateBtn.disabled    = false;
    generateBtn.textContent = '⚡ GENERATE & CREATE';
  };
  genWs.onerror = () => {
    addLog('> WebSocket error during generation', 'error');
    setBotState('idle', '');
    generateBtn.disabled    = false;
    generateBtn.textContent = '⚡ GENERATE & CREATE';
  };
}

// ── Brief ─────────────────────────────────────────────────────────
async function onBrief(name) {
  const data = await api(`/api/companies/${name}/brief`);
  showBrief(name, data.content || 'No brief yet. Run a cycle first.');
}

function showBrief(name, content) {
  briefLabel.textContent  = name;
  briefContent.textContent = content;
  briefPanel.classList.remove('hidden');
}

// ── Delete ────────────────────────────────────────────────────────
async function onDelete(name) {
  if (!confirm(`Delete '${name}' and remove from registry?`)) return;
  await fetch(`/api/companies/${name}`, { method: 'DELETE' });
  addLog(`> Deleted: ${name}`, 'done');
  await refresh();
}

// ── Bot ───────────────────────────────────────────────────────────
function setBotState(state, msg) {
  botSprite.className = `bot-sprite ${state}`;
  const labels = { idle: 'IDLE', working: 'WORKING...', done: 'DONE ✓' };
  botStatus.textContent = labels[state] || state.toUpperCase();
  botStatus.className   = `bot-status ${state}`;
  if (msg !== undefined) setBotMsg(msg);
}

function setBotMsg(text) {
  botMsg.textContent = text || '';
}

function setCardStatus(name, text, cls) {
  const el = document.getElementById(`cstatus-${name}`);
  if (el) { el.textContent = text; el.className = `card-status ${cls}`; }
}

// ── Modal ─────────────────────────────────────────────────────────
function openModal() {
  modalError.classList.add('hidden');
  pathPreview.textContent = '';
  document.getElementById('inp-desc').value   = '';
  document.getElementById('inp-name').value   = '';
  document.getElementById('inp-outdir').value = '';
  modal.classList.remove('hidden');
  setTimeout(() => document.getElementById('inp-desc').focus(), 50);
}

function closeModal() { modal.classList.add('hidden'); }

function showModalErr(msg) {
  modalError.textContent = '> ' + msg;
  modalError.classList.remove('hidden');
}

// ── Log ───────────────────────────────────────────────────────────
function addLog(text, cls = '') {
  const div = document.createElement('div');
  div.className = `log ${cls}`;
  div.textContent = text;
  logLines.appendChild(div);
  logLines.scrollTop = logLines.scrollHeight;
  while (logLines.children.length > 120) logLines.removeChild(logLines.firstChild);
}

// ── Fetch ─────────────────────────────────────────────────────────
async function api(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

init().catch(err => { console.error(err); addLog('> Init error: ' + err.message, 'error'); });
