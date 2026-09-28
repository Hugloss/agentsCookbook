---
name: sensitive-data-masking
description: Produces policy-safe shareable evidence by detecting, classifying, and consistently masking sensitive personal, secret, operational, and business data.
license: MIT
---

# Sensitive Data Masking

Standalone, bounded transformation for producing shareable evidence that preserves structure, relationships, and diagnostic meaning while preventing information outside the selected disclosure policy from crossing the trust boundary.

## INVARIANT

> **Nothing prohibited by the selected disclosure policy may survive in shareable output, and sanitization must not destroy permitted evidence needed to understand or reproduce the artifact.**

Detection and masking are separate decisions. Finding a value that looks operational, versioned, numeric, or identifier-like does not by itself make that value sensitive.

The same sensitive subject should map to the same typed placeholder within one masking scope. Different sensitive subjects should normally remain distinguishable. Placeholder identity must not persist across unrelated masking runs unless cross-run linkage is explicitly required.

Use this workflow:

`SCOPE -> HUNT -> CLASSIFY -> MASK -> PROVE`

## SCOPE

Establish the disclosure boundary before deciding what to mask.

Identify:
- who will receive the transformed artifact;
- what categories are prohibited, permitted, or unresolved for that recipient;
- whether public provenance or reproducibility metadata must remain visible;
- whether business-domain values may cross the boundary;
- the exact bounded input being transformed.

Typical boundaries include:
- same internal team;
- another internal team;
- trusted vendor or support case;
- customer;
- public issue or documentation;
- public benchmark or dataset.

If no disclosure policy is supplied, treat credentials and secrets conservatively, preserve clearly public or generic technical evidence, and mark context-dependent personal, operational, provenance, and business values unresolved rather than silently inventing a policy.

## HUNT

Detect broadly. Hunt for:

- personal identity: names, email addresses, phone numbers, usernames, physical addresses, dates of birth, and national or personal identification numbers;
- credentials and secrets: passwords, API keys, access tokens, bearer tokens, OAuth credentials, session identifiers, cookies, private keys, secret keys, authentication headers, and secret-bearing environment variables;
- connection material: database connection strings, authenticated URLs, DSNs, credentials embedded in commands, and connection parameters;
- internal identity: tenant, customer, account, subscription, project, organization, document, record, and other proprietary identifiers;
- operational topology: private service and application names, hostnames, FQDNs, internal domains, IP addresses, routes, clusters, nodes, namespaces, pods, deployments, queues, Kafka topics or consumer groups, indexes, registries, and environment-specific labels;
- internal provenance and build metadata: private repository names, private commit identities, build IDs, pipeline/run IDs, private release tags, private image coordinates, and other non-public versioning identities;
- business-domain values: customer or transaction data, monetary amounts, dates, domain identifiers, and other payload values when the disclosure policy classifies them as sensitive;
- financial data: bank accounts, payment-card numbers, and comparable financial identifiers;
- identity documents: passport, driver's-license, and comparable document numbers;
- path leakage: home-directory names, account names, repository names, tenant identifiers, mounts, or other sensitive values embedded in filesystem paths;
- commands and diagnostics: command lines, stack traces, exception text, environment dumps, HTTP headers, URLs, query parameters, and log fields;
- document and artifact metadata: filenames, archive manifests, document properties, build manifests, OCR-derived text, and metadata that may reveal prohibited identities or topology;
- nested values: sensitive material embedded inside JSON, YAML, XML, CSV, logfmt, query strings, headers, URLs, shell syntax, or serialized objects nested inside other serialized values.

Do not stop at the first representation of a sensitive subject. When one subject is identified, hunt correlated forms such as a service name embedded in pod names, routes, image tags, hostnames, paths, or index names.

## CLASSIFY

Classify each detected subject before replacement.

Use these broad classes:

