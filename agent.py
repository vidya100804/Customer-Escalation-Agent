"""
agent.py - Core escalation agent logic
Shared by both main.py (FastAPI) and slack_bot.py (Slack)
"""

import asyncio
import json
import os
from typing import Any, List, Optional
from urllib.parse import quote_plus

import httpx
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel

load_dotenv()


try:
    from stripe_tools import get_stripe_payment_info

    USE_REAL_STRIPE = True
    print("[OK] Using real Stripe integration")
except ImportError:
    USE_REAL_STRIPE = False
    print("[WARN] Stripe not available - using mock payment data")


class EscalationRequest(BaseModel):
    user_email: str
    issue_summary: str
    priority: str = "P2"
    reporter_name: str
    ticket_id: Optional[str] = None


class EscalationResponse(BaseModel):
    summary: str
    technical_findings: str
    root_cause: str
    suggested_actions: List[str]
    escalate_to_engineering: bool
    escalation_reason: str
    confidence: float
    analysis_mode: str = "heuristic"
    model_name: Optional[str] = None
    evidence: Optional[dict[str, Any]] = None


async def _mock_user_details(email: str) -> dict[str, Any]:
    return {
        "user_id": "usr_12345",
        "email": email,
        "name": "John Doe",
        "account_tier": "Pro",
        "subscription_status": "active",
        "last_login": "2024-01-15T14:22:00Z",
        "api_calls_last_30_days": 15420,
    }


async def _mock_payment_info(email: str) -> dict[str, Any]:
    return {
        "plan": "Pro Monthly - $29.99",
        "status": "active",
        "failed_payment_attempts": 2,
        "last_error": "card_declined",
        "last_payment_date": "2024-01-01T00:00:00Z",
    }


async def _mock_logs(email: str) -> list[dict[str, Any]]:
    return [
        {
            "timestamp": "2024-01-15T14:20:15Z",
            "level": "ERROR",
            "service": "payment-service",
            "message": "Payment failed: card declined",
            "error_code": "PAY_503",
        },
        {
            "timestamp": "2024-01-15T14:18:45Z",
            "level": "WARNING",
            "service": "payment-service",
            "message": "Retry attempt 2/3",
            "error_code": "PAY_RETRY",
        },
    ]


async def _mock_tickets(email: str) -> list[dict[str, Any]]:
    return [
        {
            "ticket_id": "ZD-9876",
            "subject": "Payment failed",
            "status": "solved",
            "resolution": "User updated payment method",
        }
    ]


def _is_placeholder(value: Optional[str]) -> bool:
    if value is None:
        return True
    normalized = value.strip().lower()
    if not normalized:
        return True
    markers = (
        "your-",
        "placeholder",
        "example.com",
        "changeme",
        "replace-me",
    )
    return any(marker in normalized for marker in markers)


def _request_tokens(request: EscalationRequest) -> dict[str, str]:
    return {
        "user_email": request.user_email,
        "email": request.user_email,
        "email_urlencoded": quote_plus(request.user_email),
        "issue_summary": request.issue_summary,
        "priority": request.priority,
        "reporter_name": request.reporter_name,
        "ticket_id": request.ticket_id or "",
    }


def _render_template(template: str, tokens: dict[str, str]) -> str:
    return template.format(**tokens)


def _load_templated_json(raw: Optional[str], tokens: dict[str, str]) -> Optional[Any]:
    if not raw or _is_placeholder(raw):
        return None
    rendered = _render_template(raw, tokens)
    return json.loads(rendered)


def _normalize_response_payload(response: httpx.Response) -> Any:
    content_type = response.headers.get("content-type", "").lower()
    if "application/json" in content_type:
        return response.json()

    body = response.text.strip()
    if not body:
        return {}

    try:
        return response.json()
    except ValueError:
        return {"text": body}


async def _fetch_production_payload(prefix: str, request: EscalationRequest) -> Optional[Any]:
    url_template = os.getenv(f"{prefix}_API_URL_TEMPLATE")
    if _is_placeholder(url_template):
        return None

    tokens = _request_tokens(request)
    method = (os.getenv(f"{prefix}_API_METHOD") or "GET").upper()
    timeout = float(os.getenv(f"{prefix}_API_TIMEOUT_SECONDS") or "10")
    headers = _load_templated_json(os.getenv(f"{prefix}_API_HEADERS_JSON"), tokens) or {}
    params = _load_templated_json(os.getenv(f"{prefix}_API_PARAMS_JSON"), tokens)
    body = _load_templated_json(os.getenv(f"{prefix}_API_BODY_JSON"), tokens)
    auth_token = os.getenv(f"{prefix}_API_TOKEN")

    if auth_token and not _is_placeholder(auth_token):
        headers.setdefault("Authorization", f"Bearer {auth_token}")

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.request(
            method=method,
            url=_render_template(url_template, tokens),
            headers=headers,
            params=params,
            json=body,
        )
        response.raise_for_status()
        return _normalize_response_payload(response)


