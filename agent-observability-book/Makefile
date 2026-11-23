# Companion code for AI Agent Observability & Governance in Practice.
EXAMPLES := receipts/examples
CHAIN := $(EXAMPLES)/01-speedy-order-lookup.json \
         $(EXAMPLES)/02-speedy-refund-40.json \
         $(EXAMPLES)/03-outcome-refund-40.json

.PHONY: labs test receipt tamper maturity trace lint trace-receipts handoff \
        decisions collector figures help

test:            ## every chapter's tests
	pytest -q

help:            ## list every lab, by chapter
	@grep -h '^[a-z0-9-]*:.*##' $(MAKEFILE_LIST) \
	  | sed 's/:.*## /|/' | sort -t'|' -k2 -V \
	  | awk -F'|' '{printf "  make %-15s %s\n", $$1, $$2}'

receipt:         ## Chapter 2: build and validate the example receipts
	python -m receipts.build_examples $(EXAMPLES)
	python -m receipts.validate $(CHAIN) $(EXAMPLES)/04-night-owl-refund-85-R1.json

tamper:          ## Chapter 2: alter one receipt; the validator must fail
	-python -m receipts.tamper

maturity:        ## Chapter 3: score Pronto's fleet on the maturity model
	python -m maturity.assess maturity/fleet.json

trace:           ## Chapter 4: run Speedy's $40 refund and write its trace
	python -m pronto.run traces/speedy-refund-40.json

lint:            ## Chapter 4: check the trace against the GenAI conventions
	python -m telemetry.lint traces/speedy-refund-40.json

trace-receipts:  ## Chapter 4: build R1 receipts from the trace alone
	python -m receipts.from_trace traces/speedy-refund-40.json \
	  build/receipts-from-trace

handoff:         ## Chapter 5: one conversation across MCP, A2A and a queue
	python -m pronto.handoffs traces
	python -m telemetry.lint traces/handoff-pronto.json
	python -m receipts.from_trace traces/handoff-pronto.json \
	  build/receipts-conversation --brief

decisions:       ## Chapter 6: three turns, then why and which actions used what
	python -m decisions.run traces
	python -m decisions.graph traces/decisions.json why order:ord_5521
	python -m decisions.graph traces/decisions.json used policy:refunds
	python -m receipts.from_trace traces/decisions.json \
	  build/receipts-decisions --brief

collector:       ## Chapter 7: a night through redaction and tail sampling
	python -m collector.run build/collector

figures:         ## print figures: SVG sources to 300 DPI grayscale PNG
	sh figures/build.sh

# Chapter 8 onward: one fragment per chapter in mk/ (see mk/README.md)
LABS :=
-include mk/ch*.mk

labs: $(LABS)    ## every lab from Chapter 8 on
