"""Pronto's tool servers, reached over MCP (Chapter 5).

McpClient and McpServer speak MCP's JSON-RPC message format, passed
as JSON text through an in-process transport so the lab runs offline.
Nothing crosses the boundary except that text, so trace context
survives only if it is written into the message: params._meta, as
the OpenTelemetry MCP conventions specify.
"""
import json

from opentelemetry import trace
from opentelemetry.sdk.trace.sampling import ALWAYS_ON, ParentBased
from opentelemetry.trace import SpanKind, Status, StatusCode

from pronto.tools import TOOLS, ToolError, target
from receipts.tools import digest
from telemetry.propagation import extract, inject

PROTOCOL = "2026-07-28"

# The default sampler obeys the caller's sampled flag, so a caller
# could switch off the server's record of a refund. This one doesn't.
RECORD_EVERY_CALL = ParentBased(
    ALWAYS_ON, remote_parent_not_sampled=ALWAYS_ON)


def _attributes(tool, request_id, session_id):
    return {"mcp.method.name": "tools/call",
            "gen_ai.operation.name": "execute_tool",
            "gen_ai.tool.name": tool,
            "jsonrpc.request.id": str(request_id),
            "mcp.session.id": session_id,
            "mcp.protocol.version": PROTOCOL,
            "network.transport": "tcp"}


class McpServer:
    """One MCP server: a service with its own tracer and tools."""

    def __init__(self, world, tracer, tools):
        self.world, self.tracer, self.tools = world, tracer, tools

    def handle(self, wire):
        request = json.loads(wire)
        params = request["params"]
        tool, args = params["name"], params["arguments"]
        if tool not in self.tools:
            return json.dumps({"jsonrpc": "2.0", "id": request["id"],
                               "error": {"code": -32602,
                                         "message": f"unknown {tool}"}})
        session = params["_meta"]["pronto.example/client"]
        attributes = _attributes(tool, request["id"], session["id"])
        attributes.update({                     # who says they called
            "pronto.mcp.client.agent_id": session["agent_id"],
            "pronto.mcp.client.name": session["name"]})
        if TOOLS[tool].side_effect:
            attributes.update({
                "pronto.tool.target": target(tool, args),
                "pronto.tool.arguments_digest": digest(args)})
        parent = extract(params["_meta"])
        span = self.tracer.start_span(
            f"tools/call {tool}", context=parent,
            kind=SpanKind.SERVER, attributes=attributes,
            start_time=self.world.clock.now())
        with trace.use_span(span, end_on_exit=False):
            self.world.clock.advance(TOOLS[tool].latency_s)
            try:
                result = TOOLS[tool].run(self.world, args)
                if "ref" in result:
                    span.set_attributes({
                        "pronto.effect.status": "succeeded",
                        "pronto.effect.ref": result["ref"]})
            except ToolError as error:
                result = {"error": type(error).__name__,
                          "message": str(error)}
                span.set_status(Status(StatusCode.ERROR, str(error)))
                span.set_attributes({"error.type": result["error"],
                                     "pronto.effect.status": "blocked"})
            span.end(end_time=self.world.clock.now())
        return json.dumps({"jsonrpc": "2.0", "id": request["id"],
                           "result": {"structuredContent": result,
                                      "isError": "error" in result}})


class McpClient:
    """An agent's MCP session with one server."""

    def __init__(self, world, tracer, server, session_id, agent):
        self.world, self.tracer, self.server = world, tracer, server
        self.session = {"id": session_id, "agent_id": agent["id"],
                        "name": agent["name"]}
        self.next_id = 1

    def call(self, tool, arguments):
        request_id, self.next_id = self.next_id, self.next_id + 1
        self.world.clock.advance(0.01)
        session = self.session["id"]
        span = self.tracer.start_span(
            f"tools/call {tool}", kind=SpanKind.CLIENT,
            attributes=_attributes(tool, request_id, session),
            start_time=self.world.clock.now())
        with trace.use_span(span, end_on_exit=False):
            claim = {"pronto.example/client": self.session}
            meta = inject(claim)
            wire = json.dumps({
                "jsonrpc": "2.0", "id": request_id,
                "method": "tools/call",
                "params": {"name": tool, "arguments": arguments,
                           "_meta": meta}})
            self.world.clock.advance(0.02)       # network, each way
            reply = json.loads(self.server.handle(wire))
            self.world.clock.advance(0.02)
            result = (reply["result"]["structuredContent"]
                      if "result" in reply else
                      {"error": "McpError",
                       "message": reply["error"]["message"]})
            if "error" in result:
                span.set_status(Status(StatusCode.ERROR,
                                       result["message"]))
                span.set_attribute("error.type", result["error"])
            span.end(end_time=self.world.clock.now())
        return result
