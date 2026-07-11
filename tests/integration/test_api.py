import uuid
import pytest
from httpx import AsyncClient
from app.core.config import settings

@pytest.mark.asyncio
async def test_create_and_list_templates(client: AsyncClient) -> None:
    # 1. Create a template
    payload = {
        "name": "welcome_email",
        "subject": "Welcome {{name}}!",
        "content": "Hello {{name}}, welcome to {{site}}!"
    }
    resp = await client.post("/templates", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "welcome_email"
    assert "id" in data

    # 2. List templates
    resp_list = await client.get("/templates")
    assert resp_list.status_code == 200
    templates = resp_list.json()
    assert len(templates) >= 1
    assert any(t["name"] == "welcome_email" for t in templates)

@pytest.mark.asyncio
async def test_send_notification_happy_path(client: AsyncClient) -> None:
    # Seed template
    await client.post("/templates", json={
        "name": "otp",
        "subject": "Your Code",
        "content": "Your code is {{code}}"
    })

    payload = {
        "userId": "user_happy",
        "templateName": "otp",
        "variables": {"code": "555666"},
        "channels": ["EMAIL"],
        "priority": "HIGH"
    }
    resp = await client.post("/notifications", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["userId"] == "user_happy"
    assert len(data["deliveries"]) == 1
    assert data["deliveries"][0]["channel"] == "EMAIL"
    assert data["deliveries"][0]["status"] == "PENDING"

    # Get status of the notification
    notif_id = data["id"]
    status_resp = await client.get(f"/notifications/{notif_id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["id"] == notif_id

@pytest.mark.asyncio
async def test_send_notification_missing_template(client: AsyncClient) -> None:
    payload = {
        "userId": "user_test",
        "templateName": "nonexistent_template",
        "variables": {},
        "channels": ["EMAIL"]
    }
    resp = await client.post("/notifications", json=payload)
    assert resp.status_code == 400
    assert "Template 'nonexistent_template' not found" in resp.json()["error"]["message"]

@pytest.mark.asyncio
async def test_send_notification_missing_variable(client: AsyncClient) -> None:
    await client.post("/templates", json={
        "name": "alert",
        "subject": "Alert",
        "content": "Alert: {{msg}}"
    })

    payload = {
        "userId": "user_test",
        "templateName": "alert",
        "variables": {},  # missing variable 'msg'
        "channels": ["EMAIL"]
    }
    resp = await client.post("/notifications", json=payload)
    assert resp.status_code == 400
    assert "Missing required template variables" in resp.json()["error"]["message"]

@pytest.mark.asyncio
async def test_send_notification_invalid_channel(client: AsyncClient) -> None:
    payload = {
        "userId": "user_test",
        "templateName": "otp",
        "variables": {"code": "123"},
        "channels": ["INVALID_CHANNEL"]
    }
    resp = await client.post("/notifications", json=payload)
    # Pydantic validation error maps to 400 Bad Request
    assert resp.status_code == 400
    assert "validation failed" in resp.json()["error"]["message"].lower()

@pytest.mark.asyncio
async def test_preferences_endpoints_and_opt_out(client: AsyncClient) -> None:
    # 1. Get default preferences (which defaults to all channels opted-in)
    resp = await client.get("/users/user_pref_test/preferences")
    assert resp.status_code == 200
    assert resp.json()["emailEnabled"] is True

    # 2. Set preferences (opt out of EMAIL)
    pref_payload = {
        "emailEnabled": False,
        "smsEnabled": True,
        "pushEnabled": True
    }
    set_resp = await client.post("/users/user_pref_test/preferences", json=pref_payload)
    assert set_resp.status_code == 200
    assert set_resp.json()["emailEnabled"] is False

    # Seed template
    await client.post("/templates", json={
        "name": "pref_test_template",
        "content": "Hello"
    })

    # 3. Send notification targeting EMAIL
    payload = {
        "userId": "user_pref_test",
        "templateName": "pref_test_template",
        "variables": {},
        "channels": ["EMAIL"]
    }
    resp = await client.post("/notifications", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    # Email is filtered out and skipped => deliveries list should be empty
    assert len(data["deliveries"]) == 0

@pytest.mark.asyncio
async def test_idempotency_headers(client: AsyncClient) -> None:
    await client.post("/templates", json={
        "name": "idemp_tmpl",
        "content": "Hello"
    })

    payload = {
        "userId": "user_idemp",
        "templateName": "idemp_tmpl",
        "variables": {}
    }
    headers = {"x-idempotency-key": "test-idemp-key-1"}

    # First request
    resp1 = await client.post("/notifications", json=payload, headers=headers)
    assert resp1.status_code == 201
    data1 = resp1.json()

    # Duplicate request (same payload) -> Returns same cached response body
    resp2 = await client.post("/notifications", json=payload, headers=headers)
    assert resp2.status_code == 201
    assert resp2.json()["id"] == data1["id"]

    # Duplicate key with a different payload -> 409 Conflict
    diff_payload = {
        "userId": "user_idemp_different",
        "templateName": "idemp_tmpl",
        "variables": {}
    }
    resp3 = await client.post("/notifications", json=diff_payload, headers=headers)
    assert resp3.status_code == 409
    assert "associated with a different payload" in resp3.json()["error"]["message"]

@pytest.mark.asyncio
async def test_rate_limiting_api(client: AsyncClient) -> None:
    original_limit = settings.RATE_LIMIT_MAX_REQUESTS
    settings.RATE_LIMIT_MAX_REQUESTS = 2
    try:
        await client.post("/templates", json={
            "name": "rate_tmpl",
            "content": "Hello"
        })

        payload = {
            "userId": "user_rate",
            "templateName": "rate_tmpl",
            "variables": {}
        }

        # Request 1 & 2 succeed
        r1 = await client.post("/notifications", json=payload)
        assert r1.status_code == 201

        r2 = await client.post("/notifications", json=payload)
        assert r2.status_code == 201

        # Request 3 is blocked
        r3 = await client.post("/notifications", json=payload)
        assert r3.status_code == 429
        assert "Retry-After" in r3.headers
    finally:
        settings.RATE_LIMIT_MAX_REQUESTS = original_limit

@pytest.mark.asyncio
async def test_notification_not_found(client: AsyncClient) -> None:
    random_uuid = str(uuid.uuid4())
    resp = await client.get(f"/notifications/{random_uuid}")
    assert resp.status_code == 404
    assert "not found" in resp.json()["error"]["message"].lower()

@pytest.mark.asyncio
async def test_get_history_endpoint(client: AsyncClient) -> None:
    # Seed template
    await client.post("/templates", json={
        "name": "history_tmpl",
        "content": "History test content"
    })

    # Send a notification
    await client.post("/notifications", json={
        "userId": "user_happy",
        "templateName": "history_tmpl",
        "variables": {},
        "channels": ["EMAIL"]
    })

    # Fetch paginated notification history
    resp = await client.get("/users/user_happy/notifications?limit=5&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
