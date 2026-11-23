# Agent Receipt Specification v0.1

**Status:** Draft for *AI Agent Observability & Governance in Practice* (Chapter 2 and Appendix A). Written November 18, 2026; to be frozen for drafting on December 4, 2026. Not a published standard. Lives in `agent-observability-book/receipts/` in https://github.com/coachmanjeet/AI-Observability-Course.

**In one line:** one record per consequential agent action that answers seven questions: who acted, for whom, knowing what, under which rule, doing what, at what cost, and where.

## 1. What a receipt is, and isn't

A receipt is the evidence record a reviewer, auditor or incident lead reads first. It points to the trace for detail but stands on its own. It is not a trace, a log line or a billing event, though it links to all three.

**How it relates to existing receipt drafts.** Several individual IETF Internet-Drafts already define signed, hash-chained receipts for agent actions, among them `draft-sahu-agent-action-receipts-00` (August 2026) and `draft-noa-scitt-ai-agent-receipt-01`, a SCITT profile (August 2026). They focus on integrity: proving a record was issued by a key and hasn't been altered. The Sahu draft treats its actor as self-asserted and doesn't address delegation, cost, context or residency. The SCITT profile explicitly leaves out whether the agent was correct and whether any downstream effect occurred.

The Agent Receipt is a **content profile**: it defines *what* a complete record must say, using OpenTelemetry names where they exist. Its integrity block is deliberately minimal, so a receipt can travel inside either draft's envelope (see Section 9).

## 2. When to emit a receipt

Emit one receipt for each **consequential action**: any action whose side effect is one of these.

| `side_effect` | Examples |
| --- | --- |
| `read_sensitive` | Reading an order, a medical record or any data labeled confidential or restricted |
| `write` | Updating a record, changing a configuration |
| `financial` | Refunds, payments, credits, price changes |
| `external_communication` | Emailing a customer, posting to a channel, calling another company's agent |
| `permission_change` | Granting a scope, creating a credential, adding a user |
| `destructive` | Deleting data, cancelling an order, revoking access |

Model calls and plain reads of non-sensitive data don't get receipts; the trace covers them. Emit at the enforcement point (the gateway) when one exists, otherwise in the agent runtime as soon as the effect is known. **Denied and blocked actions get receipts too,** with `decision: deny` and `effect.status: blocked`. They are often the most important evidence in a security review.

## 3. Design rules

1. **Point, don't copy.** Receipts hold digests and references, never raw prompts, model outputs, tool arguments, tokens or names. `principal_id` is pseudonymous.
2. **Reuse OpenTelemetry.** Where a GenAI or MCP convention exists, use its name (Section 7). Receipt-native fields cover only what has no convention: delegation, policy decisions, cost, billing and residency.
3. **Never edit; append.** Receipts are immutable and hash-chained. Outcomes arrive later as separate outcome records that link back.
4. **No floats.** Money is a decimal string and counts are integers, so the canonical form is stable and no amount is ever rounded.
5. **Partial is allowed, but declared.** Every receipt states its conformance level (Section 5), so a reader knows which questions it can't answer.

## 4. The seven questions

| Question | Section | Key fields | Filled in by (chapter) |
| --- | --- | --- | --- |
| Who acted? | `who` | `agent_id`, `agent_version`, `kind` (first-party, third-party, shadow), `owner`, `registry_ref`, `workload_id` | 4, 15, 16 |
| For whom? | `for_whom` | `principal_id`, `tenant_id`, `scopes`, `delegation_chain`, `token_ref` | 17, 18 |
| Knowing what? | `knowing_what` | `model`, `context_pack`, `sources` (with version, authority, sensitivity), `memory_reads` | 6, 9, 11, 12, 13 |
| Under which rule? | `under_which_rule` | `decision`, `policy_set`, `determining_policies`, `enforcement_point`, `autonomy_tier`, `approvals`, `request` | 19, 21 |
| Doing what? | `did_what` | `action`, `effect`, `outcome` | 4, 5, 8, 27 |
| At what cost? | `at_what_cost` | `tokens`, `model_cost`, `billable` meters | 7, 28 |
| Where? | `where` | `cloud_provider`, `region`, `environment`, `data_residency` | 32 |

