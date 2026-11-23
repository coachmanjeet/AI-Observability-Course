.PHONY: policy
LABS += policy

policy:          ## Chapter 14: Cedar policy at the MCP gateway
	python -m policy.gateway build/policy
