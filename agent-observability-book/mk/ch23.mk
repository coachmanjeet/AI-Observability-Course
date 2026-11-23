.PHONY: entitlements
LABS += entitlements

entitlements:    ## Chapter 23: plans, quotas, budget kill switch
	python -m metering.entitlements build/entitlements
