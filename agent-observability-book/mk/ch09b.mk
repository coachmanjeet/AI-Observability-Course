.PHONY: memory
LABS += memory

memory:          ## Chapter 9: scoped, expiring, erasable memory
	python -m context.memory build/memory
