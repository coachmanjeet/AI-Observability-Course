.PHONY: residency
LABS += residency

residency:       ## Chapter 32: residency-aware routing and where
	python -m comply.residency build/residency
