---
name: sensitive-data-masking
description: Identifies and consistently masks PII, credentials, secrets, and sensitive infrastructure data in supplied documents and logs without leaking original values.
license: MIT
---

# Sensitive Data Masking

Standalone, bounded transformation for producing shareable documents and logs with sensitive values removed while preserving useful structure and context.

## INVARIANT

> **Do not declare output masked while any detected or unresolved sensitive value remains in cleartext.**

The same sensitive source value should map to the same placeholder within one masking scope. Placeholder identity must not persist across unrelated documents unless explicitly required.

## HUNT

Hunt for:
- personal identity: names, email addresses, phone numbers, usernames, physical addresses, dates of birth, and national or personal identification numbers;
- credentials and secrets: passwords, API keys, access tokens, bearer tokens, OAuth credentials, session identifiers, cookies, private keys, secret keys, and authentication headers;
- connection material: database connection strings, authenticated URLs, DSNs, credentials embedded in command lines, and secret-bearing environment variables;
- infrastructure: internal URLs, hostnames, domain names, IP addresses, service addresses, cluster or node identifiers, and other non-public topology;
- financial data: bank accounts, payment-card numbers, and similar financial identifiers;
- identity documents: passport, driver's-license, and comparable document numbers;
- path leakage: user names, account names, tenant identifiers, or other sensitive values embedded in filesystem paths;
- nested values: sensitive data embedded inside JSON, YAML, XML, headers, URLs, query parameters, stack traces, shell commands, exception messages, or structured log fields.

Treat context-sensitive values such as person names, addresses, dates of birth, and apparently harmless identifiers as unresolved when their sensitivity cannot be determined confidently.

## MASK

Replace sensitive values with typed opaque placeholders.

Prefer distinct placeholders when preserving relationships is useful:

- names → `[NAME_1]`
- phone numbers → `[PHONE_1]`
- email addresses → `[EMAIL_1]`
- physical addresses → `[ADDRESS_1]`
- personal or national IDs → `[ID_NUMBER_1]`
- dates of birth → `[DOB_1]`
- URLs → `[URL_1]`
- hosts, domains, and IP addresses → `[HOST_1]`
- usernames or account identifiers → `[USER_1]`
- API keys, tokens, credentials, and secret keys → `[SECRET_1]`
- passwords → `[PASSWORD_1]`
- financial identifiers → `[FINANCIAL_1]`
- document identifiers → `[DOCUMENT_ID_1]`
- other sensitive values → `[SENSITIVE_1]`

Reuse the same placeholder for repeated occurrences of the same source value within the current masking scope.

Different source values should normally receive different placeholders even when they belong to the same category.

Do not preserve original values in placeholder metadata.

## PROVE

After masking:

1. scan the transformed output again for structured sensitive-data patterns;
2. inspect context for unstructured or partially transformed sensitive values;
3. inspect nested structures such as URLs, headers, connection strings, command lines, and serialized objects;
4. verify that repeated source values were masked consistently;
5. verify that masking did not copy the original value into comments, summaries, evidence, or metadata;
6. distinguish completed masking from unresolved uncertainty.

A verification pass must inspect the **masked output**, not merely trust the list of replacements performed during the first pass.

If verification cannot establish that all detected sensitive material has been removed, return `MASKING_INCOMPLETE` rather than claiming success.

## DO NOT REPORT

Do not:
- report discovered secrets or PII in cleartext;
- quote sensitive source fragments as evidence;
- place original values in replacement ledgers, diagnostics, or summaries;
- use raw values as placeholder suffixes;
- substitute a hash of the original value as masking when that hash could enable correlation, enumeration, or recovery;
- treat regex coverage alone as proof that unstructured PII is absent;
- silently ignore malformed or partially recognized credentials;
- expose credentials hidden inside URLs, headers, environment assignments, or connection strings;
- preserve masking identities across unrelated documents unless that linkage is explicitly part of the requested contract;
- claim that unsupported, unreadable, truncated, or uninspected content has been verified.

## PREFER

Prefer:
- deterministic parsing and pattern matching for structured values;
- contextual analysis for names, addresses, dates of birth, and other unstructured PII;
- parsing structured formats before masking raw text when doing so reduces ambiguity;
- masking the smallest complete sensitive value that prevents disclosure while retaining useful surrounding context;
- stable placeholders within one document or explicitly defined masking scope;
- fail-closed handling when a value is plausibly sensitive and cannot safely be classified;
- preserving line structure, ordering, timestamps, severity, field names, and other non-sensitive evidence needed for debugging or analysis.

For logs, inspect authentication headers, request URLs, query parameters, environment dumps, exception text, connection strings, command-line arguments, stack traces, and serialized payloads especially carefully.

## BOUNDARY

This skill transforms supplied bounded content.

It does not become:
- a DLP platform;
- a secret manager;
- a credential-rotation system;
- a document crawler;
- an OCR system;
- a log-ingestion or observability platform;
- a persistent sensitive-value database.

Acquisition, storage, transport, access control, and destruction of the original sensitive source remain outside this skill unless separately specified.

## OUTPUT

By default return only the masked document or log.

When a report is requested, return `# Sensitive Data Masking Report` containing:
- status: `MASKED` or `MASKING_INCOMPLETE`;
- categories detected;
- replacement count per category;
- total replacements;
- unresolved sensitive categories or regions, if any;
- verification performed;
- unsupported or uninspected content, if any.

Never include original sensitive values in the report.

A `MASKING_INCOMPLETE` result must not be represented as safe-to-share output.
