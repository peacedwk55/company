# PROGRESS — AI Company Factory

> ไฟล์นี้คือแหล่งความจริงว่าทำถึงไหนแล้ว และต้องทำอะไรต่อ
> AI ที่มาต่องาน: อ่านไฟล์นี้ก่อนเสมอ

---

## สถานะปัจจุบัน

| | |
|---|---|
| **Stage สำเร็จล่าสุด** | Backend พร้อม + Standalone Bundle + Company Dashboard (pixel art) |
| **Next action** | UI Pixel Office — ตัดสินใจ level (dashboard ปรับปรุง vs isometric full scene) |
| **Tests** | **78/78 passed** |
| **Updated** | 2026-06-01 |

### วิธีเปิด Factory Dashboard
```powershell
$py = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
cd "D:\Demo-Application\AI-company-factory"
& $py start.py
# เปิด http://localhost:8000
```

---

## Architecture ปัจจุบัน

```
AI Company Factory (repo นี้)
├── Factory Dashboard  → http://localhost:8000
│   ├── ⚡ GENERATE COMPANY  ← Claude สร้างบริษัทจาก description
│   ├── Registry list        ← บริษัทที่สร้างแล้ว + path
│   └── ▶ RUN               ← รัน daily cycle ของแต่ละบริษัท
│
└── สร้าง Standalone Project ที่ user เลือก path เอง
    └── D:\projects\myfund\  (example)
        ├── run_cycle.py     ← python run_cycle.py (รัน cycle เอง)
        ├── start.py         ← Company Dashboard (ยังเป็น placeholder)
        ├── agents.yaml      ← Agent roster ที่ Claude generate
        ├── workflow.yaml
        ├── constitution.md
        └── memory/          ← observations, decisions, risk_log, briefings
```

---

## Flow End-to-End (บริษัทเทรด เป็นตัวอย่าง)

```
1. ผู้ใช้พิมพ์ใน Factory Dashboard:
   "บริษัท AI วิเคราะห์ตลาด crypto สร้างรายงานรายวัน"
   Team: 4 agents | Style: balanced

2. Claude generates spec:
   - market_analyst (reasoning)   → วิเคราะห์ BTC/ETH/SET
   - risk_manager   (routine)     → ประเมินความเสี่ยง
   - portfolio_tracker (routine)  → ติดตาม positions
   - ceo            (critical)    → ตัดสิน strategy

3. Factory สร้าง standalone project ที่ D:\projects\cryptofund\

4. กด ▶ RUN บน Factory Dashboard:
   [market_analyst]   BTC momentum +3%, volume above avg
   [risk_manager]     risk score: LOW
   [portfolio_tracker] portfolio stable
   [ceo]              stance: BULLISH
   [brief]            saved → memory/briefings/2026-06-01.md

5. Brief โผล่บน dashboard
```

---

## สิ่งที่ทำเสร็จแล้ว ✅

### Core Engine
- [x] `factory/memory.py` — append-only, FileLock, parse, dedup, task CRUD
- [x] `factory/templates.py` — load, validate_inputs, render placeholders
- [x] `factory/create.py` — create() + create_from_description() + **_bundle_engine()**
- [x] `factory/generator.py` — Claude generates full company spec from description
- [x] `factory/run.py` — run_cycle() + GenericAgent fallback + registry lookup
- [x] `factory/brief.py` — generate daily brief markdown
- [x] `factory/registry.py` — track บริษัทที่สร้าง + path
- [x] `factory/autonomy.py` — AutonomyGate **bind จริง** กับ work_style

### AutonomyGate (ทำงานจริง)
| work_style | LOW | MEDIUM | HIGH |
|---|---|---|---|
| conservative | ❌ confirm | ❌ confirm | ❌ block |
| balanced (default) | ✅ auto | ❌ confirm | ❌ block |
| aggressive | ✅ auto | ✅ auto | ❌ block |

### Agents
- [x] `factory/agents/analyst.py` — AnalystAgent (trading-specific)
- [x] `factory/agents/risk.py` — RiskAgent + hard limits in CODE
- [x] `factory/agents/ceo.py` — CEOAgent
- [x] `factory/agents/generic.py` — **GenericAgent** (ทำงานได้ทุก role จาก spec)