def _evidence_bundle(
    user_data: Any,
    payment_data: Any,
    logs: Any,
    tickets: Any,
    data_sources: dict[str, str],
) -> dict[str, Any]:
    return {
        "user_account": user_data,
        "payment": payment_data,
        "logs": logs,
        "tickets": tickets,
        "data_sources": data_sources,
    }


async def get_user_details(request: EscalationRequest) -> dict[str, Any]:
    try:
        payload = await _fetch_production_payload("USER", request)
        if payload is not None:
            return {"source": "production:user_api", "payload": payload}
    except Exception as e:
        print(f"[WARN] User API fetch failed: {e}. Falling back to mock user data.")
    return {"source": "mock:user_details", "payload": await _mock_user_details(request.user_email)}


async def get_payment_info(request: EscalationRequest) -> dict[str, Any]:
    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    if USE_REAL_STRIPE and not _is_placeholder(stripe_key):
        return {
            "source": "production:stripe",
            "payload": await get_stripe_payment_info(request.user_email),
        }
    return {
        "source": "mock:payment",
        "payload": await _mock_payment_info(request.user_email),
    }


async def get_recent_logs(request: EscalationRequest) -> dict[str, Any]:
    try:
        payload = await _fetch_production_payload("LOGS", request)
        if payload is not None:
            return {"source": "production:logs_api", "payload": payload}
    except Exception as e:
        print(f"[WARN] Logs API fetch failed: {e}. Falling back to mock logs.")
    return {"source": "mock:logs", "payload": await _mock_logs(request.user_email)}


async def get_previous_tickets(request: EscalationRequest) -> dict[str, Any]:
    try:
        payload = await _fetch_production_payload("TICKETS", request)
        if payload is not None:
            return {"source": "production:tickets_api", "payload": payload}
    except Exception as e:
        print(f"[WARN] Ticket API fetch failed: {e}. Falling back to mock tickets.")
    return {"source": "mock:tickets", "payload": await _mock_tickets(request.user_email)}


SYSTEM_PROMPT = """
You are an Expert Technical Support Agent called "Customer Escalation Agent".
Analyze customer escalations and respond in this exact format:

SUMMARY: <one sentence about what's happening>

TECHNICAL FINDINGS:
<bullet points of what you found in the data - use • prefix>

ROOT CAUSE: <most likely cause, be specific>

SUGGESTED ACTIONS:
- <action 1>
- <action 2>
- <action 3>

ESCALATE TO ENGINEERING: YES/NO - <reason>

CONFIDENCE: <0.0-1.0>

Rules:
- Use data, not speculation
- Be specific with error codes, timestamps, amounts
- Avoid deep technical jargon - support engineers read this
- Only escalate for real system bugs, outages, or security issues
- Do not suggest "contact engineering" as a first action
"""


def _first_value(record: Any, keys: list[str], default: Any = None) -> Any:
    if not isinstance(record, dict):
        return default
    for key in keys:
        value = record.get(key)
        if value not in (None, "", []):
            return value
    return default


def _to_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def _format_findings(lines: list[str]) -> str:
    return "\n".join(f"• {line}" for line in lines if line)


def _logs_as_text(logs: Any) -> str:
    if isinstance(logs, str):
        return logs
    if isinstance(logs, list):
        chunks = []
        for entry in logs:
            if isinstance(entry, dict):
                chunks.append(
                    " ".join(
                        str(entry.get(key, ""))
                        for key in ("timestamp", "level", "service", "error_code", "message")
                    ).strip()
                )
            else:
                chunks.append(str(entry))
        return "\n".join(chunks)
    return json.dumps(logs)


