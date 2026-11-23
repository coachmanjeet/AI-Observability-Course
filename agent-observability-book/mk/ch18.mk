.PHONY: tower
LABS += tower

tower:           ## Chapter 18: control tower over 1P and 3P agents
	python -m orchestration.tower build/tower
