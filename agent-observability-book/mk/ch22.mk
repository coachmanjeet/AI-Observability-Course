.PHONY: usage
LABS += usage

usage:           ## Chapter 22: usage events, idempotent, per tenant
	python -m metering.usage build/usage
