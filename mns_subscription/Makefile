test:
	@PYTHONPATH=src:tests python -m unittest

cover:
	@PYTHONPATH=src:tests coverage run -m unittest discover

report:
	coverage report -m
.PHONY: build package test
