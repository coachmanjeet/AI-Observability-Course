"""Builds the v0.1 example receipts for Pronto's 2 a.m. incident (Chapters 1 and 2).

Usage: python -m receipts.build_examples receipts/examples

01  Speedy reads the customer's order                 R4, read_sensitive
02  Speedy refunds $40 of spoiled strawberries        R4, financial (rung 2: under $50, spot-checked)
03  Outcome record: the refund resolved the case       appended later
04  Night Owl refunds $85, over the $50 rule           R1, financial (shadow agent, no approval)
"""
import json
import pathlib
import sys

from receipts.tools import GENESIS, digest, seal

out = pathlib.Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)

SPEEDY = {
    "agent_id": "agent://pronto/speedy",
    "agent_name": "Speedy",
    "agent_version": "2.3.1",
    "kind": "first_party",
    "owner": "team:customer-support",
    "registry_ref": "registry://pronto/agents/speedy@2.3.1",
    "workload_id": "spiffe://pronto.example/ns/support/agent/speedy",
    "identity": "verified",
    "runtime": "pronto-support-runtime",
}
FOR_CUSTOMER = {
    "principal_type": "user",
    "principal_id": "cust_7f3a91",
    "tenant_id": "pronto",
    "scopes": ["orders:read:own", "refunds:create:max_50"],
    "delegation_chain": [
        {"actor": "spiffe://pronto.example/ns/support/agent/speedy", "via": "rfc8693_token_exchange",
         "scopes": ["orders:read:own", "refunds:create:max_50"]}
    ],
    "token_ref": digest({"jti": "tok_b81d22"}),
}
MODEL = {"provider": "mock", "request_model": "pronto-mock-1", "response_model": "pronto-mock-1"}
CONTEXT_PACK = {"id": "pronto-support", "version": "1.4.0", "digest": digest({"pack": "pronto-support", "v": "1.4.0"})}
POLICY_SET = {"id": "pronto-refunds", "version": "3", "digest": digest({"policy_set": "pronto-refunds", "v": "3"})}
WHERE = {"cloud_provider": "aws", "region": "us-west-2", "environment": "production",
         "data_residency": "US", "model_endpoint_region": "us-west-2"}
TRACE_ID = "4bf92f3577b34da6a3ce929d0e0e4736"

lookup = {
    "receipt_version": "0.1",
    "receipt_id": "rcpt_01JD7Q8M2K4V9X3T6B5N0PZRAV",
    "issued_at": "2026-11-14T02:06:41Z",
    "conformance": "R4",
    "consequence": {"side_effect": "read_sensitive", "reason": "Reads a customer's order, which holds personal data"},
    "who": SPEEDY,
    "for_whom": FOR_CUSTOMER,
    "knowing_what": {
        "model": MODEL,
        "context_pack": CONTEXT_PACK,
        "sources": [],
        "memory_reads": [{"store_id": "mem://pronto/support/cust_7f3a91", "record_count": 2}],
    },
    "under_which_rule": {
        "decision": "allow",
        "engine": "cedar",
        "policy_set": POLICY_SET,
        "determining_policies": ["orders-read-own-customer"],
        "enforcement_point": "gateway://pronto/mcp-gateway-us-west",
        "evaluated_at": "2026-11-14T02:06:41Z",
        "autonomy_tier": "act_autonomously",
        "request": {"subject": "agent://pronto/speedy", "action": "orders.get", "resource": "order:ord_5521",
                    "context": {"on_behalf_of": "cust_7f3a91"}},
        "approvals": [],
    },
    "did_what": {
        "action": {"operation": "execute_tool", "tool": "orders.get", "tool_call_id": "call_8c20", "via": "mcp",
                   "mcp_method": "tools/call", "target": "order:ord_5521",
                   "arguments_digest": digest({"order_id": "ord_5521"})},
        "effect": {"status": "succeeded", "summary": "Read order ord_5521 for the requesting customer"},
        "outcome": {"status": "not_applicable", "metric": "none"},
    },
    "at_what_cost": {
        "tokens": {"input": 2410, "output": 96, "cache_read": 1800},
        "model_cost": {"value": "0.00508", "currency": "USD"},
        "billable": [{"meter": "agent_action", "quantity": 0, "status": "not_billable"}],
        "billing_account": "tenant:pronto",
    },
    "where": WHERE,
    "evidence": {"trace_id": TRACE_ID, "span_id": "00f067aa0ba902b6", "conversation_id": "conv_44be2d",
                 "mcp_session_id": "mcps_19c4850a"},
}
seal(lookup, GENESIS)

