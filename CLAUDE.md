# Agentforce Observability Setup

A Claude Code skill that walks users through enabling Agentforce Observability in a Salesforce org, configuring the Agent API for programmatic session generation, and populating the pre-built Agent Analytics dashboards with real traced data.

## What this does

- **/setup-observability** — Guided 8-phase setup wizard: enables Session Tracing, Audit & Feedback, creates a Service Agent with Agent API access, and generates real traced sessions to populate dashboards

## Reference Documentation
- Session Tracing setup: https://help.salesforce.com/s/articleView?id=ai.generative_ai_session_trace_setup.htm
- Audit & Feedback setup: https://help.salesforce.com/s/articleView?id=ai.generative_ai_feedback_enable.htm
- Session Tracing data model: https://help.salesforce.com/s/articleView?id=ai.generative_ai_session_trace_data_model.htm
- OTel API (trace export): https://developer.salesforce.com/docs/ai/agentforce/guide/otel-api.html
- Agent API (runtime): https://developer.salesforce.com/docs/ai/agentforce/guide/agent-api-get-started.html
- Agent API examples: https://developer.salesforce.com/docs/ai/agentforce/guide/agent-api-examples.html

## Prerequisites

- A Salesforce org with Agentforce enabled
- Data Cloud enabled in the org
- Salesforce CLI (`sf`) v2.140+ installed locally (`sf update` to upgrade)
- An admin user with Setup access
- Browser access for SF CLI web login (required for Agent API JWT auth)

## Architecture

```
Agentforce Agent (Service Agent type)
    ↓ (user prompts via Agent API / sf agent preview)
ConversationDefinitionSession + EventLog (Salesforce Core)
    ↓ (Session Tracing pipeline, ~10-15 min lag)
Data Cloud DLOs:
  - AiAgentSession__dll
  - AiAgentInteraction__dll
  - AiAgentInteractionStep__dll (actions + I/O payloads)
  - AiAgentInteractionMessage__dll
  - AiAgentSessionParticipant__dll
  - AiAgentSessionLog__dll
    ↓ (Standard DMOs mapped by pre-built SDMs)
Pre-built Tableau Next Dashboards:
  - Service Agent Analytics
  - Employee Agent Analytics
```

## Key Setup Steps (Summary)

### 1. Enable Observability
- Setup → Quick Find → "Einstein Generative AI" → **Einstein Audit, Analytics, and Monitoring Setup**
- Toggle ON: **Agentforce Session Tracing** (+ sub-toggles: Agent Platform Tracing, Agent Optimization)
- Toggle ON: **Audit and Feedback**
- Toggle ON: **Agent Health Monitoring**

### 2. Create a Service Agent
- Agentforce Studio → New Agent → Service Agent template
- This creates an `ExternalCopilot` type agent with `EinsteinServiceAgent` AgentType
- The agent exposes a "Run As User" / Agent User field (unlike Employee/InternalCopilot agents)

### 3. Create Agent User
```bash
sf org create agent-user --target-org <alias>
```
This creates a user with AgentforceServiceAgentBase, AgentforceServiceAgentUser, and EinsteinGPTPromptTemplateUser permission sets.

### 4. Configure Connected App for Agent API
- Setup → App Manager → find/create connected app
- OAuth Settings:
  - Add scopes: `chatbot_api`, `sfap_api`, `web`, `api`, `refresh_token`
  - Enable **Client Credentials Flow**
  - Uncheck "Require PKCE"
- Manage → Edit Policies → Client Credentials Flow → Set **Run As** user

### 5. Authenticate CLI
```bash
sf org login web --instance-url https://<my-domain>.my.salesforce.com --alias <alias> --set-default
```

### 6. Generate Sessions
```bash
sf agent preview start --api-name <AgentDeveloperName> --target-org <alias> --json
sf agent preview send --api-name <AgentDeveloperName> --session-id <id> --utterance "your message" --target-org <alias> --json
sf agent preview end --session-id <id> --api-name <AgentDeveloperName> --target-org <alias>
```

## What Populates the Dashboards

| Dashboard Metric | Data Source | How to Generate |
|-----------------|-------------|-----------------|
| Unique Sessions | AiAgentSession | Any session start |
| Engagement Rate | Session engaged flag | Send at least 1 message |
| Escalation Rate | Session end type = Escalated | Prompt: "transfer me to a human" |
| Deflection Rate | Session resolved without escalation | Prompt: question → "thanks, that helps" |
| Abandon Rate | Session with no end/response | Start session, send 1 msg, don't end |
| Action Usage | AiAgentInteractionStep (ACTION_STEP) | Prompts that trigger actions (queries, updates) |
| Error Rate | AiAgentSessionLog | Prompts that cause failures |
| Quality/Trust Metrics | Ai_Feedback DMO | Requires Audit & Feedback enabled + time |
| Token/Credit Cost | TenantConsumptionInsights | Requires paid Agentforce plan with credit metering |
| RAG Metrics | AiRetrieverQualityMetric | Agent must use Knowledge retrieval |

## Known Limitations & Gotchas

