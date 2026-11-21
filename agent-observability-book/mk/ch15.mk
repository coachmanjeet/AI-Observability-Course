.PHONY: registry
LABS += registry

registry:        ## Chapter 15: one registry, owners, tiers, lifecycle
	python -m registry.registry build/registry
