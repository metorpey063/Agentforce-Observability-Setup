# Agentforce Observability Setup

A Claude Code skill for Salesforce SEs and admins to rapidly enable Agentforce Observability, configure the Agent API, and generate real traced agent sessions that populate the pre-built Agent Analytics dashboards in Tableau Next.

## What it does

Running `/setup-observability` walks you through:

1. **Enabling Session Tracing** — toggles on the observability pipeline in Setup, provisioning 8 Data Cloud DLOs and pre-built Tableau Next dashboards
2. **Creating a Service Agent** — builds an API-compatible agent (ExternalCopilot type) with the correct user assignment
3. **Configuring the Agent API** — sets up OAuth scopes and CLI authentication for programmatic access
4. **Generating real sessions** — runs 30-50+ diverse agent conversations that exercise escalation, deflection, abandonment, and general support flows
5. **Verifying dashboard population** — confirms data is flowing through the pipeline and identifies what's working vs. what needs more time

## Quick Start

```bash
# From this directory, start Claude Code
claude

# Run the setup skill
/setup-observability
```

Or use the session generator directly:
```bash
python generate_sessions.py --agent Agent_test --org my-org-alias --count 50
```

## What gets built

After running the skill, your org will have:

- **Agentforce Session Tracing** enabled with full observability pipeline
- **Pre-built dashboards** populated with real session data:
  - Service Agent Analytics (escalation rate, deflection, engagement, action usage)
  - Employee Agent Analytics (same metrics for internal copilot)
- **A Service Agent** configured for API access
- **50+ traced sessions** covering escalation, deflection, abandonment, and general support scenarios

## Architecture

```
User prompts (via sf agent preview CLI)
    ↓
Agentforce Service Agent (ExternalCopilot type)
    ↓
ConversationDefinitionSession + EventLog (immediate, Salesforce Core)
    ↓ (~10-15 min sync)
Data Cloud DLOs (AiAgentSession, AiAgentInteractionStep, etc.)
    ↓ (mapped via pre-built SDMs)
Tableau Next Dashboards (Service Agent Analytics, Employee Agent Analytics)
```

## Prerequisites

- Salesforce org with Agentforce + Data Cloud enabled
- Admin/Setup access
- Salesforce CLI v2.140+ (`sf update` to upgrade)
- Claude Code

## Key Learnings & Gotchas

See [CLAUDE.md](CLAUDE.md) for the full technical reference, including:
- Which agent types work with the API (and which don't)
- Why token/credit data doesn't appear in SDO/trial orgs
- The JWT bootstrap authentication flow the CLI uses
- How to troubleshoot common errors

## Files

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Full technical reference and known limitations |
| `.claude/commands/setup-observability.md` | The `/setup-observability` skill (8-phase wizard) |
| `generate_sessions.py` | Standalone session generation script |
| `CHANGELOG.md` | Version history |
