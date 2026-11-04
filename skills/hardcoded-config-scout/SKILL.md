---
name: hardcoded-config-scout
description: Finds hardcoded runtime settings that block required configuration, while protecting intentional constants.
license: MIT
---

# Hardcoded Configuration Scout

Standalone, read-only discovery and proof of hardcoded **operational configuration**. Recommend corrections within the existing config path; do not edit files, invent deployment requirements, or add a configuration framework.

## INVARIANT

> **A literal is a configuration defect only when a reachable operational value must vary for a supported context but the effective configuration path fixes, ignores, or silently overrides it.** A grep match or large import fan-out does not prove that a value belongs in the environment.

## HUNT

1. **Establish supported variation.** Define the requested repository/subsystem scope. Read entry points, deployment contracts, hardware constraints, supported override mechanisms and security policy before prescribing configuration. Do not invent a second deployment mode to justify a finding.
2. **Discover possible literals.** Inspect `config.py`, `settings.py`, `constants.py`, similarly named files, and relevant Python/JS/TS, shell, CI, YAML, Docker/Compose, Kubernetes/Helm and deployment templates. Look for absolute developer or machine paths (`/home/...`, `/opt/...`, `C:\\...`), endpoints/IPs/ports, model/data paths, CPU/memory budgets, concurrency, timeouts, retry limits, feature flags, uppercase constants, embedded default values, and direct `os.environ` or `process.env` access. Use scoped file and text search (for example `rg --files` and `rg -n` if installed), but treat results only as leads. Respect ignore rules; skip vendored, generated and binary files unless directly affected.
3. **Trace use.** Follow candidate definition -> imports/references -> entry point -> configuration resolution -> final consumer/effect. Record how many distinct files consume the value as a prioritization signal, not a criterion for externalization. Dynamic or external consumers may be unknown.
4. **Reconcile configuration ownership.** Inspect actual precedence among existing CLI flags, config files, env vars, code defaults, CI workflows, Compose, Helm, `.env.example` and docs. Determine whether the value is already overridable, overridden too late, or shadowed by an environment-specific fallback. A template declaration does not prove the override reaches the consumer.
5. **Check real variation.** Find a supported context where a different value is required and show how that value is accepted or rejected by the actual path. A targeted existing test or non-destructive check can strengthen the claim. A source-proved ignored override does not require a live deployment; distinguish exercised evidence from source analysis.

Never open untracked secrets, copy credentials or print private endpoints/tokens in findings. Redact sensitive literals, and route disclosure questions to the appropriate security process rather than treating an env var as automatically safe.

## PROVE

A **confirmed finding** requires all of:
- **Location:** file:line, symbol, type and units; safely show the literal or redact it.
- **Variability contract:** documentation, actual supported deployment/hardware constraint, caller contract or observed requirement establishing that the value needs to differ.
- **Reachable path:** entry point -> effective configuration/precedence -> consumer, identifying where operator input is unavailable, ignored, discarded or overridden.
- **Consequence:** a realistic portability, reliability, operability or security impact.
- **Disconfirmation checked:** test the possibility of an effective existing override, intentionally pinned contract, documented single-environment constraint or deliberate validation guard.
- **Evidence boundary:** inspected paths/contexts and whether the claim is source-derived, executed, or still unresolved.

If supported variability, reachability, precedence or ownership cannot be established, keep an **INVESTIGATION LEAD** with the next decisive check. Import counts affect priority only. A missing `.env.example` value is not proof of broken configuration unless an authoritative template contract requires it.

## DO NOT REPORT

Do not flag solely:
- mathematical, schema, protocol, serialization or algorithm constants;
- intentionally pinned compatibility versions and policy-controlled safety limits;
- test fixtures, mock endpoints, documentation illustrations or generated content outside production authority;
- safe defaults with effective, documented and validated overrides;
- repeated consumers using one legitimate canonical config owner;
- documented single-context deployment values without a supported need to vary.

Do not externalize safety policy merely to make it overrideable. Establish who is authorized to change it and which validation remains mandatory. Do not propose a new manager, registry, config file or env key when one existing owner can resolve the problem. Do not infer secrets are secured merely because they moved to environment variables.

## PREFER

Recommend the smallest change through the **existing authoritative configuration path**:

1. Reuse an existing setting first; delete the shadowing literal or competing fallback instead of adding another owner.
2. If no setting exists, select an env var, CLI flag or config-file key according to real operator conventions. Suggest a collision-free name (such as `OCR_MODEL_DIR` in an OCR-scoped service), not a mandatory naming scheme.
3. Define required vs optional, portable default vs fail-fast, type/units, valid ranges, precedence and authorization. Use managed secrets for secret values where the deployment requires it.
4. Identify exact definition and consumer changes; update `.env.example`, Compose, CI, deployment manifests and docs only where they participate in the supported contract. Specify targeted checks: override takes effect, absent/invalid values behave as required, and unchanged contexts keep behavior.

### Discrimination checks (illustrative, not repository findings)

- **Potential FINDING:** a test runner unconditionally requests a two-CPU cgroup quota even though supported runner capacities vary and the normal configuration path cannot set the quota. Prove the runnable path and supported variation before reporting.
- **LEAVE ALONE:** a protocol delimiter is deliberately fixed and used by many files.
- **INSUFFICIENT EVIDENCE:** a literal URL looks machine-specific but supported deployments and effective override behavior are unavailable.

### Neighboring owners

`repository-improvement-scout` owns broad preliminary leads; this skill owns **whether a hardcoded operational value needs externalization**. `entrypoint-authority-review` owns competing launch/default authorities, and `single-source-of-truth-review` owns multiple accepted producers of the same configuration fact. Route proven split-authority causes there rather than proposing duplicated fixes. `sensitive-data-masking` owns transformation of evidence under disclosure policies.

## OUTPUT

Return `# Hardcoded Configuration Scout` containing:
- **Inspection boundary:** paths, deployment contexts, config sources/consumers inspected, omissions and truncated/unavailable evidence.
- **Confirmed findings:** location, safe rendering of current value, variability evidence, reachability and precedence trace, consequence, disconfirmation, current owner, proposed key/mechanism, type/default/validation, exact change locations, docs/templates, and regression check.
- **Investigation leads:** candidate, evidence, unresolved prerequisite and next decisive check.
- **Leave alone:** inspected intentional/safe constants and effective overrides.
- **Validation:** checks actually run vs merely proposed, plus remaining risk.

End with exactly one bounded verdict:
- `FINDING` — at least one config defect is proved; keep unresolved neighbors visible.
- `CLEAN` — the entire declared relevant configuration path and consumers were inspected, with no defect or material unresolved candidate in scope.
- `LEAVE ALONE` — the suspicious candidates were shown intentional or already effectively configurable; no broader inventory claim.
- `INSUFFICIENT EVIDENCE` — no defect is proved and material context, consumer, precedence or inspection scope remains unresolved.

Never infer repository-wide absence from a partial search. Do not impose a fixed finding quota.
