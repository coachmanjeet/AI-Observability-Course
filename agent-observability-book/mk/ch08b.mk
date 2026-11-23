.PHONY: semantics
LABS += semantics

semantics:       ## Chapter 8: raw SQL vs the governed metric
	python -m context.semantic build/semantics
