"""Calculation service: execute add/div and notify history directly."""
import os

import requests
from flask import Flask, jsonify, request
from operations import add, divide

app = Flask(__name__)
HISTORY_URL = os.environ.get("HISTORY_URL", "http://history:5005").rstrip("/")
REQUEST_TIMEOUT = 3


def error(code, message, status=400):
    return jsonify(error=code, message=message), status


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def notify_history(record):
    """Replacement for Lab 4's local save_last(record) call."""
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
    if kind not in ("add", "div"):
        return error("unknown_operation", "Only add and div are supported")
    if not isinstance(arguments, list) or len(arguments) != 2:
        return error("invalid_arguments", "Expected 2 argument(s)")
    if not all(is_number(value) for value in arguments):
        return error("invalid_arguments", "Numeric arguments required")
    if kind == "div" and arguments[1] == 0:
        return error("division_by_zero", "The divisor cannot be zero")

    value = add(*arguments) if kind == "add" else divide(*arguments)
    record = {"operation": kind, "arguments": arguments, "result": value}
    failure = notify_history(record)
    if failure is not None:
        return failure
    return jsonify(record), 200


@app.get("/health")
def health():
    return jsonify(status="ok"), 200
