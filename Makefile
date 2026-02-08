PYTHON ?= .venv/bin/python
SNAPSHOT_SCRIPT := infra/scripts/generate_snapshot.py
BACKUP_SCRIPT := infra/scripts/backup_restore.py
SNAPSHOT_OUT ?= snapshot.md
SNAPSHOT_JSON ?= snapshot.json
EVAL_SCRIPT := infra/scripts/evaluate_search.py
JUDGED_QUERIES ?= data/eval/uhj_judged_queries.json
SEARCH_GATE_LIMIT ?= 5
SEARCH_GATE_MIN_HIT_RATE ?= 0.65
SEARCH_GATE_MIN_MRR ?= 0.60
SEARCH_GATE_MAX_P95_MS ?= 250.0
SEARCH_GATE_MIN_NO_HIT_ACCURACY ?= 0.90

.PHONY: snapshot snapshot-json verify search-gate backup-roundtrip security-check release-check

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

backup-roundtrip:
	@.venv/bin/python $(BACKUP_SCRIPT) roundtrip --output /tmp/letterops-release-roundtrip.tar.gz

security-check:
	@$(PYTHON) -m pip check
	@$(PYTHON) -m pip_audit --cache-dir /tmp/pip-audit-cache --ignore-vuln CVE-2024-23342

release-check: verify search-gate backup-roundtrip security-check
