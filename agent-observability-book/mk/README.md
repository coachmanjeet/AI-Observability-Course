One make fragment per chapter from Chapter 8 on: `mk/chNN.mk`.
Each adds its lab targets and appends them to `LABS`, so
`make labs` runs every chapter's lab, and CI runs `make labs`.
