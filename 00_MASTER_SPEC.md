# 00_MASTER_SPEC.md — AI Company Factory (Single Source of Truth)

Version: 1.0
Status: **AUTHORITATIVE** — ไฟล์นี้คือแหล่งความจริงเดียว (single source of truth)
Date: 2026-06-01

---

## 📌 วิธีอ่านเอกสารนี้

เอกสารเดิม 7 ไฟล์ (`01`–`05`, `readme`, `ex.`) **ยังเก็บไว้เป็น reference**
แต่ถ้ามีข้อความขัดแย้งกัน → **ให้ยึดไฟล์นี้เป็นหลัก**

> 🤖 **ถึง AI ที่จะ generate code — อ่านตรงนี้ก่อน:**
> 1. ใช้ไฟล์นี้ไฟล์เดียวเป็น contract; ไฟล์ `01`–`05`, `readme`, `ex` เป็น context/เจตนา ไม่ใช่ spec ที่ build
> 2. **§12–§16 คือพิมพ์เขียวที่ลง code ได้ทันที**: §12 repo layout · §13 module interfaces (signatures) · §14 schemas เต็ม · §15 mock LLM · §16 build order รายไฟล์ + Definition of Done
> 3. Build ตามลำดับ §16 (M0→M5) เท่านั้น; ทุก module ต้องมาพร้อม test (§9) และ run บน Windows ได้
> 4. Default ทุกอย่างปลอดภัย: **Mock LLM** (ไม่เรียก API จริง), **paper trading**, **append-only memory**, **atomic write**
> 5. สิ่งที่ติดป้าย 🟡 v1.0+ / 🔴 Future ใน §2, §5 — **ห้าม generate** จนกว่า MVP (§3) จะผ่าน acceptance criteria

ไฟล์นี้แก้จุดอ่อน 8 ข้อที่พบในเอกสารเดิม:

| # | จุดอ่อนเดิม | แก้ที่ section |
|---|---|---|
| 1 | มีแต่ planning ไม่มี code | §3 MVP + §4 Factory Spec (พร้อมลง code) |
| 2 | Vision ใหญ่เกินจริง | §2 (เก็บ vision ไว้ + ติดป้าย MVP/Future) |
| 3 | Markdown เป็น DB ไม่ scale | §6 Data Strategy |
| 4 | Factory ไม่มี spec จริง | §4 Factory Technical Spec |
| 5 | เอกสารขัดแย้งกันเอง | §5 Reconciled Roadmap + §10 Glossary |
| 6 | Trading เสี่ยงกฎหมาย/เงิน | §8 Safety & Legal |
| 7 | ไม่คิดค่า Claude API | §7 Cost Model |
| 8 | ไม่มี testing / MVP ชัด | §3 MVP + §9 Testing |

---

## §1. หลักการสูงสุด (Prime Directives)

1. **Brain first, UI last** — สร้างสมองก่อน หน้าจอทีหลังเสมอ
2. **Smallest working system first** — ทุก phase ต้อง run ได้จริงก่อนไป phase ถัดไป
3. **Vision ใหญ่ได้ แต่ build ทีละชิ้น** — ฝันใหญ่ ลงมือเล็ก
4. **File-based ก่อน Database ทีหลัง** — เริ่มด้วยไฟล์ ค่อยย้ายเข้า DB เมื่อจำเป็น (ดู §6)
5. **ทุก agent action ต้องผ่าน Autonomy Gate** — ไม่มี action ไหนข้าม safety check (ดู §8)

---

## §2. VISION (เก็บไว้ครบ — ติดป้ายชัด)

> **"Operating System for Artificial Companies"**
> ระบบที่ generate และ run บริษัท AI ได้ไม่จำกัด แบบ dynamic

```
[ USER INPUT ]
      ↓
[ SAAS COMPANY FACTORY ]   ← โรงงาน (เครื่องจักร)
      ↓
[ COMPANY GENERATOR ]      ← สายการผลิต
      ↓
[ /companies/{id}/ ]       ← บริษัทที่ถูกผลิต (instance)
      ↓
[ RUNNING AI COMPANY ]     ← บริษัทเริ่มทำงาน
```

### Vision Stages — ติดป้าย MVP / Future

| Stage | คำอธิบาย | ป้าย |
|---|---|---|
| 1. Single Company OS | บริษัทเดียว ใช้ภายใน | 🟢 **MVP** |
| 2. Multi-Company | หลาย company, isolated memory | 🟡 **v1.0** |
| 3. Company Templates | เลือก type (Trading/Marketing/SaaS) | 🟡 **v1.0** |
| 4. Company Generator | AI สร้างบริษัทจาก input | 🟢 **MVP** (เวอร์ชันง่าย) → 🟡 v1.0 (เต็ม) |
| 5. Autonomous Network | บริษัท AI คุย/แข่ง/เทรดกันเอง | 🔴 **Future (R&D)** |

> **กฎ:** อะไรที่ติดป้าย 🔴 Future ห้ามแตะจนกว่า 🟢 MVP จะ run ได้จริงและมีคนใช้

---

## §3. MVP DEFINITION (เป้าหมายแรกที่ต้องไปให้ถึง)

