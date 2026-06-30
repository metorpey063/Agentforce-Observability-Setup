"""
Agentforce Session Generator
Generates real agent sessions via the SF CLI to populate Agent Analytics dashboards.

Usage:
    python generate_sessions.py --agent Agent_test --org agentforce-obs --count 30

Requires:
    - Salesforce CLI v2.140+ (sf)
    - Org authenticated: sf org login web --instance-url <url> --alias <alias>
    - Agent created and activated (ExternalCopilot type with BotUserId set)
"""

import subprocess
import json
import time
import argparse
import random
import sys


# --- Prompt Libraries ---

ESCALATION_PROMPTS = [
    ["I need to speak to a real person", "I dont want to talk to a bot", "Transfer me to a human agent now"],
    ["This is unacceptable, get me a supervisor", "I want to file a formal complaint with a manager"],
    ["Connect me to a live agent please", "I have a complex issue only a human can solve"],
    ["I want to talk to someone in billing", "A real person, not an AI"],
    ["Transfer me to support", "I need human assistance immediately"],
    ["Let me speak to an agent", "This is urgent and I need a person"],
    ["I refuse to deal with a chatbot", "Get me a human right now"],
    ["Escalate this to a manager", "I have been trying to resolve this for weeks"],
    ["I need to speak with someone who can authorize a refund", "Only a manager can help"],
    ["Please transfer me", "I want a live representative"],
]

DEFLECTION_PROMPTS = [
    ["What are your business hours?", "Thanks that answers my question"],
    ["How do I reset my password?", "Got it, I will try that now. Thank you"],
    ["What is your shipping policy?", "Perfect, that helps. Goodbye"],
    ["Do you offer student discounts?", "Great, I will apply with that code. Thanks"],
    ["How do I update my email address?", "I found the setting. All done thank you"],
    ["What file formats do you support?", "OK that is what I needed to know"],
    ["Where can I download my invoice?", "Found it. Thanks for the help"],
    ["What are the system requirements?", "My system meets those. Thank you"],
    ["How do I cancel auto-renewal?", "Done. Thanks for the quick answer"],
    ["What payment methods do you accept?", "Perfect, I will use that option"],
]

GENERAL_PROMPTS = [
    ["What are my open cases?", "Show me the details on the most recent one", "Can you escalate that case?"],
    ["I need help with a billing issue", "I was overcharged by 50 dollars", "Please issue a credit"],
    ["I want to check my order status", "Order number is ORD-98765", "When will it ship?"],
    ["I have a technical issue", "My device wont turn on after the update", "Walk me through a reset"],
    ["I want to cancel my subscription", "I no longer need the premium tier", "What are the fees?"],
    ["Help me update my address", "My new address is 123 Main St Denver CO", "Confirm the change"],
    ["I received the wrong item", "I ordered blue but got red", "How do I exchange it?"],
    ["My payment failed", "Card ending in 4242", "Can you retry the charge?"],
    ["I need a copy of my invoice", "For the month of May", "Can you email it to me?"],
    ["Whats the status of my support ticket?", "Ticket TKT-5567", "Its been 3 days with no update"],
    ["I want to upgrade my plan", "What are the enterprise options?", "How does pricing compare?"],
    ["I need to dispute a charge", "The charge on June 15 for 199 dollars", "I never authorized it"],
    ["Can you help me reset my password?", "My email is user@company.com"],
    ["Schedule a callback for me", "Tomorrow morning works best", "Between 9 and 11 AM"],
    ["My delivery was damaged", "The package was crushed", "I want a full refund"],
    ["I want to close my account", "Yes I am sure", "Please confirm deletion"],
    ["Can you check if there are outages?", "The west coast region seems slow"],
    ["I need to transfer my license", "To a different team member"],
    ["What training resources are available?", "Do you have video tutorials?"],
    ["I want to bulk import contacts", "I have a CSV with 500 records", "What format do you accept?"],
]

ABANDONMENT_PROMPTS = [
    ["I have a problem with my account"],
    ["Hello, I need help"],
    ["Can someone help me with an order issue?"],
    ["I want to check something"],
    ["Is anyone there?"],
]


def run_cmd(args, timeout=90):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"


def start_session(agent, org):
    code, out, err = run_cmd(
        ["sf", "agent", "preview", "start", "--api-name", agent, "--target-org", org, "--json"],
        timeout=30
    )
    if code == 0:
        return json.loads(out)["result"]["sessionId"]
    return None


def send_message(agent, org, session_id, utterance):
    code, out, err = run_cmd(
        ["sf", "agent", "preview", "send",
         "--api-name", agent,
         "--session-id", session_id,
         "--utterance", utterance,
         "--target-org", org,
         "--json"],
        timeout=90
    )
    if code == 0:
        data = json.loads(out)
        messages = data.get("result", {}).get("messages", [])
        is_escalate = any(m.get("type") == "Escalate" for m in messages)
        return True, is_escalate
    return False, False