| Class | Examples | Default treatment |
| --- | --- | --- |
| personal | names, email, phone, personal IDs | mask when crossing the permitted identity boundary |
| credential/secret | passwords, tokens, keys, authenticated cookies | mask or remove conservatively |
| internal identity | tenant, customer, proprietary object IDs | policy-dependent; normally mask for external/public sharing |
| operational topology | private services, clusters, namespaces, hosts, indexes, routes | policy-dependent; normally mask for external/public sharing |
| internal provenance | private commits, builds, pipelines, repository/release identities | mask when non-public or prohibited |
| business-domain value | transaction values, amounts, domain dates/IDs | policy-dependent |
| generic technical evidence | timestamps, HTTP codes, durations, counts, ports, protocol facts | normally preserve |
| public provenance | public package versions, public release tags, public repository/commit identities | normally preserve when useful for reproducibility |

Classification must consider context, field names, surrounding structure, provenance, and disclosure policy.

For opaque alphanumeric values, do not use appearance alone as the decision. An unknown opaque identifier in a sensitive field or prohibited context should be treated conservatively; a public checksum, HTTP status, duration, count, or reproducibility-critical public identity should not be destroyed merely because it resembles an ID.

If classification remains materially uncertain, keep it unresolved and do not claim the result safe to share.

## MASK

Replace classified sensitive values with typed opaque placeholders.

Prefer semantic placeholder types such as:

- names -> `[NAME_1]`
- phone numbers -> `[PHONE_1]`
- email addresses -> `[EMAIL_1]`
- physical addresses -> `[ADDRESS_1]`
- personal or national IDs -> `[ID_NUMBER_1]`
- dates of birth -> `[DOB_1]`
- usernames or account identifiers -> `[USER_1]`
- API keys, tokens, credentials, and secret keys -> `[SECRET_1]`
- passwords -> `[PASSWORD_1]`
- hosts, domains, and private IP addresses -> `[HOST_1]`
- services or applications -> `[SERVICE_1]`
- environments -> `[ENV_1]`
- clusters -> `[CLUSTER_1]`
- namespaces -> `[NAMESPACE_1]`
- indexes -> `[INDEX_1]`
- repositories -> `[REPOSITORY_1]`
- private commits -> `[COMMIT_1]`
- build identities -> `[BUILD_1]`
- pipeline/run identities -> `[PIPELINE_1]`
- private versions or releases -> `[VERSION_1]`
- tenant/customer identities -> `[TENANT_1]`
- business-domain identifiers -> `[DOMAIN_ID_1]`
- sensitive monetary values -> `[AMOUNT_1]`
- sensitive domain dates -> `[DATE_1]`
- financial identifiers -> `[FINANCIAL_1]`
- document identifiers -> `[DOCUMENT_ID_1]`
- other sensitive values -> `[SENSITIVE_1]`

Reuse the same placeholder for repeated representations of the same sensitive subject within the current masking scope, including correlated forms when they unambiguously identify that subject.

Different subjects should receive different placeholders even when they belong to the same category.

Do not:
- encode original values in placeholder suffixes or metadata;
- use reversible encodings as masking;
- substitute stable hashes when they enable correlation, enumeration, or recovery;
- make aliases stable across unrelated runs by default.

## STRUCTURED CONTENT

When a format is parseable, traverse the structure rather than treating it as one opaque string.

Inspect keys, values, attributes, text nodes, headers, query components, and nested serialized payloads. This includes JSON, YAML, XML, CSV, logfmt, URL/query structures, and structured log fields.

If a string field itself contains a serialized payload, inspect it recursively when safely recognizable. Bound recursion, total decoded size, and parser work so malformed or adversarial content cannot cause unbounded expansion.

Preserve syntax and framing whenever possible. If structural parsing fails or would be unsafe, fall back to bounded textual inspection and report the uninspected or unresolved region.

## PROVE

Verification is a second adversarial pass over the transformed output, not a restatement of what the first pass intended to replace.

Prove all of the following:

