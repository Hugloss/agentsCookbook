-include .env

.PHONY: benchmark-check benchmark benchmark-report _benchmark-env

_benchmark-env:
	@test -f .env || { \
		echo "ERROR: .env is required. Copy .env.example to .env and set all benchmark authority values."; \
		exit 2; \
	}
	@test -n "$(strip $(HASHMARKS_BENCH_SOURCE))" || { \
		echo "ERROR: HASHMARKS_BENCH_SOURCE must be set in .env."; \
		exit 2; \
	}
	@test -n "$(strip $(BENCHMARK_SUITE))" || { \
		echo "ERROR: BENCHMARK_SUITE must be set in .env."; \
		exit 2; \
	}
	@test -n "$(strip $(BENCHMARK_ROOT))" || { \
		echo "ERROR: BENCHMARK_ROOT must be set in .env."; \
		exit 2; \
	}

benchmark-check: _benchmark-env
	@HASHMARKS_BENCH_SOURCE="$(HASHMARKS_BENCH_SOURCE)" \
	python -m benchmarks preflight \
		--suite "$(BENCHMARK_SUITE)" \
		--root "$(BENCHMARK_ROOT)" \
		--harness-root .

benchmark: _benchmark-env
	@HASHMARKS_BENCH_SOURCE="$(HASHMARKS_BENCH_SOURCE)" \
	python -m benchmarks run \
		--suite "$(BENCHMARK_SUITE)" \
		--root "$(BENCHMARK_ROOT)" \
		--harness-root .

benchmark-report: _benchmark-env
	@python -m benchmarks report \
		--suite "$(BENCHMARK_SUITE)" \
		--root "$(BENCHMARK_ROOT)"
