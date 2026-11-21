.PHONY: packs packs-tamper
LABS += packs packs-tamper

packs:           ## Chapter 11: build, sign, gate and release packs
	python -m context.packs release build/packs

packs-tamper:    ## Chapter 11: edit a built pack and verify it
	python -m context.packs tamper build/packs
