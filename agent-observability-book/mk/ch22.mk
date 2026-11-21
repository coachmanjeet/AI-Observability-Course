.PHONY: topologies
LABS += topologies

topologies:      ## Chapter 22: one task, four topologies, scored
	python -m orchestration.score build/orchestration
