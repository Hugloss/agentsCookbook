# Behavior-Preserving Split — Agent Economics plan

## Purpose

Generalize a refactoring pattern proven useful during Hashmarks structural-debt cleanup:

1. measure a concrete structural/debt candidate;
2. establish strong behavioral tests and meaningful coverage **before** changing production structure;
3. identify a narrow extraction boundary supported by evidence;
4. split oversized implementation into smaller typed state/configuration objects or focused helpers without intentionally changing behavior;
5. rerun the pre-existing behavioral evidence after every bounded split;
6. run broader repository verification;
7. remeasure current debt and choose the next candidate from fresh evidence.

This is deliberately a **behavior-preserving split** workflow, not a generic "clean up ugly files" command and not automatic refactoring authority.

## Hard invariants

- Debt, size, complexity, churn, or hotspot rank may nominate an investigation target; none authorizes an edit.
- No production split begins until the relevant behavior has strong executable evidence. Missing or weak coverage is a reason to strengthen tests first.
- Tests must capture intended behavior, authority boundaries, failure modes, and important negative cases. Do not add tests that merely mirror implementation structure.
- The pre-split behavioral suite becomes the invariant used to detect accidental behavior change during extraction.
- A split must not intentionally change public behavior, acceptance policy, repository authority, or observable failure semantics.
- Prefer small typed state/configuration objects and focused helpers when they make ownership explicit. Do not create parallel code paths, compatibility shims, or abstraction layers solely to reduce a metric.
- Focused PASS is not repository qualification. Broader repository gates remain required.
- After a successful split, remeasure the current repository. Never carry forward a hand-curated hotspot list as authority.
- If a strong pre-existing test fails after the split, fix the implementation unless the test is proven to violate the intended contract. Never weaken a test merely to make the refactor green.
- Agent Economics remains evidence/measurement/verification guidance. The target repository owns behavior and policy.

## Capability shape

Do not begin by adding an autonomous refactor engine. First compose existing evidence:

`quality-debt / hotspot-focus`
→ candidate only
→ `test-focus`
→ behavioral evidence review
→ coverage-strength gate
→ human/agent-owned bounded split
→ focused verification
→ affected/component verification
→ repository gate
→ `quality-debt / hotspot-focus` remeasurement.

A reusable addition is justified only where existing probes cannot represent an important evidence boundary. Any new surface must remain provider-neutral and parameterized.

## Phases

### BP0 — Preserve the proven lesson

Document the behavior-preserving split contract and its non-authority boundary. Add a qualification that prevents future guidance from presenting debt rank as edit authority or focused PASS as completion.

### BP1 — Pre-edit behavioral evidence

Review whether `test-focus`, provider evidence, and repository-declared gates can establish direct owning tests, affected tests, broader gates, and important uncovered behavior. If evidence is insufficient, emit a **test-strengthening requirement**, not an edit recommendation.

Prefer composing existing evidence over inventing a coverage score. If coverage data is admitted later, preserve exact producer/provenance/scope and never equate line coverage with behavioral adequacy.

### BP2 — Split contract

Represent a proposed split as evidence, not source mutation. Bind the target/source identity, candidate definition/range, confirmed tests, affected verification, behavior-preserving invariant, proposed extraction kind, forbidden outcomes, and post-edit verification ladder. Do **not** generate the production edit. Stale packets fail closed.

### BP3 — Post-split verification

After the external agent edits: bind changed source identity; run focused behavioral tests; run affected/component gates; run repository gate; compare failures with the pre-split contract; reject "successful cleanup" when broader verification fails. Verification economics remain separate from correctness.

### BP4 — Fresh remeasurement

Rerun quality/hotspot evidence against the new repository bytes. Compare only semantically compatible measurements. Record resolved/reduced/increased/new debt, file/definition movement, newly exposed candidates, and verification cost. The next target comes from current bytes, never a frozen historical list.

### BP5 — Hashmarks dogfood

Use current Hashmarks `main`, not the historical `ruff-debt` branch.

For each bounded candidate:

1. exact-bootstrap the qualified agentsCookbook revision;
2. run `doctor` / reviewed profile as needed;
3. measure current quality debt;
4. choose one candidate from current evidence;
5. obtain `test-focus` and Hashmarks repository-intelligence evidence;
6. strengthen behavioral/adversarial tests first when the boundary is not sufficiently protected;
7. freeze the pre-split behavioral evidence;
8. perform one bounded behavior-preserving split;
9. run focused tests, then affected/component tests, then Hashmarks' broader repository gate;
10. remeasure;
11. retain the change only if behavior remains protected and the structural result is actually simpler;
12. repeat from fresh evidence.

The historical Hashmarks cleanup is precedent/evidence for the workflow, not a list of files to refactor again.

### BP6 — Empirical economics

Capture the work as Agent Economics dogfood evidence without confusing cleanup success with empirical proof. Compare evidence/context consumed, files opened, tool calls, verification attempts, failed edits, iterations/time to a correct bounded split, and local-vs-CI agreement. Retain unfavorable outcomes.

### BP7 — Convergence

When the Hashmarks campaign reaches its intended debt target: remove temporary consumer scaffolding; keep only generalized agentsCookbook capabilities that proved useful; delete experiment-only branches after evidence is preserved; verify Hashmarks main has no Agent Economics policy ownership; rerun current debt and repository qualification from clean bytes.

## Initial Hashmarks execution order

Start with current-main measurement. Do not select a file from memory or the old `ruff-debt` branch.

For the first candidate, prefer a boundary where debt evidence is concrete, behavior already has strong tests (or can be strengthened narrowly), extraction can be done without changing public semantics, and the result can remove complexity rather than redistribute it.

The first Hashmarks iteration also qualifies this workflow. If existing Agent Economics surfaces already provide enough evidence, keep the cookbook change documentation-only. Add code only for a demonstrated reusable gap.
