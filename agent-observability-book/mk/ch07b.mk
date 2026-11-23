.PHONY: recover
LABS += recover

recover:         ## Chapter 7: money moved, receipt didn't
	python -m audit.recover
