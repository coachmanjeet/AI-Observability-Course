.PHONY: discover
LABS += discover

discover:        ## Chapter 11: find every agent from seven sources
	python -m registry.discover registry/evidence build/discover
