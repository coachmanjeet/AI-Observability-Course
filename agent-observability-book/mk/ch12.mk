.PHONY: memory
LABS += memory

memory:          ## Chapter 12: scoped, expiring, erasable memory
	python -m context.memory build/memory
