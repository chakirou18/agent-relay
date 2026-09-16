# Agent Relay (SQLite starter)

Agent Relay is a small FastAPI service for registering agents, delivering one
task at a time, and recording results. The local starter is self-contained:
SQLite persists the queue and attempts, while workers execute tasks on their own
machines. The included worker deterministically returns `input.upper()`.

## Run it

```bash
uv sync
uv run uvicorn main:app --reload
```

Open <http://127.0.0.1:8000/> for the token-based local dashboard. The default
database is `./agent-relay.db`; set `RELAY_DATABASE_URL` to use another SQLite
file. `GET /health` is a liveness check and `GET /ready` verifies database
connectivity and schema (it queries the real tables, so a wiped volume
reports not-ready instead of passing with zero tables).

Register two identities and send a task:

```bash
alice=$(curl -sS -X POST http://127.0.0.1:8000/api/v1/agents \
  -H 'content-type: application/json' -d '{"name":"alice"}')
bob=$(curl -sS -X POST http://127.0.0.1:8000/api/v1/agents \
  -H 'content-type: application/json' -d '{"name":"uppercase"}')
```

The response contains each agent's secret `token` once. Keep it outside source
control. Use `Authorization: Bearer <token>` for all subsequent API calls;
registration is the only unauthenticated endpoint. For a shared installation,
set `RELAY_ENROLLMENT_SECRET` and send it as `X-Enrollment-Secret` when
registering.

## Run the deterministic worker

The worker can register itself and save credentials in a mode-0600 JSON file:

```bash
uv run python main.py worker \
  --base-url http://127.0.0.1:8000 \
  --name uppercase \
  --credentials ./uppercase-credentials.json \
  --worker-id laptop-1
```

For failure/redelivery demonstrations, make local execution intentionally slow
and stop the process after one completion:

```bash
uv run python main.py worker --credentials ./uppercase-credentials.json \
  --slow-seconds 75 --worker-id slow-laptop
```

The worker heartbeats during long work. Killing it leaves the claim leased;
after the 60-second lease expires, another worker can claim the task with a new
token and incremented attempt number. `RELAY_LEASE_SECONDS` and
`RELAY_MAX_ATTEMPTS` are configurable server settings.

An existing credential can also be supplied explicitly (the token is not
written to disk):

```bash
uv run python main.py worker --agent-id agent_123 --token agt_… --worker-id laptop-2
```

## Storage and delivery behavior

`database.py` contains SQLAlchemy models, SQLite WAL setup, and the isolated
`BEGIN IMMEDIATE` transaction helper. `storage.py` contains task/claim/recovery
operations; routes and request models are kept in `main.py` and `schemas.py`.
SQLite does not provide PostgreSQL's `FOR UPDATE SKIP LOCKED`, so the starter
serializes writer transactions to make concurrent claims safe across processes.
PostgreSQL uses a transaction-scoped advisory lock at the same storage seam,
preserving these guarantees without changing the HTTP protocol. This simple
implementation serializes relay mutations rather than parallelizing writers.

Claims are at-least-once and leased for 60 seconds by default. Heartbeats extend
an active lease. A completion or failure must include the recipient's bearer
token and claim token. Repeating the exact terminal request with that claim
token is idempotent; a stale token or different result receives `409`.

## Verify

The test suite covers the main protocol, sender/recipient access boundaries,
hashed claim-token behavior, idempotent terminal retries, concurrent claims,
lease expiry before and after recovery, pagination/error shape, and dashboard
asset serving:

```bash
uv run pytest -q
```

Tests default to a scratch database at `/tmp/agent-relay-test.db` so they
don't reset your dev server's `./agent-relay.db`. The fixture drops and
recreates all tables on whatever `RELAY_DATABASE_URL` points at, so stop
the dev server first or set `RELAY_DATABASE_URL` to a scratch file before
running tests against another database.

## Run with PostgreSQL and Docker Compose

Run `docker compose up --build -d`, then open <http://127.0.0.1:8000/>.
The `relay` service waits for the `postgres` healthcheck. Its
`RELAY_DATABASE_URL` is
`postgresql+psycopg://relay:relay_dev_password@postgres:5432/relay`.
These credentials are for local development. PostgreSQL data persists in the
`postgres-data` named volume. Existing SQLite files are not imported.

To run the live HTTP test in PowerShell:

```powershell
$env:RELAY_TEST_BASE_URL = 'http://127.0.0.1:8000'
.venv\Scripts\python.exe -m pytest -q -s test_live_api.py
```

The live test creates fresh identities without resetting the database.
Keep the other tests on a separate scratch database because their fixture
drops tables. `docker compose down` stops the stack and retains its data.

## Run in local Kubernetes (kind)

```powershell
kind create cluster --name agent-relay --wait 120s
docker build -t agent-relay:local .
kind load docker-image agent-relay:local postgres:17-bookworm --name agent-relay
kubectl --context kind-agent-relay apply -f k8s/
kubectl --context kind-agent-relay rollout status statefulset/postgres --timeout=180s
kubectl --context kind-agent-relay rollout status deployment/agent-relay --timeout=180s
# Free port 8000 if the previous Compose API is still running:
docker compose stop relay
kubectl --context kind-agent-relay port-forward service/agent-relay 8000:8000 --address 127.0.0.1
```

Keep port-forward running, then use the same dashboard URL and live test above.
The manifests include local-development credentials, a ConfigMap, a Secret,
and a PostgreSQL PVC. The API uses the loaded image with `imagePullPolicy: Never`.
Data survives PostgreSQL pod replacement; deleting the kind cluster removes
its local storage. The Kubernetes database is separate from the Compose database.

If Docker Desktop's multi-platform image metadata causes `kind load docker-image`
to fail with `content digest ... not found`, load an architecture-specific archive:

```powershell
docker image save --platform linux/amd64 -o "$env:TEMP\agent-relay-kind-images.tar" agent-relay:local postgres:17-bookworm
kind load image-archive "$env:TEMP\agent-relay-kind-images.tar" --name agent-relay
```
