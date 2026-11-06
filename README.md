# Lab 6 – Testing: reference solution

Starter (Lab 5 + `tests/test_service.py`) plus what the lab asks you to create:

| Path | What it is |
|---|---|
| `history-stub/` | Test double of `history`: `app.py` (Flask) and `Dockerfile` |
| `compose.calc.yaml` | `calc` + the stub, in isolation (ports 5001 / 5002) |
| `compose.string.yaml` | `string` + the stub, in isolation (ports 5003 / 5004) |
| `tests/bruno/` | Bruno collection: folders `calc`, `calc-stub`, `string`, `string-stub`; environments `calc-component`, `string-component`, `integration` |
| `locustfile.py` | Load test: `ApiUser` with `add`, `upper`, `last` |

## Component tests (each service alone, with its stub)

```
docker compose -f compose.calc.yaml up --build -d --wait
docker compose -f compose.string.yaml up --build -d --wait
```

Bruno (open the folder `tests/bruno`, Runner):
`calc` + `calc-stub` with environment `calc-component`; `string` + `string-stub` with `string-component`.

```
docker compose -f compose.calc.yaml down
docker compose -f compose.string.yaml down
```

## Integration tests (the whole application)

```
docker compose up --build -d --wait
```

- Bruno: folders `calc` and `string` with environment `integration` (the same requests, base URL `http://localhost:5005`).
- `python -m pytest -q tests/test_service.py` (needs Docker: the fixture resets the `history` data).

## Load test

```
locust -f locustfile.py --host http://localhost:5005
```

Web UI: `http://localhost:8089`.

## Bruno from the terminal (optional)

```
npm install -g @usebruno/cli
cd tests/bruno
bru run calc calc-stub --env calc-component
bru run string string-stub --env string-component
bru run calc string --env integration
```

Exit code `0` if everything passed, `1` otherwise.