def run_heuristic_analyzer(
    request: EscalationRequest,
    evidence: Optional[dict[str, Any]] = None,
) -> EscalationResponse:
    """
    Local fallback analysis used when no LLM key is available or the LLM call fails.
    """
    issue_lower = request.issue_summary.lower()
    evidence = evidence or {}
    user_data = evidence.get("user_account") or {}
    payment_data = evidence.get("payment") or {}
    logs = evidence.get("logs") or []
    tickets = evidence.get("tickets") or []
    data_sources = evidence.get("data_sources") or {}

    user_name = _first_value(user_data, ["name", "full_name", "display_name"], request.user_email)
    account_tier = _first_value(user_data, ["account_tier", "tier", "plan", "subscription_tier"], "Unknown")
    subscription_status = _first_value(user_data, ["subscription_status", "status", "account_status"], "unknown")
    api_calls = _first_value(user_data, ["api_calls_last_30_days", "api_calls", "usage_30d"], "unknown")

    plan_name = _first_value(payment_data, ["plan", "product", "subscription_plan"], "Unknown")
    payment_status = _first_value(payment_data, ["subscription_status", "status", "last_payment_status"], "unknown")
    failed_attempts = _first_value(payment_data, ["failed_payment_attempts", "attempt_count"], 0)
    payment_error = str(_first_value(payment_data, ["last_payment_error", "last_error", "error"], "") or "")
    payment_error_lower = payment_error.lower()
    last_payment_date = _first_value(payment_data, ["last_payment_date", "date"], "unknown")

    logs_text = _logs_as_text(logs).lower()
    ticket_count = len(_to_list(tickets))

    if "no stripe customer found" in payment_error_lower:
        return EscalationResponse(
            summary="No Stripe billing record was found for the provided email, so the payment issue could not be confirmed from billing data.",
            technical_findings=_format_findings([
                f"Checked billing for {request.user_email}.",
                f"Stripe response: {payment_error}.",
                f"User data source: {data_sources.get('user_account', 'unknown')}.",
                f"Logs data source: {data_sources.get('logs', 'unknown')}.",
                f"Ticket data source: {data_sources.get('tickets', 'unknown')}.",
            ]),
            root_cause=(
                "The provided email does not currently map to a Stripe customer record. "
                "The customer may be using a different billing email, or billing has not yet "
                "been provisioned for this account."
            ),
            suggested_actions=[
                "Confirm the exact billing email the customer used for checkout or subscription signup.",
                "Search for alternate customer emails or account IDs in Stripe if your support workflow allows it.",
                "If the customer should already exist in billing, verify the provisioning path before escalating.",
            ],
            escalate_to_engineering=False,
            escalation_reason=(
                "NO - There is not enough evidence of a system defect yet. First verify the account-to-billing mapping."
            ),
            confidence=0.93,
        )

    if "card_declined" in payment_error_lower or any(
        k in issue_lower for k in ["decline", "payment", "card", "billing", "stripe", "charge", "invoice"]
    ):
        return EscalationResponse(
            summary="The available billing evidence points to a payment-method or issuer-side problem rather than a backend platform outage.",
            technical_findings=_format_findings([
                f"Customer reference: {user_name}.",
                f"Account tier: {account_tier} ({subscription_status}).",
                f"Billing plan: {plan_name}.",
                f"Billing status: {payment_status}.",
                f"Failed payment attempts: {failed_attempts}.",
                f"Latest payment error: {payment_error or 'not available'}.",
                f"Last payment date: {last_payment_date}.",
                f"Previous related ticket count: {ticket_count}.",
            ]),
            root_cause=(
                "The available billing evidence is more consistent with a payment-method or "
                "issuer-side failure than with an internal product defect."
            ),
            suggested_actions=[
                "Ask the customer to verify the billing email and update their payment method details.",
                "If the payment method is correct, ask them to contact their bank or card issuer for authorization checks.",
                "If service continuity matters, use your normal support-side grace-period workflow before escalating.",
            ],
            escalate_to_engineering=False,
            escalation_reason=(
                "NO - Billing declines are usually handled by support unless logs also show a platform-side outage."
            ),
            confidence=0.9,
        )

    if "429" in logs_text or any(
        k in issue_lower for k in ["rate", "limit", "throttle", "429", "quota", "usage", "exceed"]
    ):
        return EscalationResponse(
            summary="The evidence looks consistent with rate limiting or usage throttling rather than a product defect.",
            technical_findings=_format_findings([
                f"Account tier: {account_tier}.",
                f"Observed usage: {api_calls} requests in the last 30 days.",
                f"Subscription status: {subscription_status}.",
                "Recent logs include 429 or throttling behavior.",
            ]),
            root_cause=(
                "The client application appears to have exceeded an allowed request quota, "
                "which triggered normal throttling controls."
            ),
            suggested_actions=[
                "Share the current usage details with the customer and confirm the relevant plan limit.",
                "Recommend client-side backoff and retry behavior if they are retrying aggressively.",
                "Offer an upgrade path if the current throughput is expected to continue.",
            ],
            escalate_to_engineering=False,
            escalation_reason=(
                "NO - Rate limiting is expected behavior when a quota is exceeded."
            ),
            confidence=0.92,
        )

    if any(term in logs_text for term in ["connection pool exhausted", "timeout", "pay_503", "503", "database"]) or any(
        k in issue_lower for k in ["down", "outage", "503", "database", "crash", "timeout", "failed", "broken", "bug"]
    ):
        return EscalationResponse(
            summary="The available evidence suggests a platform-side outage or timeout condition that may require engineering attention.",
            technical_findings=_format_findings([
                "Recent logs indicate database, timeout, or service-failure behavior in the checkout path.",
                f"Logs source: {data_sources.get('logs', 'unknown')}.",
                f"Ticket history count reviewed: {ticket_count}.",
                f"Subscription status: {subscription_status}.",
            ]),
            root_cause=(
                "The failure pattern is more consistent with an internal service issue than with a normal customer-side configuration problem."
            ),
            suggested_actions=[
                "Check active incidents and on-call alerts for the affected service.",
                "Correlate this user report with recent log spikes or deployment activity.",
                "Escalate to engineering if the issue is reproducible or affecting multiple customers.",
            ],
            escalate_to_engineering=True,
            escalation_reason=(
                "YES - The evidence points to a potential service-side problem rather than a normal support case."
            ),
            confidence=0.9,
        )

    return EscalationResponse(
        summary="The available evidence does not currently show a clear platform defect or billing failure.",
        technical_findings=_format_findings([
            f"Account tier: {account_tier}.",
            f"Subscription status: {subscription_status}.",
            f"Observed usage: {api_calls}.",
            f"Ticket history count: {ticket_count}.",
            f"Payment status: {payment_status}.",
        ]),
        root_cause=(
            "This looks more like a standard support inquiry or an issue that still needs clearer reproduction steps."
        ),
        suggested_actions=[
            "Clarify the exact customer steps, timestamps, and expected behavior.",
            "Check whether the customer is using the correct account or billing email.",
            "If the issue becomes reproducible with logs or multiple affected users, escalate with the evidence bundle.",
        ],
        escalate_to_engineering=False,
        escalation_reason=(
            "NO - The current evidence does not justify an engineering escalation yet."
        ),
        confidence=0.82,
    )


