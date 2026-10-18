Status: Proposal

# Operator UI token usage

One-sentence summary:
Keep billed Anthropic token counts on every LLM call, show them on each Operator UI pipeline stage and run, and keep a small ledger so the console can show Benedict’s spend after the run log rotates.

## 1. Overview

**What:**
Extend the LLM protocol with a `TokenUsage` value. Copy Anthropic’s `usage` object out of `ClaudeLLM`. Record it on every Operator UI stage that called the model. Sum it on the run. Append one line per call to `$BENEDICT_DATA_DIR/usage.jsonl` so the header (or a Usage view) can show today / 7d / all-time.

**Why:**
The Operator UI explains a reply (search hits, prompt, tools, duration). It does not explain cost. `generate()` already pays for tokens and then throws the counts away. Operators cannot see which mention, which tool-loop iteration, or which background path (classify, progress, MCP) spent them.

**When to use:**
Use this page when implementing [#131](https://github.com/mkarots/benedict/issues/131). Do not treat it as current shipped behavior. What ships today is duration-only stages and a header with process chips.

## 2. Non-Goals

Not responsible for:

- Reconstructing spend from truncated prompts in `runs.jsonl`
- Counting local MiniLM / Chroma embeddings as billed tokens
- Scraping Anthropic invoices or adding an Anthropic Admin API client
- A Prometheus, OpenTelemetry, or SaaS metrics stack
- Changing `max_tokens` caps or prompt assembly
- Showing usage in Slack replies
- Dollar-accurate accounting (a static price table is optional; their console is the invoice)

Out of scope: rewriting the Operator UI into a framework, raising the 2,000-run cap as a substitute for a ledger, or coupling `ClaudeLLM` to `record_llm_stage`.

## 3. Key Concepts & Terminology

| Term | Meaning |
|------|---------|
| Run | One inbound event in `runs.jsonl`. Slack mention, MCP tool, or progress cycle. The Operator UI “turn.” |
| Pipeline | The run’s `stages` list in the inspector. |
| LLM call | One `generate()`. A tool-loop run may have many. |
| TokenUsage | Billed counts from the provider: `input_tokens`, `output_tokens`, optional cache fields, `model`. |
| LLMResult | Return value of `generate()`: content (`text` or `tool_calls`) plus `TokenUsage`. |
| Turn total | Sum of `TokenUsage` on every recorded LLM call in that run. |
| Ledger | Append-only `$BENEDICT_DATA_DIR/usage.jsonl`. One line per LLM call. Survives run rotation. |
| Cockpit | Header chips and/or a Usage view that aggregate the ledger. |
| Billed tokens | Anthropic `usage` on `messages.create`. Not the 4-char estimate in `truncate_to_tokens`. |

## 4. High-Level Design

Anthropic already returns usage. Benedict does not keep it. The fix is a value object on the LLM protocol, then two sinks: the existing run stage (for the inspector) and a ledger (for totals after rotation).

`ClaudeLLM` maps `response.usage` into `TokenUsage`. Callers that already call `record_llm_stage` pass usage in `extra`. Callers that do not (`LLMCommandClassifier`, `ActionDecider`) start recording the call the same way. The UI reads stage `detail.usage` for the row and sums those objects for the run. The ledger gets a line whenever a call is recorded, including from MCP, using the same file-reload pattern as `runs.jsonl`.

**Invariants:**

- Billed counts come from the provider. The UI does not estimate from prompt text.
- Recording never raises into Slack or MCP (ADR 0001).
- The Claude adapter does not import the recorder. Composition and existing `record_*` helpers stay the write path.
- MiniLM / Chroma work is not a ledger line.
- `BENEDICT_OPERATOR_UI=0` uses the null recorder and skips the ledger for v1.

## 5. API / Interface

### LLM protocol

`generate()` returns `LLMResult` instead of `str | dict`.

```text
TokenUsage
  input_tokens: int
  output_tokens: int
  cache_read_tokens: int = 0
  cache_creation_tokens: int = 0
  model: str = ""

LLMResult
  text: str | None
  tool_calls: list[dict] | None
  assistant_content: list[dict] | None
  usage: TokenUsage
```

`MockLLM` returns zeros and the same content it returns today. Call sites that only need text use `result.text`. The tool loop uses `result.tool_calls` / `result.assistant_content` plus `result.usage`.

### Recorder

`record_llm_stage` already takes `extra`. Put usage there:

```text
detail.usage = { input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens, model }
```

Classify and decide stages get the same `usage` object on their existing stage `detail`. Do not invent a second stage name for the same call.

Run summary (`/api/runs`) and the inspector facts line add:

```text
input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens
```

Those fields are sums of stage usage on that run. Compute on read. Do not dual-write a total that can drift.

### Ledger

Path: `$BENEDICT_DATA_DIR/usage.jsonl`

One JSON object per LLM call:

| Field | Use |
| --- | --- |
| `at` | UTC timestamp |
| `run_id` | Operator UI run, empty if none |
| `source` | `slack`, `mcp`, `progress` |
| `kind` | Run kind (`conversation`, `mcp`, `progress`, …) |
| `model` | Provider model id |
| `input_tokens` | Billed input |
| `output_tokens` | Billed output |
| `cache_read_tokens` | 0 when unused |
| `cache_creation_tokens` | 0 when unused |

`/api/status` grows optional totals: `tokens_today`, `tokens_7d`, `tokens_all`. A Usage view is allowed later; the header chip is enough for v1.

### Call sites that must pass usage

| Call site | Stage today | Gap |
| --- | --- | --- |
| `tools/tool_loop.py` | `llm` per iteration | Has `record_llm_stage`; add usage |
| `agent.py` (no-tools / architect) | `llm` | Same |
| `mcp/service.py` `ask` | `llm` | Same |
| `tools/llm_classifier.py` | `classify` (no usage) | Still a `generate()` |
| `progress/decide.py` | `decide` (no usage) | Still a `generate()` |

If only existing `llm` stages are updated, the cockpit undercounts.

## 6. Happy Path Example

1. User mentions Benedict. Tool loop runs three `generate()` calls.
2. Each Claude response includes `usage`. Each `llm` stage stores `{input_tokens, output_tokens, model}` and duration. Each call appends one ledger line.
3. Activity list shows the run with `4.2s · 18.1k tok`. Inspector facts show `12.4k in · 5.7k out`. Each pipeline `llm` row shows its own in/out next to `duration_ms`.
4. Header chip shows `today 1.2M tok` from the ledger, including MCP `ask_benedict` and overnight progress `decide` calls.
5. After 2,000 newer runs rotate the JSONL, the inspector for old runs is gone. The ledger still has the spend.

## 7. Edge Cases & Failure Modes

| Failure | Handling | Guarantee |
| --- | --- | --- |
| Anthropic omits `usage` | Store zeros | Reply still sends |
| Mock / tests | Zeros | No billed implication |
| Tool loop hits max iterations | Each completed call still recorded | Partial spend is visible |
| Classify then conversation | Two (or more) calls on one run | Turn total includes both |
| Progress `decide` with no prompt in the stage | Add usage to `decide` detail; prompt recording is optional | Spend is visible |
| Ledger unwritable | Log warning, skip the line | Slack/MCP unchanged |
| MCP and Slack both append | Reload-on-stat like `runs.jsonl` | Cockpit sees both |
| Truncated prompt in the run log | Ignore prompt length | Billed counts are in `usage`, not in the prompt |
| Operator UI off | Null recorder, no ledger | Same as no run log today |
| Cache fields missing | Treat as 0 | Older SDK still works |

What is guaranteed in v1: billed in/out on recorded LLM calls, a run total, a ledger that outlives run rotation. Not guaranteed: dollar invoices, usage on historical runs from before this ships.

## 8. Constraints & Assumptions

- Slack and MCP are separate processes. They share `BENEDICT_DATA_DIR`, not memory.
- Recording must not raise into handlers (ADR 0001).
- `runs.jsonl` stays capped at 2,000. Do not raise that cap to fake a cockpit.
- Python 3.10+. No new runtime dependency for counting tokens.
- The shipped UI stays one HTML file. No React.
- Bind stays on loopback. No auth.
- Prompt caching may be off today. Still model the cache fields so a later flag does not change the ledger shape.
- Local `sentence-transformers` indexing is not in this budget.

## 9. Alternatives Considered

**Estimate from prompt characters in the UI** — rejected. Payloads are truncated at 32KB. The 4-char heuristic is a cap, not a bill.

**`ClaudeLLM` records stages itself** — rejected. The provider would depend on the console. Tests and MCP would share that coupling.

**Keep `generate()` as `str | dict` and stash usage on the instance** — rejected. Hidden mutable state. Two threads / two processes would race.

**Sum only `runs.jsonl`** — rejected as the cockpit. Fine for the open run. Lifetime spend needs a ledger.

**Scrape Anthropic billing** — rejected. Tokens belong in-process. Invoices stay in their console.

**Prometheus / OpenTelemetry first** — deferred. A JSONL ledger is enough until that file is the bottleneck.

**Count MiniLM / Chroma as tokens** — rejected. Local embeddings are not Anthropic spend.

**Show usage in Slack** — out of scope. The Operator UI is the debugger. Slack stays the chat surface.

## 10. Open Questions

Q1: Should the ledger write even when `BENEDICT_OPERATOR_UI=0`, so turning the UI on later still has history?

Q2: Header chip only, or a third nav view (Usage) with by-source / by-kind / by-model tables in v1?

Q3: Where does an optional price table live (code constant vs config), and which date’s Anthropic prices does it use?

Q4: Do cache-read tokens display as a third number on the stage row, or only in the payload JSON until prompt caching ships?

Q5: Unwrap `LLMResult` at every call site, or add a thin helper (`as_text`, `as_tool_calls`) so the tool loop and classifier stay short?

## 11. Appendix

### A. What ships today (do not confuse with this plan)

- `ClaudeLLM.generate()` returns text or `{tool_calls, assistant_content}`. It does not return `usage`.
- `record_llm_stage` stores `system`, `messages`, `duration_ms`, optional `iteration`.
- `/api/status` has version, uptime, model, component chips, `runs_today`. No tokens.
- `/api/runs` summaries have `duration_ms`. No tokens.
- Pipeline rows show `duration_ms` on the right.
- `truncate_to_tokens` uses 4 characters per token.
- Embeddings: `all-MiniLM-L6-v2` in process.

### B. Suggested implementation order

1. `TokenUsage` + `LLMResult` on the protocol. Claude copies `response.usage`. Mock returns zeros. Unit tests. UI unchanged.
2. Pass usage into existing `record_llm_stage` calls. Stage row + run summary + inspector facts.
3. Classifier and progress `generate()` record the same `usage` object.
4. `usage.jsonl` ledger + `/api/status` totals + header chip (Usage view if Q2 says yes).

### C. Code map

| Piece | Where |
| --- | --- |
| LLM protocol | `src/benedict/llm/protocol.py` |
| Claude adapter | `src/benedict/llm/llm_claude.py` |
| Mock | `src/benedict/llm/llm_mock.py` |
| Tool loop | `src/benedict/tools/tool_loop.py` |
| Classifier | `src/benedict/tools/llm_classifier.py` |
| Conversation / architect | `src/benedict/agent.py` |
| MCP ask | `src/benedict/mcp/service.py` |
| Progress decide | `src/benedict/progress/decide.py` |
| Run log | `src/benedict/operator_ui/recorder.py` |
| HTTP + status | `src/benedict/operator_ui/server.py` |
| Page | `src/benedict/operator_ui/static/index.html` |
| ADR 0001 | `docs/adr/0001-local-operator-ui.md` |
