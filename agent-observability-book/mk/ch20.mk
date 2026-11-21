.PHONY: redteam
LABS += redteam

redteam:         ## Chapter 20: OWASP Agentic Top 10 red team
	python -m policy.redteam build/redteam
