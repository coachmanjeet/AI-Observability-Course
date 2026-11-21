// pronto-refunds, version 3. Owner: payments team.
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
