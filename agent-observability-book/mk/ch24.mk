.PHONY: evidence
LABS += evidence

evidence:        ## Chapter 24: evidence pack for EU AI Act, ISO, NIST
	python -m comply.evidence build/comply
