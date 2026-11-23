.PHONY: registry
LABS += registry

registry:        ## Chapter 11: one registry, owners, tiers, lifecycle
	python -m registry.registry build/registry
