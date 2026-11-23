.PHONY: live

# Not in LABS: it needs a model endpoint. See pronto/live.py.
live:            ## Chapter 4: optional, Speedy on a real model; OTLP=url exports
	python -m pronto.live build/live/trace.json $(if $(OTLP),--otlp $(OTLP))
	python -m telemetry.lint build/live/trace.json