Two supporting sections complete the record. `evidence` holds the trace and span IDs, the conversation and MCP session IDs, and an optional `parent_receipt_id` for handoffs (Chapters 4–5). `integrity` holds the hash chain (Chapter 8).

**"Doing what" has three parts,** matching the top three rungs of Book 1's Evidence Ladder:

- **Action:** what the agent called.
- **Effect:** what changed in the target system.
- **Outcome:** whether the business result happened. It is usually known later, so it arrives as an outcome record (Section 8).

## 5. Conformance levels

A receipt can be useful before it is complete. Each level requires the sections of the levels below it, and the JSON Schema enforces this.

| Level | Name | Adds | What a reviewer can answer |
| --- | --- | --- | --- |
| R1 | Traced | `who`, `did_what`, `evidence`, `consequence` | Which agent did what, and where the trace is |
| R2 | Identified | `for_whom` | On whose behalf, with which scopes |
| R3 | Bounded | `knowing_what`, `under_which_rule` | What it knew, and which rule allowed it |
| R4 | Accountable | `at_what_cost`, `where`, `integrity` | All seven questions, tamper-evident |

An estate reaches maturity level 5 (Accountable) in Chapter 3's model when every consequential action produces an R4 receipt.

## 6. Field notes

The schema (`agent-receipt.schema.json`) is the full reference. These are the semantics that matter most.

- **`who.kind: shadow`** marks an agent caught at a gateway but missing from the registry. `owner: "unknown"` is itself a finding.
- **`for_whom.delegation_chain`** has one entry per hop. It is built from OAuth 2.0 token exchange (RFC 8693) actor claims, and scopes should narrow at each hop.
- **`for_whom.token_ref`** is a digest of the token's ID, never the token.
- **`knowing_what.sources[].version`** is an ETag, commit, or effective date. It must let a reviewer fetch exactly what the agent read.
- **`under_which_rule.request`** follows the OpenID AuthZEN Authorization API shape (subject, action, resource, context), so any policy engine's decision can be recorded the same way.
- **`under_which_rule.autonomy_tier`** has four values in v0.1: `suggest_only`, `act_with_approval`, `act_with_sampled_review` and `act_autonomously`. They line up with Book 1's autonomy ladder for Speedy's refunds: refunds over $50 are `act_with_approval`, refunds under $50 with random spot checks are `act_with_sampled_review`, and refunds under $10 are `act_autonomously`. `suggest_only` is the rung below all three, where the agent drafts and a person acts.
- **`did_what.outcome.status`** stays `pending` until an outcome record arrives. It is `not_applicable` for actions with no business outcome, such as a read.
- **`at_what_cost.billable[]`** lists the meters this action may charge. Outcome-priced meters stay `pending_outcome` until the outcome record bills them. The `idempotency_key` prevents double billing.
- **`knowing_what` from a trace** comes from decision links (Chapter 6): the tool span links to the model call that asked for it (`pronto.link: decided_by`), and that call links to each tool result in its context (`in_context`). An action decided on the customer's message alone has an empty `sources` list, which is an honest answer.
- **`at_what_cost.model_cost`** is the cost of the model call that decided the action, as an exact decimal string. The rest of the turn's model calls are metering's concern (Chapter 28). Build receipts from redacted spans, before sampling, so no consequential action loses its receipt (Chapter 7).
- **`where.data_residency`** is the jurisdiction where the data behind this action is stored. It isn't necessarily where the code ran.
- **`did_what.action.via`** names the channel the action crossed: `direct`, `mcp`, `a2a`, `queue`, `api` or `cli`. A queued action's receipt is written when the agent queues it; `effect.status` stays `succeeded` with a `message:` reference, and the worker's span links back to it (Chapter 5).
- **`evidence.parent_receipt_id`** links a receipt to the one that caused it. A handoff produces one receipt per acting agent: Speedy's `disputes.open` receipt, and a receipt for each consequential call the partner agent then makes on Pronto's systems, written from Pronto's MCP server span with `who.kind: third_party` (Chapter 5).

