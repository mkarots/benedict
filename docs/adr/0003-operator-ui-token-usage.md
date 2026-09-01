# ADR 0003: Operator UI token usage

Status: Proposed

Date: 2026-09-01

One-sentence summary:
Record Anthropic billed token counts on every LLM call, show them on each Operator UI stage and run, and keep a small ledger so the console can show Benedict’s spend after `runs.jsonl` rotates.

## Context

The Operator UI already records a run per Slack mention, MCP tool, or progress cycle (ADR 0001). Pipeline stages show `duration_ms`. The header shows live/slack/mcp/chroma. None of that includes tokens.

Anthropic returns `usage.input_tokens` and `usage.output_tokens` on `messages.create`. `ClaudeLLM.generate()` drops that object and returns only text or `tool_calls`. `record_llm_stage` stores the prompt and duration. It has an `extra` dict (`iteration` in the tool loop). Usage is not in it.

Operators cannot answer:

- How many tokens did this mention use?
- Which LLM stage in the pipeline was expensive?
- How much does Benedict spend today, this week, or overall?

`runs.jsonl` rotates at 2,000 rows. Summing usage from the run log is enough for the open inspector. It is not lifetime spend.

Local MiniLM embeddings are not billed. The `1 token ≈ 4 chars` helper in `context.py` is a prompt-size cap. Neither is Anthropic usage.

Issue [#131](https://github.com/mkarots/benedict/issues/131).

## Decision

1. **Usage is part of the LLM contract.** `generate()` returns content and a `TokenUsage` value (`input_tokens`, `output_tokens`, cache fields, `model`). `MockLLM` returns zeros. The Claude adapter copies Anthropic’s `usage` object. It does not call the recorder.
2. **Use billed counts.** Do not estimate from prompt length or truncated `runs.jsonl` payloads.
3. **Every `generate()` is recorded.** Conversation `llm` stages, classifier `classify`, progress `decide`, MCP `ask`, architect. A tool-loop turn may have many billed calls.
4. **The recorder stores usage on the stage and the UI sums the run.** Stage row: tokens next to duration. Activity list and inspector facts: turn total.
5. **A ledger survives run rotation.** Append-only `$BENEDICT_DATA_DIR/usage.jsonl`, one line per LLM call (`at`, `run_id`, `source`, `kind`, `model`, `input`, `output`, cache fields). Slack and MCP share it the same way they share `runs.jsonl`. The header or a Usage view aggregates today / 7d / all-time.
6. **Dollars are optional.** A static price table may estimate cost. Anthropic’s billing console remains the invoice source of truth.
7. **Same safety as ADR 0001.** Recording must not raise into Slack or MCP. Same `BENEDICT_OPERATOR_UI=0` switch as the run recorder for v1.

Details: [docs/TOKEN_USAGE.md](../TOKEN_USAGE.md).

## Consequences

### What we get

- One mention: billed in/out on each pipeline LLM row, plus a run total
- Classify and progress spend is visible, not only conversation `llm` stages
- A cockpit that still works after `runs.jsonl` drops old rows

### What we give up

- The current `generate()` return type (`str | dict`). Call sites unwrap an `LLMResult`
- Treating the 2,000-run JSONL as a complete spend history

### Failure modes

- Anthropic omits `usage`: record zeros, do not fail the reply
- Ledger unwritable: log a warning, Slack still replies
- Operator UI off: no run log and no ledger for that process (same as today for runs)

## Alternatives considered

**Estimate from prompt characters in the UI** — rejected. Truncated payloads and the 4-char heuristic are not billed counts.

**`ClaudeLLM` calls `record_llm_stage` itself** — rejected. Couples the provider to the console.

**Sum only `runs.jsonl`** — rejected as the cockpit. Fine for one open run. Lifetime spend needs a ledger.

**Scrape Anthropic billing** — rejected. Tokens in-process. Invoices stay in their console.

**Prometheus / OpenTelemetry first** — deferred. A JSONL ledger is enough until that file is the bottleneck.

**Count MiniLM / Chroma work as tokens** — rejected. Local embeddings are not Anthropic spend.

## References

- Design: [docs/TOKEN_USAGE.md](../TOKEN_USAGE.md)
- ADR 0001: [docs/adr/0001-local-operator-ui.md](0001-local-operator-ui.md)
- Issue [#131](https://github.com/mkarots/benedict/issues/131)
- Live UI: `src/benedict/operator_ui/static/index.html`
- Claude adapter: `src/benedict/llm/llm_claude.py`