### LLM Layer
- [x] `factory/llm/base.py` — LLMClient Protocol, LLMResponse
- [x] `factory/llm/mock.py` — MockLLMClient (offline, deterministic)
- [x] `factory/llm/anthropic_client.py` — Claude API + **prompt caching**
- [x] `factory/llm/budget_guard.py` — จำกัด token/วัน ตาม company.yaml

### CLI (python -m factory)
- [x] `create` — สร้างบริษัทจาก template (trading)
- [x] `create` — สร้างบริษัทจาก description (Claude generate)
- [x] `run` — รัน daily cycle (lookup path จาก registry)
- [x] `list` — ดูบริษัทที่สร้างแล้วทั้งหมด
- [x] `status` — ดู memory stats + brief preview
- [x] `delete` — ลบบริษัท + ออกจาก registry

### Factory Dashboard (Web UI)
- [x] `api/app.py` — FastAPI server
- [x] `api/routes/companies.py` — REST CRUD + registry-based
- [x] `api/routes/cycles.py` — WebSocket `/ws/{name}/run` realtime
- [x] `api/routes/generator.py` — WebSocket `/ws/factory/generate` streaming
- [x] `api/static/` — Pixel Dashboard (Factory Bot + Registry cards)

### Standalone Company Project (สิ่งที่ gen ออกมาให้ลูกค้า)
- [x] `engine/` — bundled engine code (copy จาก factory, rewrite imports อัตโนมัติ)
- [x] `run_cycle.py` — standalone, ไม่ต้อง install factory
- [x] `requirements.txt` — pip install แค่ 4 deps (pyyaml, filelock, anthropic, python-dotenv)
- [x] ลูกค้าแก้ได้เอง: `agents.yaml`, `constitution.md`, `workflow.yaml`, `memory/`
- [x] รัน offline ได้: `python run_cycle.py --mock`
- [x] รัน Claude จริง: ใส่ key ใน `.env` แล้ว `python run_cycle.py`

### Template
- [x] `templates/trading/` — blueprint สำหรับบริษัทเทรด

### Factory Dashboard & Company Dashboard
- [x] Factory Dashboard (`localhost:8000`) — สร้างบริษัท, registry, run cycle
- [x] Company Dashboard (`localhost:8000/company/{name}`) — pixel art characters 1–11, status, run realtime
- [x] `api/static/sprites/` — 11 ตัวละคร transparent background พร้อมใช้

### Tests: 78/78 passed
- test_memory.py, test_factory_create.py, test_agents.py, test_risk_limits.py, test_integration_run.py

---

## Business Model (ที่ตัดสินใจแล้ว)

```
คุณ (เจ้าของ factory)           ลูกค้า
────────────────────────         ──────────────────────────────
รัน factory create        →      ได้ repo บริษัทไป
ส่ง repo ให้ลูกค้า               pip install -r requirements.txt
                                  python run_cycle.py --mock   ← ทดสอบ
                                  python run_cycle.py          ← ใช้จริง
                                  แก้ไข agents.yaml ได้เอง
```

ลูกค้าไม่รู้จัก factory เลย — รัน standalone ได้ทันที

---

## แผนต่อไป

### 🎯 Next: UI Pixel Office
> Backend พร้อม 100% — ต่อไปคือ visual experience

ต้องตัดสินใจ level ก่อน:

| Level | หน้าตา | Asset ที่ต้องการ |
|---|---|---|
| **A. ปรับ Company Dashboard** | panel + character สวยขึ้น | มีอยู่แล้ว |
| **B. 2D Side-view Office** | ห้อง agent นั่ง desk แต่ละมุม | ต้องหา room/desk asset |
| **C. Isometric Full Office** | มุมเอียง เหมือน ref Water Witch | ต้องมี tileset + sprite sheet ครบ |

### อนาคต (เมื่อ UI เสร็จ)
- V1.1 Hypothesis Engine — agent ตั้งสมมติฐาน track confidence
- V2.1 Real market data — ต่อ CoinGecko/Alpha Vantage/news feed
- V1.2 Agent Personality — memory ส่วนตัว, stable ข้ามวัน

---

## File Structure ปัจจุบัน (ที่ใช้จริง)

