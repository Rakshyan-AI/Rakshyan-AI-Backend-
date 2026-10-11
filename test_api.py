import asyncio
import sys

if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.agents.supervisor_agent import SupervisorAgent

def test_supervisor():
    print("[*] Testing Multi-Agent Safety Engine...")
    supervisor = SupervisorAgent()

    test_cases = [
        "Hey! Are you ready for school tomorrow?",
        "You are so stupid and ugly, nobody likes you. Go die.",
        "Don't tell your mom about our chats. You are so mature for your age, send me a private photo.",
        "Teri photo viral kar dunga, chup chaap paise de varna dekh lena."
    ]

    for sentence in test_cases:
        res = supervisor.evaluate(sentence)
        print(f"\n--- Sentence: \"{sentence}\" ---")
        print(f"Risk Score: {res.overall_risk_score} / 100")
        print(f"Severity:   {res.severity}")
        print(f"Category:   {res.category}")
        print(f"Alerted:    {res.alert_triggered}")
        print(f"Reason:     {res.detected_reason}")

if __name__ == "__main__":
    test_supervisor()