### นิยาม MVP

> **"Factory สร้าง 1 บริษัทออกมาเป็น folder จริง → agents วนลูป 1 รอบ → เขียนผลลง memory → สร้าง daily brief"**

### MVP ทำอะไรได้ (Acceptance Criteria — วัดได้จริง)

```bash
# 1. สร้างบริษัทจาก template
python -m factory.create --template trading --name myfund

# ✅ ต้องเกิด folder:
#   companies/myfund/
#   ├── company.yaml
#   ├── agents.yaml
#   ├── memory/ (ไฟล์ .md เปล่าพร้อมใช้)
#   └── logs/

# 2. รันบริษัท 1 cycle
python -m factory.run --company myfund

# ✅ ต้องเห็น output:
#   [analyst] generated 2 observations
#   [risk]    risk score: LOW
#   [ceo]     stance: NEUTRAL
#   [brief]   saved → companies/myfund/memory/briefings/2026-06-01.md
```

### MVP Checklist (Definition of Done)

- [ ] `factory.create` อ่าน template → เขียน folder + files ครบ
- [ ] template validation: input ผิด → error ชัดเจน ไม่สร้าง folder พัง
- [ ] memory read/write ทำงาน (อ่าน `.md`, append entry, ไม่ทับของเดิม)
- [ ] agent base class + อย่างน้อย 2 agents (analyst, risk) วนลูปได้
- [ ] daily brief generate เป็นไฟล์ `.md`
- [ ] มี unit test ครอบ factory + memory (ดู §9)
- [ ] run บน Windows ได้ (เครื่อง dev จริง)

### MVP **ไม่ต้องมี**

❌ Dashboard / React  ❌ PostgreSQL  ❌ Multi-tenant
❌ Marketplace  ❌ Pixel Office  ❌ Real trading  ❌ External integrations

**ประเมินเวลา:** 2–3 สัปดาห์ (1 คน)

---

## §4. FACTORY TECHNICAL SPEC (จุดอ่อนใหญ่ที่สุด — เติมให้ครบ)

เดิมบอกแค่ "generate agents จาก templates" แต่ไม่มี spec จริง — ต่อไปนี้คือ spec ที่ลง code ได้ทันที

### 4.1 Template Format

Template = 1 folder ใน `templates/{type}/` ประกอบด้วย:

```
templates/trading/
├── template.yaml        ← metadata + ตัวแปรที่รับ input
├── agents.yaml          ← นิยาม agents (พร้อม placeholder)
├── workflow.yaml        ← daily workflow steps
├── constitution.md      ← กฎ/ค่านิยมของบริษัทประเภทนี้
└── memory_schema.yaml   ← memory files ที่ต้องสร้าง
```

**`template.yaml` ตัวอย่าง:**

```yaml
id: trading
name: "AI Trading Company"
version: 1.0
description: "Autonomous trading & investment company"

# ตัวแปรที่ user ส่งเข้ามา (มี validation)
inputs:
  name:
    type: string
    required: true
    pattern: "^[a-z0-9_]{3,32}$"   # บังคับ slug ปลอดภัย
  risk_level:
    type: enum
    values: [low, medium, high]
    default: low                    # default ปลอดภัยสุด
  initial_capital:
    type: number
    min: 0
    default: 0                      # 0 = paper trading เท่านั้น

# safety: trading type บังคับ default paper
defaults:
  execution_mode: paper             # paper | live (live ต้อง explicit + ดู §8)
```

### 4.2 Generation Pipeline (ขั้นตอนจริง)

```
create(template, inputs)
   │
   1. LOAD template folder
   │
   2. VALIDATE inputs ตาม template.yaml.inputs
   │     ❌ ถ้าไม่ผ่าน → raise ValidationError, ไม่สร้างอะไร
   │
   3. RENDER: แทน placeholder ใน agents/workflow/constitution
   │     ({{name}}, {{risk_level}} → ค่าจริง)
   │
   4. CHECK collision: ถ้า companies/{name}/ มีอยู่แล้ว → error
   │
   5. WRITE atomically:
   │     - เขียนลง temp dir ก่อน → ถ้าครบค่อย move เข้า companies/{name}/
   │     - กัน folder พังครึ่ง ๆ
   │
   6. INIT memory: สร้าง .md เปล่าตาม memory_schema.yaml
   │
   7. WRITE manifest: companies/{name}/.manifest.json
   │     (template id, version, created_at, inputs ที่ใช้)
   │
   └── return CompanyInstance
```

### 4.3 Output Structure (instance ที่ generate ออกมา)

```
companies/myfund/
├── .manifest.json          ← provenance: สร้างจาก template อะไร เมื่อไหร่
├── company.yaml            ← profile (rendered)
├── constitution.md         ← กฎบริษัทนี้
├── agents.yaml             ← agent roster (rendered)
├── workflow.yaml           ← daily steps
├── memory/
│   ├── entities.md
│   ├── hypotheses.md
│   ├── decisions.md
│   ├── observations.md
│   ├── task_queue.md
│   └── briefings/          ← brief รายวันมาเก็บที่นี่
└── logs/
    └── run.log
```

