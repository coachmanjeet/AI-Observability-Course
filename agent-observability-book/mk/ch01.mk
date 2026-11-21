.PHONY: demo
LABS += demo

demo:            ## Chapter 1: replay the 2 a.m. incident
	python -m incident.replay
