.PHONY: evidence
LABS += evidence

evidence:        ## Chapter 24: evidence pack for EU AI Act, ISO, NIST
	python -m comply.evidence build/comply

.PHONY: outside
LABS += outside

outside:         ## Chapter 24: verify a sampled pack as the customer
	python -m audit.outside build/outside
