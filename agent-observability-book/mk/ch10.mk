.PHONY: semantics
LABS += semantics

semantics:       ## Chapter 10: raw SQL vs the governed metric
	python -m context.semantic build/semantics
