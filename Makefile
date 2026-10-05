.PHONY: benchmark-check benchmark-check-all benchmark-doctor benchmark-campaign-audit benchmark-status benchmark benchmark-new benchmark-resume benchmark-runs benchmark-smoke benchmark-qualify-localization benchmark-oracle-review benchmark-oracle-review-check benchmark-report benchmark-score benchmark-reports benchmark-evidence-validate benchmark-tool-probe-prepare benchmark-tool-probe-check benchmark-tool-probe-smoke benchmark-tool-probe-smoke-gate benchmark-tool-probe benchmark-tool-probe-resume benchmark-tool-probe-status benchmark-tool-probe-score benchmark-openai-routing benchmark-openai-routing-new benchmark-openai-routing-check benchmark-openai-routing-runs benchmark-openai-routing-status benchmark-openai-routing-dogfood benchmark-context-invariance benchmark-context-invariance-check benchmark-context-invariance-check-all benchmark-context-invariance-qualify-check benchmark-context-invariance-qualify benchmark-context-invariance-qualify-status benchmark-context-invariance-new benchmark-context-invariance-resume benchmark-context-invariance-runs benchmark-context-invariance-status benchmark-context-invariance-reports

PROBE_DIR = .benchmark-runs/tool-probes/$(PROBE_SUBJECT)/v2
PROBE_SUITE = $(PROBE_DIR)/suite
PROBE_ENV = $(PROBE_SUITE)/.env
PROBE_RUNS = $(PROBE_DIR)/runs
PROBE_SMOKE = $(PROBE_DIR)/smoke

OPENAI_ROUTING_ENV ?= .env
CONTEXT_INVARIANCE_ENV ?= .env.context-invariance

benchmark-context-invariance:
	@./benchmark run --auto --env-file "$(CONTEXT_INVARIANCE_ENV)"

benchmark-context-invariance-check:
	@./benchmark check --env-file "$(CONTEXT_INVARIANCE_ENV)"

benchmark-context-invariance-check-all:
	@./benchmark preflight --env-file "$(CONTEXT_INVARIANCE_ENV)"

benchmark-context-invariance-qualify-check:
	@./benchmark preflight --env-file "$(CONTEXT_INVARIANCE_ENV)" \
		--task locate-prefix-path-enumerator \
		--subject none --subject hashmarks

benchmark-context-invariance-qualify:
	@./benchmark run --new --env-file "$(CONTEXT_INVARIANCE_ENV)" \
		--task locate-prefix-path-enumerator \
		--subject none --subject hashmarks

benchmark-context-invariance-qualify-status:
	@./benchmark status --env-file "$(CONTEXT_INVARIANCE_ENV)" \
		--task locate-prefix-path-enumerator \
		--subject none --subject hashmarks \
		--require-qualified
	@./benchmark score --env-file "$(CONTEXT_INVARIANCE_ENV)" \
		--require-analysis-evidence

benchmark-context-invariance-new:
	@./benchmark run --new --env-file "$(CONTEXT_INVARIANCE_ENV)"

benchmark-context-invariance-resume:
	@./benchmark run --resume --env-file "$(CONTEXT_INVARIANCE_ENV)"

benchmark-context-invariance-runs:
	@./benchmark runs --env-file "$(CONTEXT_INVARIANCE_ENV)"

benchmark-context-invariance-status:
	@./benchmark status --env-file "$(CONTEXT_INVARIANCE_ENV)"

benchmark-context-invariance-reports:
	@./benchmark reports --env-file "$(CONTEXT_INVARIANCE_ENV)"

benchmark-openai-routing: benchmark-openai-routing-new

benchmark-openai-routing-new:
	@./benchmark openai-routing-new --env-file "$(OPENAI_ROUTING_ENV)"

benchmark-openai-routing-check:
	@./benchmark openai-routing-check --env-file "$(OPENAI_ROUTING_ENV)"

