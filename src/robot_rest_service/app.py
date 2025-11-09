from fastapi import FastAPI, HTTPException, Body, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any
from datetime import datetime

app = FastAPI(title="Robot REST Service", version="1.0.0")

# ----- Models -----

class Position(BaseModel):
    x: int
    y: int

class Robot(BaseModel):
    id: str
    position: Position
    energy: int = Field(ge=0, le=100)
    inventory: List[str] = Field(default_factory=list)

class MovePayload(BaseModel):
    direction: str

    @validator("direction")
    def validate_direction(cls, v):
        allowed = {"up", "down", "left", "right"}
        if v not in allowed:
            raise ValueError(f"direction must be one of {allowed}")
        return v

class StatePatch(BaseModel):
    energy: Optional[int] = Field(default=None, ge=0, le=100)
    position: Optional[Position] = None

class Action(BaseModel):
    timestamp: str
    type: str
    details: Dict[str, Any] = Field(default_factory=dict)

# ----- In-memory storage -----

ROBOTS: Dict[str, Robot] = {}
ACTIONS: Dict[str, List[Action]] = {}

def seed():
    if not ROBOTS:
        ROBOTS["r1"] = Robot(id="r1", position=Position(x=0, y=0), energy=100, inventory=[])
        ROBOTS["r2"] = Robot(id="r2", position=Position(x=1, y=0), energy=100, inventory=[])
        ACTIONS["r1"] = []
        ACTIONS["r2"] = []

def log_action(robot_id: str, type_: str, details: Dict[str, Any] = None):
    if details is None:
        details = {}
    ACTIONS.setdefault(robot_id, [])
    ACTIONS[robot_id].append(Action(timestamp=datetime.utcnow().isoformat() + "Z",
                                    type=type_,
                                    details=details))

seed()

# ----- Helper: HATEOAS link builders -----

def status_links(robot_id: str):
    return {
        "self": {"href": f"/robots/{robot_id}/status"},
        "actions": {"href": f"/robots/{robot_id}/actions?page=1&size=5"},
        "move": {"href": f"/robots/{robot_id}/move", "method": "POST"},
        "pickup": {"href": f"/robots/{robot_id}/pickup/{{itemId}}", "templated": True, "method": "POST"},
        "putdown": {"href": f"/robots/{robot_id}/putdown/{{itemId}}", "templated": True, "method": "POST"},
        "attack": {"href": f"/robots/{robot_id}/attack/{{targetId}}", "templated": True, "method": "POST"},
        "update_state": {"href": f"/robots/{robot_id}/state", "method": "PATCH"},
    }

def paginate_links(robot_id: str, page: int, size: int, total_pages: int):
    links = {
        "self": {"href": f"/robots/{robot_id}/actions?page={page}&size={size}"}
    }
    if page < total_pages:
        links["next"] = {"href": f"/robots/{robot_id}/actions?page={page+1}&size={size}"}
    if page > 1:
        links["prev"] = {"href": f"/robots/{robot_id}/actions?page={page-1}&size={size}"}
    return links

# ----- Endpoints -----

@app.get("/robots/{robot_id}/status")
def get_status(robot_id: str):
    robot = ROBOTS.get(robot_id)
    if not robot:
        raise HTTPException(status_code=404, detail="Robot not found")
    payload = robot.dict()
    payload["_links"] = status_links(robot_id)
    return JSONResponse(content=payload)

@app.post("/robots/{robot_id}/move")
def move_robot(robot_id: str, payload: MovePayload):
    robot = ROBOTS.get(robot_id)
    if not robot:
        raise HTTPException(status_code=404, detail="Robot not found")

    dx, dy = 0, 0
    if payload.direction == "up":
        dy = 1
    elif payload.direction == "down":
        dy = -1
    elif payload.direction == "left":
        dx = -1
    elif payload.direction == "right":
        dx = 1

    robot.position = Position(x=robot.position.x + dx, y=robot.position.y + dy)
    ROBOTS[robot_id] = robot
    log_action(robot_id, "move", {"direction": payload.direction, "position": robot.position.dict()})
    return {"message": "moved", "position": robot.position.dict()}

