# Customer Escalation Agent - Support Copilot

An AI-powered technical triage system designed to sit between Customer Support and Engineering teams. It investigates customer issues by collecting account, billing, log, and ticket context, then recommends whether the case should stay with support or escalate to engineering.

## Key Features

- Parallel evidence retrieval for user account data, billing, logs, and ticket history
- LLM-based technical diagnosis with OpenAI or OpenRouter
- Heuristic fallback when no LLM key is configured
- Interactive web console for demo scenarios and manual investigations
- Slack-friendly escalation summary formatting
- Optional production adapters for user, logs, and tickets APIs

## Project Structure

```text
agent.py          Core escalation logic, retrieval adapters, heuristics, and Slack formatting
main.py           FastAPI app for the REST API and web console
stripe_tools.py   Stripe integration for real payment data
slack_bot.py      Slack Socket Mode integration
static/           Frontend assets for the web console
.env.example      Example environment configuration
```

## Setup

1. Install dependencies.

```bash
pip install -r requirements.txt
```

2. Copy the example environment file.

```bash
cp .env.example .env
```

3. Fill in the keys you want to use.

- `OPENAI_API_KEY` or `OPENROUTER_API_KEY` for model-based analysis
- `LLM_MAX_TOKENS` to keep responses affordable when using limited OpenRouter credits
- `STRIPE_SECRET_KEY` for real Stripe billing evidence
- `USER_*`, `LOGS_*`, and `TICKETS_*` variables for real production evidence APIs

4. Restart the server any time you change `.env`.

## Production Evidence Adapters

The app can now call real APIs for user, logs, and tickets data. Each adapter is optional and uses a URL template plus optional headers, params, JSON body, and bearer token.

Supported template variables:

- `{email}`
- `{email_urlencoded}`
- `{ticket_id}`
- `{priority}`
- `{reporter_name}`
- `{issue_summary}`

Example:

```env
USER_API_URL_TEMPLATE=https://internal.example.com/users?email={email_urlencoded}
USER_API_METHOD=GET
USER_API_HEADERS_JSON={"X-Internal-Service":"customer-escalation-agent"}
USER_API_TOKEN=replace-me-user-api-token
```

If an adapter is unset or fails, the app falls back to mock data for that source only.

## Running the App

Start the FastAPI server:

```bash
python main.py
```

Open:

- `http://localhost:8000`
- `http://localhost:8000/docs`

## API Endpoints

- `POST /investigate`
- `POST /investigate/slack`
- `GET /health`
- `GET /`

## Notes

- Stripe is the only built-in production integration in this repo.
- User, logs, and tickets adapters are generic because every company exposes those systems differently.
- The UI now shows which sources were mock vs production for each investigation.
