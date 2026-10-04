.PHONY: benchmark-check benchmark-check-all benchmark-doctor benchmark-campaign-audit benchmark-status benchmark benchmark-new benchmark-resume benchmark-runs benchmark-smoke benchmark-qualify-localization benchmark-oracle-review benchmark-oracle-review-check benchmark-report benchmark-score benchmark-reports benchmark-evidence-validate benchmark-tool-probe-prepare benchmark-tool-probe-check benchmark-tool-probe-smoke benchmark-tool-probe-smoke-gate benchmark-tool-probe benchmark-tool-probe-resume benchmark-tool-probe-status benchmark-tool-probe-score benchmark-openai-routing-check benchmark-openai-routing-dogfood

PROBE_DIR = .benchmark-runs/tool-probes/$(PROBE_SUBJECT)/v2
PROBE_SUITE = $(PROBE_DIR)/suite
PROBE_ENV = $(PROBE_SUITE)/.env
PROBE_RUNS = $(PROBE_DIR)/runs
PROBE_SMOKE = $(PROBE_DIR)/smoke

OPENAI_ROUTING_WORKSPACE ?= $(CURDIR)
OPENAI_ROUTING_HANDOFF ?= ../Hashmarks/dist/chatgpt-secure-mcp-tunnel-handoff.json
OPENAI_ROUTING_TUNNEL_CLIENT ?= $(shell command -v tunnel-client 2>/dev/null)
OPENAI_ROUTING_TUNNEL_ID ?=
OPENAI_ROUTING_MODEL ?=
OPENAI_ROUTING_MANIFEST ?= benchmarks/dogfood/openai-routing-v1.json
OPENAI_ROUTING_REPEATS ?= 1
OPENAI_ROUTING_RUN_ROOT ?= .benchmark-runs/openai-routing

benchmark-openai-routing-check:
	@if [ -z "$(OPENAI_ROUTING_TUNNEL_CLIENT)" ]; then echo 'Set OPENAI_ROUTING_TUNNEL_CLIENT or install tunnel-client' >&2; exit 2; fi
	@if [ -z "$(OPENAI_ROUTING_TUNNEL_ID)" ]; then echo 'Set OPENAI_ROUTING_TUNNEL_ID=tunnel_<32 hex>' >&2; exit 2; fi
	@if [ -z "$(OPENAI_ROUTING_MODEL)" ]; then echo 'Set OPENAI_ROUTING_MODEL to an explicit tool-capable Responses model' >&2; exit 2; fi
	@mkdir -p "$(OPENAI_ROUTING_RUN_ROOT)"
	@./benchmark openai-routing-preflight \
		--workspace "$(OPENAI_ROUTING_WORKSPACE)" \
		--handoff "$(OPENAI_ROUTING_HANDOFF)" \
		--tunnel-client "$(OPENAI_ROUTING_TUNNEL_CLIENT)" \
		--tunnel-id "$(OPENAI_ROUTING_TUNNEL_ID)" \
		--model "$(OPENAI_ROUTING_MODEL)" \
		--manifest "$(OPENAI_ROUTING_MANIFEST)" \
		--output "$(OPENAI_ROUTING_RUN_ROOT)/preflight.json"

benchmark-openai-routing-dogfood: benchmark-openai-routing-check
	@run_root="$(OPENAI_ROUTING_RUN_ROOT)/run-$(date -u +%Y%m%dT%H%M%SZ)-$$"; \
		echo "OpenAI routing dogfood run: $run_root"; \
		./benchmark openai-routing-dogfood \
			--workspace "$(OPENAI_ROUTING_WORKSPACE)" \
			--handoff "$(OPENAI_ROUTING_HANDOFF)" \
			--tunnel-client "$(OPENAI_ROUTING_TUNNEL_CLIENT)" \
			--tunnel-id "$(OPENAI_ROUTING_TUNNEL_ID)" \
			--model "$(OPENAI_ROUTING_MODEL)" \
			--manifest "$(OPENAI_ROUTING_MANIFEST)" \
			--repeats "$(OPENAI_ROUTING_REPEATS)" \
			--output-dir "$run_root"

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
