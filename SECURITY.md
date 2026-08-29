# Security Policy

## Supported versions

Benedict is pre-1.0. Security fixes ship on the latest released version only.

| Version | Supported |
| ------- | --------- |
| Latest 0.6.x release | Yes |
| Older 0.6.x patches | No — upgrade to the latest 0.6.x |
| < 0.6 | No |

The released version is in `pyproject.toml` and `src/benedict/__init__.py`.

## Reporting a vulnerability

Do not open a public GitHub issue, pull request, or Slack thread for a vulnerability.

Report privately using one of these channels:

1. **Preferred:** [GitHub private vulnerability reporting](https://github.com/mkarots/benedict/security/advisories/new) (Security → Report a vulnerability)
2. **Email:** michael.karotsieris@gmail.com with the subject `Benedict security: <short title>`

Include:

- Affected version
- What the issue is and how to reproduce it
- Impact (what an attacker could do)
- A suggested fix, if you have one

Do not include Slack tokens, API keys, or other secrets beyond what is needed to describe the issue.

## What to expect

| Step | Target |
| ---- | ------ |
| Acknowledgement | Within 2 business days |
| Initial assessment (accepted, needs more info, or declined) | Within 7 days of acknowledgement |
| Fix on a supported version | As soon as we can ship a patch; we aim to fix before public disclosure |

If we accept the report, we will confirm the issue, agree a disclosure date, and ship a patch on the latest supported version. We will credit you in the changelog if you want that.

If we decline the report, we will say why (not a vulnerability, already fixed, or out of scope).

Please do not disclose the issue publicly until we have shipped a fix or agreed a date.

## Operator practices

Benedict reads local checkouts and Slack. Treat the host as trusted.

- Keep Slack tokens and `ANTHROPIC_API_KEY` in `.env`. Never commit them.
- Do not paste tokens or keys into issues, pull requests, or Slack.
- Limit who can run the process and who can read the data directory.

Conduct reports are not security reports. Use [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
