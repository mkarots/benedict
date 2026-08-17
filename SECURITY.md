# Security Policy

## Supported Versions

Security fixes are applied to the latest released version on `main`.

| Version | Supported |
| ------- | --------- |
| 0.4.x   | Yes       |
| < 0.4   | No        |

## Reporting a Vulnerability

Do not open a public GitHub issue for security vulnerabilities.

Report privately using GitHub's [private vulnerability reporting](https://github.com/mkarots/benedict/security/advisories/new).

Include:

- A description of the issue
- Steps to reproduce
- Affected versions or commit SHA
- Impact assessment, if known

We aim to acknowledge reports within 48 hours and to provide a status update within 7 days.

Please do not disclose the issue publicly until we have published a fix or confirmed that disclosure is safe.

## Security Best Practices for Operators

Benedict runs in your environment. It does not collect telemetry.

- Store Slack and Anthropic credentials in a local `.env` file. Never commit that file.
- Restrict Slack bot scopes to what you need.
- Treat workspace directories and `state.json` as sensitive. They can contain channel mappings and conversation history.
- Keep `gh` authentication scoped if you enable GitHub CLI tools.
- Rotate tokens if they are exposed.

## Data Handling

- The bot stores channel state and conversation history locally.
- Slack message content and repository files are sent to Anthropic when LLM features are enabled, subject to [Anthropic's data policies](https://www.anthropic.com/legal/privacy).
- Slack usage is subject to [Slack's policies](https://slack.com/terms-of-service).