### 4.4 หลักการสำคัญ

- **Template = static (ใน repo) / Instance = generated (runtime)** — ไม่ปนกัน
- **Manifest = provenance** — รู้เสมอว่า instance นี้มาจาก template+version ไหน (ทำ migration ได้ทีหลัง)
- **Atomic write** — ไม่มี folder สร้างพังครึ่งทาง
- **Validation ก่อนเขียน** — input ผิดไม่ทำให้ระบบพัง

---

## §5. RECONCILED ROADMAP (รวม 14 phases / 10 weeks / 6 layers ให้ตรงกัน)

ปัญหาเดิม: เอกสารคนละไฟล์นับไม่ตรงกัน — ตารางนี้คือ mapping เดียวที่ถูกต้อง

| Stage | Phase (จาก roadmap) | Week (จาก exec plan) | Layer (จาก customization) | ป้าย |
|---|---|---|---|---|
| **M0** Foundation | Phase 0 | Week 1 | — | 🟢 MVP |
| **M1** Memory Engine | Phase 1 | Week 1 | Layer 6 (Memory) | 🟢 MVP |
| **M2** Factory + Generator | (เพิ่มใหม่ §4) | Week 1–2 | Layer 2 (Company Def) | 🟢 MVP |
| **M3** Task Engine | Phase 2 | Week 2 | Layer 6 | 🟢 MVP |
| **M4** Agent Runtime | Phase 5 | Week 5 | Layer 3 (Agents) | 🟢 MVP |
| **M5** Daily Brief | Phase 4 | Week 4 | — | 🟢 MVP |
| — จบ MVP ที่นี่ — | | | | |
| V1.1 Hypothesis | Phase 3 | Week 3 | Layer 6 | 🟡 v1.0 |
| V1.2 Agent Workforce | Phase 6 | Week 5 | Layer 3 | 🟡 v1.0 |
| V1.3 Workflow Engine | Phase 7 | Week 6 | Layer 5 (Workflows) | 🟡 v1.0 |
| V1.4 Autonomy System | Phase 11 | Week 9 | (autonomy_matrix) | 🟡 v1.0 |
| V2.1 Integrations | Phase 8 | Week 7 | Layer 4 (Skills) | 🟡 v2.0 |
| V2.2 Business Intel | Phase 9 | Week 8 | — | 🟡 v2.0 |
| V2.3 Dashboard | Phase 10 | Week 10 | — | 🟡 v2.0 |
| F1 Pixel Office | Phase 12 | Week 11+ | — | 🔴 Future |
| F2 AI Software House | Phase 13 | — | — | 🔴 Future |
| F3 Self-Improvement | Phase 14 | — | — | 🔴 Future |
| F4 Autonomous Network | (Stage 5) | — | — | 🔴 Future |

> **ใช้คอลัมน์ "Stage" (M0–M5, V1.x, V2.x, F1–F4) เป็นชื่อทางการต่อจากนี้**

---

## §6. DATA STRATEGY (แก้ปัญหา Markdown vs PostgreSQL)

ปัญหาเดิม: เลือกทั้ง Markdown และ PostgreSQL → ขัดกัน, markdown ไม่ scale

### หลักการ: **Markdown = แหล่งความจริง / Database = index ที่ derive ได้**

| ระยะ | เก็บที่ไหน | เหตุผล |
|---|---|---|
| 🟢 MVP (M0–M5) | **Markdown ล้วน** | ง่าย, อ่านออกด้วยตา, version ด้วย git ได้, ไม่ต้อง setup DB |
| 🟡 v1.0+ | **Markdown + SQLite index** | SQLite เก็บ index (ค้นหาเร็ว) แต่ markdown ยังเป็น source |
| 🟡 v2.0+ multi-tenant | **PostgreSQL** (metadata) + Markdown/object store (content) | ตอน scale หลาย company ค่อยย้าย metadata เข้า Postgres |

### กฎกัน Markdown พัง (สำคัญสำหรับ MVP)

1. **Append-only เป็นหลัก** — เพิ่ม entry ใหม่ ไม่แก้ของเก่า (กัน corrupt)
2. **1 entry = 1 block มี ID + timestamp** — parse ง่าย, dedupe ได้
3. **File lock ตอนเขียน** — กัน concurrent write (ใช้ `filelock` library)
4. **ห้าม agent 2 ตัวเขียนไฟล์เดียวกันพร้อมกัน** — route ผ่าน MemoryManager เท่านั้น

**รูปแบบ entry มาตรฐาน:**

```markdown
<!-- id: obs-20260601-001 | ts: 2026-06-01T09:00:00Z | agent: analyst -->
BTC momentum +3% over 24h. Volume above 30-day avg.
Confidence: 0.7
<!-- /id: obs-20260601-001 -->
```

---

## §7. COST MODEL (Claude API — เดิมไม่คิดเลย)

ปัญหาเดิม: 5 agents × วนลูปทุกวัน × หลาย company = ค่า API พุ่ง

### กลยุทธ์คุมค่าใช้จ่าย

