.PHONY: fleetops
LABS += fleetops

fleetops:        ## Chapter 19: canary drift, incident drill, retire
	python -m orchestration.fleetops build/fleetops
