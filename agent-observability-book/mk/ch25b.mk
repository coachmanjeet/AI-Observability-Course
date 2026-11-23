.PHONY: govcloud
LABS += govcloud

govcloud:        ## Chapter 25: Gov Cloud configuration profile
	python -m comply.govcloud build/govcloud
