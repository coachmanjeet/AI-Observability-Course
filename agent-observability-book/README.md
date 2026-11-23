# agent-observability-book

Companion code for *AI Agent Observability & Governance in Practice: Tracing, Identity, Policy and Metering for Enterprise Agent Fleets*. It lives in the course repository, https://github.com/coachmanjeet/AI-Observability-Course, next to the course materials.

Every idea in the book runs here against one company: Pronto, the online grocery store from *AI Agent Evals in Practice*, and its fleet of seven agents. Speedy, the support agent from Book 1, is joined by Pick, Route, Coder, two third-party agents (Ledger and Promo) and one shadow agent, Night Owl.

## Quick start

You need Python 3.12 or later, Git and `make` (on Windows, use WSL).

```bash
git clone --branch book2-draft \
  https://github.com/coachmanjeet/AI-Observability-Course.git
cd AI-Observability-Course/agent-observability-book
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
make demo          # smoke test: Saturday night's two refunds
make test          # every chapter's tests, about a minute
make help          # every lab, by chapter
```

Everything runs offline. Speedy runs on `MockModel`, a deterministic stand-in for a tool-calling model, so every output in the book is reproducible. The book's Appendix H lists every lab and a symptom-to-lab index: start from "money moved and no receipt was written" or "a customer was paid twice" and it names the lab that reproduces it.

## Map to the book

| Path | Chapters |
|---|---|
| `receipts/SPEC.md`: Agent Receipt spec v0.1 | 2, App. A |
| `receipts/agent-receipt.schema.json`, `agent-outcome.schema.json`: JSON Schema, conformance levels R1 to R4 | 2, App. A |
| `receipts/tools.py`: canonical form, digests, hash chain | 2, 8 |
| `receipts/validate.py`: schema, hash and chain checks; reports unanswered questions | 2 |
| `receipts/build_examples.py`, `receipts/examples/`: the 2 a.m. incident as receipts | 1, 2 |
| `receipts/tamper.py`: the tamper test | 2 |
| `maturity/assess.py`, `maturity/fleet.json`: five-level self-assessment and CI gate | 3 |
| `pronto/`: Pronto's world, Speedy's tools, a deterministic mock model, and Speedy's agent loop | 4 onward |
| `telemetry/genai.py`: OpenTelemetry GenAI spans (`invoke_agent`, `chat`, `execute_tool`) | 4 |
| `telemetry/otlp.py`, `telemetry/waterfall.py`: OTLP JSON files and a text waterfall | 4 |
| `telemetry/lint.py`: checks any OTLP JSON export against the conventions | 4 |
| `receipts/from_trace.py`, `traces/`: R1 receipts built from a trace | 4, 5 |
| `telemetry/propagation.py`: W3C trace context into and out of a carrier | 5 |
| `pronto/mcp.py`: an MCP client and server; context rides in `params._meta` | 5 |
| `pronto/a2a.py`: Speedy hands a dispute to PayCo's Ledger over A2A 1.0 | 5 |
| `pronto/queue.py`: a queued confirmation, sent later, linked to its producer | 5 |
| `pronto/handoffs.py`: the two-turn conversation, with a `--drop-context` break | 5 |
| `decisions/`: decision links to a graph; `why` and `used` queries | 6 |
| `pronto/sources.py`: the source catalog (authority, sensitivity) | 6, 9 |
| `collector/night.py`: a night of traffic with planted faults and fictional customers | 7 |
| `collector/processors.py`: redaction, tail and head sampling, leak scan | 7 |
| `collector/pronto-collector.yaml`: the same pipeline for otelcol-contrib | 7 |
| `collector/prices.py`: model and trace prices behind every cost | 7, 28 |
| `figures/`: every print figure as code (`notation.py` holds the book's legend) | all |
| `../.github/workflows/agent-observability-book.yml`: tests and labs on every change, weekly against upstream | all |

## Extend it

Score your own estate: copy `maturity/fleet.json`, describe your agents, and run `python -m maturity.assess your-fleet.json`. Add `--fail-below 2` to use it as a CI gate.

Write a receipt for your own agent: start from `receipts/examples/04-night-owl-refund-85-R1.json`, add sections until it validates at the level you need, and check it with `python -m receipts.validate your-receipt.json`.

## Standards this code implements

Dated so you know what to re-check. As of November 2026: OpenTelemetry GenAI semantic conventions (Development stability, `semantic-conventions-genai` repository), MCP specification 2026-07-28, A2A 1.0.0, OpenID AuthZEN 1.0 request shape, JSON Canonicalization Scheme (RFC 8785). The Agent Receipt is a content profile designed to travel inside the envelopes defined by `draft-sahu-agent-action-receipts-00` and `draft-noa-scitt-ai-agent-receipt-01`.
