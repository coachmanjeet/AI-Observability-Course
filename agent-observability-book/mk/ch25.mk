.PHONY: residency
LABS += residency

residency:       ## Chapter 25: residency-aware routing and where
	python -m comply.residency build/residency
