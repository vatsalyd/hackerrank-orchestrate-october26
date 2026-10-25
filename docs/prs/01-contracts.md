Title: Validate deletion-audit inputs and output contracts

Adds a Python CLI, participant-only dataset loading, strict output types, cutoff-aware citation validation, and canonical operation ordering. Invalid evidence paths, malformed CSV rows, unsupported step combinations, and future citations fail explicitly.

Validation: `python code/main.py inventory`; `python -m unittest discover -s code/tests -v`.
