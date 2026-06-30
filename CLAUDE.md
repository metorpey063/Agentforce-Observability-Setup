# Agentforce Observability Setup

A Claude Code skill that walks users through enabling Agentforce Observability in a Salesforce org, configuring the Agent API for programmatic session generation, and populating the pre-built Agent Analytics dashboards with real traced data.

## What this does

- **/setup-observability** — Guided setup: enables Session Tracing, Audit & Feedback, creates a Service Agent with Agent API access, and generates real traced sessions to populate dashboards

## Prerequisites

- A Salesforce org with Agentforce enabled
- Data Cloud enabled in the org
- Salesforce CLI (`sf`) v2.140+ installed locally
- An admin user with Setup access

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

## Known Limitations

- **Token/credit data** (`TenantConsumptionInsights`, `Ai_Response_Generation`) only populates on orgs with paid Agentforce credit consumption — SDO/trial orgs don't meter credits
- **Agent API doesn't support "Agentforce (Default)"** — must create a separate Service/External agent
- **Employee/InternalCopilot agents** don't expose Run As User in the UI — use ExternalCopilot/ServiceAgent type
- **Session end type** depends on how the session ends — programmatic `preview end` sets `NOT_SET`; escalation routing sets the proper type
- **Data Cloud sync lag** — 10-15 minutes from session creation to DLO population
- **OTel API** requires `GenAIFeedback__dlm` table (provisioned by Audit & Feedback toggle, may take hours)
- The `/agentforce/bootstrap/nameduser` JWT endpoint only works with browser-authenticated sessions (not REST API tokens)

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
