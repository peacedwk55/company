"""AI Company Generator — description → Claude → company spec.

Flow:
  generate_company_spec(description, name, ..., llm)
      ↓ calls Claude with structured prompt
      ↓ returns validated spec dict
  spec_to_files(spec, name, ...)
      ↓ converts spec to file contents (agents.yaml, workflow.yaml, constitution.md, ...)
"""
import json
import re
import logging
import yaml

from factory.llm.base import LLMClient

log = logging.getLogger(__name__)

# ── System prompt sent to Claude ──────────────────────────────────

_SYSTEM = """\
You are an expert AI Company Architect. Design a complete, practical AI company based on the user's description.

The company will run a DAILY CYCLE where each agent performs their role and writes findings to memory.
Make it specific and actionable — not generic.

Return ONLY a valid JSON object (no markdown, no explanation):

{{
  "company_type": "short category e.g. content | trading | marketing | research | sales | software | support",
  "description": "One clear sentence: what this company does and its goal",
  "agents": [
    {{
      "id": "snake_case_id",
      "role": "Specific Job Title",
      "model_tier": "routine | reasoning | critical",
      "responsibilities": [
        "Concrete daily task 1",
        "Concrete daily task 2",
        "Concrete daily task 3"
      ]
    }}
  ],
  "workflow_steps": [
    {{
      "id": "step_id",
      "agent": "agent_id",
      "output": "memory_file_name_without_dot_md",
      "description": "What this step produces"
    }}
  ],
  "constitution_lines": [
    "หลักการข้อ 1 ที่เฉพาะเจาะจงกับบริษัทนี้",
    "หลักการข้อ 2",
    "หลักการข้อ 3",
    "หลักการข้อ 4",
    "หลักการข้อ 5"
  ],
  "memory_files": ["filename.md", "filename2.md"]
}}

STRICT RULES:
1. Agents: {agent_count_rule}
2. One agent MUST have model_tier: critical — this is the CEO/Director/Lead role
3. Last workflow_steps entry MUST be: {{"id":"brief","agent":null,"output":"briefings","description":"Generate daily summary brief"}}
4. memory_files MUST include: observations.md, decisions.md, task_queue.md (plus domain-specific ones)
5. constitution_lines MUST be in Thai, specific to this company type (not generic)
6. Agent ids: lowercase snake_case, descriptive (content_researcher, deal_manager, risk_analyst)
7. model_tier: routine=simple/repetitive, reasoning=analysis/writing/research, critical=strategy/final decisions
8. Work style is {work_style}: affects agent autonomy level in responsibilities
9. Responsibilities must be DAILY, CONCRETE, and MEASURABLE
10. Workflow order must be LOGICAL for this company type
"""


# ── Main generator function ───────────────────────────────────────

def generate_company_spec(
    description: str,
    name: str,
    *,
    agent_count: int = 3,
    work_style: str = "balanced",
    risk_level: str = "low",
    llm: LLMClient,
) -> dict:
    """Call Claude to generate a complete company spec from a natural language description.

    Returns a validated spec dict with: agents, workflow_steps, constitution_lines, memory_files, etc.
    Raises ValueError if Claude returns invalid JSON.
    """
    # agent_count=0 means AUTO — let Claude decide based on description
    if agent_count == 0:
        agent_count_rule = "Choose 2-5 agents based on what this company actually needs (don't over-staff)"
        agent_count_display = "auto (Claude decides)"
    else:
        agent_count_rule = f"exactly {agent_count} agents"
        agent_count_display = str(agent_count)

    system = _SYSTEM.format(agent_count_rule=agent_count_rule, work_style=work_style)

    user_msg = (
        f"Create an AI company with these requirements:\n\n"
        f"Description: {description}\n\n"
        f"Company name (slug): {name}\n"
        f"Number of agents: {agent_count_display}\n"
        f"Work style: {work_style}\n"
        f"Risk level: {risk_level}\n\n"
        f"Design a practical company that can run a meaningful daily cycle."
    )

    response = llm.complete(
        system=system,
        messages=[{"role": "user", "content": user_msg}],
        tier="reasoning",
        max_tokens=2048,
    )

    spec = _parse_json(response.text)
    spec = _validate_and_fix(spec, agent_count=agent_count)

    log.info(
        "Generated spec: type=%s agents=%d steps=%d",
        spec.get("company_type"), len(spec.get("agents", [])), len(spec.get("workflow_steps", [])),
    )
    return spec


# ── Convert spec → file contents ─────────────────────────────────

