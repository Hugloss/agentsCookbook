# Ping-Pong Plan Flow

This flow composes eight standalone reviewers. It does not own their methodology.

## Authority

- `ping-pong-plan` owns the canonical plan.
- Reviewers provide read-only evidence.
- Skills provide standalone review methods.
- Reviewers never edit the plan or project.

## Sequence

1. Draft plan v1 from bounded repo evidence.
2. Gap completion and alternative-route reviews.
3. Synthesize one current plan.
4. Validation review.
5. Coverage-design review.
6. Red-team review.
7. Implementation simulation.
8. Fact audit.
9. Contract check.
10. Return one coordinator-authored final plan.

Every mandatory reviewer is attempted exactly once. A failed reviewer does not erase useful plan work but makes the flow incomplete.

## Context economics

Target model ceiling: 98,304 tokens. Normal work should remain substantially below that ceiling.

Each review receives a bounded evidence packet. Later reviewers receive the current subject and material decisions, not raw earlier reports. External run artifacts may preserve full reports outside active context, but they are optional and must never become a prerequisite for standalone reviewer use.

## Current runtime note

`ping-pong-plan` currently keeps orchestration instructions inline because its OpenCode/Pi authority contract denies direct skill loading. Do not move this flow file into runtime-required context until both harnesses prove a whitelisted orchestration loader preserves the same authority and reliability.
