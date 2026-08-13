from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from calendar_app import create_app


ALICE = {"Authorization": "Bearer demo-token-alice"}
BOB = {"Authorization": "Bearer demo-token-bob"}
EVENT = {"title": "Review", "description": "V2", "location": "Berlin", "start": "2026-08-10T09:00:00Z", "end": "2026-08-10T10:00:00Z"}


@pytest.fixture()
def client():
    with TestClient(create_app("sqlite://")) as value:
        yield value


def test_event_crud_for_owner(client: TestClient):
    created = client.post("/events", headers=ALICE, json=EVENT)
    assert created.status_code == 201
    event = created.json()
    assert set(event) == {"id", "owner_id", "title", "description", "location", "start", "end"}
    assert event["location"] == "Berlin"

    read = client.get(f"/events/{event['id']}", headers=ALICE)
    assert read.status_code == 200
    assert read.json() == event

    updated = client.put(f"/events/{event['id']}", headers=ALICE, json={**EVENT, "title": "Updated"})
    assert updated.status_code == 200
    assert updated.json()["title"] == "Updated"

    deleted = client.delete(f"/events/{event['id']}", headers=ALICE)
    assert deleted.status_code == 204
    assert client.get(f"/events/{event['id']}", headers=ALICE).status_code == 404


@pytest.mark.parametrize("method", ["post", "get", "put", "delete"])
def test_all_endpoints_require_authentication(client: TestClient, method: str):
    url = "/events" if method == "post" else "/events/00000000-0000-0000-0000-000000000000"
    kwargs = {"json": EVENT} if method in {"post", "put"} else {}
    assert getattr(client, method)(url, **kwargs).status_code == 401


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_foreign_event_is_hidden(client: TestClient, method: str):
    event = client.post("/events", headers=ALICE, json=EVENT).json()
    kwargs = {"json": EVENT} if method == "put" else {}
    assert getattr(client, method)(f"/events/{event['id']}", headers=BOB, **kwargs).status_code == 404


def test_invalid_time_interval_is_rejected(client: TestClient):
    invalid = {**EVENT, "end": EVENT["start"]}
    assert client.post("/events", headers=ALICE, json=invalid).status_code == 422


def test_read_access_is_audited(client: TestClient):
    event = client.post("/events", headers=ALICE, json=EVENT).json()
    client.get(f"/events/{event['id']}", headers=ALICE)
    assert client.app.state.audit_events[-1]["event"] == "access_granted"


def test_reads_are_limited_to_sixty_per_minute(client: TestClient):
    url = "/events/00000000-0000-0000-0000-000000000000"
    assert [client.get(url, headers=ALICE).status_code for _ in range(60)] == [404] * 60
    assert client.get(url, headers=ALICE).status_code == 429
