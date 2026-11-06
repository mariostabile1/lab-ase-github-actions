"""Public API Gateway: preserve Lab 4's HTTP contract, dispatch only.

Notice that it deliberately does NOT call history to save a result.
calc and string do so directly after executing a successful operation.
"""
import os

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

CALC_URL = os.environ.get("CALC_URL", "http://calc:5005").rstrip("/")
STRING_URL = os.environ.get("STRING_URL", "http://string:5005").rstrip("/")
HISTORY_URL = os.environ.get("HISTORY_URL", "http://history:5005").rstrip("/")
REQUEST_TIMEOUT = 3


def error(code, message, status=400):
    return jsonify(error=code, message=message), status


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def require_json_body():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ValueError("Request body must be a JSON object")
    return body


def require_arguments(body, expected_count):
    arguments = body.get("arguments")
    if not isinstance(arguments, list):
        raise ValueError("'arguments' must be a JSON array")
    if len(arguments) != expected_count:
        raise ValueError(f"Expected {expected_count} argument(s)")
    return arguments


def validate_public_request(body):
    """Exact Lab 4 validation order and public error codes/messages."""
    operation_type = body.get("type")
    if not isinstance(operation_type, str):
        return None, None, ("invalid_request", "'type' must be a string")

    try:
        if operation_type == "add":
            arguments = require_arguments(body, 2)
            if not all(is_number(value) for value in arguments):
                raise ValueError("add requires two numeric arguments")
        elif operation_type == "div":
            arguments = require_arguments(body, 2)
            if not all(is_number(value) for value in arguments):
                raise ValueError("div requires two numeric arguments")
            if arguments[1] == 0:
                return None, None, ("division_by_zero", "The divisor cannot be zero")
        elif operation_type == "upper":
            arguments = require_arguments(body, 1)
            if not isinstance(arguments[0], str):
                raise ValueError("upper requires one string argument")
        elif operation_type == "concat":
            arguments = require_arguments(body, 2)
            if not all(isinstance(value, str) for value in arguments):
                raise ValueError("concat requires two string arguments")
        else:
            return None, None, (
                "unknown_operation", f"Unsupported operation: {operation_type}"
            )
    except ValueError as exc:
        return None, None, ("invalid_arguments", str(exc))
    return operation_type, arguments, None


def downstream_failure(response):
    """Only forward the well-defined distributed-system errors.

    Internal validation errors should not occur after the Gateway validated
    the request; they are treated as unexpected upstream failures.
    """
    if response.status_code in (502, 504):
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if (
            isinstance(payload, dict)
            and isinstance(payload.get("error"), str)
            and isinstance(payload.get("message"), str)
        ):
            return jsonify(payload), response.status_code
    return error("upstream_error", "An internal service request failed", 502)


def forward(method, url, **kwargs):
    try:
        res = requests.request(method, url, timeout=REQUEST_TIMEOUT, **kwargs)
        if res.status_code >= 400:
            app.logger.warning("Upstream status %s from %s", res.status_code, url)
            return None, downstream_failure(res)
        data = res.json()
        if not isinstance(data, dict):
            raise ValueError("Internal service returned non-object JSON")
        return data, None
    except requests.Timeout:
        return None, error(
            "upstream_timeout", "An internal service did not respond in time", 504
        )
    except (requests.RequestException, ValueError):
        app.logger.exception("Cannot contact %s", url)
        return None, error("upstream_error", "An internal service request failed", 502)


@app.post("/operations")
def create_operation():
    try:
        body = require_json_body()
    except ValueError as exc:
        return error("invalid_request", str(exc))

    operation_type, arguments, invalid = validate_public_request(body)
    if invalid is not None:
        return error(*invalid)

    service_url = CALC_URL if operation_type in ("add", "div") else STRING_URL
    data, failure = forward(
        "POST", f"{service_url}/operations",
        json={"type": operation_type, "arguments": arguments},
    )
    if failure is not None:
        return failure
    # calc/string have already notified history before returning HTTP 200.
    if (
        data.get("operation") != operation_type
        or data.get("arguments") != arguments
        or "result" not in data
    ):
        return error("upstream_error", "An internal service returned an invalid result", 502)
    return jsonify(data), 200


@app.get("/operations/last")
def get_last_operation():
    try:
        res = requests.get(f"{HISTORY_URL}/operations/last", timeout=REQUEST_TIMEOUT)
        if res.status_code == 404:
            return error(
                "no_previous_operation",
                "No successful operation has been executed yet",
                404,
            )
        if res.status_code >= 400:
            return downstream_failure(res)
        data = res.json()
        if not isinstance(data, dict):
            raise ValueError("Invalid history response")
        return jsonify(data), 200
    except requests.Timeout:
        return error(
            "upstream_timeout", "An internal service did not respond in time", 504
        )
    except (requests.RequestException, ValueError):
        app.logger.exception("Cannot read history")
        return error("upstream_error", "An internal service request failed", 502)


@app.get("/health")
def health():
    return jsonify(status="ok"), 200
