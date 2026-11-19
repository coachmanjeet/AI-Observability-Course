"""Speedy's agent loop, instrumented with OpenTelemetry (Chapter 4).

The loop has the shape every tool-calling agent has: ask the
model, run the tools it asks for, feed back the results, and stop
when it answers. MockModel stands in for a real model so the trace
comes out the same on every run.
"""
from pronto.tools import run_tool

SPEEDY = {"id": "agent://pronto/speedy", "name": "Speedy",
          "version": "2.3.1"}
MAX_STEPS = 8


def run(world, model, spans, task):
    """One customer turn. Returns Speedy's reply."""
    cid = task["conversation_id"]
    with spans.agent(SPEEDY, cid):
        messages = [{"role": "user", "task": task}]
        for _ in range(MAX_STEPS):
            with spans.chat(model, cid) as span:
                reply = model.complete(messages)
                spans.record_reply(span, reply)
            messages.append({"role": "assistant",
                             "reply": reply})
            if not reply.tool_calls:
                return reply.text
            for call in reply.tool_calls:
                with spans.tool(call, cid) as span:
                    result = run_tool(world, call)
                    spans.record_result(span, result)
                messages.append({"role": "tool",
                                 "tool": call.name,
                                 "result": result})
        return "[step cap reached]"