refund = {
    "receipt_version": "0.1",
    "receipt_id": "rcpt_01JD7Q9B4R8C2W5Y7H1M3KQSTD",
    "issued_at": "2026-11-14T02:07:13Z",
    "conformance": "R4",
    "consequence": {"side_effect": "financial", "reason": "Issues a refund to the customer's card"},
    "who": SPEEDY,
    "for_whom": FOR_CUSTOMER,
    "knowing_what": {
        "model": MODEL,
        "context_pack": CONTEXT_PACK,
        "sources": [
            {"id": "order:ord_5521", "uri": "orders://ord_5521", "version": "etag-9f2c",
             "retrieved_at": "2026-11-14T02:06:41Z", "authority": "system:orders", "sensitivity": "confidential",
             "origin": "pronto", "trust": "authoritative"},
            {"id": "policy:refunds", "uri": "kb://pronto/policies/refunds", "version": "2026-10-01",
             "retrieved_at": "2026-11-14T02:06:45Z", "authority": "team:finance", "sensitivity": "internal",
             "origin": "pronto", "trust": "authoritative"},
            {"id": "photo:photo_7c1", "uri": "photos://photo_7c1", "version": "etag-41c7",
             "retrieved_at": "2026-11-14T02:06:52Z", "authority": "system:photos", "sensitivity": "confidential",
             "origin": "customer", "trust": "evidence"},
        ],
        "memory_reads": [{"store_id": "mem://pronto/support/cust_7f3a91", "record_count": 2}],
    },
    "under_which_rule": {
        "decision": "allow",
        "engine": "cedar",
        "policy_set": POLICY_SET,
        "determining_policies": ["refunds-under-50-sampled-review"],
        "enforcement_point": "gateway://pronto/mcp-gateway-us-west",
        "evaluated_at": "2026-11-14T02:07:12Z",
        "autonomy_tier": "act_with_sampled_review",
        "request": {"subject": "agent://pronto/speedy", "action": "refunds.create", "resource": "order:ord_5521",
                    "context": {"amount": "40.00", "currency": "USD", "on_behalf_of": "cust_7f3a91"}},
        "approvals": [],
    },
    "did_what": {
        "action": {"operation": "execute_tool", "tool": "refunds.create", "tool_call_id": "call_8c21", "via": "mcp",
                   "mcp_method": "tools/call", "target": "order:ord_5521",
                   "arguments_digest": digest({"order_id": "ord_5521", "amount": "40.00", "currency": "USD",
                                               "reason": "spoiled_perishable", "photo": True})},
        "effect": {"status": "succeeded", "external_ref": "refund:rf_9931",
                   "summary": "Refunded $40.00 for spoiled strawberries reported with a photo",
                   "amount": {"value": "40.00", "currency": "USD"}},
        "outcome": {"status": "pending", "metric": "resolved_without_escalation_within_7d",
                    "due_by": "2026-11-21T02:07:13Z"},
    },
    "at_what_cost": {
        "tokens": {"input": 3120, "output": 410, "cache_read": 1800},
        "model_cost": {"value": "0.0142", "currency": "USD"},
        "billable": [{"meter": "resolved_conversation", "quantity": 0, "status": "pending_outcome",
                      "idempotency_key": "conv_44be2d:resolved"}],
        "billing_account": "tenant:pronto",
    },
    "where": WHERE,
    "evidence": {"trace_id": TRACE_ID, "span_id": "00f067aa0ba902b7", "conversation_id": "conv_44be2d",
                 "mcp_session_id": "mcps_19c4850a"},
}
seal(refund, lookup["integrity"]["hash"])

outcome = {
    "record_type": "outcome",
    "receipt_version": "0.1",
    "receipt_id": refund["receipt_id"],
    "recorded_at": "2026-11-21T02:07:13Z",
    "status": "achieved",
    "metric": "resolved_without_escalation_within_7d",
    "evidence": {"source": "crm://pronto/cases/case_221",
                 "evaluation": {"name": "resolved_without_escalation", "score_value": 1, "score_label": "pass"}},
    "billable": [{"meter": "resolved_conversation", "quantity": 1, "status": "billed",
                  "idempotency_key": "conv_44be2d:resolved"}],
}
seal(outcome, refund["integrity"]["hash"])

night_owl = {
    "receipt_version": "0.1",
    "receipt_id": "rcpt_01JD7QA3N6F0J8P2V4X9C5LBEG",
    "issued_at": "2026-11-14T02:11:52Z",
    "conformance": "R1",
    "consequence": {"side_effect": "financial", "reason": "Issued a refund through the payments API"},
    "who": {"agent_id": "agent://unregistered/night-owl", "agent_name": "Night Owl", "agent_version": "unknown",
            "kind": "shadow", "owner": "unknown", "identity": "claimed", "runtime": "analyst-laptop"},
    "did_what": {
        "action": {"operation": "execute_tool", "tool": "payments.refund", "via": "api", "target": "order:ord_5530",
                   "arguments_digest": digest({"order_id": "ord_5530", "amount": "85.00", "currency": "USD"})},
        "effect": {"status": "succeeded", "external_ref": "refund:rf_9934",
                   "summary": "Refunded $85.00 with no policy check and no human approval",
                   "amount": {"value": "85.00", "currency": "USD"}},
        "outcome": {"status": "unknown", "metric": "unknown"},
    },
    "evidence": {"trace_id": "9a1c47e2b3d04f6c8e5a7b9d1f3c5e70", "span_id": "a3f1c9e7b5d2f8a1"},
}

files = {
    "01-speedy-order-lookup.json": lookup,
    "02-speedy-refund-40.json": refund,
    "03-outcome-refund-40.json": outcome,
    "04-night-owl-refund-85-R1.json": night_owl,
}
for name, rec in files.items():
    (out / name).write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", out / name)
