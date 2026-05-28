"""
slack_bot.py — Slack Bot for the Customer Escalation Agent
Uses Slack Bolt SDK (Socket Mode — no public URL needed for local dev!)

Commands:
  /escalate  →  Opens a modal to submit an escalation
  Result is posted back to the channel as a rich message

Setup:
  1. Create a Slack App at https://api.slack.com/apps
  2. Enable Socket Mode (for local dev — no ngrok needed!)
  3. Add Slash Command: /escalate
  4. Add Bot Token Scopes: commands, chat:write, chat:write.public
  5. Install the app to your workspace
  6. Copy SLACK_BOT_TOKEN + SLACK_SIGNING_SECRET into .env
  7. Run: python slack_bot.py
"""

import os
import asyncio
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from agent import EscalationRequest, run_agent, format_for_slack

load_dotenv()

# ─── SLACK APP SETUP ──────────────────────────────────────────────────────────

app = App(
    token=os.getenv("SLACK_BOT_TOKEN"),
    signing_secret=os.getenv("SLACK_SIGNING_SECRET"),
)


# ─── /escalate SLASH COMMAND → Open Modal ────────────────────────────────────

@app.command("/escalate")
def open_escalate_modal(ack, body, client):
    """
    When a support engineer types /escalate, open a modal form.
    They fill in: user email, issue summary, priority.
    """
    ack()  # Must acknowledge within 3 seconds

    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "escalation_modal",
            "title": {"type": "plain_text", "text": "🚨 Escalate Customer Issue"},
            "submit": {"type": "plain_text", "text": "Investigate"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "private_metadata": body["channel_id"],  # Remember which channel to post to
            "blocks": [
                {
                    "type": "input",
                    "block_id": "email_block",
                    "label": {"type": "plain_text", "text": "Customer Email"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "user_email",
                        "placeholder": {"type": "plain_text", "text": "customer@example.com"},
                    },
                },
                {
                    "type": "input",
                    "block_id": "issue_block",
                    "label": {"type": "plain_text", "text": "Issue Summary"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "issue_summary",
                        "multiline": True,
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Describe what the customer is experiencing...",
                        },
                    },
                },
                {
                    "type": "input",
                    "block_id": "priority_block",
                    "label": {"type": "plain_text", "text": "Priority"},
                    "element": {
                        "type": "static_select",
                        "action_id": "priority",
                        "placeholder": {"type": "plain_text", "text": "Select priority"},
                        "options": [
                            {"text": {"type": "plain_text", "text": "🔴 P0 — Critical (outage)"}, "value": "P0"},
                            {"text": {"type": "plain_text", "text": "🟠 P1 — High (major issue)"}, "value": "P1"},
                            {"text": {"type": "plain_text", "text": "🟡 P2 — Medium (degraded)"}, "value": "P2"},
                            {"text": {"type": "plain_text", "text": "🟢 P3 — Low (minor)"}, "value": "P3"},
                        ],
                        "initial_option": {
                            "text": {"type": "plain_text", "text": "🟡 P2 — Medium (degraded)"},
                            "value": "P2",
                        },
                    },
                },
            ],
        },
    )


# ─── MODAL SUBMISSION → Run Agent → Post Result ───────────────────────────────

@app.view("escalation_modal")
def handle_modal_submission(ack, body, client, view):
    """
    When the modal is submitted:
    1. Acknowledge immediately (Slack requires <3s)
    2. Post a "thinking..." message
    3. Run the agent (async via thread)
    4. Update the message with the result
    """
    ack()

    values = view["state"]["values"]
    user_email   = values["email_block"]["user_email"]["value"]
    issue        = values["issue_block"]["issue_summary"]["value"]
    priority     = values["priority_block"]["priority"]["selected_option"]["value"]
    channel_id   = view["private_metadata"]
    reporter     = body["user"]["name"]

    # Post a "thinking" placeholder immediately
    thinking_msg = client.chat_postMessage(
        channel=channel_id,
        text=f"🔍 Investigating escalation for `{user_email}`... (this takes ~10s)",
    )

    # Run agent in a background thread (Slack handlers are sync)
    def run_in_thread():
        request = EscalationRequest(
            user_email=user_email,
            issue_summary=issue,
            priority=priority,
            reporter_name=reporter,
        )

        # Run the async agent from a sync context
        result = asyncio.run(run_agent(request))
        slack_text = format_for_slack(request, result)

        # Determine which channel to alert in
        mention = "<!channel>" if priority in ("P0", "P1") else ""

        # Update the placeholder message with the real result
        client.chat_update(
            channel=channel_id,
            ts=thinking_msg["ts"],
            text=slack_text,
            blocks=_build_slack_blocks(request, result, mention),
        )

    import threading
    threading.Thread(target=run_in_thread, daemon=True).start()


# ─── BLOCK KIT BUILDER ────────────────────────────────────────────────────────

def _build_slack_blocks(req: EscalationRequest, res, mention: str = "") -> list:
    """
    Build rich Slack Block Kit blocks for the escalation result.
    """
    priority_emoji = {"P0": "🔴", "P1": "🟠", "P2": "🟡", "P3": "🟢"}.get(req.priority, "⚪")
    escalate_text = (
        "🚨 *YES — Page Engineering Now*"
        if res.escalate_to_engineering
        else "✅ *NO — Support Can Handle This*"
    )
    confidence_pct = f"{int(res.confidence * 100)}%"
    actions_text = "\n".join(f"{i+1}. {a}" for i, a in enumerate(res.suggested_actions))

    blocks = []

    # Header
    blocks.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": f"{priority_emoji} Escalation {req.priority} — {req.user_email}",
        },
    })

    if mention:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": mention}})

    # Context bar
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": f"*Reporter:* {req.reporter_name}"},
            {"type": "mrkdwn", "text": f"*Priority:* {req.priority}"},
            {"type": "mrkdwn", "text": f"*Confidence:* {confidence_pct}"},
        ],
    })

    blocks.append({"type": "divider"})

    # Summary
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"*📋 Summary*\n{res.summary}"},
    })

    # Issue
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"*📝 Reported Issue*\n{req.issue_summary}"},
    })

    blocks.append({"type": "divider"})

    # Technical findings
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"*🔍 Technical Findings*\n{res.technical_findings}"},
    })

    # Root cause
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"*🧠 Root Cause*\n{res.root_cause}"},
    })

    # Suggested actions
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"*🛠️ Suggested Actions*\n{actions_text}"},
    })

    blocks.append({"type": "divider"})

    # Escalation decision
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*⚡ Escalate to Engineering?*\n{escalate_text}\n_{res.escalation_reason}_",
        },
    })

    return blocks


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🤖 Customer Escalation Bot starting...")
    print("   Commands available: /escalate")
    print("   Mode: Socket Mode (no public URL needed)")

    handler = SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN"))
    handler.start()