benchmark-openai-routing-runs:
	@./benchmark openai-routing-runs --env-file "$(OPENAI_ROUTING_ENV)"

benchmark-openai-routing-status:
	@./benchmark openai-routing-status --env-file "$(OPENAI_ROUTING_ENV)"

benchmark-openai-routing-dogfood: benchmark-openai-routing-new

benchmark-tool-probe-prepare:
	@if [ "$(PROBE_SUBJECT)" != hashmarks ] && [ "$(PROBE_SUBJECT)" != enola ]; then \
		echo 'Set PROBE_SUBJECT=hashmarks or PROBE_SUBJECT=enola' >&2; exit 2; fi
	@./benchmark tool-probe-prepare \
		--suite benchmarks/suites/repository-intelligence/heldout-v1 \
		--subject $(PROBE_SUBJECT) --output-suite $(PROBE_SUITE) \
		--runtime-env-file .env --reuse

benchmark-tool-probe-check: benchmark-tool-probe-prepare
	@./benchmark oracle-review-check \
		--suite $(PROBE_SUITE) --require-complete
	@./benchmark check \
		--env-file $(PROBE_ENV) --agent opencode-native

benchmark-tool-probe-smoke: benchmark-tool-probe-check
	@./benchmark run --new \
		--env-file $(PROBE_ENV) --root $(PROBE_SMOKE) \
		--task locate-prefix-path-enumerator

benchmark-tool-probe-smoke-gate:
	@./benchmark tool-probe-smoke-gate \
		--root $(PROBE_SMOKE) --subject $(PROBE_SUBJECT)

benchmark-tool-probe: benchmark-tool-probe-check benchmark-tool-probe-smoke-gate
	@./benchmark run --new --env-file $(PROBE_ENV)

benchmark-tool-probe-resume:
	@./benchmark run --resume --env-file $(PROBE_ENV)

benchmark-tool-probe-status:
	@./benchmark status --env-file $(PROBE_ENV)

benchmark-tool-probe-score:
	@./benchmark score --env-file $(PROBE_ENV)

benchmark-oracle-review:
	@./benchmark oracle-review \
		--suite benchmarks/suites/repository-intelligence/heldout-v1 \
		--execute

benchmark-oracle-review-check:
	@./benchmark oracle-review-check \
		--suite benchmarks/suites/repository-intelligence/heldout-v1 \
		--require-complete

benchmark-check:
	@./benchmark check --env-file .env

benchmark-doctor:
	@./benchmark doctor --env-file .env

benchmark-check-all:
	@./benchmark preflight --env-file .env

benchmark-campaign-audit:
	@./benchmark campaign-audit --env-file .env

benchmark-status:
	@./benchmark status --env-file .env

benchmark-reports:
	@./benchmark reports --env-file .env

benchmark:
	@./benchmark run --auto --env-file .env

benchmark-new:
	@./benchmark run --new --env-file .env

benchmark-resume:
	@./benchmark run --resume --env-file .env

benchmark-runs:
	@./benchmark runs --env-file .env

benchmark-smoke:
	@./benchmark run --new --env-file .env \
		--subject none --subject hashmarks --subject enola \
		--task locate-prefix-path-enumerator

benchmark-qualify-localization:
	@mkdir -p .benchmark-runs/heldout-v1; \
		qualification_root=$$(mktemp -d .benchmark-runs/heldout-v1/qualification.XXXXXX) || exit 2; \
			printf 'qualification root: %s\n' "$$qualification_root"; \
			if ./benchmark run --new --env-file .env \
			--root "$$qualification_root" \
			--subject none --subject hashmarks --subject enola \
			--task locate-prefix-path-enumerator \
			--task locate-stale-index-removal \
			--task locate-directory-pruning \
			--task locate-mcp-task-evidence \
			--task locate-repository-content-identity \
			--task locate-terminal-run-check; then \
		./benchmark status --env-file .env \
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
	@./benchmark report --env-file .env

benchmark-score:
	@./benchmark score --env-file .env