1. **Prompt Caching** — constitution + memory schema ไม่เปลี่ยนบ่อย → cache (ลดได้ ~90% ของ input token ส่วนนั้น)
2. **Model tiering** — งานง่ายใช้ Haiku, งานคิดหนักใช้ Sonnet, ตัดสินใจสำคัญใช้ Opus
3. **Budget guard ต่อ company** — `company.yaml` มี `max_daily_tokens` → เกินแล้วหยุด + alert
4. **Batch ภายใน cycle** — รวม context หลาย agent ใน call เดียวเมื่อทำได้
5. **Dry-run mode** — dev/test ใช้ mock LLM (ไม่เสียเงิน, เร็ว, deterministic)

### Budget config (เพิ่มใน company.yaml)

```yaml
budget:
  max_daily_tokens: 100000
  model_tier:
    routine: claude-haiku-4-5-20251001     # observe, summarize
    reasoning: claude-sonnet-4-6           # analysis, risk
    critical: claude-opus-4-8              # ceo decisions
  on_exceed: stop_and_alert                # stop_and_alert | downgrade | continue
```

> **MVP:** ใช้ mock LLM เป็น default → พัฒนาได้โดยไม่เสียเงิน ค่อยเสียบ API จริงตอนใกล้เสร็จ

---

## §8. SAFETY & LEGAL (Trading guardrails + Autonomy)

ปัญหาเดิม: AI execute trades ได้ แต่ไม่พูดถึงกฎหมาย/ความรับผิด/sandbox

### 8.1 Autonomy Gate (ทุก action ต้องผ่าน)

```
agent อยากทำ action
   ↓
classify risk: LOW / MEDIUM / HIGH
   ↓
LOW    → auto execute + log
MEDIUM → ขอ confirm (queue ไว้รออนุมัติ)
HIGH   → block จนกว่ามนุษย์อนุมัติ explicit
```

| Action | Risk | ค่า default |
|---|---|---|
| summarize, update memory, สร้าง observation | LOW | auto |
| create task, แก้ plan, propose trade | MEDIUM | confirm |
| ส่ง email, **execute live trade**, ใช้เงินจริง, ลบข้อมูล | HIGH | approval |

### 8.2 Trading-Specific Guardrails (บังคับ — non-negotiable)

1. **Default = paper trading เสมอ** — live ต้องตั้ง `execution_mode: live` explicit + ผ่าน HIGH approval ทุกครั้ง
2. **แยก paper/live เด็ดขาด** — คนละ config, คนละ credential, คนละ log
3. **Hard risk limits** (enforce ใน code ไม่ใช่แค่ prompt):
   - max 2–5% risk/trade
   - max 10% daily drawdown → **หยุดเทรดทันที**
   - ไม่มี revenge-trading logic
4. **DISCLAIMER บังคับ** — instance trading ทุกตัวมีไฟล์ `DISCLAIMER.md`:
   > ระบบนี้เป็นเครื่องมือ research/automation ไม่ใช่คำแนะนำการลงทุน
   > ผู้ใช้รับผิดชอบความเสี่ยงเอง / ต้องมีใบอนุญาตตามกฎหมายท้องถิ่นก่อนใช้เงินจริง
5. **Kill switch** — หยุดทุก agent ได้ทันทีด้วยคำสั่งเดียว

### 8.3 Constitution = Single Point of Failure → ป้องกัน

ปัญหาเดิม: constitution ผิด = agent พังหมด

- **Constitution ต้องผ่าน validation** ก่อนใช้ (schema check + sanity test)
- **Per-company constitution** — ไม่ share ข้าม company (กันพังพร้อมกันหลายเจ้า)
- **Version + rollback** — เก็บประวัติ ถ้าแก้แล้วพฤติกรรมเพี้ยน rollback ได้

---

## §9. TESTING STRATEGY (เดิมไม่มีเลย)

### ระดับการทดสอบ

| ระดับ | ทดสอบอะไร | เครื่องมือ |
|---|---|---|
| Unit | factory validation, memory read/write, risk limits | pytest |
| Integration | create → run → brief ครบ flow | pytest + tmp_path |
| Golden/Snapshot | output brief ตรงกับ expected | pytest snapshot |
| LLM mock | agent logic โดยไม่เรียก API จริง | fake LLM client |

### กฎ

1. **Memory + Factory + Risk limits ต้องมี test 100%** — เป็นส่วนที่พังแล้วอันตราย
2. **ทุก PR ต้องผ่าน test** ก่อน merge
3. **Mock LLM เป็น default ใน test** — deterministic, ไม่เสียเงิน, เร็ว
4. **Risk limit ต้องมี test ที่พิสูจน์ว่า block ได้จริง** (เช่น drawdown 11% → ต้องหยุด)

```
tests/
├── test_factory_create.py      # validation, atomic write, collision
├── test_memory.py              # append-only, lock, parse
├── test_agents.py              # agent loop ด้วย mock LLM
├── test_risk_limits.py         # ⚠️ critical: limits enforce ได้จริง
└── test_integration_run.py     # create → run → brief end-to-end
```

---

## §10. GLOSSARY (เคลียร์คำที่เดิมใช้ปนกัน)

