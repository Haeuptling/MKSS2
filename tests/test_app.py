from fastapi.testclient import TestClient
from robot_rest_service.app import app, ROBOTS, Position

client = TestClient(app)

def test_status_endpoint():
    resp = client.get("/robots/r1/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "r1"
    assert "position" in data and "energy" in data and "inventory" in data
    assert "_links" in data and "self" in data["_links"] and "actions" in data["_links"]

def test_move_endpoint():
    before = ROBOTS["r1"].position
    resp = client.post("/robots/r1/move", json={"direction": "up"})
    assert resp.status_code == 200
    after = ROBOTS["r1"].position
    assert after.y == before.y + 1

def test_pickup_and_putdown():
    resp = client.post("/robots/r1/pickup/item42")
    assert resp.status_code == 200
    assert "item42" in resp.json()["inventory"]

    resp = client.post("/robots/r1/putdown/item42")
    assert resp.status_code == 200
    assert "item42" not in resp.json()["inventory"]

def test_update_state_patch():
    resp = client.patch("/robots/r1/state", json={"energy": 80, "position": {"x": 5, "y": 5}})
    assert resp.status_code == 200
    assert ROBOTS["r1"].energy == 80
    assert ROBOTS["r1"].position.x == 5 and ROBOTS["r1"].position.y == 5

def test_actions_pagination():
    client.post("/robots/r1/move", json={"direction": "right"})
    client.post("/robots/r1/move", json={"direction": "right"})
    client.post("/robots/r1/move", json={"direction": "right"})
    client.post("/robots/r1/move", json={"direction": "right"})
    r = client.get("/robots/r1/actions", params={"page": 1, "size": 2})
    assert r.status_code == 200
    data = r.json()
    assert data["page"] == 1
    assert data["size"] == 2
    assert "_links" in data and "self" in data["_links"]
    if data["total_pages"] > 1:
        assert "next" in data["_links"]

def test_attack_endpoint_same_position():
    client.patch("/robots/r1/state", json={"position": {"x": 10, "y": 10}, "energy": 100})
    client.patch("/robots/r2/state", json={"position": {"x": 10, "y": 10}, "energy": 100})

    resp = client.post("/robots/r1/attack/r2")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["attacker"]["energy"] == 95
    assert payload["target"]["energy"] == 90

def test_attack_endpoint_different_position():
    client.patch("/robots/r1/state", json={"position": {"x": 0, "y": 0}, "energy": 100})
    client.patch("/robots/r2/state", json={"position": {"x": 99, "y": 99}, "energy": 100})
    resp = client.post("/robots/r1/attack/r2")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["attacker"]["energy"] == 95
    assert payload["target"]["energy"] == 100
