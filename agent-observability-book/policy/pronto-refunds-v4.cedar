// pronto-refunds, version 4. Owner: payments team.
// Adds: refunds over $50, up to $500, with a bound approval.
// Evaluated at the MCP gateway for every refunds.create call.

@id("refunds-under-50-sampled-review")
permit (
  principal is Pronto::Agent,
  action == Pronto::Action::"refunds.create",
  resource is Pronto::Order
)
when {
  context.amount.lessThanOrEqual(decimal("50.00")) &&
  context.currency == "USD" &&
  context.scopes.contains("refunds:create:max_50") &&
  resource.owner == context.on_behalf_of
};

@id("refunds-50-to-500-with-approval")
permit (
  principal is Pronto::Agent,
  action == Pronto::Action::"refunds.create",
  resource is Pronto::Order
)
when {
  context.amount.lessThanOrEqual(decimal("500.00")) &&
  context.currency == "USD" &&
  resource.owner == context.on_behalf_of &&
  context has approval &&
  context.approval.role == "support_lead" &&
  context.approval.resource == resource &&
  context.approval.amount == context.amount
};

@id("registered-agents-only")
forbid (principal, action, resource)
unless { principal.registry_state == "approved" };

@id("payments-freeze")
forbid (
  principal,
  action == Pronto::Action::"refunds.create",
  resource
)
when { context.freeze };
