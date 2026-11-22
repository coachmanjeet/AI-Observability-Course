.PHONY: shiphold
LABS += shiphold

SHIPHOLD_INPUTS = packs memory registry identity delegation \
  privilege policy oversight topologies fleetops value \
  entitlements residency

shiphold: $(SHIPHOLD_INPUTS)  ## Chapter 34: Ship or Hold
	python -m shiphold.review build/shiphold
