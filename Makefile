-include .env

.PHONY: benchmark-check benchmark benchmark-report _benchmark-env

_benchmark-env:
	@test -f .env || { \
		echo "ERROR: .env is required. Copy .env.example to .env and set all benchmark authority values."; \
		exit 2; \
	}
	@test -n "$(strip $(BENCHMARK_SUITE_PATH))" || { \
		echo "ERROR: BENCHMARK_SUITE_PATH must point to the committed benchmark suite definition in .env."; \
		exit 2; \
	}
	@test -n "$(strip $(BENCHMARK_CAMPAIGN_ROOT))" || { \
		echo "ERROR: BENCHMARK_CAMPAIGN_ROOT must name the writable campaign cache/work/results directory in .env."; \
		exit 2; \
	}
	@test -n "$(strip $(BENCHMARK_HARNESS_REPO_ROOT))" || { \
		echo "ERROR: BENCHMARK_HARNESS_REPO_ROOT must point to the agentsCookbook checkout in .env."; \
		exit 2; \
	}

benchmark-check: _benchmark-env
	@python -m benchmarks preflight \
		--env-file .env \
		--suite "$(BENCHMARK_SUITE_PATH)" \
		--root "$(BENCHMARK_CAMPAIGN_ROOT)" \
		--harness-root "$(BENCHMARK_HARNESS_REPO_ROOT)"

benchmark: _benchmark-env
	@python -m benchmarks run \
		--env-file .env \
		--suite "$(BENCHMARK_SUITE_PATH)" \
		--root "$(BENCHMARK_CAMPAIGN_ROOT)" \
		--harness-root "$(BENCHMARK_HARNESS_REPO_ROOT)"

benchmark-report: _benchmark-env
	@python -m benchmarks report \
		--suite "$(BENCHMARK_SUITE_PATH)" \
		--root "$(BENCHMARK_CAMPAIGN_ROOT)"
