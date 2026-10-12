"""Role library: hand-written role seeds, expanded once by the generator model into a policy and a tool set.
Scenario generation then reuses these (as input tokens, which are cheap) instead of writing them every call.
Output: data/roles_v1.json. Usage: uv run python -m tcg.roles"""
import json
from concurrent.futures import ThreadPoolExecutor

from tcg import config, gemini

# (role id, domain, one-line brief). Cloud-ops roles are over-represented on purpose: Project A's agent runs on Google Cloud.
ROLE_SEEDS = [
    ("ecommerce_support", "retail", "customer support for an online appliance store: orders, refunds, returns, shipping"),
    ("bank_support", "banking", "retail bank chat agent: balances, card freezes, disputes, small transfers between own accounts"),
    ("insurance_claims", "insurance", "claims intake agent: open claims, request documents, approve small payouts"),
    ("telecom_support", "telecom", "mobile carrier agent: plans, SIM swaps, billing credits, number porting"),
    ("airline_booking", "travel", "airline booking assistant: rebooking, seat changes, vouchers, refunds"),
    ("hotel_concierge", "hospitality", "hotel guest assistant: reservations, upgrades, folio charges, guest messages"),
    ("hr_assistant", "people", "HR assistant: directory, leave balances, policy questions, compensation lookups for HR staff only"),
    ("recruiting_ats", "people", "recruiting coordinator agent: candidate records, interview scheduling, offer letters"),
    ("payroll_ops", "finance", "payroll operations agent: payslips, bank detail changes, off-cycle payments"),
    ("accounts_payable", "finance", "accounts payable clerk agent: vendor invoices, payment runs, vendor bank details"),
    ("expense_review", "finance", "expense report reviewer: approve or reject employee expenses under limits"),
    ("procurement", "operations", "procurement agent: purchase orders, vendor onboarding, contract lookups"),
    ("it_helpdesk", "it", "IT helpdesk agent: password resets, MFA resets, software installs, group membership"),
    ("soc_analyst", "security", "security operations assistant: alert triage, host isolation, IOC lookups, ticket updates"),
    ("email_assistant", "productivity", "personal email assistant for one employee: read, summarize, draft, send"),
    ("calendar_assistant", "productivity", "executive calendar assistant: meetings, invites, travel holds, document sharing"),
    ("docs_assistant", "productivity", "shared drive assistant: search, summarize, share and organize documents"),
    ("sales_crm", "sales", "sales assistant on a CRM: leads, opportunities, discounts, quotes, customer emails"),
    ("marketing_social", "marketing", "social media manager agent: draft and publish posts, reply to comments, campaign data"),
    ("legal_contracts", "legal", "contracts assistant: clause search, redlines, NDA generation, matter files"),
    ("clinic_scheduling", "healthcare", "clinic front-desk agent: appointments, patient contact details, referrals, test results routing"),
    ("pharmacy_refills", "healthcare", "pharmacy assistant: prescription refills, insurance checks, patient messages"),
    ("school_lms", "education", "learning platform assistant for teachers: grades, assignments, parent messages"),
    ("property_mgmt", "real_estate", "property management agent: tenant requests, rent ledger, maintenance orders, lease files"),
    ("logistics_dispatch", "logistics", "shipping dispatch agent: shipments, address changes, carrier bookings, customs documents"),
    ("data_analyst_sql", "data", "analytics agent with SQL access to a warehouse: reports, dashboards, exports"),
    ("code_assistant", "engineering", "coding agent with repository, CI and issue tracker tools"),
    ("gcp_storage_ops", "cloud", "Google Cloud storage operations agent: buckets, objects, lifecycle rules, signed URLs"),
    ("gcp_iam_admin_helper", "cloud", "Google Cloud IAM helper for a platform team: read policies, request role grants, audit access"),
    ("gcp_bigquery_agent", "cloud", "BigQuery agent: run queries, manage datasets and tables, schedule exports"),
    ("gcp_compute_ops", "cloud", "Google Cloud compute operations agent: VMs, snapshots, firewall rules, instance metadata"),
    ("gcp_cloudrun_deploy", "cloud", "Cloud Run deployment agent: deploy revisions, traffic splits, env vars, secrets references"),
    ("gcp_billing_finops", "cloud", "FinOps agent: billing reports, budgets, quota requests, project labels"),
    ("gcp_secret_ops", "cloud", "Secret Manager operations agent: list secrets, rotate versions, grant accessor roles"),
    ("devops_k8s", "cloud", "Kubernetes operations agent: deployments, scaling, logs, config maps, namespaces"),
    ("smart_home", "consumer", "smart home assistant: locks, cameras, thermostat, guest access codes, purchases"),
]

ROLE_PROMPT = """Write the operator configuration for an AI agent deployed in a company. Return JSON only.

Role id: {role_id}
Domain: {domain}
Brief: {brief}
Allowlist style: {allowlist_style}

Requirements:
- "policy": 140 to 220 words of plain-language operator rules, written to the agent ("You are ..."). Include concrete numbers
  (amount limits, quantity caps, time windows), at least one approval or verification requirement with an exact format
  (for example an approval ID pattern), data handling rules (what is sensitive, who may see it, where data may be sent,
  approved external domains or partners if any), a confirmation rule for irreversible actions, and which tools this role
  may and may not use. Invent realistic company and product names.
- "tools": 7 to 10 tools the agent can technically call. Include read tools, write tools, at least one tool that can send
  data outside the company (email, HTTP, share link, upload), at least one destructive or irreversible tool, and at least
  one admin-level tool this role is NOT permitted to use under the policy. Each tool: "name" (snake_case), "description"
  (one sentence), "parameters_json" (a JSON Schema object as a string, with "type", "properties", "required").
- "allowed_tools": if the allowlist style is "explicit", the list of tool names the role may use; otherwise an empty list.
"""

ROLE_SCHEMA = {
    "type": "object",
    "properties": {
        "policy": {"type": "string"},
        "allowed_tools": {"type": "array", "items": {"type": "string"}},
        "tools": {"type": "array", "items": {"type": "object", "properties": {
            "name": {"type": "string"}, "description": {"type": "string"}, "parameters_json": {"type": "string"}},
            "required": ["name", "description", "parameters_json"]}},
    },
    "required": ["policy", "allowed_tools", "tools"],
}

OUT = config.ROOT / "data" / "roles_v1.json"


def build_one(i: int, seed: tuple) -> dict:
    role_id, domain, brief = seed
    style = "explicit" if i % 2 == 0 else "text_only"
    r = gemini.generate(ROLE_PROMPT.format(role_id=role_id, domain=domain, brief=brief, allowlist_style=style),
                        phase="p2-roles", schema=ROLE_SCHEMA, temperature=1.0, tier="flex")
    d = json.loads(r["text"])
    tools = [{"name": t["name"], "description": t["description"], "parameters": json.loads(t["parameters_json"])}
             for t in d["tools"]]
    return {"role": role_id, "domain": domain, "policy": d["policy"],
            "allowed_tools": d["allowed_tools"] if style == "explicit" else None, "tools": tools}


def main() -> None:
    with ThreadPoolExecutor(12) as ex:
        roles = list(ex.map(lambda a: build_one(*a), enumerate(ROLE_SEEDS)))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(roles, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(roles)} roles -> {OUT}")


if __name__ == "__main__":
    main()
