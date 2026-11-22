.PHONY: evidence
LABS += evidence

evidence:        ## Chapter 31: evidence pack for EU AI Act, ISO, NIST
	python -m comply.evidence build/comply
