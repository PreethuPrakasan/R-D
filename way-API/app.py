"""
Car Service Decision AI (Stateless, Single File)

- POST /process (JSON only)
- HTTP Basic Auth
- Events supported: "sms-received", "invoice-summary", "service-calculation", "service-notes"
- Guardrails: Safety/legal blockers; PII redaction
- Stateless: no DB, no side effects; returns only JSON decisions with actions
- Uses OpenAI Chat Completions (one call) to decide actions

Quick start:
  pip install fastapi uvicorn httpx python-dotenv pydantic
  export OPENAI_API_KEY="sk-..."                  # required
  export OPENAI_MODEL="gpt-4o-mini"              # optional
  export BASIC_AUTH_USERNAME="admin"             # optional (default: admin)
  export BASIC_AUTH_PASSWORD="secret"            # optional (default: secret)
  uvicorn app:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import json
import os
import re
import secrets
import time
import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field, validator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# -------------------------
# Environment / Constants
# -------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.error("❌ OPENAI_API_KEY environment variable is required.")
    raise RuntimeError("OPENAI_API_KEY environment variable is required.")

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
HTTP_TIMEOUT = 30.0

BASIC_USER = os.getenv("BASIC_AUTH_USERNAME", "admin")
BASIC_PASS = os.getenv("BASIC_AUTH_PASSWORD", "secret")

# Log startup configuration
logger.info("🚀 Car Service Decision AI starting up...")
logger.info(f"🤖 OpenAI Model: {OPENAI_MODEL}")
logger.info(f"🔑 OpenAI API Key: {'*' * 20}{OPENAI_API_KEY[-4:] if len(OPENAI_API_KEY) > 4 else '****'}")
logger.info(f"👤 Basic Auth User: {BASIC_USER}")
logger.info(f"⏱️ HTTP Timeout: {HTTP_TIMEOUT} seconds")
logger.info(f"🌐 OpenAI URL: {OPENAI_CHAT_URL}")

# Guardrails
ALLOWED_EVENTS = {"sms-received", "invoice-summary", "service-calculation", "service-notes"}

# Risky/illegal terms (blocked for safety)
RISKY_TERMS = [
    "bypass immobilizer", "disable security", "tamper odometer", "airbag disable",
    "emissions defeat", "vin forgery", "steering lock bypass"
]
# PII keys to redact (values replaced with "REDACTED")
PII_KEYS = {
    "name", "fullName", "firstName", "lastName", "customer_name", "email", "phone",
    "phone2", "address", "license_number", "licenseNumber", "vin", "vin_number",
    "plate", "licensePlateNumber"
}

# History handling
HISTORY_MAX = 5  # last N exchanges
HISTORY_WINDOW_DAYS = 14  # doc only (caller provides already-trimmed list)


# -------------------------
# App / Auth
# -------------------------
app = FastAPI(
    title="Car Service Decision AI",
    version="1.0.0",
    description="Stateless AI service for car service center events (POST-only).",
)
security = HTTPBasic()


def require_basic(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    logger.info(f"🔐 Authentication attempt for user: {credentials.username}")
    u_ok = secrets.compare_digest(credentials.username, BASIC_USER)
    p_ok = secrets.compare_digest(credentials.password, BASIC_PASS)
    if not (u_ok and p_ok):
        logger.warning(f"❌ Authentication failed for user: {credentials.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": 'Basic realm="secure-area"'},
        )
    logger.info(f"✅ Authentication successful for user: {credentials.username}")
    return credentials.username


# -------------------------
# Utilities: scanning/redaction
# -------------------------
def _lower_strs_in(value: Any) -> List[str]:
    out: List[str] = []
    if isinstance(value, str):
        out.append(value.lower())
    elif isinstance(value, (list, tuple)):
        for item in value:
            out.extend(_lower_strs_in(item))
    elif isinstance(value, dict):
        for k, v in value.items():
            out.extend(_lower_strs_in(k))
            out.extend(_lower_strs_in(v))
    return out


def contains_any(term_list: List[str], payload: Any) -> bool:
    lowered = _lower_strs_in(payload)
    for s in lowered:
        for t in term_list:
            if t in s:
                return True
    return False


def deep_copy(obj: Any) -> Any:
    try:
        return json.loads(json.dumps(obj))
    except Exception:
        # Fallback shallow copy
        if isinstance(obj, dict):
            return {k: deep_copy(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [deep_copy(x) for x in obj]
        return obj


def redact_pii(obj: Any) -> Any:
    if isinstance(obj, dict):
        new = {}
        for k, v in obj.items():
            if k in PII_KEYS:
                new[k] = "REDACTED"
            else:
                new[k] = redact_pii(v)
        return new
    elif isinstance(obj, list):
        return [redact_pii(x) for x in obj]
    else:
        return obj


def truncate_text(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    # truncate to last period before max_len if present
    cut = text.rfind(".", 0, max_len)
    if cut == -1:
        cut = max_len
    return text[:cut].rstrip() + "…"


# -------------------------
# Utilities: summarizers
# -------------------------
def summarize_history_for_prompt(sms_list: List[Dict[str, Any]], max_items: int = HISTORY_MAX) -> str:
    """
    Turn raw sms history into intent-safe, non-verbatim bullets.
    We DO NOT echo full message text; we describe it minimally.
    """
    lines: List[str] = []
    for i, sms in enumerate(sms_list[:max_items]):
        frm = str(sms.get("from") or sms.get("sender") or sms.get("direction") or "unknown")
        ch = "sms"
        ts = str(sms.get("ts") or sms.get("timestamp") or sms.get("created_at") or "")
        # Avoid echoing full text; provide a short description by length & simple keywords
        raw_text = str(sms.get("text") or sms.get("body") or "")
        kw_hint = []
        lt = raw_text.lower()
        for kw in ("on the way", "on my way", "coming", "late", "arrived", "ready", "question", "approve", "decline", "status", "pick up", "pickup"):
            if kw in lt:
                kw_hint.append(kw)
        hint = ", ".join(sorted(set(kw_hint))) if kw_hint else f"{min(10, len(raw_text))} chars"
        lines.append(f"- [{i}] from={frm} ts={ts} hint={hint}")
    return "\n".join(lines) if lines else "- (no recent messages)"


def summarize_vehicle_service(ro_payload: Dict[str, Any]) -> str:
    vehicle = ro_payload.get("vehicle", {}) or {}
    ro = ro_payload.get("repairOrder", {}) or {}
    make = vehicle.get("make")
    model = vehicle.get("model")
    year = vehicle.get("year")
    vin = "REDACTED" if vehicle.get("vin") else None
    status = ro.get("status")
    notes = ro.get("shopNotes") or ro.get("notes")
    customer_notes = ro.get("customerNotes")
    parts_examples = []
    services = ro.get("services") or []
    
    # Enhanced service details for service-notes event
    service_details = []
    for s in services[:5]:  # Include more services
        nm = s.get("name") or s.get("type")
        desc = s.get("description", "")
        concern = s.get("concern", "")
        service_status = s.get("status", "")
        
        if nm:
            parts_examples.append(str(nm))
            
            # Add detailed service information
            if desc or concern:
                detail_parts = [nm]
                if desc:
                    detail_parts.append(f"Description: {desc}")
                if concern:
                    detail_parts.append(f"Concern: {concern}")
                if service_status:
                    detail_parts.append(f"Status: {service_status}")
                service_details.append(" - ".join(detail_parts))
        
        # lineItems names (no amounts)
        for li in (s.get("lineItems") or [])[:2]:
            li_nm = li.get("name") or li.get("type")
            if li_nm:
                parts_examples.append(str(li_nm))
    
    # Add service history if available
    service_history = ro_payload.get("serviceHistory", [])
    history_summary = []
    if service_history:
        history_summary.append("SERVICE_HISTORY:")
        for hist in service_history[:5]:  # Last 5 services
            date = hist.get("date", "")
            mileage = hist.get("mileage", "")
            ro_num = hist.get("repairOrderNumber", "")
            hist_services = hist.get("services", [])
            service_names = [s.get("name", "") for s in hist_services[:2]]
            if date and mileage:
                history_summary.append(f"- RO#{ro_num}: {date[:10]} @ {mileage}mi - {', '.join(service_names)}")
    
    basics = []
    if make or model or year:
        basics.append(f"VEHICLE: {year or ''} {make or ''} {model or ''}".strip())
    if vin:
        basics.append("VIN: REDACTED")
    if status:
        basics.append(f"RO_STATUS: {status}")
    if parts_examples:
        basics.append("WORK_ITEMS: " + ", ".join(parts_examples[:5]))
    if notes:
        basics.append("NOTES_PRESENT: yes")
    if customer_notes:
        basics.append(f"CUSTOMER_CONCERN: {customer_notes}")
    
    # Add detailed service information
    if service_details:
        basics.append("SERVICE_DETAILS:")
        basics.extend(service_details)
    
    # Combine basics and history
    result = "\n".join(basics) if basics else "(no vehicle/RO summary)"
    if history_summary:
        result += "\n" + "\n".join(history_summary)
    
    return result


def bulletize_context(customer: Dict[str, Any],
                      communications: Dict[str, Any],
                      current_ro: Dict[str, Any]) -> str:
    sms_list = list(communications.get("sms") or [])
    history_summary = summarize_history_for_prompt(sms_list)
    veh_serv = summarize_vehicle_service(current_ro)
    return f"{veh_serv}\nHISTORY_SUMMARY:\n{history_summary}"


# -------------------------
# Prompt Builders
# -------------------------
def build_system_prompt_common() -> str:
    return (
        "You are an assistant for a car service center (technicians and supervisors). "
        "Comply with safety and local laws; do not provide illegal or dangerous instructions. "
        "Reply with JSON only (no markdown or code fences). Be concise and professional."
    )


def build_user_prompt_sms_received(context_block: str) -> str:
    return (
        "TASK: Determine whether to respond by SMS and/or raise an internal notification based on the latest inbound SMS "
        "and the repair order context. Use professional tone for SMS. "
        "If insufficient context, you may return success:true with an empty actions array and a notification explaining what is missing.\n\n"
        "EXPECTED JSON SHAPE:\n"
        "{\n"
        '  "success": true,\n'
        '  "data": {\n'
        '    "actions": [\n'
        '      { "type": "sms", "content": "<string>" },\n'
        '      { "type": "notification", "subject": "<string>", "content": "<string>" },\n'
        '      { "type": "text", "content": "<string>" }\n'
        "    ]\n"
        "  }\n"
        "}\n\n"
        "CONTEXT (redacted & summarized):\n"
        "BEGIN_DATA\n"
        f"{context_block}\n"
        "END_DATA"
    )


def build_user_prompt_invoice_summary(context_block: str) -> str:
    return (
        "TASK: Generate a clear, customer-friendly explanation of the work performed that helps service advisors walk customers through their invoice confidently. "
        "For each service and part, explain: "
        "1) WHAT was done (specific work performed) "
        "2) WHY it was necessary (customer concern or safety issue) "
        "3) HOW it benefits the customer (improved performance, safety, reliability) "
        "4) WHAT parts were used (OEM quality, specifications) "
        "Use language that customers can understand while maintaining professionalism. "
        "Structure the explanation to flow logically from diagnosis to solution to outcome. "
        "Focus on value and necessity to help advisors justify charges and build customer confidence.\n\n"
        "EXPECTED JSON SHAPE:\n"
        "{\n"
        '  "success": true,\n'
        '  "data": {\n'
        '    "actions": [ { "type": "text", "content": "<customer-friendly invoice explanation with clear reasoning>" } ]\n'
        "  }\n"
        "}\n\n"
        "CONTEXT (redacted & summarized):\n"
        "BEGIN_DATA\n"
        f"{context_block}\n"
        "END_DATA"
    )


def build_user_prompt_service_calculation(context_block: str) -> str:
    return (
        "TASK: Calculate the next service due date based on vehicle information, service history, and manufacturer recommendations. "
        "Analyze the vehicle's make, model, year, current mileage, and previous service records to determine when the next service is due. "
        "Look at the service history to identify patterns - when was the last service performed and at what mileage? "
        "Calculate the next due date based on: "
        "1) Time interval (typically 3-6 months for oil changes) "
        "2) Mileage interval (typically 3,000-7,500 miles for oil changes, 15,000-30,000 for major services) "
        "3) Vehicle-specific requirements (luxury vehicles may have different intervals) "
        "Provide specific dates and mileage targets based on the actual service history data provided. "
        "Be specific about which comes first - time or mileage - and give exact recommendations.\n\n"
        "EXPECTED JSON SHAPE:\n"
        "{\n"
        '  "success": true,\n'
        '  "data": {\n'
        '    "actions": [ { "type": "text", "content": "<specific service due date calculation with exact dates and mileage targets>" } ]\n'
        "  }\n"
        "}\n\n"
        "CONTEXT (redacted & summarized):\n"
        "BEGIN_DATA\n"
        f"{context_block}\n"
        "END_DATA"
    )


def build_user_prompt_service_notes(context_block: str) -> str:
    return (
        "TASK: Generate clear, professional, and customer-friendly service notes based on completed repairs. "
        "Analyze the work performed, parts replaced, and services completed to create comprehensive notes that explain: "
        "1) What work was performed and why it was necessary "
        "2) Parts replaced and their purpose "
        "3) Services completed and their benefits "
        "4) Any recommendations for future maintenance "
        "Use professional but accessible language that customers can understand. "
        "Focus on the value and importance of the work performed. "
        "Be specific about the work done and avoid technical jargon when possible.\n\n"
        "EXPECTED JSON SHAPE:\n"
        "{\n"
        '  "success": true,\n'
        '  "data": {\n'
        '    "actions": [ { "type": "text", "content": "<professional service notes explaining completed work>" } ]\n'
        "  }\n"
        "}\n\n"
        "CONTEXT (redacted & summarized):\n"
        "BEGIN_DATA\n"
        f"{context_block}\n"
        "END_DATA"
    )


# -------------------------
# Models
# -------------------------
class ProcessRequest(BaseModel):
    event: str = Field(..., description="One of: 'sms-received', 'invoice-summary', 'service-calculation', 'service-notes'")
    customer: Dict[str, Any] = Field(default_factory=dict)
    communications: Dict[str, Any] = Field(default_factory=dict)
    currentRepairOrder: Dict[str, Any] = Field(default_factory=dict)

    @validator("event")
    def check_event(cls, v: str) -> str:
        if v not in ALLOWED_EVENTS:
            raise ValueError(f"Unsupported event '{v}'. Allowed: {sorted(ALLOWED_EVENTS)}")
        return v


class ActionItem(BaseModel):
    type: str
    content: Optional[str] = None
    subject: Optional[str] = None


class AIResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    errorMessage: Optional[str] = None


# -------------------------
# OpenAI Call
# -------------------------
async def call_openai_chat(system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    logger.info(f"🌐 Making request to OpenAI API: {OPENAI_CHAT_URL}")
    logger.info(f"🔑 Using model: {OPENAI_MODEL}")
    logger.info(f"⏱️ Timeout: {HTTP_TIMEOUT} seconds")
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
        "presence_penalty": 0.0,
        "frequency_penalty": 0.0,
        # "response_format": {"type": "json_object"}  # Uncomment if your model/account supports it
    }
    
    logger.info("📤 Sending request to OpenAI...")
    start_time = time.time()
    
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.post(OPENAI_CHAT_URL, headers=headers, json=body)
    
    end_time = time.time()
    logger.info(f"📥 Received response from OpenAI in {end_time - start_time:.2f} seconds")
    logger.info(f"📊 Response status: {resp.status_code}")
    if resp.status_code >= 400:
        # Return a structured error to the caller
        try:
            err = resp.json()
        except Exception:
            err = {"message": truncate_text(resp.text, 500)}
        raise HTTPException(status_code=502, detail={"openai_error": err, "status_code": resp.status_code})
    try:
        return resp.json()
    except Exception:
        raise HTTPException(status_code=502, detail="Malformed JSON from OpenAI")


def parse_openai_json(payload: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, int]]]:
    try:
        content = payload["choices"][0]["message"]["content"]
    except Exception:
        return None, None

    # Strip code fences if any
    text = content.strip()
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 3:
            text = parts[1]
        text = re.sub(r"^\s*json\s*", "", text, flags=re.IGNORECASE)

    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj, payload.get("usage")
    except Exception:
        return None, payload.get("usage")
    return None, payload.get("usage")


# -------------------------
# Policy Enforcement
# -------------------------
def enforce_output_policy(obj: Dict[str, Any]) -> Optional[str]:
    """Return an error code string if the output violates policy, else None."""
    # Only check for risky terms - allow finance in output
    if contains_any(RISKY_TERMS, obj):
        return "risky_content"
    return None


def sanitize_actions(actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Truncate large fields and ensure minimal schema
    sanitized: List[Dict[str, Any]] = []
    for a in actions:
        t = str(a.get("type", "")).strip()
        entry: Dict[str, Any] = {"type": t}
        if "subject" in a and isinstance(a["subject"], str):
            entry["subject"] = truncate_text(a["subject"], 200)
        if "content" in a and isinstance(a["content"], str):
            entry["content"] = truncate_text(a["content"], 500)
        sanitized.append(entry)
    return sanitized


# -------------------------
# Route: POST-only
# -------------------------
@app.post("/process", response_model=AIResponse)
async def process_route(req: ProcessRequest, _: str = Depends(require_basic)):
    logger.info(f"🚀 Starting process_route for event: {req.event}")
    
    # 1) Input policy scan (risky terms only)
    logger.info("🔍 Checking for risky terms...")
    if contains_any(RISKY_TERMS, req.dict()):
        logger.warning("❌ Request violates safety policy")
        return AIResponse(success=False, errorMessage="Request violates safety policy.")

    # 2) Redact PII for prompts (do not mutate original)
    logger.info("🔒 Redacting PII data...")
    redacted_customer = redact_pii(deep_copy(req.customer))
    redacted_ro = redact_pii(deep_copy(req.currentRepairOrder))
    redacted_comms = redact_pii(deep_copy(req.communications or {}))

    # Compress history: only last HISTORY_MAX, summarized (no verbatim text)
    sms_list = list(redacted_comms.get("sms") or [])
    redacted_comms["sms"] = sms_list[:HISTORY_MAX] if sms_list else []
    logger.info(f"📱 Processing {len(sms_list)} SMS messages (keeping last {HISTORY_MAX})")

    # 3) Build context block
    logger.info("📝 Building context block...")
    context_block = bulletize_context(redacted_customer, redacted_comms, redacted_ro)
    logger.info(f"📄 Context block length: {len(context_block)} characters")

    # 4) Build prompts per event
    logger.info(f"🎯 Building prompts for event: {req.event}")
    system_prompt = build_system_prompt_common()
    if req.event == "sms-received":
        user_prompt = build_user_prompt_sms_received(context_block)
    elif req.event == "invoice-summary":
        user_prompt = build_user_prompt_invoice_summary(context_block)
    elif req.event == "service-calculation":
        user_prompt = build_user_prompt_service_calculation(context_block)
    elif req.event == "service-notes":
        user_prompt = build_user_prompt_service_notes(context_block)
    else:
        # Already validated; just in case
        logger.error(f"❌ Unsupported event: {req.event}")
        return AIResponse(success=False, errorMessage=f"Unsupported event: {req.event}")

    logger.info(f"📋 System prompt length: {len(system_prompt)} characters")
    logger.info(f"📋 User prompt length: {len(user_prompt)} characters")

    # 5) Call OpenAI
    logger.info("🤖 Calling OpenAI API...")
    try:
        openai_raw = await call_openai_chat(system_prompt, user_prompt)
        model_used = openai_raw.get("model", OPENAI_MODEL)
        logger.info(f"✅ OpenAI response received from model: {model_used}")
        
        parsed_json, usage = parse_openai_json(openai_raw)
        if usage:
            logger.info(f"📊 OpenAI usage: {usage}")
    except Exception as e:
        logger.error(f"❌ OpenAI call failed: {str(e)}")
        raise

    if parsed_json is None:
        # Non-JSON reply from model -> convert to structured error
        logger.error("❌ OpenAI returned non-JSON response")
        return AIResponse(success=False, errorMessage="non_json_reply")

    # 6) Validate/normalize AI output schema
    logger.info("🔍 Parsing OpenAI response...")
    success = bool(parsed_json.get("success", False))
    data = parsed_json.get("data") if isinstance(parsed_json.get("data"), dict) else {}
    logger.info(f"📊 OpenAI response success: {success}")

    if success:
        actions = data.get("actions") if isinstance(data.get("actions"), list) else []
        logger.info(f"🎯 Found {len(actions)} actions in response")
        
        # sanitize and enforce output policy
        actions = sanitize_actions(actions)
        out_obj = {"success": True, "data": {"actions": actions}}

        # Final policy pass (risky terms only - allow finance in output)
        violation = enforce_output_policy(out_obj)
        if violation:
            logger.warning(f"❌ Policy violation detected: {violation}")
            return AIResponse(success=False, errorMessage=f"policy_violation:{violation}")
        
        logger.info("✅ Request processed successfully")
        return AIResponse(
            success=True,
            data={"actions": actions},
        )
    else:
        # errorMessage pass-through (sanitized length)
        msg = parsed_json.get("errorMessage") or "model_indicated_failure"
        logger.warning(f"❌ OpenAI indicated failure: {msg}")
        return AIResponse(success=False, errorMessage=truncate_text(str(msg), 300))


# Block all other verbs with 405
@app.get("/{path:path}")
@app.put("/{path:path}")
@app.patch("/{path:path}")
@app.delete("/{path:path}")
@app.options("/{path:path}")
@app.head("/{path:path}")
def method_not_allowed(path: str):
    raise HTTPException(status_code=405, detail="Method Not Allowed. Use POST /process.")
