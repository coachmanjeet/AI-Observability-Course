.PHONY: entitlements
LABS += entitlements

entitlements:    ## Chapter 30: plans, quotas, budget kill switch
	python -m metering.entitlements build/entitlements
