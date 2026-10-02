export PYTHONPATH := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))):$(PYTHONPATH)

.PHONY: benchmark-check benchmark-check-all benchmark-campaign-audit benchmark-status benchmark benchmark-new benchmark-resume benchmark-runs benchmark-smoke benchmark-qualify-localization benchmark-oracle-review benchmark-oracle-review-check benchmark-report benchmark-score benchmark-evidence-validate

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

benchmark:
	@uv run --no-project python -m benchmarks run --auto --env-file .env

benchmark-new:
	@uv run --no-project python -m benchmarks prepare --new --env-file .env

benchmark-resume:
	@uv run --no-project python -m benchmarks run --resume --env-file .env

benchmark-runs:
	@uv run --no-project python -m benchmarks runs --env-file .env

benchmark-smoke:
	@uv run --no-project python -m benchmarks run --new --env-file .env \
		--subject none --subject hashmarks \
		--task logs-00 --task splunk-00 --task dependencies-00 \
		--task semantics-00 --task identities-00 --task code_owners-00

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
