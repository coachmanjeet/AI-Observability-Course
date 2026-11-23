.PHONY: recover
LABS += recover

recover:         ## Chapter 8: money moved, receipt didn't
	python -m audit.recover