```
ai-company-factory/
├── 00_MASTER_SPEC.md      ← spec ทั้งหมด (ยึดตัวนี้)
├── PROGRESS.md            ← ไฟล์นี้
├── start.py               ← python start.py เปิด factory dashboard
├── pyproject.toml
├── .env                   ← ANTHROPIC_API_KEY (gitignored)
│
├── factory/               ← engine ทั้งหมด
│   ├── __main__.py        ← CLI: python -m factory <cmd>
│   ├── create.py          ← create() + create_from_description()
│   ├── run.py             ← run_cycle()
│   ├── generator.py       ← Claude → company spec
│   ├── registry.py        ← track companies + paths
│   ├── memory.py          ← MemoryManager
│   ├── brief.py           ← daily brief
│   ├── autonomy.py        ← AutonomyGate (work_style bound)
│   ├── templates.py       ← Template loader/renderer
│   ├── errors.py          ← custom exceptions
│   ├── config.py          ← paths, logging, .env loader
│   ├── cmd_list/status/delete.py
│   ├── agents/
│   │   ├── base.py        ← Agent ABC, CycleContext, AgentResult
│   │   ├── analyst.py     ← AnalystAgent
│   │   ├── risk.py        ← RiskAgent (hard limits in code)
│   │   ├── ceo.py         ← CEOAgent
│   │   └── generic.py     ← GenericAgent (any role)
│   └── llm/
│       ├── base.py        ← LLMClient Protocol
│       ├── mock.py        ← MockLLMClient (offline)
│       ├── anthropic_client.py  ← Claude API + prompt caching
│       └── budget_guard.py      ← token budget enforcement
│
├── templates/trading/     ← blueprint สำหรับบริษัทเทรด
│   ├── template.yaml
│   ├── company.yaml       ← มี {{placeholder}}
│   ├── agents.yaml
│   ├── workflow.yaml
│   ├── constitution.md
│   └── memory_schema.yaml
│
├── api/                   ← FastAPI server
│   ├── app.py
│   ├── routes/
│   │   ├── companies.py   ← REST CRUD
│   │   ├── cycles.py      ← WebSocket run
│   │   └── generator.py   ← WebSocket generate
│   └── static/
│       ├── index.html     ← Factory Dashboard
│       ├── style.css
│       └── app.js
│
└── tests/                 ← 78 tests
    ├── test_memory.py
    ├── test_factory_create.py
    ├── test_agents.py     ← รวม work_style tests
    ├── test_risk_limits.py
    └── test_integration_run.py
```

---

## Key Design Decisions (สำคัญ — อย่าลืม)

| Decision | เหตุผล |
|---|---|
| Factory repo ≠ Company project | บริษัทที่สร้างเป็น standalone project อิสระ |
| GenericAgent รับ spec จาก agents.yaml | ไม่ต้อง hardcode agent type ใหม่ทุกครั้ง |
| AutonomyGate bind กับ work_style จริง | HIGH block เสมอ, LOW/MEDIUM ขึ้นกับ style |
| Mock LLM เป็น default | dev/test ไม่เสียเงิน ไม่ต้องการ API key |
| Append-only memory | กัน data corruption, audit trail ครบ |
| Atomic write (temp→move) | กัน folder พังครึ่งทาง |
| Registry แยกจาก code | track path ของบริษัทโดยไม่ต้อง hardcode |


Flow จริงที่เกิดขึ้น
ฝั่งคุณ (ทำครั้งเดียว):


python -m factory create --template trading --name myfund --output-dir D:\projects
# หรือผ่าน dashboard: ⚡ GENERATE COMPANY
ส่ง folder myfund/ ให้ลูกค้า (zip / git repo / drive)

ฝั่งลูกค้า (ทำเองได้ทันที):


# 1. ติดตั้ง deps
pip install -r requirements.txt

# 2. ใส่ API key
cp .env.template .env
# แก้ไส้ .env ใส่ ANTHROPIC_API_KEY=sk-ant-...

# 3. รัน
python run_cycle.py
ไม่ต้องรู้จัก factory เลย — รัน cycle ได้ทันที

สิ่งที่ลูกค้าได้รับ

myfund/
├── run_cycle.py     ← รันนี้อย่างเดียวพอ
├── .env.template    ← copy → .env ใส่ key
├── requirements.txt ← pip install
├── README.md        ← อ่านแล้วทำตามได้เลย
├── company.yaml     ← config บริษัท
├── agents.yaml      ← ทีม AI
├── memory/          ← ข้อมูลสะสมรายวัน
└── engine/          ← ไม่ต้องแตะ (bundled)