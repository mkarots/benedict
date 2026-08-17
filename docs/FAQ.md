# Frequently Asked Questions

## What is Benedict?

Benedict is a Slack bot that links a channel to a local git repository and answers questions about that repo using Claude and optional semantic search.

## Does Benedict send my code to the cloud?

Yes, when LLM features are enabled. Relevant file contents and the user question are sent to Anthropic. Slack events stay on your machine except for the Slack API itself. There is no Benedict telemetry.

## Do I need ChromaDB and sentence-transformers?

They are installed with the package and used for semantic search. If the indexer fails to start, the bot still runs and falls back to keyword matching.

## Why does onboarding fail with "Repository Not Found"?

Benedict looks for the repo on disk. Set `BENEDICT_REPO_SOURCE_DIRS` to the parent directories that contain your clones, or pass an absolute path:

```
@benedict onboard repo /path/to/your-repo
```

## Where is state stored?

Channel mappings and conversation history are stored in `state.json` (or `BENEDICT_STATE_FILE`). Workspaces live under `workspaces/` by default.

## Can I run this without Slack?

Not as a product today. Core agent logic is testable without Slack. The runtime entry point is the Slack Socket Mode app.

## How do I report a security issue?

See [SECURITY.md](../SECURITY.md). Do not file a public issue.

## How do I contribute?

See [CONTRIBUTING.md](../CONTRIBUTING.md).

## Why is the package named benedict but the README says Slack Repo Agent?

"Slack Repo Agent" is the product description. The Python package and bot name are Benedict.
