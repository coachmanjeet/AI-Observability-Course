.PHONY: privilege
LABS += privilege

privilege:       ## Chapter 13: permission diff, drift, task tokens
	python -m policy.privilege build/privilege
