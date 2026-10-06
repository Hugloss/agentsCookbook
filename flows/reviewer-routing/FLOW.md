# Reviewer Routing Flow

The router is a convenience composition over standalone reviewers. It is not required for manual reviewer use.

## Selection

Honor explicit reviewer names. Otherwise choose the narrowest relevant specialty: plan gaps, alternative route, validation, coverage realism, red-team risk, implementation simulation, factual grounding, performance, or final contract.

## Boundaries

- Route exactly one reviewer.
- Never substitute the router's own analysis for the selected reviewer.
- Do not require Ping-Pong state or run artifacts.
- Give the reviewer a bounded subject/evidence packet.

If the user requests the full nine-review planning/build flow, use the corresponding primary flow rather than simulating it here.
