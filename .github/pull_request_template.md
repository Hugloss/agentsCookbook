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
- [ ] No standalone skill was silently added to the mandatory nine-review flow.

## Public-repo checklist

- [ ] README/catalog/docs were updated if public behavior or counts changed.
- [ ] Compatibility/platform assumptions are stated rather than implied.
- [ ] No secrets, private repository content, or machine-specific paths were added.
- [ ] Breaking or compatibility-affecting changes are called out explicitly.

## Validation

- [ ] `scripts/check-canonical-sources.sh`
- [ ] `scripts/smoke-opencode-scripts.sh`
- [ ] `scripts/smoke-run-artifacts.sh`

<!-- Describe validation appropriate to the change and its claims; see CONTRIBUTING.md#evaluation-ownership-and-evidence. Reuse relevant evidence. Link an EvalShot change only when its corpus, runner, or other evaluation assets need updating; a skill change alone does not require a paired PR. Distinguish source review/example application from model-backed or runtime execution. Do not mark skipped validation as passing or claim measured quality without execution evidence. -->