1. **Policy closure** — no detected subject prohibited by the disclosure policy survives in cleartext.
2. **Correlated-form closure** — derived forms such as service-based pod names, routes, hosts, paths, image names, or indexes do not leak the same prohibited subject.
3. **Structured closure** — nested and serialized structures were inspected to the declared bounds; unsupported or truncated regions are named.
4. **Referential consistency** — repeated references to the same subject use the same placeholder and distinct subjects are not accidentally collapsed.
5. **No side-channel copy** — originals were not copied into comments, summaries, replacement ledgers, evidence, filenames, or generated metadata.
6. **Structural validity** — parseable JSON, YAML, XML, CSV, and other framed content remains structurally usable when the output contract requires it.
7. **Diagnostic preservation** — permitted ordering, error types, causal relationships, field names, status codes, counts, timestamps, versions, and other useful technical evidence remain when policy allows.
8. **Uncertainty accounting** — every materially unresolved classification or uninspected region prevents a safe-to-share claim.

When a new reproducible leak pattern is discovered, preserve it as a focused regression attack before considering the masking contract closed.

If verification cannot establish the selected disclosure policy, return `MASKING_INCOMPLETE` rather than claiming success.

## DO NOT REPORT

Do not:
- report discovered secrets, PII, or policy-prohibited values in cleartext;
- quote sensitive source fragments as evidence;
- place original values in replacement ledgers, diagnostics, summaries, or metadata;
- treat regex coverage alone as proof that sensitive content is absent;
- silently ignore malformed or partially recognized credentials;
- expose credentials hidden inside URLs, headers, environment assignments, or connection strings;
- mask every commit, version, date, amount, number, checksum, or opaque identifier merely because it looks sensitive;
- destroy public or reproducibility-critical provenance when the policy permits it;
- collapse distinct services, tenants, IDs, or business subjects into one placeholder when their distinction matters;
- preserve masking identities across unrelated runs unless explicitly required;
- claim unsupported, unreadable, truncated, malformed, or uninspected content was verified;
- claim `MASKED` when classification is materially unresolved.

## PREFER

Prefer:
- explicit disclosure policy over category-wide assumptions;
- structural parsing before raw-text replacement where safe;
- deterministic detection for structured values and contextual classification for ambiguous values;
- masking the smallest complete sensitive subject that prevents disclosure while retaining useful surrounding evidence;
- preserving line structure, ordering, severity, causal relationships, field names, and permitted technical facts;
- public provenance and reproducibility metadata when policy permits them;
- conservative handling of credentials and unknown values in clearly sensitive contexts;
- a second attack pass that searches the sanitized artifact from a different angle than the first pass.

For logs, inspect authentication headers, request URLs, query parameters, environment dumps, exception text, connection strings, command-line arguments, stack traces, service-derived infrastructure names, and serialized payloads especially carefully.

## BOUNDARY

This skill transforms supplied bounded content under a declared disclosure policy.

It does not become:
- a DLP platform;
- a secret manager;
- a credential-rotation system;
- a document crawler;
- an OCR engine;
- a log-ingestion or observability platform;
- a corporate topology inventory;
- a persistent sensitive-value or alias database;
- an authority for deciding that all internal-looking metadata is secret.

Acquisition, storage, transport, access control, source destruction, and organization-wide classification policy remain outside this skill unless separately specified.

## OUTPUT

By default return only the masked artifact when the disclosure policy is satisfied.

When a report is requested, return `# Sensitive Data Masking Report` containing:
- status: `MASKED` or `MASKING_INCOMPLETE`;
- disclosure scope;
- categories detected;
- replacement count per category;
- total replacements;
- preserved public or diagnostic categories when relevant;
- unresolved sensitive categories or regions, if any;
- verification performed;
- unsupported, truncated, or uninspected content, if any.

Never include original sensitive values in the report.

A `MASKING_INCOMPLETE` result must not be represented as safe-to-share output.
