.PHONY: audit audit-attacks replay
LABS += audit audit-attacks replay

audit:           ## Chapter 8: build and verify the receipt store
	python -m audit.run build/audit

audit-attacks:   ## Chapter 8: tamper with the store five ways
	python -m audit.run --attacks build/audit

replay:          ## Chapter 8: replay the night's blocked refunds
	python -m audit.replay --all
