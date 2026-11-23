"""Chapter 4: the optional real-model path, against local stubs.

A stub chat-completions server plays a careful model, and a stub
OTLP receiver records what it's sent. No network, no API key."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from pronto import live
from telemetry import otlp

SCRIPT = [
    [("orders_get", {"order_id": "ord_5521"})],
    [("policy_lookup", {}), ("photos_verify", {"photo_id": "photo_7c1"})],
    [("refunds_create", {"order_id": "ord_5521", "amount": "40.00",
                         "currency": "USD"})],
    "Sorry about the strawberries. I've refunded $40.00.",
]
SEEN = {"requests": [], "traces": []}


class Stub(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(
            int(self.headers["Content-Length"])))
        if self.path.endswith("/v1/traces"):
            SEEN["traces"].append(body)
            out = {}
        else:
            SEEN["requests"].append(body)
            step = SCRIPT[len(SEEN["requests"]) - 1]
            msg = {"role": "assistant", "content": None}
            if isinstance(step, str):
                msg["content"], finish = step, "stop"
            else:
                msg["tool_calls"] = [
                    {"id": f"call_{len(SEEN['requests'])}{i}",
                     "type": "function",
                     "function": {"name": n, "arguments": json.dumps(a)}}
                    for i, (n, a) in enumerate(step)]
                finish = "tool_calls"
            out = {"id": f"chatcmpl-{len(SEEN['requests'])}",
                   "model": "stub-1",
                   "choices": [{"message": msg,
                                "finish_reason": finish}],
                   "usage": {"prompt_tokens": 1000,
                             "completion_tokens": 50}}
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def test_live_path_traces_a_real_loop(tmp_path):
    server = HTTPServer(("127.0.0.1", 0), Stub)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}"
    model = live.LiveModel(url + "/v1", "test-key", "stub-1")
    reply, spans = live.trace_live(model)
    assert "refunded $40.00" in reply
    names = [s.name for s in spans]
    assert names.count("chat stub-1") == 4
    assert "execute_tool refunds.create" in names
    # the wire carried tool results back under the right call IDs
    last = SEEN["requests"][-1]["messages"]
    tool_msgs = [m for m in last if m["role"] == "tool"]
    assert [m["tool_call_id"] for m in tool_msgs] == \
        ["call_10", "call_20", "call_21", "call_30"]
    out = tmp_path / "live.json"
    otlp.write(spans, out)
    assert live.export(out, url) == 200
    sent = SEEN["traces"][0]["resourceSpans"][0]["scopeSpans"][0]
    assert len(sent["spans"]) == len(spans)
    server.shutdown()
