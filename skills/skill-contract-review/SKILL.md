---
name: skill-contract-review
description: Reviews whether a skill owns one sharp, evidence-closed contract with non-gameable finding and clean outcomes.
license: MIT
---

# Skill Contract Review

Standalone review of a proposed or existing cookbook skill. Review the skill definition itself, not the target codebase it may later inspect.

## INVARIANT

> **A reusable skill should own one narrow question whose finding, clean, and insufficient-evidence outcomes are all bounded by explicit proof rather than by reviewer discretion or candidate-selected success criteria.**

## HUNT

Hunt for skill contracts that:
- combine unrelated failure classes or become a generic quality/architecture mega-review;
- define how to prove a finding but allow `CLEAN`, "no findings", "complete", or "qualified" from partial or undeclared observation;
- let the subject under review choose or weaken the scope, baseline, probe set, threshold, or validation oracle after results are known;
- freeze scope so tightly that evidence-backed directly affected behavior cannot be added, or let scope shrink to discard a discovered problem;
- promote suspicion, ranking, smell, or investigation leads into findings without a proof contract;
- require identity, provenance, environment, or workflow machinery unrelated to the skill's actual semantic question;
- hide an upstream/neighboring owner's defect with a local workaround instead of naming the real owner;
- duplicate another skill's invariant without a clear boundary;
- repeat the same rule across sections until prompt cost outweighs discrimination value;
- use fixed finding counts, benchmark quotas, or mandatory workflow steps as substitutes for evidence.

## PROVE

For each material issue identify:
- **Owned question** — the one review/discovery/transform question the skill answers.
- **Failure class** — the exact condition that justifies a finding.
- **Finding proof** — evidence required before reporting that condition.
- **Clean proof** — the bounded scope/completeness required before a negative or clean claim is admissible.
- **Incomplete state** — what must remain `INSUFFICIENT EVIDENCE`, partial, unknown, or otherwise non-clean.
- **Scope rule** — the minimum semantic scope, and whether evidence may require monotonic expansion.
- **Authority rule** — when success depends on policy/baseline/qualification authority, where that authority comes from and why the candidate cannot self-authorize.
- **Freshness/identity rule** — only when evidence can become stale or be reused across mutable candidates/contexts.
- **Overlap boundary** — neighboring skill that owns adjacent concerns.
- **Cost** — text, benchmark, or workflow complexity that does not improve discrimination.

A skill does not need every mechanism above. Require only the mechanisms necessary to make its own invariant non-gameable.

## DO NOT REPORT

Do not report:
- a skill merely because it is long, if its additional text owns necessary semantics;
- missing candidate identity on a stateless bounded reasoning skill where freshness cannot affect the result;
- missing repository-wide completeness when the skill explicitly makes only a local bounded claim;
- one or two extra examples as "bloat" when they materially disambiguate the invariant;
- a different writing style when the invariant, proof, false positives, and outputs are already sharp;
- absence of runtime orchestration, persistence, retries, or state machinery from a prompt-only skill.

Do not turn this review into a universal skill framework. Do not add it automatically to normal repository-review or Ping-Pong/Ping-Ping flows; it is an authoring-time review for skill definitions.

## PREFER

Prefer this compact shape when it fits:

```text
INVARIANT
HUNT
PROVE
DO NOT REPORT
PREFER
OUTPUT
```

Then add only domain-specific sections that carry unique semantic weight.

When a skill can report a negative conclusion such as `CLEAN`, "no findings", "complete", "safe", or "qualified", make that conclusion at least as evidence-bound as a positive finding.

For discovery skills, distinguish **lead** from **proved finding** and bound any no-more-leads claim to the completed search scope.

For qualification skills, derive required scope and success authority independently of candidate success. Candidate-authored changes to the governing oracle require separate admission.

For iterative repair skills, use minimum scope plus evidence-backed expansion rather than either an arbitrarily tiny scope or unbounded repository creep.

Keep benchmark cases discriminating: include at least a true violation and a near-neighbor control, then add cases only for ambiguity the model actually needs to distinguish.

## OUTPUT

Return `# Skill Contract Review` with:
- owned question and neighboring owners;
- blocking contract gaps;
- non-blocking sharpness/cost issues;
- finding-vs-clean evidence symmetry;
- scope/authority/freshness requirements that actually apply;
- smallest correction;
- benchmark discrimination needed.

End with one:
- `CLEAN` — the skill is narrow and its material outcomes are evidence-closed;
- `LEAVE ALONE` — suspicious structure was reviewed but is justified by the skill's semantics;
- `INSUFFICIENT EVIDENCE` — the skill's intended role or governing context is too unclear to judge safely.
