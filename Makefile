BENCHMARK_TARGETS := benchmark-check benchmark-check-all benchmark-doctor benchmark-campaign-audit benchmark-status benchmark benchmark-new benchmark-resume benchmark-runs benchmark-smoke benchmark-qualify-localization benchmark-oracle-review benchmark-oracle-review-check benchmark-report benchmark-score benchmark-reports benchmark-evidence-validate benchmark-tool-probe-prepare benchmark-tool-probe-check benchmark-tool-probe-smoke benchmark-tool-probe-smoke-gate benchmark-tool-probe benchmark-tool-probe-resume benchmark-tool-probe-status benchmark-tool-probe-score benchmark-openai-routing benchmark-openai-routing-new benchmark-openai-routing-check benchmark-openai-routing-runs benchmark-openai-routing-status benchmark-openai-routing-dogfood benchmark-context-invariance benchmark-context-invariance-check benchmark-context-invariance-check-all benchmark-context-invariance-qualify-check benchmark-context-invariance-qualify benchmark-context-invariance-qualify-resume benchmark-context-invariance-qualify-status benchmark-context-invariance-new benchmark-context-invariance-resume benchmark-context-invariance-runs benchmark-context-invariance-status benchmark-context-invariance-reports benchmark-harness-explain benchmark-harness-ablation benchmark-harness-find-ablation benchmark-harness-change-impact-ablation benchmark-harness-post-change-ablation benchmark-harness-correlate-evidence-ablation benchmark-harness-repository-declarations-ablation benchmark-harness-dependency-codemap-ablation benchmark-harness-verification-explanation-ablation
.PHONY: $(BENCHMARK_TARGETS)

BENCHMARK_REQUESTED_GOALS := $(filter benchmark benchmark-%,$(MAKECMDGOALS))
BENCHMARK_UNKNOWN_GOALS := $(filter-out $(BENCHMARK_TARGETS),$(BENCHMARK_REQUESTED_GOALS))
BENCHMARK_MAKE_SHORT_FLAGS := $(firstword $(MAKEFLAGS))

ifneq ($(strip $(BENCHMARK_UNKNOWN_GOALS)),)
$(error unknown benchmark target '$(firstword $(BENCHMARK_UNKNOWN_GOALS))'; did you mean one of the declared BENCHMARK_TARGETS?)
endif

ifneq ($(strip $(BENCHMARK_REQUESTED_GOALS)),)
ifneq ($(findstring n,$(BENCHMARK_MAKE_SHORT_FLAGS)),)
ifneq ($(findstring e,$(BENCHMARK_MAKE_SHORT_FLAGS)),)
ifneq ($(findstring w,$(BENCHMARK_MAKE_SHORT_FLAGS)),)
$(error benchmark targets refuse suspicious Make flags '-n -e -w'; if you meant 'make benchmark-new', remove the space)
endif
endif
endif
endif

PROBE_DIR = .benchmark-runs/tool-probes/$(PROBE_SUBJECT)/v2
PROBE_SUITE = $(PROBE_DIR)/suite
PROBE_ENV = $(PROBE_SUITE)/.env
PROBE_RUNS = $(PROBE_DIR)/runs
PROBE_SMOKE = $(PROBE_DIR)/smoke

OPENAI_ROUTING_ENV ?= .env
CONTEXT_INVARIANCE_ENV ?= .env.context-invariance
MATRIX ?= heldout
BENCHMARK_ENV ?= .env
BENCHMARK_RUN_ID_FLAG = $(if $(RUN_ID),--run-id "$(RUN_ID)",)
HARBOR_MATRIX ?= harbor-full
HARBOR_ABLATION_MATRIX ?= harbor-ablation-full
HARBOR_FIND_ABLATION_MATRIX ?= harbor-find-ablation-full
HARBOR_CHANGE_IMPACT_ABLATION_MATRIX ?= harbor-change-impact-ablation-full
HARBOR_POST_CHANGE_ABLATION_MATRIX ?= harbor-post-change-ablation-full
HARBOR_CORRELATE_EVIDENCE_ABLATION_MATRIX ?= harbor-correlate-evidence-ablation-full
HARBOR_REPOSITORY_DECLARATIONS_ABLATION_MATRIX ?= harbor-repository-declarations-ablation-full
HARBOR_DEPENDENCY_CODEMAP_ABLATION_MATRIX ?= harbor-dependency-codemap-ablation-full
HARBOR_VERIFICATION_EXPLANATION_ABLATION_MATRIX ?= harbor-verification-explanation-ablation-full

benchmark-harness-explain:
	@./benchmark explain --env-file "$(BENCHMARK_ENV)" \
		--matrix "$(HARBOR_MATRIX)" $(BENCHMARK_RUN_ID_FLAG)

benchmark-harness-ablation:
	@./benchmark ablation --env-file "$(BENCHMARK_ENV)" \
		--matrix "$(HARBOR_ABLATION_MATRIX)" $(BENCHMARK_RUN_ID_FLAG)

