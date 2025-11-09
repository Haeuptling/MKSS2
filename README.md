# MKSS2
## Requirements
- Python 3.11+
- Optional: Docker & Docker Compose

### start local
pip install -r requirements.txt
uvicorn robot_rest_service.app:app --reload
# Swagger: http://127.0.0.1:8000/docs

### Docker
docker compose up --build
# Swagger: http://127.0.0.1:8000/docs

## Usage (cURL)
```bash
BASE=http://127.0.0.1:8000
# Docker: BASE=http://localhost:8000
```

**Status**
```bash
curl $BASE/robots/r1/status
```

**Move**
```bash
curl -X POST "$BASE/robots/r1/move"   -H "Content-Type: application/json"   -d '{"direction":"up"}'
```

**State patchen (Energie/Position)**
```bash
curl -X PATCH "$BASE/robots/r1/state"   -H "Content-Type: application/json"   -d '{"energy":80,"position":{"x":5,"y":5}}'
```

**Aktionen (Pagination)**
```bash
curl "$BASE/robots/r1/actions?page=1&size=2"
```

**Pickup / Putdown**
```bash
curl -X POST "$BASE/robots/r1/pickup/item42"
curl -X POST "$BASE/robots/r1/putdown/item42"
```

**Attack**
```bash
curl -X POST "$BASE/robots/r1/attack/r2"
```