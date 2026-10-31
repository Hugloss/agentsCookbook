# Agensi distribution

Agents Cookbook can distribute its canonical skills through Agensi while keeping
the existing OpenCode and Pi setup. The exporter builds focused skill packs from
the same `skills/` source; Agensi supplies those instructions to a connected
agent through MCP. The host continues to own models, sessions, tools, permissions,
execution, isolation, and persistence.

This is a packaging and publishing workflow. A locally validated ZIP is not an
approved Agensi listing or evidence of successful execution in a connected host.

CI builds candidates for pull requests and updates to `main`. It does not
synchronize GitHub with Agensi. Follow the [skill lifecycle guide](agensi-lifecycle.md)
for additions, updates, deletions, renames, moves, and publication tracking.

## Choose the delivery route

| Route | What it provides | Setup and boundary |
| --- | --- | --- |
| OpenCode or Pi native installation | Canonical skills, supported agent wrappers, and host adapters | Keep using `scripts/link-opencode-local.sh`; see [installation](installation.md). Agensi is optional. |
| Agensi | Individual skills selected from a published pack, plus supporting text | Connect a host that supports Agensi's remote MCP server and OAuth sign-in. The host must also have the tools needed for the chosen task. |
| A ChatGPT environment with personal-skill support | A native skill imported from the canonical folder, including its referenced resources | Use that environment's supported skill-import workflow. Availability depends on the environment; an ordinary chat upload is not proof of persistent installation. |
| ChatGPT connected to Agensi | Skill instructions loaded through the Agensi connector during use | Follow the current connector setup available to that account. This is separate from native personal-skill installation. |

Agensi currently delivers text through MCP only. It does not install plugins,
hooks, slash commands, MCP settings, or the cookbook's OpenCode/Pi adapters. Its
delivery does not establish the permission boundaries or nine-reviewer execution
of the optional Ping-Pong/Ping-Ping flows. Use the existing native workflow when
those capabilities are required.

Agensi's [connection guide](https://www.agensi.io/docs/mcp-setup) explicitly
describes ChatGPT and several other hosts. It does not separately qualify Pi or
OpenCode. Native cookbook installation remains the documented route for those
hosts; do not infer Agensi compatibility from Markdown compatibility alone.

## Five packs, one catalog

[`distribution/agensi-packs.json`](../distribution/agensi-packs.json) groups
existing headings from the [skill catalog](../skills/README.md). It contains
listing metadata and category selections, not another list of skill identities.
Canonical discovery remains `skills/*/SKILL.md`.

The initial catalog contains 85 skills:

| Pack and stable ID | Choose it for | Initial skills |
| --- | --- | ---: |
| Review and Planning (`review-planning`) | Finding an investigation target, reviewing a change, or checking an implementation plan. | 15 |
| Reliability and Qualification (`reliability-qualification`) | Concurrency, delivery, recovery, repair campaigns, and evidence needed to qualify execution. | 21 |
| Evidence Integrity (`evidence-integrity`) | Whether identities, evidence, stored state, and conclusions remain trustworthy across boundaries. | 20 |
| Architecture and Simplicity (`architecture-simplicity`) | Competing authorities, repeated decisions, unnecessary paths, and hidden effects. | 19 |
| Testing and Isolation (`testing`) | Integration fixtures, event completion, test setup, isolation, and behavioral test boundaries. | 10 |

Start with the pack matching the immediate task. A source/test change review is
in **Review and Planning**; constructing or restructuring integration tests is
in **Testing and Isolation**. Choose one relevant skill inside the pack. A pack
is a collection to select from, not a command to execute every included review.

Counts describe the initial source revision; the exporter derives actual
membership from the selected catalog and checks it against canonical folders.
Adding a skill to an existing category makes it part of that category's pack.
Review the grouping when adding a category or when a pack approaches the
marketplace limit of 50 skills.