| คำ | ความหมายทางการ |
|---|---|
| **Factory** | เครื่องจักรที่อ่าน template + input → generate company instance (§4) |
| **Template** | พิมพ์เขียว static ใน `templates/` (ไม่ใช่ instance) |
| **Instance / Company** | บริษัทที่ถูก generate ออกมาใน `companies/{id}/` (runtime object) |
| **Agent** | พนักงาน AI 1 ตัว มี role + responsibilities + memory scope |
| **Skill** | ความสามารถ reusable ที่ agent หลายตัวใช้ร่วมได้ |
| **Workflow** | ลำดับการส่งงานระหว่าง agents |
| **Constitution** | กฎ/ค่านิยม ควบคุมวิธีคิดของ agents ใน company นั้น (per-company) |
| **Memory** | ความรู้ของ company เก็บเป็น markdown (§6) |
| **Autonomy Gate** | ด่านตรวจ risk ก่อนทุก action (§8) |
| **Stage (M0–F4)** | ชื่อเรียก milestone ทางการ แทน phase/week ที่เคยปนกัน (§5) |

---

## §11. ก้าวต่อไป (เมื่อพร้อมลง code)

ลำดับ build ของ MVP:

```
M0 Foundation  → project structure + config loader + logging
M1 Memory      → MemoryManager (append-only, lock, parse)  + test
M2 Factory     → create() pipeline + 1 template (trading)   + test
M3 Task        → task_queue CRUD
M4 Agents      → base Agent + analyst + risk (mock LLM)     + test
M5 Brief       → brief generator → .md
→ run end-to-end → ✅ MVP สำเร็จ
```

**Tech stack สำหรับ MVP (เบาที่สุด):**
- Python 3.12
- `pyyaml` (config), `filelock` (memory lock), `pytest` (test)
- Mock LLM client (ยังไม่เสียบ API จริง)
- **ยังไม่ต้องมี:** FastAPI, PostgreSQL, React

---

## §12. REPOSITORY LAYOUT (โครงสร้าง repo จริงของ Factory — code-gen contract)

> ⚠️ อย่าสับสน: §4.3 คือ **instance ที่ generate ออกมา** (อยู่ใน `companies/`)
> ส่วน §12 นี้คือ **โค้ดของตัว factory เอง** ที่ AI ต้องเขียน

```
ai-company-factory/
├── pyproject.toml              # deps: pyyaml, filelock, pytest (+ jsonschema optional)
├── README.md                   # quickstart (สร้างทีหลัง)
├── .gitignore                  # ต้อง ignore: companies/, *.log, __pycache__/, .venv/
│
├── factory/                    # ◀── โค้ดหลักทั้งหมดอยู่ที่นี่ (importable package)
│   ├── __init__.py
│   ├── errors.py               # ValidationError, CollisionError, BudgetExceeded, RiskBlocked
│   ├── config.py               # paths, logging setup, global settings loader
│   ├── memory.py               # MemoryManager (append-only, filelock, parse)  [§13.1]
│   ├── templates.py            # Template: load + validate_inputs + render       [§13.2]
│   ├── create.py               # create() pipeline + CLI `python -m factory.create` [§13.3]
│   ├── run.py                  # run_cycle() + CLI `python -m factory.run`        [§13.4]
│   ├── brief.py                # generate_brief() → markdown                      [§13.5]
│   ├── autonomy.py             # classify() + AutonomyGate                        [§13.6]
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py             # LLMClient (Protocol) + LLMResponse               [§13.7]
│   │   └── mock.py             # MockLLMClient (deterministic, default)           [§15]
│   └── agents/
│       ├── __init__.py
│       ├── base.py             # Agent (ABC) + CycleContext + AgentResult         [§13.8]
│       ├── analyst.py          # AnalystAgent
│       └── risk.py             # RiskAgent (enforce hard risk limits in CODE)
│
├── templates/                  # ◀── STATIC พิมพ์เขียว (เช็คอินใน git)
│   └── trading/
│       ├── template.yaml        # metadata + inputs spec (§14.1)
│       ├── agents.yaml          # agent roster + placeholders (§14.2)
│       ├── workflow.yaml        # daily steps (§14.3)
│       ├── constitution.md      # กฎบริษัทประเภทนี้ (มี {{placeholder}})
│       └── memory_schema.yaml   # ไฟล์ memory ที่ต้องสร้าง (§14.4)
│
├── companies/                  # ◀── GENERATED instances (gitignored)
│   └── .gitkeep
│
└── tests/                      # ดู §9 + §16 (ระบุว่า test ไหนคุม module ไหน)
    ├── conftest.py             # fixtures: tmp_path company, MockLLMClient
    ├── test_memory.py
    ├── test_factory_create.py
    ├── test_agents.py
    ├── test_risk_limits.py      # ⚠️ critical
    └── test_integration_run.py
```

**กติกาโครงสร้าง:**
- `factory/` = code (static) · `templates/` = blueprint (static) · `companies/` = output (runtime, gitignored)
- ทุก module เป็น pure Python + stdlib + 3 deps; ห้าม import network/DB ใน MVP
- CLI entrypoints มีแค่ 2 ตัว: `factory.create` และ `factory.run` (ตรงกับ §3 acceptance criteria)

---

