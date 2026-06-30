# Agentforce Observability Setup Wizard

Guide the user through enabling Agentforce Observability in their Salesforce org and generating real agent sessions for the pre-built Agent Analytics dashboards.

## Reference Documentation
- Setup guide: https://help.salesforce.com/s/articleView?id=ai.generative_ai_session_trace_setup.htm
- Audit & Feedback: https://help.salesforce.com/s/articleView?id=ai.generative_ai_feedback_enable.htm
- Session Tracing data model: https://help.salesforce.com/s/articleView?id=ai.generative_ai_session_trace_data_model.htm
- OTel API: https://developer.salesforce.com/docs/ai/agentforce/guide/otel-api.html
- Agent API: https://developer.salesforce.com/docs/ai/agentforce/guide/agent-api-get-started.html

## Workflow

Work through these phases sequentially, confirming each step with the user before proceeding. At each phase, verify the outcome before moving on.

### Phase 1: Prerequisites Check

1. Confirm the user has:
   - A Salesforce org with **Agentforce** enabled
   - **Data Cloud** enabled in the org (required for session tracing DLOs)
   - Admin/Setup access to the org

2. Check if `sf` CLI is installed and version ≥ 2.140:
   ```bash
   sf --version
   ```
   If outdated or not installed:
   ```bash
   sf update
   ```

