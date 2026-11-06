"""Lab 4 regression tests, now running through the public HTTP Gateway.

Start the stack first; no private endpoints are published. The fixture clears
history before each test through ``docker compose exec`` (not via a test-only
HTTP endpoint), so tests are isolated even when the named volume persists.
WARNING: running these tests deletes the stored last operation in the chosen stack.

    docker compose up --build -d --wait
    python -m pip install pytest requests
    python -m pytest -q

For the optional Redis configuration use:

    docker compose -f compose.redis.yaml up --build -d --wait
    LAB05_COMPOSE_FILE=compose.redis.yaml python -m pytest -q
"""
import os
from pathlib import Path
import subprocess

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = os.environ.get("LAB05_BASE_URL", "http://127.0.0.1:5005").rstrip("/")
COMPOSE_FILE = os.environ.get("LAB05_COMPOSE_FILE", "compose.yaml")

# Run inside history: clear the actual backend without adding a public/private
# reset endpoint or making application changes just for the tests.
RESET_HISTORY = """
import os
if os.environ.get('STORAGE_BACKEND', 'file') == 'redis':
    import redis
    redis.Redis(host=os.environ.get('REDIS_HOST', 'db')).delete('last')
else:
    from pathlib import Path
    Path('/app/data/last.json').unlink(missing_ok=True)
"""


class HttpResponse:
    """Wrap a requests.Response with Flask's familiar get_json() method."""

    def __init__(self, response):
        self.response = response
        self.status_code = response.status_code

    def get_json(self):
        return self.response.json()


class HttpClient:
    """Use real HTTP while retaining the exact Lab 4 test method calls."""

    def get(self, path):
        return HttpResponse(requests.get(BASE_URL + path, timeout=5))

    def post(self, path, json):
        return HttpResponse(requests.post(BASE_URL + path, json=json, timeout=5))


@pytest.fixture()
def client():
    try:
        subprocess.run(
            ["docker", "compose", "-f", COMPOSE_FILE, "exec", "-T", "history",
             "python", "-c", RESET_HISTORY],
            cwd=ROOT, capture_output=True, text=True, check=True, timeout=30,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        detail = getattr(exc, "stderr", "")
        raise RuntimeError(
            "The Compose application must be running before the HTTP tests. "
            "Start it with 'docker compose up --build -d --wait' "
            "(or -f compose.redis.yaml for Redis). " + str(detail)
        ) from exc
    yield HttpClient()


def test_add(client):
    response = client.post(
        "/operations",
        json={"type": "add", "arguments": [2, 4]},
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "operation": "add",
        "arguments": [2, 4],
        "result": 6,
    }


def test_division(client):
    response = client.post(
        "/operations",
        json={"type": "div", "arguments": [10, 2]},
    )

    assert response.status_code == 200
    assert response.get_json()["result"] == 5


def test_division_by_zero(client):
    response = client.post(
        "/operations",
        json={"type": "div", "arguments": [10, 0]},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "division_by_zero"


def test_upper(client):
    response = client.post(
        "/operations",
        json={"type": "upper", "arguments": ["hello"]},
    )

    assert response.status_code == 200
    assert response.get_json()["result"] == "HELLO"


def test_concat(client):
    response = client.post(
        "/operations",
        json={"type": "concat", "arguments": ["hello", "world"]},
    )

    assert response.status_code == 200
    assert response.get_json()["result"] == "helloworld"


def test_unknown_operation(client):
    response = client.post(
        "/operations",
        json={"type": "multiply", "arguments": [2, 3]},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "unknown_operation"


def test_missing_arguments(client):
    response = client.post(
        "/operations",
        json={"type": "add"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_arguments"


def test_wrong_argument_type(client):
    response = client.post(
        "/operations",
        json={"type": "div", "arguments": ["ten", 2]},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_arguments"


def test_last_before_any_success(client):
    response = client.get("/operations/last")

    assert response.status_code == 404
    assert response.get_json()["error"] == "no_previous_operation"


def test_last_after_success(client):
    client.post(
        "/operations",
        json={"type": "div", "arguments": [10, 2]},
    )

    response = client.get("/operations/last")

    assert response.status_code == 200
    assert response.get_json() == {
        "operation": "div",
        "arguments": [10, 2],
        "result": 5,
    }


def test_failed_operation_does_not_replace_last(client):
    client.post(
        "/operations",
        json={"type": "add", "arguments": [2, 4]},
    )
    client.post(
        "/operations",
        json={"type": "div", "arguments": [10, 0]},
    )

    response = client.get("/operations/last")

    assert response.status_code == 200
    assert response.get_json() == {
        "operation": "add",
        "arguments": [2, 4],
        "result": 6,
    }
