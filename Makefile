PYTHON ?= python3
SNAPSHOT_SCRIPT := infra/scripts/generate_snapshot.py
SNAPSHOT_OUT ?= snapshot.md
SNAPSHOT_JSON ?= snapshot.json

.PHONY: snapshot snapshot-json verify

snapshot:
	@$(PYTHON) $(SNAPSHOT_SCRIPT) -o $(SNAPSHOT_OUT)

snapshot-json:
	@$(PYTHON) $(SNAPSHOT_SCRIPT) --format json -o $(SNAPSHOT_JSON)

verify:
	@$(PYTHON) $(SNAPSHOT_SCRIPT) -o $(SNAPSHOT_OUT)
	@$(PYTHON) -m pytest
