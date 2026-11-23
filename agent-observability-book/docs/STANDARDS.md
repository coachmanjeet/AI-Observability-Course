# Standards and products: full status by chapter

Dated November 2026. The book prints a two-line standards note at the end of each chapter; this file keeps the fuller notes, so they can be refreshed without a new edition. Each entry was true when checked. Check the linked source before relying on it.

## Chapter 2: The Agent Receipt

Every chapter ends with a box like this one. Each is a snapshot of what was true in November 2026; standards in this field move every quarter, so check the box before you build on it.

- **OpenTelemetry GenAI conventions.** Every `gen_ai.*` and `mcp.*` attribute is at Development stability. The GenAI conventions moved to their own repository with semantic conventions v1.42.0 (June 12, 2026). Pin the version you emit.
- **Agent and principal IDs.** `gen_ai.agent.id` and `gen_ai.agent.version` were removed from internal `invoke_agent` spans; read them from the registry when absent. `enduser.*` moved to the client-side conventions; the receipt uses `user.id` semantics for `principal_id`.
- **Receipt envelopes.** Two individual IETF drafts define signed, hash-chained agent receipts: `draft-sahu-agent-action-receipts-00` and `draft-noa-scitt-ai-agent-receipt-01` (a SCITT profile), both August 2026. Neither is a working-group document yet. The Agent Receipt is a content profile designed to travel inside either envelope.
- **Authorization request shape.** `under_which_rule.request` follows the OpenID AuthZEN 1.0 authorization API.

## Chapter 3: Discover, Govern, Observe

**Standards and products status (November 2026)**

Every major platform now ships part of the reference architecture. Map each one to the reference architecture in Chapter 3 before comparing them.

