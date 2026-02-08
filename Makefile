PYTHON ?= python3
SNAPSHOT_SCRIPT := infra/scripts/generate_snapshot.py
SNAPSHOT_OUT ?= snapshot.md
SNAPSHOT_JSON ?= snapshot.json
EVAL_SCRIPT := infra/scripts/evaluate_search.py
JUDGED_QUERIES ?= data/eval/uhj_judged_queries.json
SEARCH_GATE_LIMIT ?= 5
SEARCH_GATE_MIN_HIT_RATE ?= 0.65
SEARCH_GATE_MIN_MRR ?= 0.60
SEARCH_GATE_MAX_P95_MS ?= 250.0
SEARCH_GATE_MIN_NO_HIT_ACCURACY ?= 0.90

.PHONY: snapshot snapshot-json verify search-gate

snapshot:
	@$(PYTHON) $(SNAPSHOT_SCRIPT) -o $(SNAPSHOT_OUT)

snapshot-json:
	@$(PYTHON) $(SNAPSHOT_SCRIPT) --format json -o $(SNAPSHOT_JSON)

verify:
	@$(PYTHON) $(SNAPSHOT_SCRIPT) -o $(SNAPSHOT_OUT)
	@$(PYTHON) -m pytest

search-gate:
	@.venv/bin/python $(EVAL_SCRIPT) \
		--queries-file $(JUDGED_QUERIES) \
		--vector-mode on \
		--limit $(SEARCH_GATE_LIMIT) \
		--min-hit-rate-at-k $(SEARCH_GATE_MIN_HIT_RATE) \
		--min-mrr $(SEARCH_GATE_MIN_MRR) \
		--max-p95-ms $(SEARCH_GATE_MAX_P95_MS) \
		--min-no-hit-accuracy $(SEARCH_GATE_MIN_NO_HIT_ACCURACY) \
		--fail-on-gate
