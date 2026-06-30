# Agentforce Observability Setup Wizard

Guide the user through enabling Agentforce Observability in their Salesforce org and generating real agent sessions for the pre-built Agent Analytics dashboards.

## Workflow

Work through these phases sequentially, confirming each step with the user before proceeding.

### Phase 1: Prerequisites Check
1. Confirm the user has a Salesforce org with Agentforce enabled
2. Check if `sf` CLI is installed and version ≥ 2.140: `sf --version`
   - If outdated: `sf update`
3. Ask the user to authenticate their org: `sf org login web --instance-url https://<my-domain>.my.salesforce.com --alias agentforce-obs --set-default`
4. Verify connection: `sf org display --target-org agentforce-obs --json`

### Phase 2: Enable Observability
Walk the user through the Setup UI:

1. Tell the user: "Go to **Setup → Quick Find → search 'Einstein Generative AI'** → click **Einstein Audit, Analytics, and Monitoring Setup**"
2. Ask them to toggle ON:
   - **Agentforce Session Tracing** (this provisions the Data Cloud DLOs and pre-built dashboards)
   - **Agent Platform Tracing** (sub-toggle under Session Tracing)
   - **Agent Optimization** (auto-enables with Session Tracing)
   - **Agent Health Monitoring**
   - **Audit and Feedback** (provisions trust/quality metrics)
3. Wait 2-3 minutes for provisioning
4. Verify DLOs were created by querying: `SELECT * FROM AiAgentSession__dll LIMIT 1` via the ssot/queryV2 endpoint

### Phase 3: Create Service Agent
The Agent API requires an ExternalCopilot/Service agent type (not the default Employee copilot).

1. Tell the user: "Open **App Launcher → Agentforce** (or Setup → Agents)"
2. "Click **+ New Agent** and select the **Service Agent** template"
3. "Name it something like `Agent_test` or `Observability_Demo_Agent`"
4. "Make sure it gets activated (Active version)"
5. Verify by querying: `SELECT Id, DeveloperName, MasterLabel, Type, AgentType, BotUserId FROM BotDefinition WHERE Type = 'ExternalCopilot'`
6. Confirm BotUserId is set — if null, they need to assign the Agent User in the agent's settings

### Phase 4: Create Agent User
Run: `sf org create agent-user --target-org agentforce-obs`

This creates a dedicated user with the required permission sets. If the agent's BotUserId was null, tell the user to assign this new user to the agent in Agentforce Studio settings.

### Phase 5: Configure Connected App (for programmatic API access)
Walk the user through:

1. "Go to **Setup → App Manager** → find your connected app (or create a new one)"
2. "Edit OAuth Settings and add these scopes:
   - `Access chatbot services (chatbot_api)`
   - `Access the Salesforce API Platform (sfap_api)`  
   - `Manage user data via Web browsers (web)`
   - `Manage user data via APIs (api)`"
3. "Check **Enable Client Credentials Flow**"
4. "Uncheck 'Require PKCE' if it's checked"
5. "Save, then click **Manage** → **Edit Policies**"
6. "Under 'Client Credentials Flow', set the **Run As** user to your admin user"
7. "Save. Changes take 2-5 minutes to propagate."

### Phase 6: Test Agent API Connection
Test the session creation:
```bash
sf agent preview start --api-name <AgentDeveloperName> --target-org agentforce-obs --json
```

If successful, send a test message:
```bash
sf agent preview send --api-name <AgentDeveloperName> --session-id <sessionId> --utterance "Hello, what can you help me with?" --target-org agentforce-obs --json
```

Common errors:
- "Invalid user ID provided on start session" → Agent needs BotUserId set (assign in Agentforce Studio)
- "ApiAccessError: Error obtaining API token" → Connected app missing chatbot_api/sfap_api scopes, or needs web login: `sf org login web`
- "Agent not found" → Agent not activated or wrong DeveloperName

### Phase 7: Generate Sessions
Generate a diverse set of sessions to populate all dashboard metrics:

Run a script that creates sessions in three categories:
1. **Escalation sessions** (10): Prompts like "Transfer me to a human", "I want to speak to a manager"
2. **Deflection sessions** (8): Simple questions resolved by the agent, user says "thanks"
3. **Abandonment sessions** (5): User sends one message and leaves
4. **General sessions** (20-30): Varied prompts (billing, technical, account management)

Use `sf agent preview start` / `send` / `end` commands. Key points:
- DON'T call `preview end` after escalation triggers — let the agent's routing complete
- DO end deflection sessions after the user says thanks
- DON'T end abandonment sessions at all
- Wait 1-3 seconds between messages in a session
- Wait 3 seconds between sessions

### Phase 8: Verify Dashboard Population
After generating sessions, wait 10-15 minutes for Data Cloud sync, then check:

1. Query DLO counts to confirm data is flowing
2. Tell the user to navigate to **Data 360 → Service Agent Analytics Workspace** to see the dashboard
3. Check which metrics are populating vs. still zero

Metrics that require additional setup:
- **Trust/Quality metrics**: Need Audit & Feedback to fully provision (can take hours)
- **Token/Credit data**: Only on paid Agentforce plans
- **RAG metrics**: Agent must use Knowledge retrieval actions
- **Voice metrics**: Only for voice-channel agents

## Error Handling

If the user hits issues at any phase, troubleshoot:
- Check `sf org display --target-org agentforce-obs --json` for auth issues
- Query `ConversationDefinitionEventLog` to verify sessions are being recorded
- Query `AiAgentSession__dll` via ssot/queryV2 to check Data Cloud sync
- If DLOs don't exist, Session Tracing toggle may not have been enabled
