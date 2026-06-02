'use strict';
/**
 * IsometricOffice — renders office_bg.png as background,
 * overlays real stand/sit character sprites at desk positions.
 *
 * IDLE    → stand_N.png  (gentle bob)
 * WORKING → sit_N.png    (faster bob + purple glow)
 * DONE    → sit_N.png    (green glow → back to idle)
 */

// Desk positions as fractions of the office_bg image (x_center, y_bottom)
// Calibrated to the isometric office_bg.png (1376×768)
const DESK_POS = [
  { fx: 0.26, fy: 0.72 },   // left front desk
  { fx: 0.40, fy: 0.63 },   // left-center desk
  { fx: 0.55, fy: 0.55 },   // center desk
  { fx: 0.67, fy: 0.57 },   // right-center desk
  { fx: 0.76, fy: 0.62 },   // right desk
];

class IsometricOffice {
  constructor(canvas, onAgentClick) {
    this.canvas   = canvas;
    this.ctx      = canvas.getContext('2d');
    this.onClick  = onAgentClick || function () {};

    this.agents   = [];
    this.states   = {};    // id → 'idle'|'working'|'done'
    this.sprites  = {};    // id → { stand: Image, sit: Image }
    this.layout   = [];    // [{ agent, x, y, _hit }]
    this.hoverId  = null;
    this.tick     = 0;
    this.animId   = null;
    this.bgRect   = { x: 0, y: 0, w: 0, h: 0 };
    this.bgScale  = 1;

    // Background image
    this.bgImg        = new Image();
    this.bgImg.src    = '/static/sprites/chars/office_bg.png';
    this.bgImg.onload = () => this._buildLayout();

    canvas.addEventListener('mousemove', this._onMove.bind(this));
    canvas.addEventListener('click',     this._onClic.bind(this));
    canvas.style.cursor = 'default';
  }

  // ── Public ────────────────────────────────────────────────────

  setAgents(agents) {
    this.agents = agents;
    agents.forEach(a => { this.states[a.id] = 'idle'; });
    this._buildLayout();
    this._loadSprites();
  }

  setAgentState(id, state) {
    this.states[id] = state;
  }

  start() {
    if (!this.animId) this._loop();
  }

  stop() {
    if (this.animId) { cancelAnimationFrame(this.animId); this.animId = null; }
  }

  resize(w) {
    this.canvas.width = w;
    this._buildLayout();
  }

  // ── Internals ─────────────────────────────────────────────────

  _buildLayout() {
    const CW = this.canvas.width;
    const CH = this.canvas.height;
    const BG_W = 1376, BG_H = 768;

    // Fit width, center vertically
    const drawW = CW;
    const drawH = CW / (BG_W / BG_H);
    const offY  = (CH - drawH) / 2;

    this.bgRect  = { x: 0, y: offY, w: drawW, h: drawH };
    this.bgScale = drawW / BG_W;

    this.layout = this.agents.map((a, i) => {
      const pos = DESK_POS[i % DESK_POS.length];
      return {
        agent: a,
        x: pos.fx * drawW,
        y: pos.fy * drawH + offY,
        _hit: null,
      };
    });
  }

  _loadSprites() {
    this.agents.forEach((a, i) => {
      if (this.sprites[a.id]) return;
      const n = (i % 10) + 1;
      const stand = new Image();
      stand.src = `/static/sprites/chars/stand_${n}.png`;
      const sit = new Image();
      sit.src = `/static/sprites/chars/sit_${n}.png`;
      this.sprites[a.id] = { stand, sit };
    });
  }

  _spriteH() {
    // Scale so characters are ~110px tall at full canvas width
    return Math.round(this.bgScale * 130);
  }

