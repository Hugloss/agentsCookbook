# Security Policy

Agents Cookbook is primarily a prompt library, but the repository also contains installation helpers and narrow OpenCode/Pi adapters that run inside developer tooling. Security issues in those integration surfaces should be reported privately when possible.

## Security-sensitive areas

Examples include:

- installer behavior that can overwrite or remove user files unexpectedly;
- path traversal, symlink, or run-root escapes;
- artifact reads/writes outside the configured bounded root;
- reviewer tools receiving more authority than their declared contract;
- a runtime adapter allowing an unexpected agent to write/read reviewer artifacts;
- command, path, or environment injection in repository-owned scripts;
- secrets or credentials being persisted or exposed by repository-owned integration code.

Prompt-quality disagreements, false positives, weak review methodology, model hallucinations, and normal OpenCode/Pi product bugs are not security reports unless they create a concrete security boundary violation in code owned by this repository.

## Reporting

If GitHub shows a **Report a vulnerability** option for this repository, use that private channel.

If a private GitHub vulnerability-reporting channel is not available, open a minimal public issue asking for a private reporting path. Do **not** include exploit details, secrets, private repository data, or a working proof of concept in the public issue.

Please include privately, when available:

- affected file/path and commit;
- the security boundary that is violated;
- reproduction steps;
- expected versus actual behavior;
- impact;
- the smallest known mitigation.

## Supported versions

Until tagged releases and a backport policy exist, security fixes target the current `main` branch. Older commits should not be assumed to receive fixes.

## Host responsibility

OpenCode, Pi, model providers, shells, containers, operating systems, and other external runtimes remain responsible for their own security boundaries. Agents Cookbook does not provide a general sandbox or execution-security layer.
