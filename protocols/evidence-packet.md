# Bounded Evidence Packet

A reviewer receives the smallest self-contained context needed for its specialty.

```text
USER REQUEST:
<goal>

SUBJECT:
<plan, tests, implementation evidence, or other material>

EVIDENCE:
Verified facts: <compact facts>
Inspected: <relevant files/areas>
Assumptions: <material assumptions>
Unresolved uncertainty: <unknowns>
Validation state: <relevant checks/results>
Not inspected: <important omissions only>

MODE:
<optional capability mode>

TASK:
<review-specific request>
```

## Rules

- Do not include full conversation history by default.
- Do not forward whole sibling-review reports.
- Prefer precise excerpts and identities over raw logs.
- A packet must be sufficient for standalone invocation; no hidden parent-flow state is required.
- Missing evidence is explicit rather than guessed.
- Target ordinary reviewer input below roughly 6k model tokens and exceptional packets below roughly 10k, but enforce character/byte measurements plus the actual deployed tokenizer when available rather than assuming one tokenizer.