## §13. MODULE INTERFACES (ลายเซ็นที่ AI ต้องทำให้ตรง)

> สัญญาเหล่านี้คือ "ผิวสัมผัส" ที่ test ใน §9/§16 จะเรียก — ทำ signature ให้ตรงเป๊ะ
> ใช้ type hints, `pathlib.Path`, dataclasses; raise exception จาก `factory/errors.py`

### 13.1 `factory/memory.py`
```python
@dataclass(frozen=True)
class MemoryEntry:
    id: str            # เช่น "obs-20260601-001"
    ts: str            # ISO-8601 UTC
    agent: str
    kind: str          # obs | hyp | dec | task | trade | risk ...
    body: str

class MemoryManager:
    def __init__(self, company_dir: Path) -> None: ...
    def append(self, file: str, body: str, *, agent: str, kind: str) -> MemoryEntry:
        """Append-only. ห่อด้วย comment block + id + ts (§6). ใช้ FileLock ต่อไฟล์.
        คืน MemoryEntry ที่เพิ่ง append. ห้าม overwrite ของเดิม."""
    def read(self, file: str) -> str:                 # raw text
    def entries(self, file: str) -> list[MemoryEntry]: # parsed blocks (dedupe ด้วย id)
    def next_id(self, kind: str) -> str:               # "{kind}-{YYYYMMDD}-{NNN}"
```

### 13.2 `factory/templates.py`
```python
@dataclass
class Template:
    id: str
    root: Path
    meta: dict          # ทั้งไฟล์ template.yaml
    @classmethod
    def load(cls, template_id: str, *, templates_dir: Path) -> "Template": ...
    def validate_inputs(self, inputs: dict) -> dict:
        """ตรวจตาม meta['inputs'] (type/required/pattern/enum/min/default).
        ผิด → raise ValidationError(ระบุ field). ผ่าน → คืน dict ที่เติม default แล้ว."""
    def render(self, normalized_inputs: dict) -> dict[str, str]:
        """แทน {{placeholder}} ในไฟล์ template ทั้งหมด → {relative_path: rendered_text}."""
```

### 13.3 `factory/create.py`
```python
@dataclass
class CompanyInstance:
    name: str
    path: Path
    manifest: dict

def create(template_id: str, inputs: dict, *,
           templates_dir: Path, companies_dir: Path) -> CompanyInstance:
    """Pipeline ตาม §4.2:
    1) load template  2) validate_inputs  3) render
    4) collision check (companies/{name} มีอยู่ → CollisionError)
    5) atomic write (เขียน temp dir → move; กัน folder พังครึ่ง)
    6) init memory ตาม memory_schema.yaml (สร้าง .md เปล่า + header)
    7) write .manifest.json (template_id, version, created_at, inputs)
    คืน CompanyInstance"""

def main(argv: list[str] | None = None) -> int:
    """argparse: --template <id> --name <slug> [--risk-level low|medium|high] [--initial-capital N]"""
```

### 13.4 `factory/run.py`
```python
@dataclass
class CycleResult:
    company: str
    date: str
    agent_results: list["AgentResult"]
    brief_path: Path

def run_cycle(company_name: str, *, companies_dir: Path,
              llm: "LLMClient | None" = None, date: str | None = None) -> CycleResult:
    """โหลด instance → สร้าง agents จาก agents.yaml → วน workflow.yaml 1 รอบ
    → แต่ละ action ผ่าน AutonomyGate (§8) → เขียนผลลง memory → generate brief.
    llm=None → ใช้ MockLLMClient. date=None → ต้องรับมาจาก caller/CLI (อย่าเรียก now() ใน core)."""

def main(argv: list[str] | None = None) -> int:
    """argparse: --company <name> [--dry-run]  (output ตรงกับ §3 acceptance)"""
```

### 13.5 `factory/brief.py`
```python
def generate_brief(*, company: dict, cycle_result: CycleResult,
                   memory: MemoryManager, date: str) -> str:
    """คืน markdown brief: market/priorities, risks, blockers, decisions needed.
    caller เขียนลง companies/{name}/memory/briefings/{date}.md"""
```

### 13.6 `factory/autonomy.py`
```python
class Risk(enum.Enum): LOW = "low"; MEDIUM = "medium"; HIGH = "high"

@dataclass
class Action:
    kind: str          # "update_memory" | "create_task" | "propose_trade" | "execute_live_trade" ...
    payload: dict
    agent: str

@dataclass
class GateDecision:
    risk: Risk
    allowed: bool      # LOW=True(auto); MEDIUM=False(queue confirm); HIGH=False(block)
    reason: str

def classify(action: Action) -> Risk: ...        # ตามตาราง §8.1
class AutonomyGate:
    def __init__(self, mode: str = "default") -> None: ...
    def evaluate(self, action: Action) -> GateDecision: ...
```

### 13.7 `factory/llm/base.py`
```python
@dataclass
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int

class LLMClient(typing.Protocol):
    def complete(self, *, system: str, messages: list[dict],
                 tier: str, max_tokens: int = 1024) -> LLMResponse: ...
    # tier ∈ {routine, reasoning, critical} → map model ตาม §7
```

