.PHONY: resources
LABS += resources

resources:       ## Chapter 10: MCP resources filtered per principal
	python -m context.resources build/resources
