# Script and runtime compatibility review — 2026-10-30

## Conclusion

The skills review needed a corresponding script review. Strong prompt contracts
do not compensate for an extension that fails to load, ineffective delegation
permissions, stale installed definitions, or a validator that counts failed work
as successful. This review found concrete instances of each.

The repairs extend the same consolidated skill-quality PR. The reproducible
integration baseline is OpenCode 1.19.5 and Pi 1.4.0 with `pi-open-agents` 0.1.26.
OpenCode 2 and `pi-open-agents` 0.1.27 have explicit incompatibility boundaries.
The cookbook does not silently migrate a host, weaken native permission
inheritance, or treat a package version as proof of a completed review.

The starting cookbook revision for this script review was
`ae6cf4e1ea01cbbcedffb1e6a8c974bc8ac7fb51`, following the
[complete skill catalog review](skill-quality-review-2026-10-30.md).

## Upstream versions and primary evidence

| Component | Exact source inspected | Execution evidence | Result |
| --- | --- | --- | --- |
| OpenCode 1.19.5 | Tag commit `810c0eba1a7348036f8bdf61e6632d0c36c6876c`; native SDK 1.19.5 | Official binary, isolated configuration, full preflight in both artifact modes, native tool execution | All 12 agents and 85 cookbook skills pass; artifact write/read and forbidden-role/ID controls pass after the installation repair. |
| OpenCode 2.2.3 | Tag commit `082ac6281fd395c2d0c17fd3c38214db2f89621f` | Official binary version and command probes | Different plugin/CLI contracts; existing V1 adapter is not a V2 implementation. |
| OpenCode 2.2.4 | Tag commit `45898d0f8569225eb1ddb4ee13f8581b34dff311` | Source diff against 2.2.3; no second binary execution | Released during this review. Relevant CLI/migration contracts unchanged; no restored V1 plugin execution. |
| Pi 1.4.0 | Published `@earendil-works/pi-coding-agent` package | Actual extension loader, native read tool and native delegation/permission helpers | Registration-time runtime action was invalid; corrected lifecycle loads successfully. |
| `pi-open-agents` 0.1.26 | Published npm package | Actual source loaded through Pi; execution dependency injected to avoid child/model calls | Native parent/child gates accept the corrected cookbook roles and reject forbidden delegation/tools. |
| `pi-open-agents` 0.1.27 | Published npm package, latest checked | Same native helper probe | Its inherited ceiling/rules block the cookbook flow. Preflight rejects it and unreviewed versions. |

Primary upstream references:

