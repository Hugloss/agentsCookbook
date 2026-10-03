export PYTHONPATH := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))):$(PYTHONPATH)

.PHONY: benchmark-check benchmark-check-all benchmark-campaign-audit benchmark-status benchmark benchmark-new benchmark-resume benchmark-runs benchmark-smoke benchmark-qualify-localization benchmark-oracle-review benchmark-oracle-review-check benchmark-report benchmark-score benchmark-reports benchmark-evidence-validate benchmark-tool-probe-prepare benchmark-tool-probe-check benchmark-tool-probe-smoke benchmark-tool-probe-smoke-gate benchmark-tool-probe benchmark-tool-probe-resume benchmark-tool-probe-status benchmark-tool-probe-score

PROBE_DIR = .benchmark-runs/tool-probes/$(PROBE_SUBJECT)/v2
PROBE_SUITE = $(PROBE_DIR)/suite
PROBE_ENV = $(PROBE_SUITE)/.env
PROBE_RUNS = $(PROBE_DIR)/runs
PROBE_SMOKE = $(PROBE_DIR)/smoke

benchmark-tool-probe-prepare:
	@if [ "$(PROBE_SUBJECT)" != hashmarks ] && [ "$(PROBE_SUBJECT)" != enola ]; then \
		echo 'Set PROBE_SUBJECT=hashmarks or PROBE_SUBJECT=enola' >&2; exit 2; fi
	@uv run --no-project python -m benchmarks tool-probe-prepare \
		--suite benchmarks/suites/repository-intelligence/heldout-v1 \
		--subject $(PROBE_SUBJECT) --output-suite $(PROBE_SUITE) \
		--runtime-env-file .env --reuse

benchmark-tool-probe-check: benchmark-tool-probe-prepare
	@uv run --no-project python -m benchmarks oracle-review-check \
		--suite $(PROBE_SUITE) --require-complete
	@uv run --no-project python -m benchmarks check \
		--env-file $(PROBE_ENV) --agent opencode-native

benchmark-tool-probe-smoke: benchmark-tool-probe-check
	@uv run --no-project python -m benchmarks run --new \
		--env-file $(PROBE_ENV) --root $(PROBE_SMOKE) \
		--task locate-prefix-path-enumerator

benchmark-tool-probe-smoke-gate:
	@uv run --no-project python -m benchmarks tool-probe-smoke-gate \
		--root $(PROBE_SMOKE) --subject $(PROBE_SUBJECT)

benchmark-tool-probe: benchmark-tool-probe-check benchmark-tool-probe-smoke-gate
	@uv run --no-project python -m benchmarks run --new --env-file $(PROBE_ENV)

benchmark-tool-probe-resume:
	@uv run --no-project python -m benchmarks run --resume --env-file $(PROBE_ENV)

benchmark-tool-probe-status:
	@uv run --no-project python -m benchmarks status --env-file $(PROBE_ENV)

benchmark-tool-probe-score:
	@uv run --no-project python -m benchmarks score --env-file $(PROBE_ENV)

benchmark-oracle-review:
	@uv run --no-project python -m benchmarks oracle-review \
		--suite benchmarks/suites/repository-intelligence/heldout-v1 \
		--execute

benchmark-oracle-review-check:
	@uv run --no-project python -m benchmarks oracle-review-check \
		--suite benchmarks/suites/repository-intelligence/heldout-v1 \
		--require-complete

benchmark-check:
	@uv run --no-project python -m benchmarks check --env-file .env

benchmark-check-all:
	@uv run --no-project python -m benchmarks preflight --env-file .env

benchmark-campaign-audit:
	@uv run --no-project python -m benchmarks campaign-audit --env-file .env

benchmark-status:
	@uv run --no-project python -m benchmarks status --env-file .env

benchmark-reports:
	@uv run --no-project python -m benchmarks reports --env-file .env

benchmark:
	@uv run --no-project python -m benchmarks run --auto --env-file .env

benchmark-new:
	@uv run --no-project python -m benchmarks run --new --env-file .env

benchmark-resume:
	@uv run --no-project python -m benchmarks run --resume --env-file .env

benchmark-runs:
	@uv run --no-project python -m benchmarks runs --env-file .env

benchmark-smoke:
	@uv run --no-project python -m benchmarks run --new --env-file .env \
		--subject none --subject hashmarks --subject enola \
		--task locate-prefix-path-enumerator

benchmark-qualify-localization:
	@mkdir -p .benchmark-runs/heldout-v1; \
		qualification_root=$$(mktemp -d .benchmark-runs/heldout-v1/qualification.XXXXXX) || exit 2; \
			printf 'qualification root: %s\n' "$$qualification_root"; \
			if uv run --no-project python -m benchmarks run --new --env-file .env \
			--root "$$qualification_root" \
			--subject none --subject hashmarks --subject enola \
			--task locate-prefix-path-enumerator \
			--task locate-stale-index-removal \
			--task locate-directory-pruning \
			--task locate-mcp-task-evidence \
			--task locate-repository-content-identity \
			--task locate-terminal-run-check; then \
		uv run --no-project python -m benchmarks status --env-file .env \
			--root "$$qualification_root" --require-qualified \
			--subject none --subject hashmarks --subject enola \
			--task locate-prefix-path-enumerator \
			--task locate-stale-index-removal \
			--task locate-directory-pruning \
			--task locate-mcp-task-evidence \
			--task locate-repository-content-identity \
			--task locate-terminal-run-check; \
		else exit 1; fi

benchmark-evidence-validate:
	@uv run --no-project python -m benchmarks.evidence validate \
		--corpus benchmarks/suites/repository-intelligence/multidomain-v2/evidence.json

benchmark-report:
	@uv run --no-project python -m benchmarks report --env-file .env

benchmark-score:
	@uv run --no-project python -m benchmarks score --env-file .env