benchmark-harness-find-ablation:
	@./benchmark ablation --env-file "$(BENCHMARK_ENV)" \
		--matrix "$(HARBOR_FIND_ABLATION_MATRIX)" $(BENCHMARK_RUN_ID_FLAG)

benchmark-harness-change-impact-ablation:
	@./benchmark ablation --env-file "$(BENCHMARK_ENV)" \
		--matrix "$(HARBOR_CHANGE_IMPACT_ABLATION_MATRIX)" $(BENCHMARK_RUN_ID_FLAG)

benchmark-harness-post-change-ablation:
	@./benchmark ablation --env-file "$(BENCHMARK_ENV)" \
		--matrix "$(HARBOR_POST_CHANGE_ABLATION_MATRIX)" $(BENCHMARK_RUN_ID_FLAG)

benchmark-harness-correlate-evidence-ablation:
	@./benchmark ablation --env-file "$(BENCHMARK_ENV)" \
		--matrix "$(HARBOR_CORRELATE_EVIDENCE_ABLATION_MATRIX)" $(BENCHMARK_RUN_ID_FLAG)

benchmark-harness-repository-declarations-ablation:
	@./benchmark ablation --env-file "$(BENCHMARK_ENV)" \
		--matrix "$(HARBOR_REPOSITORY_DECLARATIONS_ABLATION_MATRIX)" $(BENCHMARK_RUN_ID_FLAG)

benchmark-harness-dependency-codemap-ablation:
	@./benchmark ablation --env-file "$(BENCHMARK_ENV)" \
		--matrix "$(HARBOR_DEPENDENCY_CODEMAP_ABLATION_MATRIX)" $(BENCHMARK_RUN_ID_FLAG)

benchmark-harness-verification-explanation-ablation:
	@./benchmark ablation --env-file "$(BENCHMARK_ENV)" \
		--matrix "$(HARBOR_VERIFICATION_EXPLANATION_ABLATION_MATRIX)" $(BENCHMARK_RUN_ID_FLAG)

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

benchmark-context-invariance-qualify-resume:
	@if [ -z "$(RUN_ID)" ]; then echo 'Set RUN_ID to the context-invariance run to resume' >&2; exit 2; fi
	@./benchmark run --resume --run-id "$(RUN_ID)" --env-file "$(CONTEXT_INVARIANCE_ENV)" \
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
	@if [ -z "$(RUN_ID)" ]; then echo 'Set RUN_ID to the context-invariance run to resume' >&2; exit 2; fi
	@./benchmark run --resume --run-id "$(RUN_ID)" --env-file "$(CONTEXT_INVARIANCE_ENV)"

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
	@if [ -z "$(PROBE_SUBJECT)" ]; then \
		echo 'Set PROBE_SUBJECT to a non-control subject id from the selected suite' >&2; exit 2; fi
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
	@if [ -z "$(RUN_ID)" ]; then echo 'Set RUN_ID to the tool-probe run to resume' >&2; exit 2; fi
	@./benchmark run --resume --run-id "$(RUN_ID)" --env-file $(PROBE_ENV)

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
	@./benchmark check --env-file "$(BENCHMARK_ENV)" --matrix "$(MATRIX)"

benchmark-doctor:
	@./benchmark doctor --env-file "$(BENCHMARK_ENV)" --matrix "$(MATRIX)"

benchmark-check-all:
	@./benchmark preflight --env-file "$(BENCHMARK_ENV)" --matrix "$(MATRIX)"

benchmark-campaign-audit:
	@./benchmark campaign-audit --env-file "$(BENCHMARK_ENV)" --matrix "$(MATRIX)"

benchmark-status:
	@./benchmark status --env-file "$(BENCHMARK_ENV)" --matrix "$(MATRIX)" $(BENCHMARK_RUN_ID_FLAG)

benchmark-reports:
	@./benchmark reports --env-file "$(BENCHMARK_ENV)" --matrix "$(MATRIX)" $(BENCHMARK_RUN_ID_FLAG)

benchmark:
	@./benchmark run --auto --env-file "$(BENCHMARK_ENV)" --matrix "$(MATRIX)"

benchmark-new:
	@./benchmark run --new --env-file "$(BENCHMARK_ENV)" --matrix "$(MATRIX)" --no-json-results

benchmark-resume:
	@if [ -z "$(RUN_ID)" ]; then echo 'Set RUN_ID to a saved run ID from make benchmark-runs MATRIX=$(MATRIX)' >&2; exit 2; fi
	@./benchmark run --resume --run-id "$(RUN_ID)" --env-file "$(BENCHMARK_ENV)" --matrix "$(MATRIX)"

benchmark-runs:
	@./benchmark runs --env-file "$(BENCHMARK_ENV)" --matrix "$(MATRIX)"

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
	@./benchmark report --env-file "$(BENCHMARK_ENV)" --matrix "$(MATRIX)" $(BENCHMARK_RUN_ID_FLAG)

benchmark-score:
	@./benchmark score --env-file "$(BENCHMARK_ENV)" --matrix "$(MATRIX)" $(BENCHMARK_RUN_ID_FLAG)
