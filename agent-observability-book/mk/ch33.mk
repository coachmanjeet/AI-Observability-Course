.PHONY: govcloud
LABS += govcloud

govcloud:        ## Chapter 33: Gov Cloud configuration profile
	python -m comply.govcloud build/govcloud