The reliability pack keeps `empirical-benchmark-campaign`,
`adversarial-repair-campaign`, and `dogfood-saturation-loop` together. They have
different execution, repair, and closure contracts; packaging does not combine
them into one procedure. Other cross-skill recommendations are routing advice.
If a needed specialist is in another pack, locate and load it explicitly or use
the canonical repository. Do not assume its instructions are already available.
In particular, the repair campaign can obtain qualifying defect proof from
`codebase-finding-derivation` in **Review and Planning** or the appropriate narrow
specialist in another pack. Keeping campaign skills together does not bundle
every possible defect oracle or remove that evidence handoff.

An Agensi *skill pack* is one listing containing several skills. Agensi's
*bundle* feature combines separate paid listings and is unnecessary for these
free catalog packs.

## Build from an identified source

The exporter requires Git and Python 3's standard library. It adds no package
dependencies and does not run an installer, contact Agensi, or publish a listing.
Use a fresh output directory for each release so artifacts from different source
revisions are not mixed. From the repository root:

```bash
python3 scripts/package-agensi.py --output-dir dist/agensi
```

Select a commit or tag explicitly when preparing a release:

```bash
python3 scripts/package-agensi.py --output-dir dist/agensi --ref HEAD
```

Use a known commit or tag in place of `HEAD` for a repeatable release. The
exporter resolves the reference to an immutable commit and packages that
revision's canonical source, rather than silently mixing edited skill files
with committed files. The selected commit must include the distribution
manifest; newly added or edited worktree files do not become release inputs
until committed. A checkout predating this packaging support cannot be exported
by borrowing a manifest silently from another revision.

The output contains `agents-cookbook-<pack-id>.zip` for each pack. Each ZIP has a
root `README.md`, `LICENSE`, `SOURCE.json`, and the selected `skills/<name>/`
folders. The README groups its skills by the existing catalog categories and
includes their catalog descriptions and links. That navigation is generated
from the selected source revision rather than maintained as another skill list.
`SOURCE.json` records the canonical repository URL, full source commit,
pack ID, sorted skill membership, the distribution manifest hash, and SHA-256 of
every other exported file. It also records `content_sha256`, a digest of that
sorted path-to-file-hash mapping. The mapping excludes `SOURCE.json` to avoid
circular identity and to keep source-only provenance changes separate from
delivered content changes. The README points to `SOURCE.json` for the exact
revision, so a new commit alone does not change the content digest. Keep the
ZIP and this inventory together so a marketplace update can be traced back to
the exact reviewed source. Archive ordering and metadata are deterministic for
the same committed inputs.

Each pack preserves the complete selected skill directories, including
references and optional `agents/openai.yaml` metadata, and the repository's MIT
license. Native metadata remains source content; Agensi does not turn it into a
host configuration or enforce its permissions. Generated package documentation
describes the pack and source identity without changing the canonical prompts.

Review the generated archive contents, skill counts, reference closure, and
hashes before uploading. Build twice from the same inputs if byte reproducibility
is material to the release. A hash identifies bytes; it does not prove runtime
compatibility, skill quality, or marketplace acceptance.

The GitHub Actions workflow also produces candidate package artifacts for
inspection. Downloading that artifact can add an outer ZIP around the pack ZIPs.
Extract the outer archive and upload **one inner
`agents-cookbook-<pack-id>.zip` per Agensi listing**. Agensi does not discover
`SKILL.md` inside a nested ZIP; uploading the aggregate artifact archive will
not publish all packs.

## Requirements to disclose in each listing

Every pack needs a host able to inspect the relevant source, requirements, and
evidence. A skill must return bounded or insufficient evidence when those inputs
are unavailable. Loading instructions never grants repository access, shell
access, credentials, network access, or permission to change files.

