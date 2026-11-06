"""History service: the sole owner of persisted last-operation state.

The optional Redis backend preserves this HTTP API unchanged.
"""
import os
from flask import Flask, jsonify, request

if os.environ.get("STORAGE_BACKEND", "file") == "redis":
    from redis_storage import load_last, save_last
else:
    from storage import load_last, save_last

app = Flask(__name__)


def error(code, message, status=400):
    return jsonify(error=code, message=message), status


@app.post("/operations")
def record_operation():
    record = request.get_json(silent=True)
    if not isinstance(record, dict):
        return error("invalid_request", "Request body must be a JSON object")
    if set(record) != {"operation", "arguments", "result"}:
        return error("invalid_request", "Invalid operation result")
    if record["operation"] not in ("add", "div", "upper", "concat"):
        return error("invalid_request", "Invalid operation type")
    if not isinstance(record["arguments"], list):
        return error("invalid_request", "Invalid arguments")
    result = record["result"]
    if not isinstance(result, (int, float, str)) or isinstance(result, bool):
        return error("invalid_request", "Invalid result")

    save_last(record)
    return jsonify(record), 200


@app.get("/operations/last")
def last_operation():
    record = load_last()
    if record is None:
        return error(
            "no_previous_operation", "No successful operation has been executed yet", 404
        )
    return jsonify(record), 200


@app.get("/health")
def health():
    return jsonify(status="ok"), 200
