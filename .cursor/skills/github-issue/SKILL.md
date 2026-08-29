---
name: github-issue
description: >-
  Treats a GitHub issue as either a code problem or a design-document
  request, then follows the matching workflow through analysis,
  implementation or writing, review, and a pull request. Use when the
  user runs /github-issue, passes a github.com issue URL, or asks to
  implement, fix, or write a design for a GitHub issue.
---

# Treat a GitHub issue

An issue could ask for code or design documents. Classify it, then follow the matching workflow to completion. The skill takes as argument a GitHub URL pointing to an issue.

Before you start, read these project files if you have not already:

- [CONTRIBUTING.md](../../../CONTRIBUTING.md)
- [CODE_OF_CONDUCT.md](../../../CODE_OF_CONDUCT.md)
- [.github/PULL_REQUEST_TEMPLATE.md](../../../.github/PULL_REQUEST_TEMPLATE.md)
- [.github/ISSUE_TEMPLATE/bug_report.md](../../../.github/ISSUE_TEMPLATE/bug_report.md)

Do not open a public issue or PR for a vulnerability or a conduct report. See [SECURITY.md](../../../SECURITY.md) and [CODE_OF_CONDUCT.md](../../../CODE_OF_CONDUCT.md).

## Invocation

```
/github-issue https://github.com/<owner>/<repo>/issues/<n>
```

The URL is required. If the user omitted it, ask for it and stop. Do not invent an issue.

## Fetch

Accept:

- `https://github.com/<owner>/<repo>/issues/<n>`
- `https://github.com/<owner>/<repo>/issues/<n>#...` (ignore the fragment)

Extract `owner`, `repo`, `n`. Use `gh`. Do not guess the issue from memory.

```bash
gh issue view "<url>" --json title,body,number,url,labels,comments,author,state
```

If `gh` fails (auth, private repo, missing CLI), say so and stop. Do not fabricate the issue.

Work in a checkout of `owner/repo`. If the current workspace is a different repo, say so and stop.

## Classify

Read the title, body, and labels. Choose one path:

- **Code** — the issue describes a problem to be solved with code (bug, feature, refactor, tests).
- **Design document** — the issue asks for a design document, architecture write-up, or analysis without implementing code.

If both appear, ask which path to take and stop. If neither is clear, ask one clarifying question and stop.

Copy the matching checklist and complete it in order. Keep the user's issue wording; do not reframe the request.

## Code path

If the issue describes a problem to be solved with code then follow these steps:

1. Identify the main problem and describe it sufficiently
2. Identify possible approaches to solve it, compare and contrast them
3. Choose the best approach going forward and document your choice
4. Breakdown the requirements of the chosen approach into distinct required software changes
5. Implement all requirements
6. Review the implemented code and fix important and document other ones
7. Make a pull request

Do steps 1–4 in the reply before writing code. Do not skip the comparison or the choice.

In step 6, fix issues that affect correctness, safety, or the issue's requirements. Document the rest in the reply (and in the PR if they are worth a follow-up).

In step 7, open a pull request against the repo default branch. Link the issue. Use `gh pr create` and fill [.github/PULL_REQUEST_TEMPLATE.md](../../../.github/PULL_REQUEST_TEMPLATE.md). Follow `.cursor/rules/pull-requests.mdc`. Do not push or open a PR if the user asked you not to.

## Design document path

If the issue is about creating a design document then following these steps:

- Identify the problem at discussion
- Write a document that gives an overview of the problem and its subproblems if any
- Write any other requirements/constraints that affect the problem
- Do a precise, concise and accurate analysis of the problem, that should leave no questions regarding the nature of the problem and why its a problem.
- To each subproblem, lay out possible solutions, and compare and constrat them together,
- then explain how all the parts of the solution together solve the problem

Write the document in the repo. Prefer the project's existing design-doc location and template when one exists. Otherwise use `docs/` and this outline:

```markdown
# <Title>

One-sentence summary.

## Problem

## Subproblems

## Requirements and constraints

## Analysis

## Solutions per subproblem

## How the parts solve the problem
```

Open a pull request that adds the document and links the issue. Do not implement product code on this path unless the issue also requires it and the user confirmed the code path.
