.PHONY: surface
LABS += surface

surface:         ## Chapter 26: agent-facing MCP surface for outsiders
	python -m orchestration.surface build/surface
