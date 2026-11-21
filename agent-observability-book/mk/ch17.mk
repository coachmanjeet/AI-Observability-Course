.PHONY: delegation
LABS += delegation

delegation:      ## Chapter 17: token exchange, consent, for_whom
	python -m identity.delegation build/delegation
