# Contracts between internal services (reference solution)

These interfaces are intentionally **private**, available only on the Compose
network. Do not publish their ports on the host.

| Caller | Target | Method + path | Purpose |
| --- | --- | --- | --- |
| Gateway | calc | `POST http://calc:5005/operations` | Execute `add` or `div` |
| Gateway | string | `POST http://string:5005/operations` | Execute `upper` or `concat` |
| calc, string | history | `POST http://history:5005/operations` | Persist a successful result |
| Gateway | history | `GET http://history:5005/operations/last` | Retrieve last successful result |

## Calculation/string internal request

```json
{"type": "add", "arguments": [2, 3]}
```

The internal operation request uses the same two field names as the public
operation request; each service only accepts its own subset of operation types.

## History notification and stored record

Only **after** a successful operation, calc or string sends:

```json
{"operation": "add", "arguments": [2, 3], "result": 5}
```

This uses the *result* field name `operation`, **not** the public input field
`type`. The history service returns 200 with that same record after saving.
When no operation has been recorded, `GET /operations/last` responds 404 with:

```json
{
  "error": "no_previous_operation",
  "message": "No successful operation has been executed yet"
}
```

## Synchronous error semantics

If history cannot be reached (or it rejects a notification), calc/string
responds 502; if its notification times out, it responds 504. The Gateway
relays these distributed failure errors. The computation itself may have
finished, but **the whole request is not reported as a success** unless history
has acknowledged persistence.

This models the v4 slides' requested failure propagation; it does **not**
solve ambiguous network outcomes, multi-writer consistency, or exactly-once
processing. Those are advanced design concerns outside the lab.

## OpenAPI descriptions

Each service owns its own contract:

- `gateway/openapi.yaml`: the unchanged public routes (`POST /operations`, `GET /operations/last`)
  plus the liveness endpoint and distributed failure responses.
- `calc/openapi.yaml`: private `POST /operations` for `add` and `div`.
- `string/openapi.yaml`: private `POST /operations` for `upper` and `concat`.
- `history/openapi.yaml`: private `POST /operations` to store a **result** (`operation`,
  `arguments`, `result`) and `GET /operations/last` to read it.

All four documents also describe their `GET /health` liveness endpoint. Internal
`servers` URLs are service names in the Docker Compose network, not addresses
intended to be called directly from the host.

## The original Lab 4 tests (unchanged scenarios)

The only test file is `tests/test_service.py`. It keeps the **same 11 test names,
requests, expected status codes and assertions** as Lab 4, but now calls the
public Gateway via real HTTP instead of importing Flask's in-process test client.
It clears the stored last operation **before each test**, from within the history
container, so a previously used named volume does not alter the test results.
The reset is performed by the pytest fixture, not by an application endpoint.
**Run on a disposable lab stack:** the fixture deletes any existing last-operation
record in the selected stack (including its Redis bonus variant).

For the file-backed main exercise, from the `material05/` directory:

```sh
docker compose up --build -d --wait
python -m pip install pytest requests
python -m pytest -q
```

Stop the application with `docker compose down` (preserves history-data).
Remove the volume with `docker compose down -v` when you intend to delete data.

For the optional Redis stack, run **one stack at a time** because both publish
port 5005, and use the matching Compose file for the tests:

```sh
docker compose down
docker compose -f compose.redis.yaml up --build -d --wait
LAB05_COMPOSE_FILE=compose.redis.yaml python -m pytest -q
```

Optional `LAB05_BASE_URL` overrides the client URL (default `http://127.0.0.1:5005`).
The test fixture requires Docker Compose and a running `history` container.
