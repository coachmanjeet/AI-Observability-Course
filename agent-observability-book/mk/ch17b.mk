.PHONY: durable
LABS += durable

durable:         ## Chapter 17: durable workflow with voice and vision
	python -m orchestration.durable build/durable