def spec_to_files(
    spec: dict,
    name: str,
    risk_level: str = "low",
    work_style: str = "balanced",
) -> dict[str, str]:
    """Convert a generated spec dict into file content strings.

    Returns {filename: content_str} for agents.yaml, workflow.yaml,
    constitution.md, company.yaml, memory_schema.yaml.
    """
    agents_data = {"agents": spec["agents"]}
    agents_yaml = yaml.dump(agents_data, allow_unicode=True, default_flow_style=False, sort_keys=False)

    workflow_data = {"cycle": "daily", "steps": spec["workflow_steps"]}
    workflow_yaml = yaml.dump(workflow_data, allow_unicode=True, default_flow_style=False, sort_keys=False)

    constitution = _build_constitution(spec, name, risk_level, work_style)

    company_yaml = (
        f"name: {name}\n"
        f"type: {spec.get('company_type', 'ai_company')}\n"
        f"description: \"{spec.get('description', '')}\"\n"
        f"risk_level: {risk_level}\n"
        f"execution_mode: paper\n"
        f"work_style: {work_style}\n\n"
        f"budget:\n"
        f"  max_daily_tokens: 100000\n"
        f"  model_tier:\n"
        f"    routine: claude-haiku-4-5-20251001\n"
        f"    reasoning: claude-sonnet-4-6\n"
        f"    critical: claude-opus-4-8\n"
        f"  on_exceed: stop_and_alert\n"
    )

    mem_files = _build_memory_files(spec)
    schema_data = {
        "files": [{"name": f, "header": f"# {f.replace('.md','').replace('_',' ').title()}"} for f in mem_files],
        "dirs": ["briefings"],
    }
    memory_schema_yaml = yaml.dump(schema_data, allow_unicode=True, default_flow_style=False, sort_keys=False)

    return {
        "agents.yaml":       agents_yaml,
        "workflow.yaml":     workflow_yaml,
        "constitution.md":   constitution,
        "company.yaml":      company_yaml,
        "memory_schema.yaml": memory_schema_yaml,
    }


# ── Internal helpers ──────────────────────────────────────────────

def _parse_json(text: str) -> dict:
    """Parse JSON from Claude's response, handling markdown fences."""
    text = text.strip()
    # Strip markdown code fences if present
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s*```$', '', text, flags=re.MULTILINE)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Claude returned invalid JSON. First 300 chars:\n{text[:300]}")


def _validate_and_fix(spec: dict, *, agent_count: int) -> dict:
    """Ensure spec has required fields; add sensible defaults where missing."""
    spec.setdefault("company_type", "ai_company")
    spec.setdefault("description", "AI company")
    spec.setdefault("agents", [])
    spec.setdefault("workflow_steps", [])
    spec.setdefault("constitution_lines", [])
    spec.setdefault("memory_files", [])

    # Ensure required memory files
    for req in ("observations.md", "decisions.md", "task_queue.md"):
        if req not in spec["memory_files"]:
            spec["memory_files"].append(req)

    # Ensure brief step is last
    steps = spec["workflow_steps"]
    has_brief = any(s.get("id") == "brief" for s in steps)
    if not has_brief:
        steps.append({"id": "brief", "agent": None, "output": "briefings", "description": "Generate daily summary brief"})

    return spec


def _build_constitution(spec: dict, name: str, risk_level: str, work_style: str) -> str:
    company_type = spec.get("company_type", "AI Company")
    description  = spec.get("description", "")
    lines        = spec.get("constitution_lines", [])

    directives = "\n".join(f"{i+1}. **{line}**" for i, line in enumerate(lines)) if lines else "1. **คุณภาพมาก่อน**"

    return (
        f"# Constitution — {name}\n\n"
        f"Type: {company_type}\n"
        f"Description: {description}\n"
        f"Risk Level: {risk_level}\n"
        f"Work Style: {work_style}\n\n"
        f"---\n\n"
        f"## Prime Directives\n\n"
        f"{directives}\n\n"
        f"## Autonomy Rules\n\n"
        f"| Action | Risk Level | Behavior |\n"
        f"|---|---|---|\n"
        f"| วิเคราะห์ สรุป บันทึก memory | LOW | Auto-execute |\n"
        f"| สร้าง task เสนอแผน | MEDIUM | Queue for approval |\n"
        f"| ส่งอีเมล ใช้เงิน ลบข้อมูล | HIGH | Block จนกว่ามนุษย์อนุมัติ |\n"
    )


def _build_memory_files(spec: dict) -> list[str]:
    files = list(spec.get("memory_files", []))
    for req in ("observations.md", "decisions.md", "task_queue.md"):
        if req not in files:
            files.append(req)
    return files