| Pack | Inputs and capabilities to disclose |
| --- | --- |
| Review and Planning | Relevant repository files, requirements, and comparable base/candidate changes. Source and test review need both sides of the change. Performance claims need observations; planning alone does not require executing the plan. |
| Reliability and Qualification | Source, configuration, lifecycle contracts, and applicable failure/recovery evidence. Repair or execution skills additionally need an editable target and its normal test/tool environment. Kafka runtime verification needs the relevant service and failure scenarios. Python repair needs the project's Ruff/Pyright/ty setup. Benchmark campaigns need an independently defined experiment and suitable execution/evidence tooling; EvalShot remains external. Masking needs the supplied evidence and disclosure policy. |
| Evidence Integrity | Relevant producers, consumers, transformations, stored representations, and provenance. Reproducing runtime or persistence behavior needs the target's execution environment; source inspection alone must not be presented as that proof. |
| Architecture and Simplicity | Source paths and the governing ownership/behavior contracts. Historical reconstruction also needs the relevant revisions. Applying repairs or proving runtime equivalence needs the target project's tools. |
| Testing and Isolation | Test sources, production paths, fixture configuration, and the project's Python/pytest environment for implementation. Local containers need a compatible container runtime; externally provisioned services need reachable endpoints and authorized credentials. Declare the selected provisioning and cleanup owners. Event verification needs the relevant observer/service access. |

No pack includes a model, container runtime, database, Kafka broker, benchmark
runner, or credential. Credentials stay in the user's host configuration and
must not enter an uploaded archive. Actual implementation and validation use the
target project's existing execution authority.

## Agensi packaging and runtime constraints

These details were checked against Agensi's public documentation on
2026-10-30. Recheck them before publication, especially when adding new resource
types or scripts.

| Constraint | Current documented behavior |
| --- | --- |
| Skill discovery | Every `SKILL.md` in the ZIP is discovered, at any depth. One is a skill; 2–50 make a pack. A root `SKILL.md` is not required. |
| Pack name | The root README's first heading can supply the pack name. Listing names must be unique and at most 60 characters. |
| Selection | The agent receives included skill names, descriptions, and paths, then requests a selected skill. Clear frontmatter remains important. |
| Supporting files | The selected skill's folder and files outside all skill folders are available. Required references must remain in the archive. |
| Website upload | At most 50 MB and 1,000 files. |
| Agent-assisted upload | At most 5 MB and 100 files; text only. A website-valid pack is not automatically valid for this route. |
| Delivery budget | All `SKILL.md` files plus at most 200 other text files, within 6 million characters per listing. A pack shares this budget across its skills. |
| Binary resources | Images, PDFs, and documents may be listed but are not served to the agent. Essential instructions must be text. |
| Bundled dependencies | `node_modules`, Python environments, and `site-packages` are prohibited. Executables fail the file-type scan. |
| Script execution | Each script is written unchanged to a temporary file, executed, then removed. It cannot rely on other packaged files being materialized beside it. The guideline is under 20 KB of logic per script. |

The initial canonical skill folders contain Markdown and optional YAML metadata,
with no bundled executable helpers. If a later skill gains scripts or binary
assets, review its actual execution and reference needs before exporting it.
Do not flatten or rewrite a helper merely to claim compatibility without testing
the resulting behavior.

Agensi's [loading protocol](https://www.agensi.io/docs/how-agents-load-skills)
uses `get_skill({slug})` for a pack index, `get_skill({slug, path})` for a selected
skill, and `get_skill({slug, file})` for an individual text resource. This is
remote text retrieval, not a materialized checkout with ordinary filesystem
relative paths. Fetch required references through the connector when needed.

## Connection and update behavior

Agensi's documented endpoint is `https://mcp.agensi.io/mcp/auth`, using Streamable
HTTP and OAuth sign-in. Follow its current host-specific setup instructions; no
API key belongs in a package.

Two service constraints matter when switching between hosts or reproducing work:

- **One connected agent per account.** Signing in a new client disconnects the
  previous client. Native cookbook installations remain independent of this
  connection policy.
- **Newest approved version on use.** Agensi does not offer buyers a way to pin
  an older skill version. Keep using a pinned native cookbook revision for work
  that requires a fixed methodology. Package provenance identifies the source
  that was published; it does not add version selection to Agensi.