### 13.8 `factory/agents/base.py`
```python
@dataclass
class CycleContext:
    company: dict
    memory: MemoryManager
    gate: AutonomyGate
    llm: LLMClient
    date: str

@dataclass
class AgentResult:
    agent: str
    summary: str               # บรรทัดที่โชว์ตอน run (เช่น "generated 2 observations")
    actions: list[GateDecision]

class Agent(abc.ABC):
    name: str
    model_tier: str            # routine | reasoning | critical
    @abc.abstractmethod
    def run(self, ctx: CycleContext) -> AgentResult: ...
    def propose(self, ctx: CycleContext, action: Action) -> GateDecision:
        """ทุก action ต้องผ่าน ctx.gate.evaluate ก่อน execute (ไม่มีทางลัด)"""
```

---

## §14. CANONICAL SCHEMAS (ไฟล์ทุกชนิด — ใช้ generate/validate ได้ตรง)

### 14.1 `templates/{type}/template.yaml`
```yaml
id: trading                      # ต้องตรงกับชื่อ folder
name: "AI Trading Company"
version: 1.0
description: "Autonomous trading & investment company"
inputs:                          # validate_inputs() อ่านจากตรงนี้
  name:            { type: string, required: true, pattern: "^[a-z0-9_]{3,32}$" }
  risk_level:      { type: enum, values: [low, medium, high], default: low }
  initial_capital: { type: number, min: 0, default: 0 }   # 0 = paper only
defaults:
  execution_mode: paper          # paper | live (live ต้อง explicit + HIGH approval §8)
```

### 14.2 `templates/{type}/agents.yaml`  (รองรับ {{placeholder}})
```yaml
agents:
  - id: ceo
    role: "Strategic decision maker"
    model_tier: critical         # → claude-opus-4-8
    responsibilities: ["set market stance", "approve high-risk trades"]
  - id: analyst
    role: "Market intelligence"
    model_tier: reasoning        # → claude-sonnet-4-6
    responsibilities: ["detect trends", "generate trade ideas"]
  - id: risk
    role: "Capital protection"
    model_tier: routine
    responsibilities: ["risk score per trade", "enforce stop-loss", "block unsafe trades"]
    hard_limits: { max_risk_per_trade_pct: 5, max_daily_drawdown_pct: 10 }
```

### 14.3 `templates/{type}/workflow.yaml`
```yaml
cycle: daily
steps:                           # run_cycle() เดินตามลำดับนี้
  - { id: market_scan,   agent: analyst, output: observations }
  - { id: strategy,      agent: ceo,     output: decisions }
  - { id: risk_check,    agent: risk,    output: risk_log }
  - { id: brief,         agent: null,    output: briefings }   # null = brief generator
```

### 14.4 `templates/{type}/memory_schema.yaml`
```yaml
files:                           # create() สร้างไฟล์เปล่าตามนี้ + header
  - { name: observations.md, header: "# Observations" }
  - { name: hypotheses.md,   header: "# Hypotheses" }
  - { name: decisions.md,    header: "# Decisions" }
  - { name: task_queue.md,   header: "# Task Queue" }
  - { name: risk_log.md,     header: "# Risk Log" }
dirs:
  - briefings                    # โฟลเดอร์ brief รายวัน
```

### 14.5 `companies/{name}/.manifest.json`  (provenance — เขียนโดย create())
```json
{
  "name": "myfund",
  "template_id": "trading",
  "template_version": 1.0,
  "created_at": "2026-06-01T09:00:00Z",
  "inputs": { "name": "myfund", "risk_level": "low", "initial_capital": 0 }
}
```

### 14.6 `companies/{name}/company.yaml`  (rendered profile + budget §7)
```yaml
name: myfund
type: trading
risk_level: low
execution_mode: paper
budget:
  max_daily_tokens: 100000
  model_tier: { routine: claude-haiku-4-5-20251001, reasoning: claude-sonnet-4-6, critical: claude-opus-4-8 }
  on_exceed: stop_and_alert      # stop_and_alert | downgrade | continue
```

### 14.7 Memory entry format (บังคับ — parser ใน §13.1 ต้องอ่านได้)
```markdown
<!-- id: obs-20260601-001 | ts: 2026-06-01T09:00:00Z | agent: analyst -->
BTC momentum +3% over 24h. Volume above 30-day avg. Confidence: 0.7
<!-- /id: obs-20260601-001 -->
```

### 14.8 `companies/{name}/DISCLAIMER.md`  (บังคับสำหรับ template ที่เกี่ยวกับเงิน §8.2)
> ระบบนี้เป็นเครื่องมือ research/automation ไม่ใช่คำแนะนำการลงทุน
> ผู้ใช้รับผิดชอบความเสี่ยงเอง / ต้องมีใบอนุญาตตามกฎหมายท้องถิ่นก่อนใช้เงินจริง

---

## §15. MOCK LLM CONTRACT (default สำหรับ dev + test)

`MockLLMClient` ต้อง implement `LLMClient` (§13.7) และ:

