-include .env

.PHONY: benchmark-check benchmark-check-all benchmark benchmark-report benchmark-score \
	_benchmark-suite-env _benchmark-agent-env _benchmark-campaign-env \
	_benchmark-selected-campaign-env _benchmark-execution-env _benchmark-score-env

_benchmark-suite-env:
	@test -f .env || { \
		echo "ERROR: .env is required. Copy .env.example to .env and set benchmark authority values."; \
		exit 2; \
	}
	@test -n "$(strip $(BENCHMARK_SUITE_PATH))" || { \
		echo "ERROR: BENCHMARK_SUITE_PATH must point to the committed benchmark suite definition in .env."; \
		exit 2; \
	}

_benchmark-agent-env: _benchmark-suite-env
	@awk -F= '$$1 ~ /^[[:space:]]*BENCHMARK_AGENT[[:space:]]*$$/ { \
		value = $$2; sub(/[[:space:]]*#.*/, "", value); \
		gsub(/[[:space:]]/, "", value); if (value != "") found = 1; \
	} END { exit !found }' .env || { \
		echo "ERROR: set BENCHMARK_AGENT explicitly in .env before selected-agent work."; \
		exit 2; \
	}
	@test -n "$(strip $(BENCHMARK_AGENT))" || { \
		echo "ERROR: set BENCHMARK_AGENT explicitly in .env before selected-agent work."; \
		exit 2; \
	}

_benchmark-campaign-env: _benchmark-suite-env
	@test -n "$(strip $(BENCHMARK_CAMPAIGN_ROOT))" || { \
		echo "ERROR: BENCHMARK_CAMPAIGN_ROOT must name the writable campaign cache/work/results directory in .env."; \
		exit 2; \
	}

_benchmark-selected-campaign-env: _benchmark-campaign-env _benchmark-agent-env

_benchmark-execution-env: _benchmark-selected-campaign-env
	@test -n "$(strip $(BENCHMARK_HARNESS_REPO_ROOT))" || { \
		echo "ERROR: BENCHMARK_HARNESS_REPO_ROOT must point to the agentsCookbook checkout in .env."; \
		exit 2; \
	}

benchmark-check: _benchmark-suite-env
	@uv run --no-project python -m benchmarks check \
		--env-file .env \
		--suite "$(BENCHMARK_SUITE_PATH)"

benchmark-check-all: _benchmark-execution-env
	@uv run --no-project python -m benchmarks preflight \
		--env-file .env \
		--suite "$(BENCHMARK_SUITE_PATH)" \
		--root "$(BENCHMARK_CAMPAIGN_ROOT)" \
		--harness-root "$(BENCHMARK_HARNESS_REPO_ROOT)" \
		--agent "$(BENCHMARK_AGENT)"

benchmark: _benchmark-execution-env
	@uv run --no-project python -m benchmarks run \
		--env-file .env \
		--suite "$(BENCHMARK_SUITE_PATH)" \
		--root "$(BENCHMARK_CAMPAIGN_ROOT)" \
		--harness-root "$(BENCHMARK_HARNESS_REPO_ROOT)" \
		--agent "$(BENCHMARK_AGENT)"

benchmark-report: _benchmark-selected-campaign-env
	@uv run --no-project python -m benchmarks report \
		--suite "$(BENCHMARK_SUITE_PATH)" \
		--root "$(BENCHMARK_CAMPAIGN_ROOT)" \
		--agent "$(BENCHMARK_AGENT)"

_benchmark-score-env: _benchmark-selected-campaign-env
	@test -n "$(strip $(BENCHMARK_SCORE_SCRIPT_PATH))" || { \
		echo "ERROR: BENCHMARK_SCORE_SCRIPT_PATH must name the selected suite's scorer in .env."; \
		exit 2; \
	}
	@test -n "$(strip $(BENCHMARK_SCORE_OUTPUT_PATH))" || { \
		echo "ERROR: BENCHMARK_SCORE_OUTPUT_PATH must name the specialized score output in .env."; \
		exit 2; \
	}

benchmark-score: _benchmark-score-env
	@uv run --no-project python "$(BENCHMARK_SCORE_SCRIPT_PATH)" \
		--results "$(BENCHMARK_CAMPAIGN_ROOT)/results" \
		--output "$(BENCHMARK_SCORE_OUTPUT_PATH)" \
		--agent "$(BENCHMARK_AGENT)"