async def run_agent(
    request: EscalationRequest,
    custom_api_key: Optional[str] = None,
) -> EscalationResponse:
    """
    Main agent entrypoint.
    Gathers all context in parallel, then calls the LLM.
    If the OpenAI/OpenRouter API key is missing or invalid, falls back to the heuristic analyzer.
    """
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    api_key = custom_api_key or openrouter_key or os.getenv("OPENAI_API_KEY")
    is_openrouter = bool((openrouter_key and api_key == openrouter_key) or (api_key and api_key.startswith("sk-or-v1-")))
    max_output_tokens = int(os.getenv("LLM_MAX_TOKENS") or "700")
    is_placeholder = (
        not api_key
        or "your-openai" in api_key
        or api_key.startswith("sk-your")
        or "your-openrouter" in api_key
        or api_key == ""
    )

    user_result, payment_result, logs_result, tickets_result = await asyncio.gather(
        get_user_details(request),
        get_payment_info(request),
        get_recent_logs(request),
        get_previous_tickets(request),
    )

    user_data = user_result["payload"]
    payment_data = payment_result["payload"]
    logs = logs_result["payload"]
    tickets = tickets_result["payload"]
    data_sources = {
        "user_account": user_result["source"],
        "payment": payment_result["source"],
        "logs": logs_result["source"],
        "tickets": tickets_result["source"],
    }
    evidence = _evidence_bundle(user_data, payment_data, logs, tickets, data_sources)

    if is_placeholder:
        print("[WARN] API key is placeholder/empty. Running local heuristic analyzer.")
        await asyncio.sleep(1.2)
        result = run_heuristic_analyzer(request, evidence)
        result.evidence = evidence
        result.analysis_mode = "heuristic"
        result.model_name = None
        return result

    context = f"""
=== ESCALATION REQUEST ===
User Email:    {request.user_email}
Issue:         {request.issue_summary}
Priority:      {request.priority}
Reported by:   {request.reporter_name}
Ticket ID:     {request.ticket_id or "N/A"}

=== DATA SOURCES ===
{json.dumps(data_sources, indent=2)}

=== USER ACCOUNT ===
{json.dumps(user_data, indent=2)}

=== PAYMENT / BILLING ===
{json.dumps(payment_data, indent=2)}

=== RECENT ERROR LOGS ===
{json.dumps(logs, indent=2)}

=== PREVIOUS SUPPORT TICKETS ===
{json.dumps(tickets, indent=2)}
"""

    try:
        if is_openrouter:
            print("[INFO] Initializing AsyncOpenAI via OpenRouter compatibility layer")
            client = AsyncOpenAI(
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
            )
            model_name = os.getenv("OPENROUTER_MODEL") or "google/gemini-2.5-pro"
            response = await client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": context},
                ],
                temperature=0.2,
                max_tokens=max_output_tokens,
                extra_headers={
                    "HTTP-Referer": "https://localhost:8000",
                    "X-Title": "Customer Escalation Agent",
                },
            )
            analysis_mode = "llm:openrouter"
        else:
            client = AsyncOpenAI(api_key=api_key)
            model_name = "gpt-4o"
            response = await client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": context},
                ],
                temperature=0.2,
                max_tokens=max_output_tokens,
            )
            analysis_mode = "llm:openai"

        result = _parse_response(response.choices[0].message.content or "")
        if _llm_result_is_incomplete(result):
            print("[WARN] LLM response was incomplete. Falling back to heuristic analyzer.")
            result = run_heuristic_analyzer(request, evidence)
            result.analysis_mode = "heuristic"
            result.model_name = model_name
        else:
            result.analysis_mode = analysis_mode
            result.model_name = model_name
        result.evidence = evidence
        return result
    except Exception as e:
        print(f"[WARN] API call failed: {e}. Falling back to heuristic analyzer.")
        result = run_heuristic_analyzer(request, evidence)
        result.evidence = evidence
        result.analysis_mode = "heuristic"
        result.model_name = None
        return result