1. **ไม่มี network call** — ทำงาน offline 100%
2. **Deterministic** — input เดิม → output เดิมเสมอ (เพื่อ golden/snapshot test §9)
3. **Scriptable** — รับ `scripted: dict[str, str]` map จาก `agent_id`/`tier` → ข้อความตอบ; ไม่มี key → คืน default ที่อ่านรู้เรื่อง เช่น `"[mock:{agent}] ok"`
4. **Token accounting** — `input_tokens ≈ len(system+messages)//4`, `output_tokens ≈ len(text)//4` (พอให้ budget guard §7 ทดสอบได้)
5. **ไม่ throw** เว้นแต่ถูกสั่งให้ simulate error (สำหรับ test error path)

```python
class MockLLMClient:
    def __init__(self, scripted: dict[str, str] | None = None) -> None: ...
    def complete(self, *, system, messages, tier, max_tokens=1024) -> LLMResponse: ...
```
> การเสียบ Claude API จริง = สร้าง `factory/llm/anthropic.py` ทีหลัง (ใช้ prompt caching + model tier §7) โดยไม่แตะ interface

---

## §16. BUILD ORDER (รายไฟล์ + Definition of Done — AI เดินตามนี้)

> สร้างทีละ stage; **stage ถัดไปเริ่มได้ก็ต่อเมื่อ test ของ stage ก่อนหน้าเขียว**
> ทุก stage = code + test + รันผ่านบน Windows

| Stage | สร้างไฟล์ | DoD (เสร็จเมื่อ) | Test ที่คุม |
|---|---|---|---|
| **M0** Foundation | `pyproject.toml`, `factory/__init__.py`, `errors.py`, `config.py`, `.gitignore`, `conftest.py` | `python -c "import factory"` ผ่าน; logging ใช้ได้ | (smoke) |
| **M1** Memory | `factory/memory.py` | append-only + FileLock + parse + next_id ทำงาน; ของเดิมไม่ถูกทับ | `test_memory.py` |
| **M2** Factory | `templates/trading/*`, `factory/templates.py`, `factory/create.py` | `python -m factory.create --template trading --name myfund` สร้าง folder ครบตาม §4.3; input ผิด → ValidationError, ไม่สร้าง folder; ซ้ำ → CollisionError | `test_factory_create.py` |
| **M3** Task | (ต่อยอด `memory.py`: task_queue CRUD helpers) | create/update/close task ลง `task_queue.md` ได้ append-only | `test_memory.py` (task cases) |
| **M4** Agents | `factory/llm/base.py`, `factory/llm/mock.py`, `factory/autonomy.py`, `factory/agents/base.py`, `analyst.py`, `risk.py` | analyst + risk วนลูปด้วย MockLLM; ทุก action ผ่าน AutonomyGate; **risk limit block ได้จริง** (drawdown 11% → หยุด) | `test_agents.py`, `test_risk_limits.py` |
| **M5** Brief + Run | `factory/brief.py`, `factory/run.py` | `python -m factory.run --company myfund` พ่น output ตาม §3 + เซฟ `briefings/{date}.md` | `test_integration_run.py` |
| ✅ **MVP DONE** | — | create→run→brief end-to-end เขียวทั้งหมด บน Windows | ทั้ง suite ผ่าน |

**กฎระหว่าง build:**
1. อย่าเรียกเวลา/สุ่มใน core logic — รับ `date`/seed จากภายนอก (เพื่อ deterministic test)
2. Mock LLM เป็น default ทุก test (ไม่เสียเงิน, เร็ว, deterministic)
3. `test_risk_limits.py` ต้องพิสูจน์ว่า limit **block** ได้จริง ไม่ใช่แค่ log
4. ห้ามเขียนนอก `companies/{name}/` และต้อง atomic (temp→move)
5. หยุดที่ MVP DONE — อย่าเผลอสร้าง FastAPI/React/PostgreSQL/Marketplace (🟡/🔴 ใน §2, §5)

---

---

## §17. BUILD STATUS (อัพเดทโดย AI หลังทุก session)

> 🤖 ถึง AI ที่มาต่อ: อ่าน PROGRESS.md ก่อนเสมอ — มีสถานะล่าสุด + next action

| Stage | สถานะ | หมายเหตุ |
|---|---|---|
| M0 Foundation | ✅ Code เขียนครบ | pyproject.toml, errors.py, config.py, __init__.py, .gitignore, conftest.py |
| M1 Memory | ✅ Code เขียนครบ | factory/memory.py + tests/test_memory.py |
| M2 Factory | ✅ Code เขียนครบ | templates/trading/*, factory/templates.py, factory/create.py + tests |
| M3 Task | ✅ Code เขียนครบ | built into MemoryManager (create_task, update_task, open_tasks) |
| M4 Agents | ✅ Code เขียนครบ | factory/llm/*, factory/autonomy.py, factory/agents/* + tests |
| M5 Brief+Run | ✅ Code เขียนครบ | factory/brief.py, factory/run.py + test_integration_run.py |
| **pytest ผ่าน** | ✅ **71/71 passed** | Python 3.12.10 @ `%LOCALAPPDATA%\Programs\Python\Python312\` |

**MVP สำเร็จ** — CLI demo ผ่าน acceptance criteria §3 ครบ (2026-06-01)

END OF MASTER SPEC