### Agent API restrictions
- **Agent API doesn't support "Agentforce (Default)"** — must create a separate Service/External agent
- **Employee/InternalCopilot agents** don't expose "Run As User" in the UI and have `BotUserId = null` — you cannot PATCH this field via API either (`CANNOT_INSERT_UPDATE_ACTIVATE_ENTITY`). Only `ExternalCopilot` (Service Agent template) exposes this setting.
- **`bypassUser: true`** in the Agent API uses the agent's BotUserId — if that's null, you get `"Invalid user ID provided on start session: "`. Use `bypassUser: false` or assign a user.

### Authentication flow
- The SF CLI `sf agent preview` commands use a **JWT** obtained from `GET {instanceUrl}/agentforce/bootstrap/nameduser` with `Cookie: sid={accessToken}`. This only works with browser-authenticated sessions — not REST API access tokens or client_credentials tokens.
- **`sf org login web` is required** (not `sf org login access-token`). The browser flow gives the CLI a session that the bootstrap endpoint accepts.
- **Don't pass `--client-id` to `sf org login web`** unless your connected app has `http://localhost:1717/OauthRedirect` in callback URLs. The default PlatformCLI app handles this automatically.
- **Client credentials flow** (`grant_type=client_credentials`) must be POSTed to the **My Domain URL** (e.g. `https://mydomain.my.salesforce.com/services/oauth2/token`), NOT `login.salesforce.com` — the latter returns `"request not supported on this domain"`.
- Connected app scope changes are **non-breaking** — adding `chatbot_api`/`sfap_api` scopes and enabling client credentials flow doesn't invalidate existing refresh tokens or affect the authorization code flow.

### Data pipeline
- **Data Cloud sync lag** — 10-15 minutes from session creation to DLO population
- **Session end type** depends on how the session ends — programmatic `sf agent preview end` sets `sessionEndType = "NOT_SET"`. The agent's own escalation routing sets proper types like `"Escalated"`. To get escalation data, DON'T call `preview end` after the agent escalates — let it complete.
- **OTel API** (`GET /services/data/v66.0/einstein/audit/otel/{session-id}`) requires `GenAIFeedback__dlm` table to exist — provisioned by the Audit & Feedback toggle but can take **hours** to become available.
- **Audit & Feedback DLOs** (`Ai_Feedback`, `GenAiResponseGeneration`) provision slowly — the toggle enables them but actual data flow may take 12-24 hours.

### Escalation/Abandon metrics in preview mode
- **Escalation Rate = 0%** in preview mode because `sf agent preview end` always sets session end type to `CLOSED_USER_REQUEST`, never `CLOSED_TRANSFERRED`. The dashboard formula (`Escalation_Status_clc`) specifically checks for step name `'CLOSED_TRANSFERRED'` in `SESSION_END` type interactions.
- The agent DOES call `escalate_to_human` (visible in `AiAgentInteractionStep` as an LLM tool call) — the action fires but the Omni-Channel handoff can't complete without a live channel deployment.
- **Abandon Rate = 0%** for the same reason — even "abandoned" sessions (where we don't call `preview end`) eventually get `CLOSED_USER_REQUEST` when the session expires.
- **To get real escalation data**: deploy the agent on a Messaging channel with Omni-Channel routing (Messaging for In-App & Web → Omni-Flow → queue). When the agent escalates, the routing flow transfers to the queue and records `CLOSED_TRANSFERRED`. This requires modifying the Omni-Channel routing flow — risky in SDO orgs with existing demos.
- **Deflection Rate DOES work** (72%) — sessions ended with `CLOSED_USER_REQUEST` that had at least one TURN interaction count as deflected.

### Credit/cost metering
- **Token/credit data** (`TenantConsumptionInsights`, `Ai_Response_Generation`) only populates on orgs with **paid Agentforce credit billing** — SDO/trial/developer orgs don't meter credits the same way.
- The pre-built dashboard's `Total_Flex_Credits_clc` metric formula is: `SUM(IF [Tenant_Consumption_Insights].[Card_Definition_Developer_Name] = 'FlexCredits' AND [AI_Agent_Interaction_Step].[Ai_Agent_Interaction_Step_Type] = 'ACTION_STEP' THEN [Tenant_Consumption_Insights].[Units_Consumed] ELSE 0 END)` — this will always return 0 until consumption data flows.
- **Workaround for demos**: Use `AiAgentInteractionStep` start/end timestamps to calculate action duration as a proxy for cost.

### CLI requirements
- SF CLI must be **v2.140+** for `sf agent preview start/send/end` commands. Earlier versions don't have the agent plugin.
- The CLI requires a `sfdx-project.json` file in the working directory (even a minimal one works: `{"packageDirectories": [{"path": "force-app", "default": true}], "sourceApiVersion": "66.0"}`).
- `sf agent preview end` can timeout (>15s) — handle gracefully in scripts, sessions expire on their own.

## Prompt Patterns for Session Generation

### Escalation triggers:
- "I need to speak to a real person"
- "Transfer me to a human agent"
- "Escalate this to a manager"
- "I refuse to deal with a chatbot"

### Deflection triggers (self-resolved):
- Simple question → "Thanks, that answers my question"
- "How do I reset my password?" → "Got it, I'll try that. Thank you"

### Action triggers (QueryRecords, GetRecordDetails, etc.):
- "What are my open cases?"
- "Show me account details for Acme Corp"
- "Update my phone number to 555-1234"

### Abandonment:
- Send 1 message, don't call preview end
