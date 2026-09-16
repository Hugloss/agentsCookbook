## What problem does this solve?

<!-- Describe the concrete prompt, repository, integration, or documentation failure being addressed. -->

## Change boundary

<!-- What changes, and what intentionally does not change? -->

## Evidence

<!-- Real repository path, example, reproduction, evaluation case, or user-facing failure that justifies the change. -->

## Skill / prompt checklist

- [ ] The change owns a narrow question or clearly sharpens an existing one.
- [ ] Findings require evidence rather than grep/smell alone.
- [ ] False positives / nearby concerns are explicit where relevant.
- [ ] Existing skill overlap was checked before adding a new skill.
- [ ] Runtime-specific behavior was not moved into reusable methodology.
- [ ] No standalone skill was silently added to the mandatory eight-review flow.

## Public-repo checklist

- [ ] README/catalog/docs were updated if public behavior or counts changed.
- [ ] Compatibility/platform assumptions are stated rather than implied.
- [ ] No secrets, private repository content, or machine-specific paths were added.
- [ ] Breaking or compatibility-affecting changes are called out explicitly.

## Validation

- [ ] `scripts/check-canonical-sources.sh`
- [ ] `node scripts/run-skill-benchmarks.js --validate-corpus`
- [ ] `scripts/smoke-opencode-scripts.sh`
- [ ] `scripts/smoke-run-artifacts.sh`

<!-- Add any model-backed or runtime-specific evidence that was actually run. Do not mark skipped validation as passing. -->
