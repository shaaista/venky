import io
import json
from dataclasses import dataclass

from main import app


@dataclass
class CheckResult:
    name: str
    status: str
    detail: dict


BLOCKER_MARKERS = (
    "invalid_grant",
    "Missing Google credentials",
    "TAVILY_API_KEY is missing",
    "LLM_API_KEY is missing",
)


def classify_payload(name, response, payload, success_titles=None, blocked_titles=None):
    if response.status_code >= 500:
        return CheckResult(name, "fail", {"status": response.status_code, "payload": payload})

    title = payload.get("response", {}).get("title", "")
    text = payload.get("response", {}).get("text", "")

    if payload.get("ok") is True:
        return CheckResult(name, "pass", {"status": response.status_code, "payload": payload})

    if any(marker in text for marker in BLOCKER_MARKERS) or title in (blocked_titles or set()):
        return CheckResult(name, "blocked", {"status": response.status_code, "payload": payload})

    if success_titles and title in success_titles:
        return CheckResult(name, "pass", {"status": response.status_code, "payload": payload})

    return CheckResult(name, "fail", {"status": response.status_code, "payload": payload})


def main():
    client = app.test_client()
    results = []

    response = client.get("/api/health")
    payload = response.get_json()
    results.append(
        CheckResult(
            "health",
            "pass" if response.status_code == 200 and payload.get("ok") else "fail",
            {"status": response.status_code, "payload": payload},
        )
    )

    response = client.get("/")
    body = response.get_data(as_text=True)
    page_ok = (
        response.status_code == 200
        and "AutoPilot AI" in body
        and 'id="voice-button"' in body
        and 'id="theme-toggle"' in body
    )
    results.append(CheckResult("index", "pass" if page_ok else "fail", {"status": response.status_code}))

    response = client.post("/api/command", json={"message": "hello there"})
    payload = response.get_json()
    greeting_ok = (
        payload.get("ok") is True
        and payload.get("response", {}).get("meta", {}).get("intent") in ("greeting", "general_chat")
    )
    results.append(
        CheckResult(
            "command_greeting_chat",
            "pass" if greeting_ok else "fail",
            {"status": response.status_code, "payload": payload},
        )
    )

    response = client.post("/api/command", json={"message": "remind me tomorrow at 8pm to call the client"})
    payload = response.get_json()
    reminder_text = payload.get("response", {}).get("text", "")
    reminder_ok = (
        payload.get("response", {}).get("meta", {}).get("intent") == "set_reminder"
        and "Invalid reminder time" != payload.get("response", {}).get("title")
    )
    reminder_status = "pass" if payload.get("ok") and reminder_ok else None
    if reminder_status is None:
        if reminder_ok and any(marker in reminder_text for marker in BLOCKER_MARKERS):
            reminder_status = "blocked"
        else:
            reminder_status = "fail"
    results.append(
        CheckResult(
            "command_reminder_parse",
            reminder_status,
            {"status": response.status_code, "payload": payload},
        )
    )

    response = client.post(
        "/api/attachment/summarize",
        data={
            "file": (
                io.BytesIO(
                    b"This is a test document. Deadline tomorrow. Please confirm the budget and send the final note."
                ),
                "test.txt",
            )
        },
        content_type="multipart/form-data",
    )
    payload = response.get_json()
    attachment_ok = (
        payload.get("ok") is True
        and payload.get("response", {}).get("title") == "Attachment summary"
    )
    results.append(
        CheckResult(
            "attachment_summary",
            "pass" if attachment_ok else "fail",
            {"status": response.status_code, "payload": payload},
        )
    )

    response = client.post("/api/research", json={"topic": "What is retrieval augmented generation?"})
    payload = response.get_json()
    results.append(classify_payload("research", response, payload))

    response = client.get("/api/mail/summary")
    payload = response.get_json()
    results.append(classify_payload("mail_summary", response, payload))

    response = client.post(
        "/api/email/send",
        json={
            "recipient": "example@example.com",
            "subject": "Test",
            "message": "Please confirm receipt.",
        },
    )
    payload = response.get_json()
    results.append(classify_payload("email_send", response, payload))

    response = client.post(
        "/api/reminder/create",
        json={
            "title": "Test reminder",
            "when": "tomorrow 6pm",
            "description": "Smoke test",
            "duration_minutes": 30,
        },
    )
    payload = response.get_json()
    results.append(classify_payload("reminder_create", response, payload))

    trace_id = None
    for result in results:
        payload = result.detail.get("payload") or {}
        trace_id = trace_id or payload.get("response", {}).get("meta", {}).get("trace_id")

    if trace_id:
        response = client.post(
            "/api/feedback",
            json={"trace_id": trace_id, "reward": 1, "label": "positive"},
        )
        payload = response.get_json()
        status = "pass" if response.status_code == 200 and payload.get("ok") else "fail"
        results.append(CheckResult("feedback", status, {"status": response.status_code, "payload": payload}))
    else:
        results.append(CheckResult("feedback", "fail", {"reason": "No trace_id available from earlier checks"}))

    response = client.get("/api/learning/status")
    payload = response.get_json()
    status = "pass" if response.status_code == 200 and payload.get("ok") else "fail"
    results.append(CheckResult("learning_status", status, {"status": response.status_code, "payload": payload}))

    summary = {
        "pass": sum(1 for result in results if result.status == "pass"),
        "blocked": sum(1 for result in results if result.status == "blocked"),
        "fail": sum(1 for result in results if result.status == "fail"),
    }

    print(json.dumps([result.__dict__ for result in results], indent=2))
    print(json.dumps(summary, indent=2))

    raise SystemExit(1 if summary["fail"] else 0)


if __name__ == "__main__":
    main()
