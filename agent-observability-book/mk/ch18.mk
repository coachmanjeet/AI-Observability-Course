.PHONY: privilege
LABS += privilege

privilege:       ## Chapter 18: permission diff, drift, task tokens
	python -m policy.privilege build/privilege