  _drawAgent(item) {
    const ctx   = this.ctx;
    const a     = item.agent;
    const state = this.states[a.id] || 'idle';
    const spr   = this.sprites[a.id];
    if (!spr) return;

    const img = state === 'working' ? spr.sit : spr.stand;
    if (!img?.complete || !img.naturalHeight) return;

    const t  = this.tick;
    const SH = this._spriteH();
    const SW = Math.round(img.naturalWidth * SH / img.naturalHeight);

    // Bob animation
    const bob = state === 'working'
      ? Math.sin(t * 0.10) * 3
      : Math.sin(t * 0.035) * 2;

    const sx = Math.round(item.x - SW / 2);
    const sy = Math.round(item.y - SH + bob);

    // Shadow under feet
    ctx.save();
    ctx.fillStyle = 'rgba(0,0,0,0.18)';
    ctx.beginPath();
    ctx.ellipse(item.x, item.y + 2, SW * 0.4, 6, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // Sprite with state glow
    ctx.save();
    if (state === 'working') {
      ctx.shadowColor = '#6c63ff';
      ctx.shadowBlur  = 18 + Math.sin(t * 0.12) * 6;
    } else if (state === 'done') {
      ctx.shadowColor = '#4caf82';
      ctx.shadowBlur  = 14;
    }
    ctx.drawImage(img, sx, sy, SW, SH);
    ctx.restore();

    // Hover dashed ring
    if (this.hoverId === a.id) {
      ctx.save();
      ctx.strokeStyle = '#8b84ff';
      ctx.lineWidth   = 2;
      ctx.setLineDash([5, 3]);
      ctx.strokeRect(sx - 3, sy - 3, SW + 6, SH + 6);
      ctx.restore();
    }

    // Name tag pill
    const label = a.id.replace(/_/g, ' ');
    ctx.save();
    ctx.font = `bold ${Math.max(10, Math.round(this.bgScale * 13))}px "Noto Sans Thai", sans-serif`;
    ctx.textAlign    = 'center';
    ctx.textBaseline = 'middle';
    const tw  = ctx.measureText(label).width + 16;
    const th  = 20;
    const tx  = item.x - tw / 2;
    const ty  = sy - 14;

    // Pill background
    const pillColor = state === 'working' ? '#6c63ff'
                    : state === 'done'    ? '#3a7d44'
                    : 'rgba(12,12,28,0.82)';
    ctx.fillStyle = pillColor;
    this._pill(ctx, tx, ty, tw, th, 9);
    ctx.fill();

    ctx.fillStyle = '#f0f0ff';
    ctx.fillText(label, item.x, ty + th / 2);

    if (state === 'working') {
      ctx.fillStyle = '#00ff88';
      ctx.beginPath();
      ctx.arc(tx + tw - 8, ty + th / 2, 4, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();

    // Store hit area
    item._hit = { x: sx, y: sy, w: SW, h: SH };
  }

  _pill(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
  }

  // ── Hit testing ───────────────────────────────────────────────

  _agentAt(mx, my) {
    for (let i = this.layout.length - 1; i >= 0; i--) {
      const { agent, _hit: h } = this.layout[i];
      if (h && mx >= h.x - 4 && mx <= h.x + h.w + 4 &&
               my >= h.y - 4 && my <= h.y + h.h + 4) {
        return agent;
      }
    }
    return null;
  }

  _onMove(e) {
    const r  = this.canvas.getBoundingClientRect();
    const a  = this._agentAt(e.clientX - r.left, e.clientY - r.top);
    this.hoverId             = a ? a.id : null;
    this.canvas.style.cursor = a ? 'pointer' : 'default';
  }

  _onClic(e) {
    const r = this.canvas.getBoundingClientRect();
    const a = this._agentAt(e.clientX - r.left, e.clientY - r.top);
    if (a) this.onClick(a);
  }

  // ── Render loop ───────────────────────────────────────────────

  _loop() {
    const ctx = this.ctx;
    const CW  = this.canvas.width;
    const CH  = this.canvas.height;

    ctx.fillStyle = '#12132a';
    ctx.fillRect(0, 0, CW, CH);

    // Office background
    const bg = this.bgImg;
    if (bg?.complete && bg.naturalHeight > 0) {
      const { x, y, w, h } = this.bgRect;
      ctx.drawImage(bg, x, y, w, h);
    }

    // Agents sorted back-to-front by y
    const sorted = [...this.layout].sort((a, b) => a.y - b.y);
    sorted.forEach(item => this._drawAgent(item));

    this.tick++;
    this.animId = requestAnimationFrame(this._loop.bind(this));
  }
}

window.IsometricOffice = IsometricOffice;
