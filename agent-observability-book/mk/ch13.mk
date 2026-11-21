.PHONY: resources
LABS += resources

resources:       ## Chapter 13: MCP resources filtered per principal
	python -m context.resources build/resources
