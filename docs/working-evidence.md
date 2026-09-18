# Working evidence

Agent Economics uses plain files for task-local continuity. It does not own a database, hidden evidence service, repository graph, or persistent repository-intelligence cache.

## Ownership rule

Ask one question before putting information in working evidence: Could another agent working on the same repository reuse this fact without knowing the current task? If yes, it belongs in Hashmarks or another repository-intelligence provider when one is available.

Working evidence is for the current task: the goal, task/environment-local facts, agent decisions, and remaining work.

## Minimal shape

The canonical shape has schema agentscookbook-working-evidence/v1 and exactly four conceptual sections: task, known, decisions, and remaining. A host may store it as .agent/evidence.yaml. Agent Economics does not require that path, does not create a daemon around it, and does not make the file historical.

## Do not copy repository intelligence

Do not place repository graphs, ownership graphs, test graphs, repository snapshots, or verification caches in working evidence. Prefer stable provider references and query the repository-intelligence owner for current facts.

Hashmarks may own repository identity/generation, structural impact, imports/references/ownership, test relationships, provenance, completeness, freshness, observation deltas, diagnostic identities, and generation-bound external observations. Agent Economics owns the policy decision made from those facts.

## Lifecycle

Keep only the current useful working set. Delete task-local facts when they are no longer useful. Environment-local facts need explicit invalidation conditions when reuse could be unsafe. Supported lifetimes are file-edit, worktree-change, repository-generation, dependency-change, environment-change, process-restart, session-end, and never-within-session. Repository-generation invalidation requires a provider reference: working evidence must not create its own repository generation counter.

## Graceful degradation

The contract works without Hashmarks. A host may discover evidence locally when no repository-intelligence provider exists. That fallback must not become a second persistent repository model.

## Current implementation slice

scripts.agent_economics.working_evidence provides a stdlib-only constructor and validator for this minimal contract. The validator rejects obvious top-level repository-intelligence copies that would create parallel ownership.
