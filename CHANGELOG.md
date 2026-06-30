# Changelog

## [1.0.0] - 2026-06-30

### Added
- `/setup-observability` skill — 8-phase guided wizard for enabling Agentforce Observability
- `generate_sessions.py` — standalone script for generating diverse agent sessions (escalation, deflection, abandonment, general)
- Full `CLAUDE.md` technical reference with architecture, known limitations, and troubleshooting
- `README.md` with quick start and architecture overview

### Key Discoveries (from initial development)
- Agent API does NOT support `InternalCopilot` / Employee agent types — must use `ExternalCopilot` (Service Agent template)
- `BotUserId` field is not exposed in the UI for Employee agents — only Service agents show "Agent User" settings
- SF CLI `sf agent preview` requires browser-authenticated session (`sf org login web`) — access-token auth doesn't provide the JWT the bootstrap endpoint needs
- Token/credit consumption data (`TenantConsumptionInsights`, `Ai_Response_Generation`) only populates on paid Agentforce plans — SDO/trial orgs don't meter
- The `Audit and Feedback` toggle provisions `Ai_Feedback` DMO but it can take hours to become queryable
- Session end types (`Escalated`, `Abandoned`, etc.) depend on HOW the session ends — programmatic `preview end` sets `NOT_SET`; the agent's own escalation routing sets the proper type
- Data Cloud sync from event logs to DLOs has a 10-15 minute lag
- The OTel API (`/einstein/audit/otel/{sessionId}`) requires `GenAIFeedback__dlm` to exist (provisioned by Audit & Feedback toggle)