@app.post("/robots/{robot_id}/pickup/{item_id}")
def pickup(robot_id: str, item_id: str):
    robot = ROBOTS.get(robot_id)
    if not robot:
        raise HTTPException(status_code=404, detail="Robot not found")
    if item_id not in robot.inventory:
        robot.inventory.append(item_id)
        ROBOTS[robot_id] = robot
    log_action(robot_id, "pickup", {"itemId": item_id})
    return {"message": "picked up", "inventory": robot.inventory}

@app.post("/robots/{robot_id}/putdown/{item_id}")
def putdown(robot_id: str, item_id: str):
    robot = ROBOTS.get(robot_id)
    if not robot:
        raise HTTPException(status_code=404, detail="Robot not found")
    if item_id in robot.inventory:
        robot.inventory.remove(item_id)
        ROBOTS[robot_id] = robot
        log_action(robot_id, "putdown", {"itemId": item_id})
        return {"message": "put down", "inventory": robot.inventory}
    else:
        raise HTTPException(status_code=400, detail="Item not in inventory")

@app.patch("/robots/{robot_id}/state")
def update_state(robot_id: str, patch: StatePatch = Body(...)):
    robot = ROBOTS.get(robot_id)
    if not robot:
        raise HTTPException(status_code=404, detail="Robot not found")
    changed = {}
    if patch.energy is not None:
        robot.energy = patch.energy
        changed["energy"] = robot.energy
    if patch.position is not None:
        robot.position = patch.position
        changed["position"] = robot.position.dict()
    ROBOTS[robot_id] = robot
    log_action(robot_id, "state_update", changed)
    return {"message": "updated", "changed": changed}

@app.get("/robots/{robot_id}/actions")
def list_actions(
    robot_id: str,
    page: int = Query(1, ge=1),
    size: int = Query(5, ge=1, le=100),
):
    if robot_id not in ROBOTS:
        raise HTTPException(status_code=404, detail="Robot not found")
    items = ACTIONS.get(robot_id, [])
    total_actions = len(items)
    total_pages = max(1, (total_actions + size - 1) // size)
    start = (page - 1) * size
    end = start + size
    page_items = [a.dict() for a in items[start:end]]
    response = {
        "page": page,
        "size": size,
        "total_actions": total_actions,
        "total_pages": total_pages,
        "_links": paginate_links(robot_id, page, size, total_pages),
        "items": page_items,
    }
    return JSONResponse(content=response)

@app.post("/robots/{robot_id}/attack/{target_id}")
def attack(robot_id: str, target_id: str):
    attacker = ROBOTS.get(robot_id)
    target = ROBOTS.get(target_id)
    if not attacker or not target:
        raise HTTPException(status_code=404, detail="Attacker or target not found")

    if attacker.energy < 5:
        raise HTTPException(status_code=400, detail="Not enough energy to attack")

    # Cost to attacker
    attacker.energy = max(0, attacker.energy - 5)

    # Simple rule: if on same tile, deal 10 energy damage; else no damage
    damage = 0
    if attacker.position == target.position:
        damage = 10
        target.energy = max(0, target.energy - damage)

    ROBOTS[robot_id] = attacker
    ROBOTS[target_id] = target

    log_action(robot_id, "attack", {"targetId": target_id, "damage": damage, "energy_after": attacker.energy})
    log_action(target_id, "attacked_by", {"attackerId": robot_id, "damage": damage, "energy_after": target.energy})

    return {
        "message": "attack executed",
        "attacker": {"id": attacker.id, "energy": attacker.energy},
        "target": {"id": target.id, "energy": target.energy},
        "damage": damage,
    }
