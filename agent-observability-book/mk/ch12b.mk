.PHONY: delegation
LABS += delegation

delegation:      ## Chapter 12: token exchange, consent, for_whom
	python -m identity.delegation build/delegation
