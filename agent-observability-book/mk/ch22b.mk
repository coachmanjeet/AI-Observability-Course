.PHONY: pricing
LABS += pricing

pricing:         ## Chapter 22: six pricing models on pilot traffic
	python -m metering.pricing build/pricing
