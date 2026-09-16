# Sharp Skill Discrimination Corpus

These are behavioral cases for the narrow repository-review skills.

Each case has a **positive** example the skill should report and a **control** example it should reject as a false positive. A useful local-model evaluation must test both. Merely loading the skill is not behavioral proof.

| Skill | Positive case | Control case |
| --- | --- | --- |
| `stale-work-race-review` | Request A starts, request B supersedes it, B commits, then A commits stale state with no current-owner check. | Operations are serialized and A cannot complete after B starts. |
| `ui-lifecycle-race-review` | View A schedules RAF work, navigation replaces A with B, then A's queued callback touches B's DOM. | Cleanup cancels the scheduled callback and the callback validates the current view identity. |
| `semantic-redecision-review` | Admission resolves eligibility, then scheduler independently recomputes the same eligibility from raw flags. | A trust boundary validates the already-resolved result without changing its semantic meaning. |
| `durable-commit-path-review` | API cancellation and worker cleanup can each independently write the same terminal transition. | Several callers converge on one canonical compare-and-transition commit. |
| `resolved-fact-regression-review` | A canonical repository identity is resolved, but execution receives a raw path and resolves identity again. | Downstream code asserts the canonical identity still matches persistence without reinterpreting it. |
| `state-authority-review` | Database status and a writable cache can independently become the effective truth for the same lifecycle state. | Database is canonical and an immutable receipt is explicitly historical evidence. |
| `invalid-state-model-review` | `status=running`, `completed_at!=null`, and `cancelled=true` are simultaneously representable although impossible. | Optional fields are independent domain facts and their combinations are genuinely valid. |
| `single-observation-review` | One operation walks and reads an include graph, then a later stage walks and reads the same source tree again. | Two separate logical operations each perform their own observation. |
| `call-chain-collapse-review` | Helper → service → facade only forwards the same arguments to the existing domain owner. | A thin adapter performs a real protocol or trust-boundary conversion. |
| `alternate-path-removal-review` | A canonical execution API exists but one caller still uses a legacy direct-executor path with equivalent semantics. | Two paths implement genuinely different supported workflows. |
| `hidden-side-effect-review` | A getter-like helper performs a durable database write that is invisible from the caller boundary. | An explicitly named command method performs the documented write. |
| `dependency-surface-review` | A function receives a 30-field context but consumes two fields and forwards the rest. | A cohesive aggregate is the real domain input and most fields participate in its invariant. |
| `test-work-amplification-review` | A local behavior assertion triggers a full repository scan and subprocess bootstrap through the production API. | An end-to-end test intentionally proves the full scan/bootstrap behavior. |
| `repeated-test-setup-review` | Every small test rebuilds the same expensive application/bootstrap graph because production construction is heavy. | Clean database setup is required for isolation of persistence semantics. |
| `test-isolation-boundary-review` | A pure calculation can only be tested after starting a DB and HTTP server because the production API entangles effects. | The test is explicitly verifying DB/HTTP integration behavior. |
| `test-orchestration-complexity-review` | One narrow behavior test must coordinate five subsystems, callbacks, cleanup, and internal lifecycle states. | A genuine end-to-end workflow test intentionally covers those coordinated subsystems. |
| `deterministic-causality-test-review` | A test sleeps 500 ms and hopes a worker committed before asserting. | The test controls a fake clock/barrier and observes explicit completion. |
| `test-state-contamination-review` | Test order changes results because a module-global mutable cache survives between tests. | Tests share immutable process-wide configuration. |
| `test-contract-coupling-review` | A behavior-preserving refactor fails tests because they assert private helper order and exact internal calls. | A structural test enforces a real boundary such as forbidding UI imports of a persistence client. |
| `architecture-risk-triage` | A repository hotspot shows repeated graph reads and duplicate semantic decisions; triage routes them to the two narrow specialists. | A user already names the exact specialist and supplies its target evidence; triage should not replace that focused review. |

## Evaluation rule

For every case, record:

- skill loaded;
- finding or clean verdict;
- evidence cited;
- false-positive behavior;
- whether the response stayed inside the skill's invariant;
- context/tool cost when measured.

A skill fails discrimination when it reports the control case as its defect, misses the positive case, or drifts into another skill's responsibility.
