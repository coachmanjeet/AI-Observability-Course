# The same refund rule in Rego, for teams that run OPA.
# Not executed in the lab; Cedar is the engine of record.
package pronto.refunds

import rego.v1

default allow := false

allow if {
	input.action == "refunds.create"
	input.principal.registry_state == "approved"
	to_number(input.context.amount) <= 50
	input.context.currency == "USD"
	"refunds:create:max_50" in input.context.scopes
	input.resource.owner == input.context.on_behalf_of
	not input.context.freeze
}
