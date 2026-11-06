"""history-stub: a stand-in for the history service, used only in component tests.

POST /operations   what calc and string call. The "result" of the record decides the answer:
                   "500" -> HTTP 500, "504" -> answers after 5 seconds (the caller gives up after 3), else 200
GET  /__calls      the records received since the last reset
POST /__reset      forget the received records
GET  /health       used by docker compose
"""
import time
from flask import Flask, jsonify, request

app = Flask(__name__)
calls = []


@app.post("/operations")
def operations():
    record = request.get_json(silent=True)
    calls.append(record)
    result = str(record["result"])
    if result == "500":
        return jsonify(error="stub_error"), 500
    if result == "504":
        time.sleep(5)
    return jsonify(record), 200


@app.get("/__calls")
def received():
    return jsonify(calls), 200


@app.post("/__reset")
def reset():
    calls.clear()
    return jsonify(calls=0), 200


@app.get("/health")
def health():
    return jsonify(status="ok"), 200
