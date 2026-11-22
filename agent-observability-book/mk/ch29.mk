.PHONY: pricing
LABS += pricing

pricing:         ## Chapter 29: six pricing models on pilot traffic
	python -m metering.pricing build/pricing
