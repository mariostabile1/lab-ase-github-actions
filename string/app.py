"""String service: execute upper/concat and notify history directly."""
import os

import requests
from flask import Flask, jsonify, request
from operations import concat, upper

app = Flask(__name__)
HISTORY_URL = os.environ.get("HISTORY_URL", "http://history:5005").rstrip("/")
REQUEST_TIMEOUT = 3


def error(code, message, status=400):
    return jsonify(error=code, message=message), status


def notify_history(record):
    """Remote replacement for Lab 4's save_last(record)."""
    try:
        response = requests.post(
            f"{HISTORY_URL}/operations", json=record, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return None
    except requests.Timeout:
        return error("upstream_timeout", "History did not respond in time", 504)
    except requests.RequestException:
        app.logger.exception("History notification failed")
        return error("history_unavailable", "Cannot save the operation in history", 502)


@app.post("/operations")
def execute():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return error("invalid_request", "Request body must be a JSON object")
    kind = body.get("type")
    arguments = body.get("arguments")
    if kind not in ("upper", "concat"):
        return error("unknown_operation", "Only upper and concat are supported")
    expected = 1 if kind == "upper" else 2
    if not isinstance(arguments, list) or len(arguments) != expected:
        return error("invalid_arguments", f"Expected {expected} argument(s)")
    if not all(isinstance(value, str) for value in arguments):
        return error("invalid_arguments", "String arguments required")

    value = upper(*arguments) if kind == "upper" else concat(*arguments)
    record = {"operation": kind, "arguments": arguments, "result": value}
    failure = notify_history(record)
    if failure is not None:
        return failure
    return jsonify(record), 200


@app.get("/health")
def health():
    return jsonify(status="ok"), 200