def _parse_response(raw: str) -> EscalationResponse:
    summary = technical_findings = root_cause = escalation_reason = ""
    suggested_actions: List[str] = []
    escalate = False
    confidence = 0.8
    current_section = ""

    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        if line.startswith("SUMMARY:"):
            summary = line.replace("SUMMARY:", "", 1).strip()
            current_section = "summary"
        elif line.startswith("TECHNICAL FINDINGS:"):
            current_section = "findings"
        elif line.startswith("ROOT CAUSE:"):
            root_cause = line.replace("ROOT CAUSE:", "", 1).strip()
            current_section = "root_cause"
        elif line.startswith("SUGGESTED ACTIONS:"):
            current_section = "actions"
        elif line.startswith("ESCALATE TO ENGINEERING:"):
            val = line.replace("ESCALATE TO ENGINEERING:", "", 1).strip()
            escalate = val.upper().startswith("YES")
            escalation_reason = val
            current_section = "escalate"
        elif line.startswith("CONFIDENCE:"):
            try:
                confidence = float(line.replace("CONFIDENCE:", "", 1).strip())
            except ValueError:
                confidence = 0.8
            current_section = "confidence"
        else:
            if current_section == "findings":
                technical_findings += f"{line}\n"
            elif current_section == "actions" and (line.startswith("-") or line.startswith("•")):
                suggested_actions.append(line.lstrip("-• ").strip())

    return EscalationResponse(
        summary=summary or "Analysis complete.",
        technical_findings=technical_findings.strip() or "No additional findings.",
        root_cause=root_cause or "Unable to determine root cause.",
        suggested_actions=suggested_actions or ["Review the issue with the user."],
        escalate_to_engineering=escalate,
        escalation_reason=escalation_reason or "No escalation needed.",
        confidence=confidence,
    )


def _llm_result_is_incomplete(result: EscalationResponse) -> bool:
    return (
        result.technical_findings == "No additional findings."
        or result.root_cause == "Unable to determine root cause."
        or result.suggested_actions == ["Review the issue with the user."]
    )


def format_for_slack(req: EscalationRequest, res: EscalationResponse) -> str:
    escalate_emoji = "🚨 *YES - Escalate to Engineering*" if res.escalate_to_engineering else "✅ *NO - Support can handle*"
    priority_emoji = {"P0": "🔴", "P1": "🟠", "P2": "🟡", "P3": "🟢"}.get(req.priority, "⚪")
    confidence_bar = "█" * round(res.confidence * 10) + "░" * (10 - round(res.confidence * 10))
    actions = "\n".join(f"  {i + 1}. {action}" for i, action in enumerate(res.suggested_actions))

    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{priority_emoji} *Customer Escalation - {req.priority}*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*User:* `{req.user_email}`
*Issue:* {req.issue_summary}
*Reporter:* {req.reporter_name}

*SUMMARY*
{res.summary}

*TECHNICAL FINDINGS*
{res.technical_findings}

*ROOT CAUSE*
{res.root_cause}

*SUGGESTED ACTIONS*
{actions}

*ESCALATE TO ENGINEERING?*
{escalate_emoji}
_{res.escalation_reason}_

*Confidence:* `{confidence_bar}` {int(res.confidence * 100)}%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".strip()