## 7. OpenTelemetry mapping

Every `gen_ai.*` and `mcp.*` attribute is still at Development stability. The names below were checked against a guide verified at semantic-conventions-genai commit `c739977` (July 30, 2026). Re-check them at manuscript lock.

| Receipt field | OpenTelemetry source | Note |
| --- | --- | --- |
| `who.agent_id`, `agent_name`, `agent_version` | `gen_ai.agent.id`, `gen_ai.agent.name`, `gen_ai.agent.version` | `id` and `version` were removed from internal `invoke_agent` spans; read them from the registry when absent |
| `who.runtime` | `service.name` (resource) | |
| `for_whom.principal_id` | `user.id` | `enduser.*` has moved to the client-side conventions; verify at lock |
| `for_whom.delegation_chain` | none | Receipt-native, from RFC 8693 actor claims |
| `knowing_what.model.provider` | `gen_ai.provider.name` | Replaced `gen_ai.system` |
| `knowing_what.model.request_model`, `response_model` | `gen_ai.request.model`, `gen_ai.response.model` | |
| `knowing_what.sources[].id` | `gen_ai.data_source.id` | On the tool span that read the record, for the model call that decided the action (Chapter 6) |
| `knowing_what.sources[].version` | `pronto.source.version` | No convention yet; supplied by the system that holds the record |
| `knowing_what.memory_reads[]` | `gen_ai.memory.store.id`, `gen_ai.memory.record.count` | |
| `under_which_rule.*` | none | Receipt-native; the request uses the AuthZEN shape |
| `did_what.action.operation` | `gen_ai.operation.name` | Usually `execute_tool` |
| `did_what.action.tool`, `tool_call_id` | `gen_ai.tool.name`, `gen_ai.tool.call.id` | |
| `did_what.action.arguments_digest` | digest of `gen_ai.tool.call.arguments` | Arguments are opt-in content; keep only the digest |
| `did_what.action.mcp_method` | `mcp.method.name` | |
| Outcome record `evidence.evaluation` | `gen_ai.evaluation.name`, `gen_ai.evaluation.score.value`, `gen_ai.evaluation.score.label` | From the `gen_ai.evaluation.result` event |
| `at_what_cost.tokens` | `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.usage.cache_read.input_tokens` | |
| `at_what_cost.model_cost` | none | Receipt-native. The deciding model call's tokens times a dated price list; `input_tokens` already includes cached tokens, so only the uncached share is priced at the input rate (Chapter 7) |
| `at_what_cost.billable` | none | Receipt-native (Chapter 28) |
| `where.cloud_provider`, `region`, `environment` | `cloud.provider`, `cloud.region`, `deployment.environment.name` (resource) | |
| `where.data_residency` | none | Receipt-native |
| `evidence.trace_id`, `span_id` | W3C trace context | MCP carries it in `params._meta` |
| `evidence.conversation_id` | `gen_ai.conversation.id` | Don't synthesize one |
| `evidence.mcp_session_id` | `mcp.session.id` | |
| `evidence.parent_receipt_id` | none | Receipt-native. Joined through the partner's trace ID, which the A2A client span records as `pronto.a2a.remote_trace_id` |

## 8. Outcome records

The business outcome usually isn't known when the action runs. A refund's real outcome is whether the case closed without escalation a week later. So outcomes are separate records (`agent-outcome.schema.json`). Each one carries the `receipt_id` it resolves, its status, its evidence (a source plus an optional evaluation result) and any meters it bills. It joins the same hash chain, so the receipt never changes and the outcome can't be quietly rewritten.

This is also how outcome-based pricing stays honest. In the example, the `resolved_conversation` meter is `pending_outcome` on the receipt and becomes `billed` only on the outcome record, under the same idempotency key.

## 9. Integrity and transport

