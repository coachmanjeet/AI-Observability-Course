.PHONY: topologies
LABS += topologies

topologies:      ## Chapter 17: one task, four topologies, scored
	python -m orchestration.score build/orchestration
