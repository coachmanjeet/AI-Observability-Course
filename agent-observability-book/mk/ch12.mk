.PHONY: identity
LABS += identity

identity:        ## Chapter 12: attest, issue and verify agent identity
	python -m identity.workload build/identity
