# Agensi skill lifecycle

The cookbook automatically builds the desired pack contents. Agensi publication
requires an explicit submission to the appropriate listing. Once an update is
approved, Agensi serves that version on the next load; the previous version
remains live while review is pending or the update is rejected.

This guide separates **candidate built**, **submitted**, **approved**, and
**verified live**. A CI success or upload response must not stand in for the last
state. See [Agensi updates](https://www.agensi.io/docs/updates) and the
[distribution guide](agensi-distribution.md).

## What changes automatically

Update the canonical skill folders and the existing catalog together. Export
from the committed revision after the required checks pass.

| Change | Candidate build | Publication action |
| --- | --- | --- |
| Edit a skill or its resources | Includes the new bytes in its owning pack | Submit the complete updated pack to its existing listing. |
| Add a skill to a mapped category | Discovers it without another skill registry | Update that category's existing pack listing. |
| Delete a skill and its catalog entry | Omits the entire former folder, including resources | Update the existing pack, then verify removal on the live service. |
| Rename a skill | Removes the former path and includes the new one | Describe the replacement and verify both paths; assume no alias. |
| Split a skill into several skills | Includes the replacement folders when they are cataloged | Update affected packs and document which replacement handles each old use. |
| Move a skill between packs | Removes it from one and adds it to the other | Coordinate updates to both existing listings. |
| Delete the last skill in one category | Allows the empty category if its pack still contains skills | Update the remaining nonempty pack normally. |
| Leave an entire declared pack empty | Stops with an error | Remove or reassign the pack in the manifest; decide remote retirement separately. |
| Add a catalog category | Stops if its skills have no pack assignment | Assign the category explicitly, then rebuild. |
| Create a new pack ID | Builds its archive after categories are assigned without overlap | Create a new listing unless an explicit identity migration says otherwise. |
| Remove a pack ID | Stops producing its archive after its skills/categories are removed or reassigned | Retire the actual listing explicitly; a missing local ZIP does not remove it. |
| Grow a pack beyond 50 skills | Stops rather than omitting or silently splitting skills | Choose the new grouping and coordinate any resulting listing changes. |

Removing or renaming a skill also requires reviewing its callers, agent bindings,
flow recipes, documentation, and cross-skill handoffs. The exporter checks local
Markdown file links; it does not interpret every prose reference to another
skill. Fix those references in the same source change.

## Identify changed packs without unnecessary releases

Every build records exact provenance in `SOURCE.json`, including its commit and
the distribution manifest hash. The ZIP hash identifies that exact artifact.
Those identities can change even when a particular pack's instructions do not.

Use `content_sha256` to compare the payload for the **same resolved pack/listing**:

- It includes filenames and file bytes for all skills, supporting resources,
  optional UI metadata, the license, and the generated README.
- The README includes the pack name, summary, catalog categories and member
  descriptions, skill links, and delivery guidance, so those changes also affect
  the content digest.
- It excludes only `SOURCE.json`, where source revision and build provenance live.
  A commit-only change or an unrelated pack's metadata change therefore does not
  require another release of an unchanged pack.

Compare with the last **verified live** content digest for each listing, not
merely the previous Git commit or CI run. The five listings may have different
approved source revisions. A missing previous digest means unknown; inspect the
live package or establish the first publication record before deciding no update
is needed. Older candidates without the field need an explicit comparison.

A digest is an equality check, not a marketplace identity or an approval. Equal
content in different pack IDs does not authorize replacing or deleting a listing.

## Keep one publication record per pack

Use the existing local pack ID as the key in the maintainer's release record.
For each pack, record:

- the confirmed Agensi listing identifier/URL and current slug;
- the last verified live marketplace version, source commit, content digest,
  and exact uploaded ZIP hash;
- any pending candidate's identities, submission outcome, and review state;
- any rename, move, or retirement that is still incomplete.

Populate remote identifiers from the actual service. Do not derive a new slug
from a changed display name or assume that an unknown listing is absent. A
display-name change normally keeps the local pack ID and targets its existing
listing. Changing the local ID requires an explicit identity decision.

Keep pending and approved records separate. Advance the live record only after
approval and verification. Record a rejection without replacing the known live
baseline. When equal content needs no update, retain the actual approved commit
and version; a newer checked source is not a new publication. CI artifacts are
candidate outputs, not this publication record.

## Submit a complete snapshot

The supported website route uploads a new ZIP on the existing listing's edit
page. For creator MCP use, `update_skill` takes the existing `skill_slug` and
the **full package** as `files`, with optional version and changelog fields.
Send the complete desired pack, not only changed files. Include a changelog that
identifies additions, removals, replacements, or changed prerequisites.

New-listing `submit_skill` has a preview and confirmation flow. The advertised
`update_skill` schema has no equivalent preview, expected-current-version, or
idempotency-key parameter and marks updates non-idempotent. Inspect the live
listing and pending submissions, review the intended files, and serialize
updates to each listing. After a timeout or uncertain response, reconcile the
service's state before retrying; do not submit again blindly.

The public interfaces checked on 2026-10-30 document explicit submissions rather
than repository watching or GitHub webhooks. The current exporter has no uploader,
OAuth client, review polling, or remote deletion behavior. An eventual publisher
can use the supported creator interface, but must retain these state boundaries.

Sources: [agent submission](https://www.agensi.io/docs/submit-from-your-agent),
[website submission](https://www.agensi.io/docs/submit-on-the-website), and the
public `tools/list` metadata at [Agensi MCP](https://mcp.agensi.io/mcp).

## Verify additions, removals, and moves after approval

Load the actual listing's pack index, compare its membership with the approved
candidate, and retrieve `SOURCE.json` and the changed skills/resources through
the advertised file interface. Confirm the intended source and content identity.
Compare the retrieved skill/resource bytes with the candidate's recorded file
hashes; do not rely only on the receipt's assertion of a content digest.
For removals and renames, also check the former member/resource paths. A locally
omitted file is not proof that Agensi no longer serves its old path; the public
docs do not specify historical-path deletion or alias guarantees.

Use the returned paths rather than guessing them. Record a mismatch or failed
verification as incomplete publication. An already-loaded conversation and a
native copy are separate from the next hosted load; do not promise retroactive
replacement or revocation of those copies.

A move between listings has independent approvals. Normally publish and verify
the destination first, then remove the member from the source listing. This
preserves availability but can briefly expose both copies. If duplicate
availability is unacceptable, agree on another transition before submission;
do not claim an atomic change across listings. Complete the move only after both
listings match the intended final membership.

See [skill loading](https://www.agensi.io/docs/how-agents-load-skills).

## Retire an entire listing explicitly

Removing a local pack definition does not take its remote listing down. Agensi
documents Creator Studio deletion for a listing nobody has bought; taking down
a purchased listing requires contacting Agensi. Do not invent a pause/delete MCP
operation or represent an empty pack as a supported retirement mechanism.

Follow the current service policy and verify the outcome before marking the
listing retired. See [taking a listing down](https://www.agensi.io/docs/protect-your-work).

## Native installations follow their own update route

Agensi approval does not update OpenCode/Pi installations or ChatGPT personal
skills. Follow the canonical [native update instructions](installation.md#updating)
for linked OpenCode/Pi sources, including additions, removals, and renames.
Native personal-skill copies require their environment's supported update or
removal workflow.
