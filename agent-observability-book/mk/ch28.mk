.PHONY: usage
LABS += usage

usage:           ## Chapter 28: usage events, idempotent, per tenant
	python -m metering.usage build/usage
