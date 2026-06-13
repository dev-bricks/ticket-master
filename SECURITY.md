# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x | Yes |

## Reporting a Vulnerability

If you discover a security vulnerability, please **do not** open a public GitHub
issue. Instead, report it privately:

1. Open a [GitHub Security Advisory](https://github.com/dev-bricks/ticket-master/security/advisories/new)
   in this repository, or
2. Send a brief description to the maintainer via the contact on
   [github.com/lukisch](https://github.com/lukisch).

Please include:
- A description of the vulnerability
- Steps to reproduce or a proof-of-concept
- The potential impact

You can expect an acknowledgement within 7 days and a fix or mitigation plan
within 30 days where feasible.

## Scope

ticket-master is a local agent router. It does not handle network requests,
authentication, or user data directly. The primary security surface is:

- **Provider CLI invocation:** starters pass a bootstrap prompt to your locally
  installed LLM CLI. Ensure your provider CLI is from a trusted source.
- **Config file:** `config/ticket-master.config.json` is gitignored. Do not
  commit credentials or API keys.
- **Ticket files:** tickets may contain internal project information. The
  `tickets/` directory is partially gitignored (lifecycle subdirs are empty
  by default; adapt `.gitignore` to your privacy requirements).