- **Canonical form:** JCS (RFC 8785): compact UTF-8 JSON with object keys sorted by their UTF-16 code units (RFC 8785, Section 3.2.3), which differs from sorting by code points once a key holds characters outside the Basic Multilingual Plane. v0.1 has no floats, so JCS's number rules never apply. The reference implementation's `jcs_order` sorts the JCS way, and `tests/test_jcs_order.py` checks it against the RFC's own ordering example.
- **Hash:** SHA-256 over the canonical record, excluding `integrity.hash` and `integrity.signature`. The hash covers `prev_hash`, so every record commits to the whole chain before it.
- **Chain:** `prev_hash` is the hash of the previous record in the same ledger. The first record uses `sha256:` followed by 64 zeros. v0.1 assumes one ledger per tenant.
- **Signature:** optional in v0.1. Both IETF drafts above use Ed25519. Adopting it, so a receipt can be wrapped as a Sahu log line or a SCITT Signed Statement without conversion, is the leading candidate for v0.2.
- **R1–R3 receipts may be unchained.** Only R4 requires `integrity`.

## 10. Privacy and retention

A receipt never contains raw prompts, model outputs, tool arguments, credentials, names or email addresses. It holds digests and references instead, which has a useful consequence. Content a receipt points to can be erased under a right-to-erasure request **without breaking the chain**, because the chain covers digests, not content.

Pseudonymous isn't anonymous. A `principal_id` that someone holding another table can link back to a customer is still personal data under the GDPR (Recital 26), so receipts are personal data wherever that link exists. Erasing the content and the link table leaves a receipt that proves an action happened without saying to whom; whether that's enough for a given request is a question for privacy counsel, not for this specification. Receipts follow the longest record-keeping rule that applies to the action. The content behind them follows its own, usually shorter, retention.

## 11. Worked example: Speedy's $40 refund at 2:07 a.m.