- **Registry and discovery.** AWS Agent Registry reached general availability on August 31, 2026; it auto-detects agents across accounts and turns them into draft records for approval ([Unite.AI](https://www.unite.ai/?p=458932)). Microsoft Agent 365, generally available since May 1, 2026, gives each agent an Entra Agent ID and includes shadow agents found on endpoints in its registry ([DEV](https://dev.to/holgerimbery/microsoft-agent-365-the-control-plane-for-ai-agents-is-now-generally-available-ggi)).
- **Identity, registry and gateway together.** Google announced Agent Identity, Agent Registry and Agent Gateway with [Gemini Enterprise Agent Platform](https://cloud.google.com/blog/products/ai-machine-learning/introducing-gemini-enterprise-agent-platform) on April 22, 2026, and made more of them generally available through the summer, according to the platform's [release notes](https://docs.cloud.google.com/gemini-enterprise-agent-platform/release-notes). Check each feature's status before you plan around it.
- **Policy at the gateway.** Policy in Amazon Bedrock AgentCore reached general availability on March 3, 2026, enforcing Cedar policies at the gateway, outside agent code ([AWS](https://aws.amazon.com/de/about-aws/whats-new/2026/03/policy-amazon-bedrock-agentcore-generally-available/)).
- **Control tower.** ServiceNow extended its AI Control Tower to AI running on any system on May 5, 2026, adding runtime visibility and an AI gateway for MCP traffic ([ServiceNow](https://newsroom.servicenow.com/press-releases/details/2026/ServiceNow-expands-AI-Control-Tower-to-discover-observe-govern-secure-and-measure-AI-deployed-across-any-system-in-the-enterprise/default.aspx)).
- **Protocols underneath.** A2A 1.0.0 (March 12, 2026) publishes Agent Cards at a well-known URI; MCP's 2026-07-28 specification aligns authorization with OAuth 2.0 and OpenID Connect; the IETF WIMSE working group's AI Identity Management System draft builds on SPIFFE and OAuth 2.0.

## Chapter 4: Tracing Agents End to End

- **Where the conventions live.** Semantic conventions v1.42.0 (June 12, 2026) moved every `gen_ai.*`, OpenAI and MCP definition into the separate `semantic-conventions-genai` repository ([semantic-conventions releases](https://github.com/open-telemetry/semantic-conventions/releases)). As of mid-August 2026 that repository had no tagged release, and everything in it is at Development stability ([Particula](https://particula.tech/blog/opentelemetry-genai-semantic-conventions-stable)). Pin a commit, not a version.
- **Recent changes.** v1.41 required the tool name in `execute_tool` span names, added `invoke_workflow`, and split `invoke_agent` into CLIENT and INTERNAL spans ([Greptime](https://greptime.com/blogs/2026-05-09-opentelemetry-genai-semantic-conventions)).
- **Agent identity attributes.** In the GenAI repository's current [agent span conventions](https://raw.githubusercontent.com/open-telemetry/semantic-conventions-genai/main/docs/gen-ai/gen-ai-agent-spans.md), the internal `invoke_agent` span lists `gen_ai.agent.name` but no longer `gen_ai.agent.id` or `gen_ai.agent.version`. This is the same change Chapter 2's box describes; in August 2026 it was still waiting for a release. Speedy sets all three. If a framework stops emitting the ID and version, take them from the registry (Chapter 11).
- **Switches.** `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` selects the latest experimental names in instrumentations that support it. `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` controls content capture, with values such as `NO_CONTENT`, `SPAN_ONLY`, `EVENT_ONLY` and `SPAN_AND_EVENT` in the Python contrib packages ([OpenTelemetry Python contrib](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation-genai/util.html)).

- **MCP tracing conventions.** OpenTelemetry's MCP conventions are at Development stability. They say instrumentations should propagate trace context inside `params._meta`, injecting `traceparent` and `tracestate` on the sender and extracting them on the receiver as the remote parent ([OpenTelemetry](https://opentelemetry.io/docs/specs/semconv/gen-ai/mcp/)). They also list JSON-RPC codes that shouldn't count as errors, including `-32602`, which servers return for a tool that doesn't exist ([Last9](https://last9.io/blog/mcp-server-monitoring/)).
- **MCP specification.** SEP-414 is Final. It documents `traceparent`, `tracestate` and `baggage` in `_meta` and explains why those keys are an exception to MCP's DNS-prefix rule for `_meta` keys ([MCP SEP-414](https://modelcontextprotocol.io/seps/414)). The lab speaks protocol version `2026-07-28` ([MCP Playground](https://mcpplaygroundonline.com/blog/mcp-observability-opentelemetry)). Over Streamable HTTP, some servers make the `_meta` context the MCP span's parent and link the span to its HTTP request span ([Apollo GraphQL](https://www.apollographql.com/docs/deploy-preview/4a7edbb134727d73e7b1b675/apollo-mcp-server/telemetry)).
- **A2A 1.0.** Clients must send `A2A-Version: 1.0` on every request, and a server that gets no header assumes a 0.3 client ([AAIF](https://aaif.io/blog/a2a-v1-0-a-builder-s-guide-part-1-discovery-tasks-and-clients)). In 1.0, a `SendMessage` result wraps the task in a `task` key ([Clix](https://docs.clix.so/a2a/version-compatibility.md)). Returning a trace ID in task metadata is Pronto's agreement with PayCo, not part of A2A.
- **Messaging conventions.** A process span should link to each message's creation context. Whether it also uses that context as its parent is a separate choice, allowed for a single message ([OneUptime](https://oneuptime.com/blog/post/2026-09-03-multiple-queue-messages-share-one-trace-id-span-links/view)). Many of the messaging conventions are at Development stability.

## Chapter 5: Decision Traces and Context Graphs

- **Data sources.** `gen_ai.data_source.id` is in the GenAI attribute registry, for the data that AI agents and RAG applications use for grounding ([OpenTelemetry](https://opentelemetry.io/docs/specs/semconv/attributes-registry/gen-ai/)). Retrieval spans arrived in v1.40 ([Greptime](https://greptime.com/blogs/2026-05-09-opentelemetry-genai-semantic-conventions)), and a retrieval span is named after its data source ([Dash0](https://www.dash0.com/knowledge/opentelemetry-genai-semantic-conventions-explained)). Pronto uses the same attribute on tool spans that read a record. The GenAI conventions are at Development stability.
- **Decision edges.** There is no convention for linking a tool call to the model call that requested it, other than the tool-call ID, whose model-side copy is opt-in content. Pronto's `pronto.link` values (`decided_by`, `in_context`) are its own. Record versions (`pronto.source.version`) have no convention either.
- **Context graphs.** An industry framing, not a standard. Implementations range from trace-derived graphs like this lab's to dedicated stores.

## Chapter 6: Content Capture, PII and Telemetry Cost

- **Redaction processor.** In the Collector's contrib distribution, at beta stability for traces and alpha for logs and metrics. It masks with `****` by default and supports `hmac-sha256` and `hmac-sha512` hashing ([pkg.go.dev](https://pkg.go.dev/github.com/open-telemetry/opentelemetry-collector-contrib/processor/redactionprocessor)). The lab's config targets `otelcol-contrib` v0.165.0.
- **Tail sampling processor.** Policies include `status_code`, `latency`, `string_attribute` and `probabilistic`, and all spans of a trace must reach the same Collector instance ([pkg.go.dev](https://pkg.go.dev/github.com/open-telemetry/opentelemetry-collector-contrib/processor/tailsamplingprocessor)).
- **Token counts.** `gen_ai.usage.input_tokens` includes cached tokens, and `gen_ai.usage.cache_read.input_tokens` counts those served from cache ([OpenTelemetry](https://opentelemetry.io/docs/specs/semconv/attributes-registry/gen-ai/)). Both are at Development stability.
- **Prices.** Grafana Cloud lists traces at $0.50 per GB ([Grafana](https://grafana.com/docs/grafana-cloud/cost-management-and-billing/manage-invoices/understand-your-invoice/application-observability-invoice.md)). LangSmith bills base traces at $5 per 1,000, and its [pricing page](https://www.langchain.com/pricing?product=langsmith) puts extended retention at 180 days for new SaaS traces, though some of its billing docs still said 400 in November 2026 ([ZenML](https://www.zenml.io/blog/langsmith-pricing)). Prices change often. Put your own in `collector/prices.py`.

## Chapter 7: Audit Trails and Replay

- **Transparency logs.** The IETF published the SCITT architecture as [RFC 9943](https://datatracker.ietf.org/doc/html/rfc9943), a standards-track architecture for signed statements registered with a transparency service, whose receipts are COSE receipts (RFC 9942). Its reference API, SCRAPI, was still an [Internet-Draft](https://datatracker.ietf.org/doc/html/draft-ietf-scitt-scrapi) in mid-2026. A checkpoint in this lab is a simplified, single-writer version of the same idea.
- **Signatures.** The lab uses a JWS (RFC 7515) with a detached payload and the EdDSA algorithm over Ed25519 (RFC 8032). A COSE_Sign1 envelope is the equivalent in CBOR, and is what SCITT expects.
- **Receipt envelopes.** The individual IETF drafts for agent action receipts noted in Chapter 2 remained drafts. The Agent Receipt's `integrity` block is designed to travel inside them.
- **EU AI Act.** [Article 12](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-12) requires high-risk systems to allow automatic recording of events over their lifetime; Article 19 sets the six-month minimum for keeping those logs. Neither requires a specific integrity mechanism, and Help Net Security [notes](https://www.helpnetsecurity.com/?p=366232) there was no finalized technical standard for Article 12 logging yet. The high-risk rules apply from December 2, 2027 (Chapter 24).

## Chapter 8: Trusted Context: Sources, Catalogs and Metrics

- **MCP resources.** The MCP specification lets servers [annotate resources](https://modelcontextprotocol.io/specification/latest/server/resources) with an intended audience, a priority and a `lastModified` timestamp, which clients can use to filter and prioritize context. There is no standard field for authority, origin or trust. Chapter 10 serves Pronto's catalog through MCP resources.
- **OpenTelemetry.** `gen_ai.data_source.id` names a source on a span (Chapter 5). Version, authority and origin have no convention; Pronto uses its own namespace.
- **Content Credentials.** The C2PA [launched version 2.3](https://c2pa.org/the-c2pa-launches-content-credentials-2-3-and-celebrates-5-years-of-impact-across-the-digital-ecosystem/) of the Content Credentials specification in early 2026. Credentials attest where media came from and whether it changed, not whether it's true. [Wikipedia notes](https://en.wikipedia.org/wiki/Content_Credentials) a researcher demonstrated in October 2026 a way to alter an image without invalidating its signatures, so treat credentials as one signal.
- **Receipt v0.1.** Sources carry eight fields, including `origin` and `trust`, which are required at R4.

- **Open Semantic Interchange.** Snowflake announced on January 27, 2026 that the [first OSI specification is live](https://www.snowflake.com/en/blog/open-semantic-interchanges-specs-finalized/) in an Apache 2.0 repository. It defines a vendor-neutral model for datasets, metrics, dimensions, relationships and context. The working group includes dbt Labs, Salesforce, ThoughtSpot and many others.
- **MetricFlow.** dbt Labs [open-sourced MetricFlow](https://www.getdbt.com/blog/the-osi-spec-updates), the engine behind its semantic layer, at Coalesce 2025, and joined OSI.
- **This lab** uses a minimal YAML format so the idea stays visible. Map it to OSI or MetricFlow definitions in production.
- **Receipt v0.1** records a metric as an ordinary source. A `kind` field (record, metric, entity) is a v0.2 candidate.

## Chapter 9: Context Packs and Memory

- **Agent Skills.** Anthropic published Agent Skills as an open format on December 18, 2025, and later [donated it to the Agentic AI Foundation](https://www.anthropic.com/news/donating-agent-skills-to-the-agentic-ai-foundation); the specification is at agentskills.io. A skill is a folder with a `SKILL.md` file. The format doesn't define signing or pinned dependencies; packs add those.
- **AGENTS.md** is a project-level instructions file hosted by the Agentic AI Foundation. It fits naturally as a pack's instructions file.
- **Signing.** The lab signs manifests with Ed25519, like Chapter 7's receipts. Software supply-chain tooling (Sigstore, in-toto attestations) can sign packs as build artifacts instead.
- **Receipt v0.1** records `context_pack` as ID, version and digest.

- **OpenTelemetry.** The GenAI conventions define memory operations for agents, at Development stability (Chapter 4). Record each read on a span, with the store ID and count.
- **OWASP.** ASI06, Memory and Context Poisoning, is in the [Top 10 for Agentic Applications](https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/) released in December 2025.
- **Erasure.** Data protection laws such as the GDPR give people a right to have personal data erased. Agent memory is personal data when it describes a person. Chapter 25 covers residency for memory stores.
- **Receipt v0.1** records `memory_reads` as store ID and record count. Per-record digests are a v0.2 candidate.

## Chapter 10: Permission-Aware Context over MCP

- **MCP resources.** Servers expose resources with `resources/list` and `resources/read`, and can [annotate them](https://modelcontextprotocol.io/specification/latest/server/resources) with an audience, a priority and a last-modified time. The specification leaves access control to the server; it doesn't define row or field filtering.
- **MCP authorization.** The 2026-07-28 specification aligns MCP authorization with OAuth 2.0 and OpenID Connect (Chapter 12 uses it to carry a delegated principal).
- **Error codes.** The lab uses -32002 for "resource not found", following the MCP resources specification.

## Chapter 11: Discover and Register Every Agent

- **Discovery in platforms.** Microsoft Agent 365 became [generally available on May 1, 2026](https://microsoft.com/en-us/security/blog/2026/05/01/microsoft-agent-365-now-generally-available-expands-capabilities-and-integrations), with discovery of local and cloud agents through Defender and Intune, and registry sync with AWS Bedrock and Google Cloud in preview. [AWS Agent Registry](https://aws.amazon.com/about-aws/whats-new/2026/08/aws-agent-registry-generally-available) became generally available on August 31, 2026, and can auto-detect agents on AgentCore runtimes and gateways across an organization. Each covers its own platforms first.
- **MCP Registry.** The MCP project's registry lists public servers with verified names. Private servers need a private registry (Chapter 11).
- **A2A Agent Cards.** Agents that speak A2A publish a card at a well-known URI, which discovery can read (Chapter 11).
- **No standard discovery format** exists for joining evidence across sources. The lab's draft record is Pronto's own.

- **A2A Agent Cards.** In A2A 1.0, an agent publishes its card at [`/.well-known/agent-card.json`](https://www.getmaxim.ai/articles/a2a-agent-card.md). Cards can carry JWS signatures over a canonical form of the card. A signature shows the card wasn't altered; on its own, it doesn't prove who operates the agent.
- **MCP Registry.** The official registry launched in preview in September 2025. It stores `server.json` metadata under namespaces verified through GitHub, DNS or HTTP, and [doesn't support private servers](https://modelcontextprotocol.io/registry); it recommends hosting your own registry for those.
- **Platform registries.** Microsoft Agent 365, AWS Agent Registry, Google's Agent Registry and MuleSoft Agent Registry all hold agent records with approval workflows, and several validate records against the A2A and MCP schemas (Chapter 11 dates their releases).
- **No common registry record format** spans these products. The lab's record is Pronto's own, built from A2A and MCP descriptions.

## Chapter 12: Agent Identity and Delegation

- **SPIFFE** defines workload identifiers and SVIDs in X.509 and JWT forms. SPIRE is its reference implementation. The lab models a SPIRE server's behavior; it doesn't run one.
- **IETF WIMSE.** The working group adopted [draft-ietf-wimse-aims](https://datatracker.ietf.org/doc/html/draft-ietf-wimse-aims), "AI Identity Management System", in September 2026, with authors from Defakto, AWS, Zscaler, Ping Identity, OpenAI and Okta. It proposes best practices for agent authentication and authorization built on WIMSE, SPIFFE and OAuth, and is informational, not a new protocol.
- **Agent principals in identity providers.** Microsoft Entra Agent ID is [generally available](https://learn.microsoft.com/en-za/entra/agent-id/whats-new-agent-id); [Okta for AI Agents](https://www.okta.com/en-in/blog/ai/okta-ai-agents-early-access-announcement/) entered early access in March 2026 with a comparable construct. Names, objects and flows differ by vendor.
- **Receipt v0.1** records `who.workload_id` as a URI.

- **RFC 8693, OAuth 2.0 Token Exchange,** defines subject and actor tokens and the nested `act` claim the lab uses. RFC 9449 (DPoP) can bind a token to a key the agent holds.
- **MCP authorization.** The 2026-07-28 revision treats MCP servers as OAuth 2.1 resource servers. [Clients must send the RFC 8707 `resource` parameter, and servers must validate audience](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/security-considerations); token passthrough is forbidden.
- **Cross-App Access.** [draft-ietf-oauth-identity-assertion-authz-grant](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-identity-assertion-authz-grant) (ID-JAG, Standards Track, October 2026) lets an enterprise IdP decide which apps and agents may reach which APIs for a user, using token exchange. MCP's enterprise-managed authorization builds on it. Keycloak's support is experimental.
- **Agent-specific OAuth drafts.** An individual draft for on-behalf-of authorization for AI agents [has expired](https://datatracker.ietf.org/doc/draft-oauth-ai-agents-on-behalf-of-user/); the OAuth working group is collecting agent use cases, including delegation chains, in draft-chen-oauth-agent-authz-use-cases.
- **Receipt v0.1** records `for_whom` with `delegation_chain` and a `token_ref` digest.

## Chapter 13: Least Privilege for Agents

- **OWASP Top 10 for Agentic Applications** (December 2025) includes ASI02, Tool Misuse and Exploitation, and ASI03, Identity and Privilege Abuse.
- **MCP authorization** (2026-07-28 revision): servers return `insufficient_scope` with the scopes a request needs, clients request additional scopes incrementally, and servers account for scope hierarchies.
- **RFC 9396, OAuth 2.0 Rich Authorization Requests,** carries structured `authorization_details`, such as payment amounts, where a scope string isn't enough.
- **Cloud tooling.** AWS IAM Access Analyzer reports unused roles, keys and permissions, and Google Cloud's role recommender suggests smaller roles from usage. Microsoft retired Entra Permissions Management in 2025. None of them sees your agents' receipts; the lab's approach works across systems.

## Chapter 14: Policy at the Action Boundary

- **Cedar** is open source and runs in-process; the lab uses the `cedarpy` bindings. Amazon Verified Permissions hosts Cedar as a service.
- **AgentCore Policy.** AWS made [Policy in Amazon Bedrock AgentCore generally available](https://aws.amazon.com/about-aws/whats-new/2026/03/policy-amazon-bedrock-agentcore-generally-available) on March 3, 2026. Policies are attached to an AgentCore Gateway, which evaluates each agent-tool request before allowing it; policies are written in Cedar and can be drafted from natural language.
- **OPA and Rego** remain the common choice for infrastructure policy. The OpenID Foundation's AuthZEN working group defines a standard API between enforcement points and decision engines, so a gateway can swap engines.
- **MCP** defines authorization for connecting to servers, not policy for individual tool calls; that belongs to gateways and servers.
- **Receipt v0.1** records `under_which_rule` with engine, policy set version and digest, determining policies, enforcement point and the request.

## Chapter 15: Threat-Modeling Agents

- **OWASP Top 10 for Agentic Applications** (December 2025, OWASP GenAI Security Project) lists ASI01 through ASI10, with mitigations for each. OWASP's agentic threats and mitigations taxonomy goes deeper.
- **MCP** lets clients list tools and be notified when the list changes. Pinning and quarantine are gateway behavior, not part of the protocol.
- **Malicious package tracking.** OpenSSF's malicious packages database records cases such as `postmark-mcp` as OSV entries, which dependency scanners can consume.
- **Receipt v0.1** allows `decision: deny` and `effect.status: blocked`. Collapsing identical denials with a count is Pronto's proposal for v0.2.

## Chapter 16: Human Oversight That Scales

- **Human oversight in regulation.** The EU AI Act requires high-risk AI systems to be designed for effective human oversight, including the ability to intervene and stop them. Chapter 24 maps receipts to its record-keeping and oversight duties.
- **NIST AI RMF** treats human oversight as part of managing AI risk; its generative AI profile adds guidance on human review of outputs.
- **MCP** includes elicitation, which lets a server ask the user for input during a tool call. It can carry a confirmation, but tiers, binding and the facts view are your design.
- **Receipt v0.1** records `autonomy_tier` and `approvals` (approver, time, decision, method) in `under_which_rule`.

## Chapter 17: Orchestration and Long-Running Work

- **A2A** defines how agents discover each other through agent cards and exchange tasks. It doesn't decide who may call whom; that's your registry and gateway.
- **MCP** connects agents to tools; an agent exposed as an MCP tool inherits the gateway controls from Part V.
- **Delegation across agents.** RFC 8693's nested `act` claim carries the chain across hops. The OAuth working group's agent use-case draft discusses delegation chains explicitly.
- **Receipt v0.1** records `did_what.action.via` and links receipts across agents with `evidence.parent_receipt_id`.

- **Durable execution.** Temporal, AWS Step Functions, Azure Durable Functions and similar engines provide histories, replay and retries. Several agent frameworks now integrate with them; check how your framework maps model calls and tool calls to activities.
- **Trace context** (W3C Trace Context) defines `traceparent`. Carrying it through telephony depends on your voice platform's support for custom headers or parameters.
- **OpenTelemetry span links** connect each step's trace to the workflow's start without one long-lived span.
- **Receipt v0.1** links receipts with `evidence.parent_receipt_id`; a `workflow_id` field is proposed for v0.2.

## Chapter 18: The AI Control Tower for 1P and 3P Agents

- **No standard defines a control tower.** The building blocks are standards covered earlier: SPIFFE and OAuth for identity, A2A agent cards and MCP metadata for the registry, OpenTelemetry for traces, Cedar or OPA for policy.
- **Vendor control planes** (Table 24.2) differ most on third-party discovery, open export of records, and partner ingestion. Ask for each in writing.
- **Receipt v0.1** is designed as the portable record between towers; conformance levels let a tower report coverage honestly.

## Chapter 19: Fleet Operations

- **OpenTelemetry GenAI semantic conventions** include attributes for the model requested and the model that responded; record both, since providers can route requests to different models or versions.
- **Progressive delivery** (canaries, feature flags, automated rollback) is standard practice for services; OpenFeature is a CNCF standard for feature-flag APIs that can carry the traffic split.
- **Receipt v0.1** records `who.agent_version` and `registry_ref`, plus context pack and policy set versions.

## Chapter 20: Agent-First Experience

- **MCP authorization.** Since the 2025-11-25 revision, clients and servers should support [Client ID Metadata Documents](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization); the 2026-07-28 revision marks Dynamic Client Registration as deprecated. Elicitation lets a server ask the user for confirmation, and tool annotations describe read-only and destructive tools.
- **Web Bot Auth.** The IETF working group's [draft-ietf-webbotauth-httpsig-protocol](https://datatracker.ietf.org/doc/draft-ietf-webbotauth-httpsig-protocol/) defines HTTP message signatures for automated traffic, with authors from Cloudflare and Google. It is a draft.
- **A2A agent cards** advertise agents' skills and endpoints for other agents.
- **Receipt v0.1** records external agents with `who.kind: third_party` and sessions in `evidence.mcp_session_id`.

## Chapter 21: From Telemetry to Business Value

- **OpenTelemetry GenAI semantic conventions** define token usage attributes on model spans and an evaluation result event; outcome records reuse the evaluation shape.
- **No standard defines business outcomes for agents.** Pick yours, define its window, and document it with the agent's registry record.
- **Receipt v0.1** records `did_what.outcome` as pending with a metric and due date; the outcome record schema (`agent-outcome.schema.json`) records the result and chains to the receipt.

## Chapter 22: Metering and Pricing Agent Work

- **No standard defines agent usage events.** CloudEvents is a common envelope for usage events; OpenTelemetry carries the data they're derived from.
- **OpenTelemetry GenAI conventions** define token usage on model spans; record the tenant as a resource or span attribute so usage can be partitioned.
- **Receipt v0.1** records `at_what_cost.billable` with meter, quantity, status and idempotency key, and outcome records carry the billed entry.

- **No standard defines agent pricing units.** Published vendor prices (Table 29.1) change often; record the date you checked.
- **Billing platforms** increasingly support usage, credits and outcome-based plans; check whether yours can bill on events that arrive days after the service date.
- **Receipt v0.1** lists every meter an action may charge, so pricing models can change without changing what agents record.

## Chapter 23: Provisioning, Entitlements and FinOps

- **FinOps for AI.** The FinOps Foundation's FOCUS specification standardizes cloud billing data and has been extending beyond cloud infrastructure to SaaS usage; check its current version for how it covers model and token charges.
- **Cloud budgets** (AWS Budgets, Azure Cost Management, Google Cloud budgets) alert on spend but generally don't stop an application's work; per-tenant kill switches belong in your runtime.
- **Receipt v0.1** records `at_what_cost.billing_account` on every receipt.

## Chapter 24: Controls to Frameworks

- **EU AI Act.** The Digital Omnibus on AI was published in the Official Journal in July 2026. High-risk obligations apply from 2 December 2027 (Annex III) and 2 August 2028 (Annex I); Article 50's transparency duties for AI interacting with people apply now. Harmonized standards for logging are still being drafted.
- **ISO/IEC 42001:2023** is certifiable; Annex A has 38 controls. Control numbering in this chapter follows the 2023 edition.
- **NIST AI RMF 1.0** and its generative AI profile are voluntary. Subcategory IDs follow the 1.0 core.
- **SOC 2** criteria come from the AICPA's Trust Services Criteria; agents fall under the same access and monitoring criteria as other systems.
- **Receipt v0.1** conformance levels and the hash chain are designed to be checked by tools like this one.

## Chapter 25: Residency, Sovereignty and Regulated Clouds

- **GDPR** governs transfers of personal data outside the EU; the EU-US Data Privacy Framework provides one transfer mechanism, and its legal status should be checked when you rely on it.
- **The US CLOUD Act** (2018) lets US authorities seek data held by US providers wherever it's stored, through legal process.
- **Cloud providers** offer EU regions, EU data boundaries and sovereign-cloud offerings with different operating and legal models; compare their terms, not their names.
- **Receipt v0.1** records `where` with cloud, region, environment, residency and model endpoint region.

- **FedRAMP** launched its Consolidated Rules for 2026 (CR26) on June 25, 2026. Certifications now use classes: Class B replaces Low, Class C replaces Moderate and Class D replaces High, with a new entry Class A. The classes are FedRAMP's certification categories, not a renaming of FIPS 199: agencies still categorize their own systems by impact, so confirm the mapping with your authorizing official rather than assuming it's one-for-one. The rules become mandatory for all providers on January 1, 2027, and Rev5 remains the path to Class D until its 20x pilot. [Secureframe's roadmap](https://secureframe.com/blog/fedramp-20x-roadmap) tracks the dates; FedRAMP.gov is canonical.
- **Continuous validation.** FedRAMP's Continuous Validation Standard targets 80% or more automated validation of Key Security Indicators.
- **FIPS 140-3** validates cryptographic modules; **FIPS 186-5** approves signature algorithms, including EdDSA.
- **Models in GovCloud** are authorized model by model, with their own dates; check the provider's list, not the console.
- **DoD Impact Levels** (IL4, IL5) are a separate authorization, and state and local programs often use **GovRAMP** instead of FedRAMP.

## Chapter 26: Ship or Hold for the Control Plane

- **Agent Receipt v0.1** is this book's specification (Appendix A). Two fields the chapters showed an auditor needs are in v0.1 and required at R4: `who.identity`, verified or claimed (Chapter 12), and `origin` and `trust` on each source, so a receipt can show that the agent read untrusted content (Chapter 8). What the chapters found beyond that is listed for v0.2 (Appendix A.11). The candidates: structured approval fields, with the approval's ID, the order and amount it was bound to and its expiry, which v0.1 packs into the `method` string (Chapter 16); a witness on each section, naming the system that vouches for it, which a rebuilt receipt needs (Chapter 7); repeated denials collapsed into one record with a count (Chapter 15); and a workflow ID in `evidence` (Chapter 17). The authorization boundary in `where` (Chapter 25) is a candidate for regulated deployments.
- **Every standard in Chapters 24 to 25** has dates that will move: the EU AI Act's high-risk obligations, FedRAMP's 2026 rules, and model authorizations in government regions. The review reruns its checks; re-check the dates as well.
- **The protocols underneath** (MCP, A2A, OAuth token exchange, SPIFFE, Cedar, OpenTelemetry's GenAI conventions) each have their own status boxes in the chapters that use them.
