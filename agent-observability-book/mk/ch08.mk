.PHONY: supply supply-audit
LABS += supply supply-audit

supply:          ## Chapter 8: provenance checks on a retrieval
	python -m context.supply retrieve build/context

supply-audit:    ## Chapter 8: check every read in the decision trace
	python -m context.supply audit traces/decisions.json