3. Authenticate the org using the **browser flow** (this is required — access-token auth won't work for the Agent API):
   ```bash
   sf org login web --instance-url https://<my-domain>.my.salesforce.com --alias agentforce-obs --set-default
   ```
   
   **IMPORTANT**: Use the default `PlatformCLI` connected app (don't pass `--client-id`). If you pass a custom connected app's client ID, you'll get `redirect_uri_mismatch` unless that app has `http://localhost:1717/OauthRedirect` in its callback URLs. The default PlatformCLI app handles this automatically.

4. Verify connection:
   ```bash
   sf org display --target-org agentforce-obs --json
   ```
   Confirm `connectedStatus: "Connected"` and note the `instanceUrl`.

### Phase 2: Enable Observability

Walk the user through the Setup UI step by step.

**Navigation**: Setup → Quick Find → search **"Einstein au"** → click **"Einstein Audit, Analytics, and Monitoring Setup"** (under "Einstein Generative AI" section in the left nav)

The page shows a list of toggles. Enable them in this order:

1. **Agentforce Session Tracing** (main toggle) — "Capture and store detailed interaction data for all agents. Uses Generative AI to analyze agent sessions. Get a full view of the agent's behavior from start to finish, including reasoning engine executions, actions, prompt and gateway inputs/outputs, error messages, and agent responses. Provisions the analytics semantic model required for Agent Analytics and Agent Optimization."
   
   Sub-toggles (appear after enabling Session Tracing):
   - **Agent Platform Tracing** — "Enable Agent Platform Tracing for all agents and save the data in Data Cloud. This trace data provides deep insights and visibility into every Platform Action, such as Flow and Apex actions."
   - **Agent Optimization** — "Identify gaps in your agent performance and gain actionable insights. Uses generative AI to analyze and categorize user interactions by intent." (Note: this turns on automatically with Session Tracing)
   - **Agent Health Monitoring** — "Track agent performance in near-real time with metrics, reporting, alerts, and trace logs."

2. **Audit and Feedback** — "Collect and store Einstein generative AI audit and feedback data for analysis and reporting."
   
   Sub-toggle:
   - **Knowledge/RAG Quality Data and Metrics** — "Monitor retrievers to track run-time performance, view trends, and identify opportunities to improve results."

**What gets provisioned** (takes 2-5 minutes after toggling):
- 8 Data Cloud DLOs for session tracing:
  - `AiAgentSession__dll` — one row per agent session
  - `AiAgentInteraction__dll` — one row per turn within a session
  - `AiAgentInteractionStep__dll` — one row per action/LLM call (richest table — has input/output payloads)
  - `AiAgentInteractionMessage__dll` — user and agent messages with content
  - `AiAgentSessionParticipant__dll` — who participated (user, agent, subagents)
  - `AiAgentSessionLog__dll` — error/warning logs
  - `AiAgentSessionAttachmentBridge__dll` — file attachments
  - `AiAgentMessageAttachmentBridge__dll` — per-message attachments
- Pre-built Tableau Next workspaces + dashboards:
  - `Service_Agent_Analytics_Workspace` → "Service Agent Analytics" dashboard
  - `Employee_Agent_Analytics_Workspace` → "Employee Agent Analytics" dashboard
- Pre-built SDMs:
  - `Service_Agent_Analytics_SDM_07a` / `Service_Agent_Analytics_Extension_07a`
  - `Employee_Agent_Analytics_SDM_07a` / `Employee_Agent_Analytics_Extension_07a`
  - `sfm_Agentforce_Analytics_Foundations` (shared foundation model)

**Verification** — after 2-3 minutes, confirm provisioning by checking that the data streams exist:
```python
# Via the SF API (or SOQL in dev console)
GET /services/data/v62.0/ssot/data-streams?limit=100
# Look for streams with connector "AIPlatform_AGENT_SESSION_TRACING"
```

Or query the DLO directly:
```sql
SELECT * FROM AiAgentSession__dll LIMIT 1
```
(If this returns 400 "table does not exist", the provisioning hasn't completed yet — wait a few more minutes.)

### Phase 3: Create Service Agent

The Agent API (used by `sf agent preview`) does **NOT** support:
- Agents of type "Agentforce (Default)" (the built-in employee copilot)
- `InternalCopilot` / `Employee` type agents — these don't expose a "Run As User" field in the UI

You MUST create an `ExternalCopilot` / `EinsteinServiceAgent` type agent.

**Steps:**
1. Tell the user: "Open **App Launcher** (9 dots) → search **'Agentforce'** → click **Agentforce**"
2. "Click **+ New Agent**"
3. "Select the **Service Agent** template" — this is the key choice. It creates an agent with:
   - `Type: ExternalCopilot`
   - `AgentType: EinsteinServiceAgent`
   - A visible "Agent User" / "Run As" field in settings
   - Pre-configured actions: QueryRecords, GetRecordDetails, AnswerQuestionsWithKnowledge, UpdateRecordFields, EscalateToHuman, etc.
4. "Name it (e.g. `Agent_test` or `Observability_Demo`)"
5. "Activate it" — the agent needs at least one Active version

**Verification:**
```sql
SELECT Id, DeveloperName, MasterLabel, Type, AgentType, BotUserId 
FROM BotDefinition 
WHERE Type = 'ExternalCopilot'
```
Confirm:
- `Type = 'ExternalCopilot'`
- `AgentType = 'EinsteinServiceAgent'`
- `BotUserId` is NOT null (if null, see Phase 4)

**If the user can't find the Service Agent template**: They may need the Agentforce Service Agent license enabled. Check Setup → Company Information → Permission Set Licenses for "Agentforce Service Agent".

### Phase 4: Create Agent User & Assign to Agent

**Create the user:**
```bash
sf org create agent-user --target-org agentforce-obs
```

This creates a dedicated user (e.g. `agent.user.<hash>@salesforce.com`) with permission sets:
- `AgentforceServiceAgentBase`
- `AgentforceServiceAgentUser`
- `EinsteinGPTPromptTemplateUser`

**Assign to the agent** (if BotUserId was null in Phase 3):

The Service Agent template should auto-assign the agent user during creation. If it didn't:
1. Open the agent in Agentforce Studio
2. Look for **Settings** or the gear icon on the agent
3. Find the **"Agent User"** or **"Run As"** field
4. Set it to the user created above

**IMPORTANT gotcha**: If the user is looking at an Employee/InternalCopilot agent, this setting does NOT exist in the UI. That's why Phase 3 requires creating a Service (ExternalCopilot) agent — only that type exposes the user assignment.

**Verification:**
```sql
SELECT Id, DeveloperName, BotUserId FROM BotDefinition WHERE DeveloperName = '<agent_name>'
```
`BotUserId` must be non-null.

### Phase 5: Configure Connected App (for CLI Agent API access)

The `sf agent preview` commands use a JWT obtained via the `/agentforce/bootstrap/nameduser` endpoint. This requires the org's connected app to have specific scopes.

**IMPORTANT**: You do NOT need to use a custom connected app for the CLI. The default `PlatformCLI` app that `sf org login web` uses works IF the org has the right features enabled. However, if you get `ApiAccessError: Error obtaining API token`, you need to configure scopes on a connected app.

**Steps:**
1. "Go to **Setup → App Manager**"
2. Find the connected app being used (if custom) or create a new one
3. "Edit OAuth Settings and ensure these scopes are present:
   - `Access chatbot services (chatbot_api)` — **required for Agent API**
   - `Access the Salesforce API Platform (sfap_api)` — **required for Agent API**
   - `Manage user data via Web browsers (web)`
   - `Manage user data via APIs (api)`
   - `Perform requests at any time (refresh_token, offline_access)`"
4. "Check **Enable Client Credentials Flow**" (needed for programmatic access without browser)
5. "**Uncheck** 'Require PKCE' if it's checked"
6. "Add `http://localhost:1717/OauthRedirect` to Callback URLs" (only if using this app with `sf org login web --client-id`)
7. "Save"
8. "Click **Manage** → **Edit Policies**"
9. "Under 'Client Credentials Flow', set the **Run As** user to your admin user"
10. "Save. Changes take 2-5 minutes to propagate."

**These changes do NOT break existing auth flows** — adding scopes and enabling client credentials is purely additive. Existing refresh tokens continue working.

### Phase 6: Test Agent API Connection

**Re-authenticate after scope changes** (the CLI needs to pick up the new scopes):
```bash
sf org login web --instance-url https://<my-domain>.my.salesforce.com --alias agentforce-obs --set-default
```

**Start a test session:**
```bash
sf agent preview start --api-name <AgentDeveloperName> --target-org agentforce-obs --json
```

Expected success response:
```json
{"status": 0, "result": {"sessionId": "019f18c3-...", "agentApiName": "Agent_test"}}
```

**Send a test message:**
```bash
sf agent preview send --api-name <AgentDeveloperName> --session-id <sessionId> --utterance "Hello, what can you help me with?" --target-org agentforce-obs --json
```

Expected success response:
```json
{"status": 0, "result": {"messages": [{"type": "Inform", "message": "..."}], "sessionId": "..."}}
```

**End the test session:**
```bash
sf agent preview end --session-id <sessionId> --api-name <AgentDeveloperName> --target-org agentforce-obs
```

**Common errors and fixes:**

| Error | Cause | Fix |
|-------|-------|-----|
| `"Invalid user ID provided on start session: "` | Agent's `BotUserId` is null | Assign the Agent User to the agent in Agentforce Studio (Phase 4) |
| `"ApiAccessError: Error obtaining API token: invalid or missing access token"` | CLI can't get JWT from bootstrap endpoint | Re-authenticate with `sf org login web` (browser flow). Check that connected app has `chatbot_api` + `sfap_api` scopes. |
| `"Agent not found"` or exit code 2 | Agent isn't activated or DeveloperName is wrong | Activate the agent in Agentforce Studio. Check DeveloperName with SOQL on BotDefinition. |
| `"redirect_uri_mismatch"` during web login | Custom connected app missing localhost callback | Add `http://localhost:1717/OauthRedirect` to the app's callback URLs, or don't pass `--client-id` (use default PlatformCLI). |
| `"RequiresProjectError"` | CLI needs a project context | Create a minimal `sfdx-project.json`: `{"packageDirectories": [{"path": "force-app", "default": true}], "sourceApiVersion": "66.0"}` and `mkdir force-app` |

### Phase 7: Generate Sessions

Now generate a diverse set of sessions to populate all dashboard metrics. Use the `generate_sessions.py` script in this project:

```bash
python generate_sessions.py --agent <AgentDeveloperName> --org agentforce-obs --count 50
```

This creates sessions in four categories:
- **Escalation** (25%): "Transfer me to a human", "I want to speak to a manager" — triggers the agent's escalation routing
- **Deflection** (25%): Simple questions the agent answers, user says "thanks" — counts as successfully self-served
- **General** (40%): Billing, technical, account management prompts that exercise various actions
- **Abandonment** (10%): User sends one message then disappears — no session end

**Key behaviors:**
- Escalation sessions are NOT ended programmatically — the agent's own routing completes the handoff (sets proper `sessionEndType`)
- Deflection sessions ARE ended after the user says thanks
- Abandonment sessions are NEVER ended — simulates user leaving
- 1-3 second delay between messages, 3 seconds between sessions
- Timeout handling ensures one bad session doesn't kill the batch

**Expected runtime**: ~15-20 minutes for 50 sessions.

**Manual alternative** (if CLI isn't working): Run prompts manually through the Agentforce panel in Lightning. Click the Agentforce icon in the utility bar, type messages. Each conversation = one traced session.

### Phase 8: Verify Dashboard Population

After session generation, wait **10-15 minutes** for the Data Cloud pipeline to sync.

**Check DLO row counts:**
```sql
SELECT COUNT(*) FROM AiAgentSession__dll
SELECT COUNT(*) FROM AiAgentInteraction__dll
SELECT COUNT(*) FROM AiAgentInteractionStep__dll
SELECT COUNT(*) FROM AiAgentInteractionMessage__dll
```

**Expected data volume for 50 sessions:**
- Sessions: 50+
- Interactions: 150-200 (multiple turns per session)
- Steps: 400-600 (multiple LLM + action steps per turn)
- Messages: 200-300 (user + agent messages)

**Check the dashboards:**
- Navigate to **Data 360** (App Launcher → Data 360 or Tableau)
- Open **Service Agent Analytics Workspace** → **Service Agent Analytics** dashboard
- Or **Employee Agent Analytics Workspace** → **Employee Agent Analytics** dashboard

**What should populate vs. what will remain zero:**

| Metric | Expected Status | Notes |
|--------|----------------|-------|
| Unique Sessions | ✓ Populated | Any session counts |
| Unique Interactions | ✓ Populated | Every turn counts |
| Engagement Rate | ✓ Populated | Sessions with at least 1 user message |
| Escalation Rate | ✓ Populated | Sessions where agent responded with Escalate type |
| Deflection Rate | ✓ Populated | Sessions resolved without escalation |
| Abandon Rate | ⚠️ May be zero | Depends on how `sessionEndType` gets set for abandoned sessions |
| Action Usage | ✓ Populated | ACTION_STEP entries (QueryRecords, GetRecordDetails, etc.) |
| Subagent/Topic Insights | ✓ Populated | Topic classification data |
| Error Rate | ⚠️ Likely zero | Only if actual errors occur (uncommon in normal prompts) |
| Quality Score / Trust | ⚠️ Zero until Audit provisions | `Ai_Feedback` DMO takes hours/days to provision after enabling |
| RAG Metrics | ⚠️ Zero unless Knowledge used | Agent must invoke AnswerQuestionsWithKnowledge with a configured Knowledge base |
| Token/Credit Cost | ✗ Zero (SDO/trial orgs) | `TenantConsumptionInsights` only populates with paid Agentforce credit billing |
| Voice Interruption Rate | ✗ Zero | Only for voice-channel deployments |
| Session Duration | ✓ Populated | Calculated from start/end timestamps |

### Phase 9: Schedule Recurring Session Generation

Ask the user: "How long would you like to generate daily sessions to build up dashboard history?"

Options:
- **7 days** — Quick test, enough for basic trends
- **14 days** — Good for a demo with 2 weeks of history
- **30 days** — Full month, solid trend data
- **60 days** — Rich history for time-over-time comparisons
- **90 days** — Maximum depth, great for quarterly views
- **Perpetually** — Runs indefinitely until manually stopped

Also ask: "How many sessions per day?" (default: 20, range: 10-50)

**Implementation — macOS launchd (persistent, survives restarts):**

Create a plist at `~/Library/LaunchAgents/com.agentforce.observability.sessions.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.agentforce.observability.sessions</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Library/Frameworks/Python.framework/Versions/3.12/bin/python3</string>
        <string>{path_to_project}/generate_sessions.py</string>
        <string>--agent</string>
        <string>{agent_developer_name}</string>
        <string>--org</string>
        <string>{org_alias}</string>
        <string>--count</string>
        <string>{daily_count}</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>17</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>{path_to_project}/logs/sessions.log</string>
    <key>StandardErrorPath</key>
    <string>{path_to_project}/logs/sessions.err</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/Library/Frameworks/Python.framework/Versions/3.12/bin</string>
    </dict>
</dict>
</plist>
```

Load it: `launchctl load ~/Library/LaunchAgents/com.agentforce.observability.sessions.plist`

For non-perpetual durations, tell the user to unload after the period expires:
`launchctl unload ~/Library/LaunchAgents/com.agentforce.observability.sessions.plist && rm ~/Library/LaunchAgents/com.agentforce.observability.sessions.plist`

**Stopping the schedule at any time:**
- Unload: `launchctl unload ~/Library/LaunchAgents/com.agentforce.observability.sessions.plist`
- Remove: `rm ~/Library/LaunchAgents/com.agentforce.observability.sessions.plist`
- Check logs: `cat {path_to_project}/logs/sessions.log | tail -20`

**Verification:** After the first scheduled run, check:
```bash
tail -5 {path_to_project}/logs/sessions.log
```
Should show "Complete: N/N sessions successful"

**Note:** The SF CLI auth token expires periodically. If sessions start failing, the user needs to re-authenticate: `sf org login web --instance-url <url> --alias <alias>`. Consider reminding the user of this when setting up long schedules (60/90 days).

## Troubleshooting

### "Observability DLOs never appeared"
- Confirm Session Tracing is toggled ON (Setup → Einstein Audit, Analytics, and Monitoring Setup)
- Check that Data Cloud is enabled: Setup → Data Cloud Setup should show active state
- Wait up to 10 minutes — initial provisioning can be slow

### "Sessions are created but DLOs stay empty"
- The sync pipeline has a 10-15 minute lag
- Check `ConversationDefinitionEventLog` first — if this has rows but DLOs don't, the pipeline is just behind
- If EventLog is also empty, Session Tracing event logging may not be enabled on the specific agent

### "Dashboard shows zero for everything"
- Check the dashboard's SDM data objects — some may be `unmapped: true` (no backing DLO)
- The pre-built dashboards use `Service_Agent_Analytics_Extension_07a` SDM — verify it has data objects with data
- Some metrics require trust data (`Ai_Feedback`) which provisions separately and slowly

### "Trust metrics (Quality Score, etc.) are zero"
- Audit & Feedback toggle provisions `Ai_Feedback` / `GenAiResponseGeneration` DMOs
- These can take **hours** to fully provision and start receiving data
- The OTel API will return `"table GenAIFeedback__dlm does not exist"` until provisioning completes
- No workaround — just wait

### "Token/Credit data is zero"
- `TenantConsumptionInsights` only populates on orgs with **paid Agentforce credit metering**
- SDO, trial, and developer orgs don't meter credits the same way
- The `Total_Flex_Credits_clc` metric formula references this table — it will show 0 until real billing flows
- Workaround for demos: use `AiAgentInteractionStep` duration as a proxy for cost
