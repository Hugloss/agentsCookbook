# Empirical benchmark framework

This directory owns reusable, product-neutral experiments for agents, tools, evidence systems, and software-engineering outcomes.

## Authority boundary

The harness is the experiment authority. A product under test never grades itself.

A benchmark suite freezes repository identity, task, mutation, oracle, conditions, budgets, and scoring before campaign execution. Observed outcomes are preserved as `PASS`, `FAIL`, `INCOMPLETE`, `INVALID`, `CONTAMINATED`, or `NO_QUALIFYING_DEFECT`; infrastructure failures are never silently converted into product failures.

## Model

`suite -> experiment -> condition -> trial`

Subjects and agents are replaceable participants. Hashmarks, Enola, Codex, local models, test selectors, and future tools are adapters, not schema concepts.

Each trial binds suite/experiment version, frozen task/repository identity, mutation/oracle identity, agent/subject identity, harness commit/environment, seed/budgets/tool exposure, observed execution identity, raw events, and an immutable result receipt.

## Method

Fresh authority -> frozen input -> isolated execution -> observed execution identity -> independent oracle -> immutable receipt -> aggregate only valid evidence.

Do not change a frozen task or oracle after seeing a result. Create a new suite/experiment version instead.