Speedy, Pronto's support agent, refunds $40 for spoiled strawberries that the customer reported with a photo within 24 hours. It acts on the customer's behalf, under the policy that lets refunds under $50 go through with sampled review (Book 1's $50 rule). This is the R4 receipt (`examples/02-speedy-refund-40.json`):

```json
{
  "receipt_version": "0.1",
  "receipt_id": "rcpt_01JD7Q9B4R8C2W5Y7H1M3KQSTD",
  "issued_at": "2026-11-14T02:07:13Z",
  "conformance": "R4",
  "consequence": {
    "side_effect": "financial",
    "reason": "Issues a refund to the customer's card"
  },
  "who": {
    "agent_id": "agent://pronto/speedy",
    "agent_name": "Speedy",
    "agent_version": "2.3.1",
    "kind": "first_party",
    "owner": "team:customer-support",
    "registry_ref": "registry://pronto/agents/speedy@2.3.1",
    "workload_id": "spiffe://pronto.example/ns/support/agent/speedy",
    "runtime": "pronto-support-runtime"
  },
  "for_whom": {
    "principal_type": "user",
    "principal_id": "cust_7f3a91",
    "tenant_id": "pronto",
    "scopes": [
      "orders:read:own",
      "refunds:create:max_50"
    ],
    "delegation_chain": [
      {
        "actor": "spiffe://pronto.example/ns/support/agent/speedy",
        "via": "rfc8693_token_exchange",
        "scopes": [
          "orders:read:own",
          "refunds:create:max_50"
        ]
      }
    ],
    "token_ref": "sha256:478ab5a12a15f5c9620b66eee8664009d2003789e022ca0fb208283decc68f1a"
  },
  "knowing_what": {
    "model": {
      "provider": "mock",
      "request_model": "pronto-mock-1",
      "response_model": "pronto-mock-1"
    },
    "context_pack": {
      "id": "pronto-support",
      "version": "1.4.0",
      "digest": "sha256:3631935aa54fcf18d9c8de14dd83d6bba02e1e940815aaf5f92643fbe1766d3e"
    },
    "sources": [
      {
        "id": "order:ord_5521",
        "uri": "orders://ord_5521",
        "version": "etag-9f2c",
        "retrieved_at": "2026-11-14T02:06:41Z",
        "authority": "system:orders",
        "sensitivity": "confidential"
      },
      {
        "id": "policy:refunds",
        "uri": "kb://pronto/policies/refunds",
        "version": "2026-10-01",
        "retrieved_at": "2026-11-14T02:06:45Z",
        "authority": "team:finance",
        "sensitivity": "internal"
      },
      {
        "id": "photo:photo_7c1",
        "uri": "photos://photo_7c1",
        "version": "etag-41c7",
        "retrieved_at": "2026-11-14T02:06:52Z",
        "authority": "system:photos",
        "sensitivity": "confidential"
      }
    ],
    "memory_reads": [
      {
        "store_id": "mem://pronto/support/cust_7f3a91",
        "record_count": 2
      }
    ]
  },
  "under_which_rule": {
    "decision": "allow",
    "engine": "cedar",
    "policy_set": {
      "id": "pronto-refunds",
      "version": "3",
      "digest": "sha256:0daf2617f82d3e13b4a6c0521fe24d21abf779d30cdafcba9fd7dc61f2ef49d9"
    },
    "determining_policies": [
      "refunds-under-50-sampled-review"
    ],
    "enforcement_point": "gateway://pronto/mcp-gateway-us-west",
    "evaluated_at": "2026-11-14T02:07:12Z",
    "autonomy_tier": "act_with_sampled_review",
    "request": {
      "subject": "agent://pronto/speedy",
      "action": "refunds.create",
      "resource": "order:ord_5521",
      "context": {
        "amount": "40.00",
        "currency": "USD",
        "on_behalf_of": "cust_7f3a91"
      }
    },
    "approvals": []
  },
  "did_what": {
    "action": {
      "operation": "execute_tool",
      "tool": "refunds.create",
      "tool_call_id": "call_8c21",
      "via": "mcp",
      "mcp_method": "tools/call",
      "target": "order:ord_5521",
      "arguments_digest": "sha256:6c5ce5682a1fd46f07e93962a3702b7397b3aec8f31e89081c24b1209860cbe7"
    },
    "effect": {
      "status": "succeeded",
      "external_ref": "refund:rf_9931",
      "summary": "Refunded $40.00 for spoiled strawberries reported with a photo",
      "amount": {
        "value": "40.00",
        "currency": "USD"
      }
    },
    "outcome": {
      "status": "pending",
      "metric": "resolved_without_escalation_within_7d",
      "due_by": "2026-11-21T02:07:13Z"
    }
  },
  "at_what_cost": {
    "tokens": {
      "input": 3120,
      "output": 410,
      "cache_read": 1800
    },
    "model_cost": {
      "value": "0.0142",
      "currency": "USD"
    },
    "billable": [
      {
        "meter": "resolved_conversation",
        "quantity": 0,
        "status": "pending_outcome",
        "idempotency_key": "conv_44be2d:resolved"
      }
    ],
    "billing_account": "tenant:pronto"
  },
  "where": {
    "cloud_provider": "aws",
    "region": "us-west-2",
    "environment": "production",
    "data_residency": "US",
    "model_endpoint_region": "us-west-2"
  },
  "evidence": {
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
    "span_id": "00f067aa0ba902b7",
    "conversation_id": "conv_44be2d",
    "mcp_session_id": "mcps_19c4850a"
  },
  "integrity": {
    "canonicalization": "JCS-RFC8785",
    "prev_hash": "sha256:ef2e907965fd7dad1d65db137392eef9160aa4a75a4ccef39dfd74de19a051f1",
    "hash": "sha256:f862495f8b62e5d92ba39a523601caa0d8af3a02e61330ec2413c3c07c6ab6c3"
  }
}
```

Four minutes later, Night Owl, a shadow agent on an analyst's laptop, refunds $85 through the payments API. That breaks the $50 rule: no policy check, no human approval. The payments API logs can only support an R1 receipt (`examples/04-night-owl-refund-85-R1.json`). The validator shows exactly what nobody can answer:

```text
PASS 01-speedy-order-lookup.json: R4, answers 7/7, chained
PASS 02-speedy-refund-40.json: R4, answers 7/7, chained
PASS 03-outcome-refund-40.json: outcome achieved, chained
     resolves rcpt_01JD7Q9B4R8C2W5Y7H1M3KQSTD
PASS 04-night-owl-refund-85-R1.json: R1, answers 2/7, unchained
     cannot answer: for whom, knowing what, under which rule, at
     what cost, where
```

The tamper test changes the refund amount from 40.00 to 400.00 in a copy of the receipt:

```text
PASS 01-speedy-order-lookup.json: R4, answers 7/7, chained
FAIL 02-tampered.json: hash does not match; record altered
```

This contrast between Speedy's seven answers and Night Owl's two is Chapter 1's 2 a.m. incident in one screen.

## 12. Open questions to settle before the December 4 freeze

1. **Autonomy tier names.** *Resolved Nov 18:* the four values stay, mapped to Book 1's autonomy ladder (Section 6).
2. **Signatures.** Require Ed25519 at R4 so receipts drop into the IETF envelopes, or keep them optional?
3. **Ledger scope.** One chain per tenant (v0.1), per agent, or per enforcement point? A single writer per chain is simplest to verify.
4. **Handoffs.** *Resolved Nov 18:* one receipt per acting agent, linked by `parent_receipt_id`. The Chapter 5 lab produces five receipts for one two-turn conversation, and the partner's receipt points at Speedy's handoff receipt.
5. **Volume under attack.** Denied actions always get receipts. Measure the volume during the Chapter 20 red-team lab before keeping that rule.
6. **License.** Suggested: CC BY 4.0 for the spec text and Apache 2.0 for the code.
7. **Engage, don't compete.** Contact the authors of the two IETF drafts before publishing v0.1 publicly, and offer the receipt as a content profile that their envelopes can carry.

## Files

| File | Purpose |
| --- | --- |
| `agent-receipt.schema.json` | JSON Schema (2020-12) for receipts, with conformance levels enforced |
| `agent-outcome.schema.json` | JSON Schema for outcome records |
| `tools.py` | Canonical form, digests, hash chain |
| `build_examples.py` | Builds the four example records |
| `validate.py` | Checks schemas, hashes and the chain; reports unanswered questions |
| `tamper.py` | The tamper test: alters one amount and expects the validator to fail |
| `examples/` | Order lookup (R4), $40 refund (R4), its outcome record, Night Owl's $85 refund (R1) |

To reproduce, from `agent-observability-book/`: `make receipt`, or `python -m receipts.build_examples receipts/examples` and then `python -m receipts.validate receipts/examples/*.json`.

## Sources

- [draft-sahu-agent-action-receipts-00: Signed, Hash-Chained Action Receipts for AI Agents](https://www.ietf.org/archive/id/draft-sahu-agent-action-receipts-00.html)
- [draft-noa-scitt-ai-agent-receipt-01: A SCITT Profile for AI-Agent Action Receipts](https://ftp.kaist.ac.kr/ietf/draft-noa-scitt-ai-agent-receipt-01.txt)
- [OpenTelemetry GenAI semantic conventions implementation guide (verified at commit c739977)](https://hidekazu-konishi.com/entry/opentelemetry_genai_semantic_conventions_guide.html)
- [Dash0: OpenTelemetry GenAI semantic conventions explained](https://www.dash0.com/knowledge/opentelemetry-genai-semantic-conventions-explained)
- [OpenTelemetry MCP attribute registry](https://opentelemetry.io/docs/specs/semconv/registry/attributes/mcp/)
- [OpenTelemetry end-user attributes (moved)](https://opentelemetry.io/docs/specs/semconv/registry/attributes/enduser/)
- [NHIMG agent identity standards tracker (RFC 8693, AuthZEN 1.0, JWS with RFC 8785)](https://nhimg.org/agent-identity-standards-tracker)
- [IETF draft-ietf-wimse-aims: AI Identity Management System](https://datatracker.ietf.org/doc/html/draft-ietf-wimse-aims)
