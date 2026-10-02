export PYTHONPATH := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))):$(PYTHONPATH)

.PHONY: benchmark-check benchmark-check-all benchmark benchmark-smoke benchmark-qualify-localization benchmark-report benchmark-score benchmark-evidence-validate

benchmark-check:
	@uv run --no-project python -m benchmarks check --env-file .env

benchmark-check-all:
	@uv run --no-project python -m benchmarks preflight --env-file .env

benchmark:
	@uv run --no-project python -m benchmarks run --env-file .env

benchmark-smoke:
	@uv run --no-project python -m benchmarks run --env-file .env \
		--subject none --subject hashmarks \
		--task logs-00 --task splunk-00 --task dependencies-00 \
		--task semantics-00 --task identities-00 --task code_owners-00

benchmark-qualify-localization:
	@qualification_root=$$(mktemp -d /tmp/agentscookbook-heldout-v1-localization-qualification.XXXXXX) || exit 2; \
		printf 'qualification root: %s\n' "$$qualification_root"; \
		if uv run --no-project python -m benchmarks run --env-file .env \
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