def end_session(agent, org, session_id):
    try:
        subprocess.run(
            ["sf", "agent", "preview", "end",
             "--session-id", session_id,
             "--api-name", agent,
             "--target-org", org],
            capture_output=True, timeout=30
        )
    except subprocess.TimeoutExpired:
        pass


def generate_sessions(agent, org, count=30, escalation_pct=0.25, deflection_pct=0.25, abandon_pct=0.10):
    n_escalation = max(1, int(count * escalation_pct))
    n_deflection = max(1, int(count * deflection_pct))
    n_abandon = max(1, int(count * abandon_pct))
    n_general = count - n_escalation - n_deflection - n_abandon

    print(f"Generating {count} sessions:")
    print(f"  {n_escalation} escalation, {n_deflection} deflection, {n_abandon} abandonment, {n_general} general")
    print()

    successful = 0
    failed = 0

    # Escalation sessions
    print("=== ESCALATION SESSIONS ===")
    for i in range(n_escalation):
        prompts = random.choice(ESCALATION_PROMPTS)
        print(f"  {i+1}/{n_escalation}...", end=" ", flush=True)

        session_id = start_session(agent, org)
        if not session_id:
            print("FAILED to start")
            failed += 1
            time.sleep(3)
            continue

        msg_count = 0
        got_escalate = False
        for prompt in prompts:
            ok, escalated = send_message(agent, org, session_id, prompt)
            if ok:
                msg_count += 1
            if escalated:
                got_escalate = True
                break
            time.sleep(1)

        if not got_escalate:
            time.sleep(5)
            end_session(agent, org, session_id)
        else:
            time.sleep(10)

        successful += 1
        label = " [ESCALATED]" if got_escalate else ""
        print(f"OK ({msg_count} msgs){label}")
        time.sleep(3)

    # Deflection sessions
    print("\n=== DEFLECTION SESSIONS ===")
    for i in range(n_deflection):
        prompts = random.choice(DEFLECTION_PROMPTS)
        print(f"  {i+1}/{n_deflection}...", end=" ", flush=True)

        session_id = start_session(agent, org)
        if not session_id:
            print("FAILED to start")
            failed += 1
            time.sleep(3)
            continue

        msg_count = 0
        for prompt in prompts:
            ok, _ = send_message(agent, org, session_id, prompt)
            if ok:
                msg_count += 1
            time.sleep(1)

        time.sleep(3)
        end_session(agent, org, session_id)
        successful += 1
        print(f"OK ({msg_count} msgs)")
        time.sleep(3)

    # General sessions
    print("\n=== GENERAL SESSIONS ===")
    for i in range(n_general):
        prompts = random.choice(GENERAL_PROMPTS)
        print(f"  {i+1}/{n_general}...", end=" ", flush=True)

        session_id = start_session(agent, org)
        if not session_id:
            print("FAILED to start")
            failed += 1
            time.sleep(3)
            continue

        msg_count = 0
        for prompt in prompts:
            ok, escalated = send_message(agent, org, session_id, prompt)
            if ok:
                msg_count += 1
            if escalated:
                time.sleep(10)
                break
            time.sleep(1)
        else:
            time.sleep(3)
            end_session(agent, org, session_id)

        successful += 1
        print(f"OK ({msg_count} msgs)")
        time.sleep(3)

    # Abandonment sessions
    print("\n=== ABANDONMENT SESSIONS ===")
    for i in range(n_abandon):
        prompts = random.choice(ABANDONMENT_PROMPTS)
        print(f"  {i+1}/{n_abandon}...", end=" ", flush=True)

        session_id = start_session(agent, org)
        if not session_id:
            print("FAILED to start")
            failed += 1
            time.sleep(3)
            continue

        send_message(agent, org, session_id, prompts[0])
        # DO NOT end session - simulate abandonment
        successful += 1
        print("OK (abandoned)")
        time.sleep(3)

    print(f"\n{'='*50}")
    print(f"Complete: {successful}/{count} sessions successful, {failed} failed")
    print(f"Wait 10-15 minutes for Data Cloud to sync, then check your dashboards.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Agentforce sessions for observability")
    parser.add_argument("--agent", required=True, help="Agent DeveloperName (e.g. Agent_test)")
    parser.add_argument("--org", required=True, help="SF CLI org alias (e.g. agentforce-obs)")
    parser.add_argument("--count", type=int, default=30, help="Total sessions to generate (default: 30)")
    parser.add_argument("--escalation-pct", type=float, default=0.25, help="Fraction of escalation sessions")
    parser.add_argument("--deflection-pct", type=float, default=0.25, help="Fraction of deflection sessions")
    parser.add_argument("--abandon-pct", type=float, default=0.10, help="Fraction of abandonment sessions")

    args = parser.parse_args()
    generate_sessions(
        agent=args.agent,
        org=args.org,
        count=args.count,
        escalation_pct=args.escalation_pct,
        deflection_pct=args.deflection_pct,
        abandon_pct=args.abandon_pct,
    )