Agensi asks agents to use the skill and return the resulting work without
persisting or exporting the delivered skill text. A skill can still create the
requested output artifact. Native installation from the public MIT-licensed
repository is a separate route; distributing through Agensi does not replace
the canonical source or its license.

## Publish through the website

Publishing is an account action separate from building the packages:

1. Create or sign in to an Agensi account and enable **Creator Mode** under
   **Dashboard → Settings**. Complete the creator profile. Free listings need no
   payout setup.
2. Build and inspect a pack from the reviewed source revision. Exercise the
   relevant skill and reference-loading behavior in the intended host before
   advertising compatibility.
3. Open [Submit a skill](https://www.agensi.io/dashboard/submit) and upload that
   pack's ZIP. One pack creates one listing; repeat for the other packs.
4. Use the generated pack name and summary as a starting point. Supply an
   accurate description, a real request and complete example result, compatibility
   requirements, limitations, categories, and the canonical repository/docs link.
   Keep initial listings free and preserve MIT attribution.
5. Review detected permissions, file access, tools, network access, and required
   services against the actual skill contents. Do not claim a capability merely
   because the upload form accepts it.
6. Inspect the listing preview and submit it for review. Agensi scans the files,
   performs an AI review, and requires human approval for a new listing. A local
   check does not guarantee approval.
7. Once approved, verify that a connected host can find the pack, select a skill,
   retrieve its required references, and produce the expected bounded output on
   a representative task. Record the source revision, listing/version, host,
   capabilities, and observed result.

Agensi supports later agent-assisted submissions through its authenticated
creator tools. New-listing `submit_skill` has a preview and explicit confirmation;
existing-listing `update_skill` is a separate full-package update without that
preview protocol. Review the intended update before calling it. This exporter
does not perform either action. See the [lifecycle guide](agensi-lifecycle.md)
for stable listing identity, pending updates, and verification after approval.

For an update, upload the newly reviewed ZIP on the existing listing's edit page
and describe the change. The current version remains live during review or if
the update is rejected. Verify the approved version after publication and retain
its source/hash inventory. Marketplace version numbering and Git revisions are
different identities; preserve their mapping.

## Validation and claims

Keep the evidence levels separate:

- Packaging checks establish membership, included bytes, reference availability,
  source identity, and the limits they actually enforce.
- Repository checks establish the cookbook's structural and adapter contracts.
- A live Agensi load establishes availability for that listing and host.
- A representative task exercises the chosen skill and host capabilities.
- Behavioral quality, reliability, or performance claims require appropriate
  execution evidence and controls. Reusable evaluation corpora and runners remain
  in EvalShot; a packaging change does not automatically require a second PR.

Run the repository checks required by
[`CONTRIBUTING.md`](../CONTRIBUTING.md#validation) before opening a PR. Report
checks that were unavailable or not executed. Do not describe package generation
as marketplace approval, universal ChatGPT support, or full OpenCode/Pi runtime
qualification.

## Official references

- [How Agensi works](https://www.agensi.io/docs/how-it-works)
- [Package your skill](https://www.agensi.io/docs/packaging)
- [What you can sell](https://www.agensi.io/docs/what-you-can-sell)
- [How agents load skills](https://www.agensi.io/docs/how-agents-load-skills)
- [Connect your agent](https://www.agensi.io/docs/mcp-setup)
- [MCP server and sign-in](https://www.agensi.io/docs/mcp-server)
- [Creator quickstart](https://www.agensi.io/docs/creator-quickstart)
- [Submit on the website](https://www.agensi.io/docs/submit-on-the-website)
- [Submit from your agent](https://www.agensi.io/docs/submit-from-your-agent)
- [Review and approval](https://www.agensi.io/docs/review-and-approval)
- [Use a skill](https://www.agensi.io/docs/use-a-skill)
- [Update your skill](https://www.agensi.io/docs/updates)
- [Creator FAQ](https://www.agensi.io/docs/creator-faq)
- [Protect your work](https://www.agensi.io/docs/protect-your-work)
