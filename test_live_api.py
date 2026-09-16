r"""SPEC acceptance scenario 1 over real HTTP, using the server's database.

Run against an already running relay (PowerShell):
    $env:RELAY_TEST_BASE_URL = 'http://127.0.0.1:8000'
    .venv\Scripts\python.exe -m pytest -q -s test_live_api.py

Each run creates unique agents and leaves its completed task for inspection.
No existing records are changed or deleted. The API has no deletion endpoint.
Set RELAY_TEST_PRINT_TOKEN=1 to print the sender token for the local dashboard.
Without RELAY_TEST_BASE_URL this optional live test is skipped.
"""

import os
import uuid

import httpx
import pytest


def test_sender_reads_completed_result():
    base_url = os.getenv("RELAY_TEST_BASE_URL")
    if not base_url:
        pytest.skip("Set RELAY_TEST_BASE_URL to test a running relay")

    run_id = uuid.uuid4().hex
    sender_name = f"q2-sender-{run_id}"
    recipient_name = f"q2-recipient-{run_id}"
    enrollment = os.getenv("RELAY_ENROLLMENT_SECRET")
    registration_headers = {"X-Enrollment-Secret": enrollment} if enrollment else {}

    with httpx.Client(base_url=base_url, timeout=10, trust_env=False) as client:
        def register(name):
            response = client.post(
                "/api/v1/agents", json={"name": name}, headers=registration_headers
            )
            assert response.status_code == 201
            agent = response.json()
            return agent, {"Authorization": f"Bearer {agent['token']}"}

        sender, sender_headers = register(sender_name)
        recipient, recipient_headers = register(recipient_name)
        print(f"Sender: {sender_name} / {sender['agent_id']}")
        print(f"Recipient: {recipient_name} / {recipient['agent_id']}")

        created = client.post(
            "/api/v1/tasks",
            headers={**sender_headers, "Idempotency-Key": run_id},
            json={"to": recipient["agent_id"], "input": "hello relay"},
        )
        assert created.status_code == 201
        task_id = created.json()["task_id"]
        assert created.json()["status"] == "queued"
        print(f"Task ID: {task_id}")
        print(f"Status after creation: {created.json()['status']}")

        claimed = client.post(
            "/api/v1/tasks/claim",
            headers=recipient_headers,
            json={"worker_id": f"q2-{run_id}", "wait_seconds": 0},
        )
        assert claimed.status_code == 200
        claim = claimed.json()
        assert claim["task_id"] == task_id
        assert claim["from"] == sender["agent_id"]
        assert claim["input"] == "hello relay"
        assert claim["attempt"] == 1

        processing = client.get(f"/api/v1/tasks/{task_id}", headers=sender_headers)
        assert processing.status_code == 200
        assert processing.json()["status"] == "processing"
        print(f"Status after claim: {processing.json()['status']}")

        completed = client.post(
            f"/api/v1/tasks/{task_id}/complete",
            headers=recipient_headers,
            json={"claim_token": claim["claim_token"], "output": "HELLO RELAY"},
        )
        assert completed.status_code == 200
        assert completed.json() == {"task_id": task_id, "status": "completed"}
        print(f"Status after result submission: {completed.json()['status']}")

        retrieved = client.get(f"/api/v1/tasks/{task_id}", headers=sender_headers)
        assert retrieved.status_code == 200
        task = retrieved.json()
        assert task["task_id"] == task_id
        assert task["from"] == sender["agent_id"]
        assert task["to"] == recipient["agent_id"]
        assert task["status"] == "completed"
        assert task["output"] == "HELLO RELAY"
        assert task["error"] is None
        assert task["attempt_count"] == 1
        assert task["finished_at"] is not None
        print(f"Final status seen by sender: {task['status']}")
        if os.getenv("RELAY_TEST_PRINT_TOKEN") == "1":
            print(f"Dashboard sender token: {sender['token']}")