- [OpenCode release history](https://dev.opencode.ai/changelog/), including
  the separate 1.x update channel and explicit 2.x upgrade.
- [OpenCode V1 migration guide](https://opencode.ai/v2/docs/migrate-v1) and
  [plugin migration contract](https://opencode.ai/v2/docs/build/plugins/migrate-v1/).
- [Pinned OpenCode 2.2.4 source](https://github.com/anomalyco/opencode/tree/45898d0f8569225eb1ddb4ee13f8581b34dff311).
- [Pi release history](https://pi.dev/changelog) and
  [Pi 1.4.0 package](https://www.npmjs.com/package/@earendil-works/pi-coding-agent/v/1.4.0).
- [`pi-open-agents` package documentation and change notes](https://pi.dev/packages/pi-open-agents).
- [Extension 0.1.26 source](https://github.com/andrea-tomassi/pi-open-agents/tree/e86a547af7c37f7c991a952159d2e65f4f495fd9) and
  [extension 0.1.27 source](https://github.com/andrea-tomassi/pi-open-agents/tree/725a1ff17ed449cdfc86ceb9f2f37637a2a5a8ff).

The fetched npm tarballs had these SHA-256 digests:

| Tarball | SHA-256 |
| --- | --- |
| `pi-coding-agent-1.4.0.tgz` | `d155c16ef6fa00960fbf58b2911536e80b05f33700e0b14fbd08967ede0c7428` |
| `pi-open-agents-0.1.26.tgz` | `1a237bc14de627fcca26e9bc37e65273e0bf814c41b010b7240e64d90b84cb0f` |
| `pi-open-agents-0.1.27.tgz` | `9d10fbcdba12baeb4fea9cd688762a650fce25404fab5abbb39ff6d5a9e8c0bf` |

Pi's current package requires Node >=22.19.0; the audit used Node 24.22.1.
The isolated dependency installation pinned `tslib` 2.8.1 because the registry's
selected 2.9.1 tarball returned 404. This was a test-environment resolution
constraint, not a change to the cookbook or a global package installation.

## Confirmed problems and corrections

### 1. Pi extension loading and native permission semantics

The old adapter called `pi.setActiveTools` while the extension factory was
loading. Pi's real loader exposes an uninitialized action stub at that point.
Loading the unchanged adapter produced zero extensions and the error
`Extension runtime not initialized. Action methods cannot be called during extension loading.`

The adapter now registers its hooks during loading and selects the reviewer's
finite tool set at `session_start`. The independent `tool_call` blocker remains
active. Lifecycle-faithful regressions reject a registration-time action, and
the optional native probe exercises the actual Pi loader.

The native permission gate also evaluates `subagent` separately from the
OpenCode `task` permission. All three canonical primaries previously lacked
that native grant. They now explicitly permit `subagent`, while native
`allowedAgents` restricts delegation to the exact nine reviewers and `maxDepth`
prevents reviewer delegation. The native probe checks the allowed set, rejection
of an outside agent, forbidden shell access, and the child's depth boundary.
OpenCode 1 effective-tool checks reject an unexpected enabled `subagent` custom
tool, so the cross-host metadata change does not silently enlarge that host's
accepted tool surface.

In `pi-open-agents` 0.1.27, inherited deny/ask rules and the parent's effective
tool ceiling remove authority required by this flow. The cookbook's wildcard
deny removes otherwise explicitly allowed tools, and the parent does not own the
child-only artifact sink. The same native helper probe fails with 0.1.27.
The repair is an explicit checked-version boundary, not a bypass of those
upstream restrictions. Full Pi preflight accepts Pi 1.4.0 with extension 0.1.26;
older, prerelease and future combinations require a new review.

### 2. Pi package and agent discovery

The old smoke fixture put an npm package declaration in `settings.extensions`.
Current Pi resolves npm declarations from `settings.packages`; a declaration in
the wrong field could let preflight pass without proving package installation.
The check now validates the package identity/version, native project/user
precedence, relevant enablement filters, and the declared/installed version.

Shared agent discovery changed to `.agents/agents/*.md` in `pi-open-agents`
0.1.22. Discovery checks now inspect supported project families, nested agent
files and frontmatter names, so a renamed file cannot hide a shadow definition.
Static installation evidence is labeled as such; it is not a live tool session.

### 3. OpenCode version and effective-tool checks

OpenCode 1 reports disabled artifact tools as absent when artifact mode is
off. Requiring each to equal the literal Boolean `false` rejected valid native
output. The build coordinator also has no direct reviewer-skill authority, so
requiring its `skill` tool to be enabled contradicted the canonical definition.
Both expectations now match actual 1.19.5 output. Checks still require needed
tools, reject unexpected enabled tools, and validate exact identity/mode/skill
discovery rather than substring presence.

Native execution exposed two additional problems that fixture-only validation
had missed. The installed plugin symlink resolved its bare SDK import from the
cookbook checkout, while OpenCode installed that dependency in its own config
directory. The actual loader reported that `@opencode-ai/plugin` could not be
found, so artifact tools never registered. A small real config-local entry now
imports the host's SDK and passes its helper into the dependency-free canonical
adapter. The installer migrates the known old symlink and verifies exact entry
bytes; modified entries require a backup for replacement and survive removal.
This wiring introduces no copied artifact behavior or second package resolver.

The native CLI also returned exit zero with truncated skill JSON when stdout
went through a pipe; directing the same output to a regular file preserved the
complete JSON. Full preflight now captures discovery directly to a temporary
file, keeps diagnostics on stderr, and rejects invalid JSON rather than repairing
it into a success. The complete discovered skill IDs must still match.

OpenCode 2 uses a different plugin API and different debug/export commands. A
version-aware helper refuses unsupported full integration before issuing V1
commands. Quick source/link validation remains a structural check. Portable
skill Markdown is still available to another host, including V2; that is not
qualification of the cookbook's V1 artifact plugin on V2.

### 4. Session validation must distinguish attempts from success

The old OpenCode gate could count all nine reviewer IDs even when every task
ended in error. Malformed export text could also be searched as a fallback.
It now consumes structured native evidence, validates session/message/tool-call
identity, and counts only completed usable results. Failed, pending, running,
empty, background-launch-only, nested payload and malformed evidence cannot
qualify a review. Session selection is bound to the selected project and scope.

Pi stores a session tree. Checks and export now share one small passive parser
that selects the active branch and pairs actual assistant calls with matching
tool results. Inactive branches and unrelated embedded data cannot fill missing
reviewer slots.

More fundamentally, native Pi `AgentToolLog.status: "done"` records that a tool
execution ended; it does not encode whether the tool succeeded. A parent-only
trace therefore cannot prove a successful skill read or artifact save. Full
qualification reports incomplete evidence instead of manufacturing success.
Even a successful native read can return only a selected slice. Offset reads,
remaining-line notices and native truncation cannot establish a complete initial
skill load; the checker preserves that distinction.
When native details link a child session file, the checker can bind its actual
successful tool results to the observed child calls. It checks the fork's parent
identity and the entire current child task's tool sequence, so an unreported
tool before or after a purported skill read cannot disappear from the audit.
The ordinary fresh-child
path does not supply that file; a deliberately selected fork profile has
different context semantics and must be identified separately.

### 5. Artifact integrity and export

Both live readers previously returned a changed report body without validating
its receipt, and accepted a report whose receipt had been removed. They now
validate confined paths, receipt run/reviewer identity and runtime, hash, exact character count,
and summary/report budgets before returning content. The run-store checker also
verifies that the `reviews` and `receipts` directories themselves remain inside
the run root, not only that files remain inside those directories.

The post-run exporter now preserves failed, missing, unfinished and unknown
outcomes. Successful output requires explicit native completion evidence. It
records source provenance, selects Pi's active branch, refuses to overwrite a
nonempty or symlink output location, and publishes a fully materialized staging
directory. A failed export cannot leave a mixture of previous and current
reviewer artifacts that looks like one completed run.

These hashes detect mismatch against local receipts. They are not signatures or
authentication against an actor able to rewrite both a report and its receipt.
Artifact consistency alone also does not establish that the review is correct.

### 6. Installer update and removal behavior

Three focused cases failed against the starting installer and pass after repair:

1. A checkout path containing spaces split during skill discovery. NUL-delimited
   discovery now preserves the path.
2. Deleted or renamed source skills left stale installed links, and the
   uninstaller only considered current names. Update/removal now reconcile
   installed same-name links owned by this exact checkout, including deleted
   source targets. Foreign links, custom aliases, user files and backups survive.
3. A known missing required agent was discovered after destination writes.
   Required source files and the adapter's reviewer catalog are now validated
   before installation starts. Independent review also reproduced an installation
   that passed with a missing catalog; absence, invalid JSON and inconsistent
   reviewer names now fail before destination writes.

Reconciliation runs after current links verify and supports the existing dry
run. This is not a claim that every filesystem failure is transactional.
Rerunning the installer after changing revisions discovers additions and removes
retired owned names. Native model/provider configuration remains host-owned.

## Validation and maintenance contract

Final local checks passed:

| Check | Observed result |
| --- | --- |
| Canonical source gate | 85 skills, 12 agents, 2 adapters and 9 mandatory reviewers. |
| Node regression suites | 15 passing tests, no failures or skips; installation lifecycle, catalog failures, host-local SDK resolution, modified-entry preservation, configuration ownership and Pi package/discovery. |
| Focused OpenCode suite | 66 passing cases; native-shaped CLI fixtures, actual SQLite queries/storage, full catalog capture and actual adapter functions with the schema factory substituted. |
| Artifact/session/export suite | 16 passing groups, including altered/missing receipts, confinement, native-shaped child outcomes, incomplete or partial skill evidence, branch selection and failed publication. |
| Pi adapter boundary | All 9 identities; factory lifecycle, role separation, finite tools and receipt integrity. |
| OpenCode native 1.19.5 | Full preflight passes with artifacts off and on; all 12 roles/85 cookbook skills; actual SDK/context artifact write/read pass; primary write and reviewer-ID spoof are denied. No model calls. |
| Pi native 1.4.0 + extension 0.1.26 | 6 passing loader/helper checks, including actual native fork creation and skill/artifact I/O; child execution replaced by a capture function. |
| Pi native 1.4.0 + extension 0.1.27 | Expected incompatibility reproduced: all 3 parent delegation checks fail because the native ceiling removes `read`. |
| Syntax and whitespace | Script/adapter JavaScript, shell syntax and `git diff --check` pass. |

The repository gates exercise the changed failure paths without installing
third-party runtimes or calling a model in ordinary CI:

```bash
scripts/check-canonical-sources.sh
scripts/smoke-opencode-scripts.sh
scripts/smoke-run-artifacts.sh
node --test scripts/test-*.js
node scripts/check-pi-reviewer-boundary.js
```

`smoke-opencode-scripts.sh` includes the focused OpenCode CLI/session/adapter
regressions. Its CLI transport is a fixture; the artifact implementation is real
with the host's schema factory substituted. The Pi boundary suite models the
uninitialized loader lifecycle and checks actual adapter functions. Neither is
described as a native model execution.

The separate, optional `scripts/check-pi-native-compatibility.js` loads explicitly
supplied installed Pi/extension packages and exercises their real helpers. It
does not download packages, change user configuration, start a child Pi, or call
a model. Its injected child-execution dependency is stated in the output.

After selecting the checked OpenCode version and installing the cookbook, the
native artifact path can be probed without a model call:

```bash
export AGENTS_COOKBOOK_RUN_DIR="$(mktemp -d)"
scripts/preflight-opencode-ping-pong.sh
opencode debug agent plan-coverage-reviewer --tool review_artifact \
  --params '{"artifact_id":"plan-coverage-reviewer","summary":"Native transport check.","content":"# Native transport check"}'
opencode debug agent ping-pong-plan --tool review_artifact_read \
  --params '{"artifact_id":"plan-coverage-reviewer"}'
node scripts/check-run-artifacts.js --run-dir "$AGENTS_COOKBOOK_RUN_DIR" \
  --reviewer plan-coverage-reviewer
```

The corresponding denial controls are a primary calling `review_artifact` and
the selected reviewer supplying another reviewer's ID; both must fail. Use a
fresh run directory for each probe, and unset the variable afterward. These
commands test native transport, not a completed reviewer analysis.

For a future host upgrade, recheck the exact package/source and effective native
contracts; add a regression for any observed break; then run the appropriate
native compatibility check. Complete model-backed sessions remain required for
claims about actual reviewer execution, model quality, context behavior or
profile promotion. Follow [local runtime qualification](local-runtime-qualification.md).

“Platinum” here means explicit contracts, source-grounded compatibility, tested
failure paths and honest unknowns. This audit does not certify every future host
release, prove absence of all defects, measure hallucination reduction, or claim
a completed model-backed nine-reviewer flow.
