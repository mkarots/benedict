# Observability 2: Network Request Tracing - Design Document

**Issue:** [#20](https://github.com/mkarots/benedict/issues/20)  
**Status:** Design Phase  
**Parent Epic:** [#11 - Epic: Observability and a thin operator UI](https://github.com/mkarots/benedict/issues/11)  
**Dependencies:** [#19 - Observability 1: OpenTelemetry foundation](https://github.com/mkarots/benedict/issues/19)  
**Date:** 2026-08-19

## Executive Summary

This design document describes the implementation of distributed tracing for all outbound network and network-like requests initiated by Benedict. After this milestone, every external hop (Slack, Anthropic, GitHub CLI, mermaid.ink, MCP stdio) will be captured as a span with timing, status, peer information, and redacted metadata. This provides operators with complete visibility into Benedict's external dependencies and failure points.

**One-sentence summary:** Instrument every network call Benedict makes with OpenTelemetry spans so operators can see timing, status, and failure points for Slack, Anthropic, GitHub CLI, mermaid.ink, and MCP requests.

## 1. Overview

### What

Comprehensive OpenTelemetry span instrumentation for all network and network-like calls initiated by Benedict:

1. **Slack Web API and Socket Mode** - Inbound events and outbound `say()` calls
2. **Anthropic Messages API** - HTTP calls in `llm_claude.py`
3. **GitHub CLI (`gh`)** - Subprocess execution in `github_tools.py`
4. **mermaid.ink** - Diagram image URL generation in `slack_formatter.py`
5. **MCP tool invocation** - stdio-based request/response in `mcp/server.py`

### Why

**Current Pain Points:**
- No visibility into which external call failed when Benedict errors
- No timing data for slow Anthropic or GitHub responses
- No correlation between Slack mention and subsequent Anthropic/GitHub calls
- Difficult to debug timeout vs authentication vs network errors

**Benefits After This Milestone:**
- Operators see every external call as a span in Jaeger
- Failed calls (HTTP errors, subprocess failures, timeouts) are visible as error spans
- Clear timing data shows where latency originates (Slack, LLM, GitHub)
- Span attributes capture peer/method/status without exposing secrets

### When to Use

This tracing is operator-focused, not end-user focused:
- **Local development:** View traces in Jaeger to debug slow or failing calls
- **Production debugging:** Understand which external dependency is causing issues
- **Performance analysis:** Identify slow Anthropic models or GitHub API calls
- **Reliability monitoring:** Track error rates per external service

## 2. Goals and Non-Goals

### Goals

1. **Complete Coverage:** Every network hop in the table below is traced
2. **Error Visibility:** Failed calls (timeouts, HTTP errors, subprocess failures) are error spans
3. **Privacy:** No secrets, tokens, or sensitive data on span attributes
4. **Testing:** Unit tests for each surface with fake tracer (no live network)
5. **Backward Compatibility:** Tracing is opt-in; no behavior change when disabled

### Non-Goals

- **Semantic LLM-loop spans** (iteration index, tool names as agent structure) — Observability 3 (#21)
- **Prompt/response bodies** on spans (optional debug flag is Observability 3)
- **Benedict UI** for traces (that's #22 - Operator UI)
- **Custom trace exporters** beyond OTLP (foundation provides this via #19)
- **Sampling strategies** (start with 100% sampling; optimize later if needed)

## 3. Dependencies

### Prerequisites

- **Issue #19 (Observability 1)** MUST be completed first:
  - Tracer protocol (`protocols/tracer.py` or similar)
  - OTel SDK wired at composition roots (`main.py`, `mcp/server.py`)
  - Local/OTLP export configured
  - In-memory exporter for tests

### External Dependencies

No new dependencies required. OpenTelemetry SDK is already in `uv.lock`:
- `opentelemetry-api`
- `opentelemetry-sdk`
- `opentelemetry-exporter-otlp-proto-grpc`

## 4. Network Surfaces to Instrument

| Surface | File(s) | Protocol | Success Indicator | Failure Modes |
|---------|---------|----------|-------------------|---------------|
| **Slack Web API** | `slack_app.py` | HTTP (via Bolt) | 200 OK | Network error, 429 rate limit, invalid token |
| **Slack Socket Mode** | `slack_app.py` | WebSocket | Event received | Connection lost, auth failure |
| **Anthropic Messages API** | `llm/llm_claude.py` | HTTP | Response with content | 429 rate limit, 401 auth, 500 error, timeout |
| **GitHub CLI** | `commands/github_tools.py` | Subprocess | Exit code 0 | Non-zero exit, timeout, `gh` not found |
| **mermaid.ink** | `utils/slack_formatter.py` | HTTP | URL generated | N/A (no actual HTTP call, just URL construction) |
| **MCP tool invocation** | `mcp/server.py` | stdio JSON-RPC | Response received | Tool not found, execution error, timeout |

## 5. High-Level Design

### Architecture

```
User Action (Slack mention / MCP call)
    ↓
Root Span (created by #21, not this PR)
    ↓
Network Span (this PR)
    ├─ slack.send_message (if replying)
    ├─ anthropic.messages.create (if LLM call)
    ├─ gh.run (if GitHub tool used)
    ├─ mermaid.ink.generate_url (if diagram in response)
    └─ mcp.tool.invoke (if MCP tool called)
```

### Span Naming Convention

Follow OpenTelemetry semantic conventions where possible:

- **Slack:** `slack.web_api.chat.postMessage` or `slack.socket_mode.receive_event`
- **Anthropic:** `anthropic.messages.create`
- **GitHub:** `gh.subprocess.run`
- **mermaid.ink:** `mermaid.generate_url`
- **MCP:** `mcp.tool.{tool_name}`

### Span Attributes (Redacted)

Each span includes:

| Attribute | Type | Example | Notes |
|-----------|------|---------|-------|
| `peer.service` | string | `"slack"`, `"anthropic"`, `"github"`, `"mermaid"`, `"mcp"` | External service name |
| `http.method` | string | `"POST"` | HTTP method (if applicable) |
| `http.status_code` | int | `200`, `429`, `500` | HTTP status (if applicable) |
| `subprocess.exit_code` | int | `0`, `1` | Exit code (for `gh`) |
| `subprocess.argv` | string[] | `["pr", "list", "--json", "title"]` | Redacted command args |
| `mcp.tool_name` | string | `"ask_benedict"` | MCP tool invoked |
| `error` | bool | `true` | Set to `true` if span failed |
| `error.message` | string | `"HTTP 429: Rate limit exceeded"` | Human-readable error |

**Redaction Rules:**
- **Never** include raw tokens (`SLACK_BOT_TOKEN`, `ANTHROPIC_API_KEY`, `gh` tokens)
- **Never** include full file contents, prompts, or responses (defer to #21 for optional debug mode)
- **Redact** GitHub tokens from `gh` stderr/stdout using existing `_redact_tokens()` in `github_tools.py`
- **Include** safe metadata: model name, channel ID (not message content), tool name, HTTP status

## 6. Detailed Implementation Plan

### 6.1 Slack Web API and Socket Mode

**File:** `src/benedict/slack_app.py`

**Instrumentation Points:**

1. **Inbound Events (Socket Mode):**
   - Span name: `slack.socket_mode.receive_event`
   - Start span when event received
   - Attributes: `event.type`, `channel.id`, `user.id`
   - End span after event handler completes

2. **Outbound `say()` Calls:**
   - Span name: `slack.web_api.chat.postMessage`
   - Start span before `say()`
   - Attributes: `channel.id`, `thread_ts` (if reply)
   - End span after Slack API response

**Implementation Strategy:**

```python
def handle_app_mentions(event, say, logger):
    with tracer.start_span("slack.socket_mode.receive_event") as span:
        span.set_attribute("event.type", event["type"])
        span.set_attribute("channel.id", event["channel"])
        span.set_attribute("user.id", event["user"])
        
        try:
            # Existing handler logic
            ...
            
            # Trace outbound say()
            with tracer.start_span("slack.web_api.chat.postMessage") as say_span:
                say_span.set_attribute("channel.id", channel_id)
                say_span.set_attribute("thread_ts", thread_ts)
                say(message, thread_ts=thread_ts)
        except Exception as e:
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(e))
            raise
```

**Testing:**
- Mock `say()` function and verify span created with correct attributes
- Verify error span when `say()` raises exception

### 6.2 Anthropic Messages API

**File:** `src/benedict/llm/llm_claude.py`

**Instrumentation Point:**

- Span name: `anthropic.messages.create`
- Start span at beginning of `ClaudeLLM.generate()`
- Attributes: `model`, `max_tokens`, `http.status_code` (if HTTP error)
- End span after response received

**Implementation Strategy:**

```python
def generate(
    self,
    messages: List[Dict[str, Any]],
    system: str = "",
    max_tokens: int = 2000,
    tools: Optional[List[Dict[str, Any]]] = None,
) -> Union[str, Dict[str, Any]]:
    with tracer.start_span("anthropic.messages.create") as span:
        span.set_attribute("model", self.model)
        span.set_attribute("max_tokens", max_tokens)
        span.set_attribute("peer.service", "anthropic")
        
        try:
            # Build request
            kwargs = {
                "model": self.model,
                "messages": anthropic_messages,
                "max_tokens": max_tokens,
            }
            if system:
                kwargs["system"] = system
            if tools:
                kwargs["tools"] = tools
            
            # Make API call
            response = self.client.messages.create(**kwargs)
            
            # Record success
            span.set_attribute("http.status_code", 200)
            
            # Existing response parsing logic
            ...
            return result
            
        except Exception as e:
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(e))
            
            # Extract HTTP status if available
            if hasattr(e, "status_code"):
                span.set_attribute("http.status_code", e.status_code)
            
            logger.error(f"Anthropic API call failed: {e}")
            raise
```

**Testing:**
- Mock `anthropic.Anthropic` client
- Verify span created with model and max_tokens
- Verify error span on API exception (429, 500, timeout)

### 6.3 GitHub CLI

**File:** `src/benedict/commands/github_tools.py`

**Instrumentation Point:**

- Span name: `gh.subprocess.run`
- Start span before `subprocess.run()`
- Attributes: `subprocess.argv` (redacted), `subprocess.exit_code`, `subprocess.timeout`
- End span after subprocess completes

**Implementation Strategy:**

```python
def execute(
    self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None
) -> ToolResult:
    argv = _normalize_argv(arguments.get("argv"))
    if argv is None:
        return ToolResult(success=False, output="Invalid argv")
    
    with tracer.start_span("gh.subprocess.run") as span:
        span.set_attribute("peer.service", "github")
        span.set_attribute("subprocess.argv", argv)  # Already redacted by _normalize_argv
        span.set_attribute("subprocess.timeout", self.timeout_s)
        
        try:
            workspace_dir = Path(context.get("workspace_dir", "."))
            
            result = subprocess.run(
                [GITHUB_BINARY] + argv,
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
                cwd=workspace_dir,
            )
            
            # Record exit code
            span.set_attribute("subprocess.exit_code", result.returncode)
            
            # Mark as error if non-zero exit
            if result.returncode != 0:
                span.set_attribute("error", True)
                span.set_attribute("error.message", f"gh exited {result.returncode}")
            
            # Redact tokens from output (existing logic)
            stdout = _redact_tokens(_truncate(result.stdout))
            stderr = _redact_tokens(_truncate(result.stderr))
            
            return ToolResult(
                success=(result.returncode == 0),
                output=stdout if result.returncode == 0 else stderr,
            )
            
        except subprocess.TimeoutExpired:
            span.set_attribute("error", True)
            span.set_attribute("error.message", f"gh timeout after {self.timeout_s}s")
            return ToolResult(success=False, output=f"Timeout after {self.timeout_s}s")
        
        except FileNotFoundError:
            span.set_attribute("error", True)
            span.set_attribute("error.message", "gh binary not found")
            return ToolResult(success=False, output="gh not found")
```

**Testing:**
- Mock `subprocess.run()`
- Verify span created with argv and timeout
- Verify error span on non-zero exit, timeout, and `gh` not found

### 6.4 mermaid.ink

**File:** `src/benedict/utils/slack_formatter.py`

**Instrumentation Point:**

This is URL generation only, not an actual HTTP call. However, it's still a "network-like" operation since the generated URL will be fetched by Slack.

- Span name: `mermaid.generate_url`
- Start span when generating URL
- Attributes: `diagram.length`, `encoding.type` (`"base64"`)
- No HTTP status (Slack fetches the URL, not Benedict)

**Implementation Strategy:**

```python
def generate_mermaid_url(diagram_code: str) -> str:
    with tracer.start_span("mermaid.generate_url") as span:
        span.set_attribute("peer.service", "mermaid.ink")
        span.set_attribute("diagram.length", len(diagram_code))
        span.set_attribute("encoding.type", "base64")
        
        try:
            encoded = base64.urlsafe_b64encode(diagram_code.encode()).decode()
            url = f"https://mermaid.ink/img/{encoded}"
            return url
        except Exception as e:
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(e))
            raise
```

**Testing:**
- Mock diagram code generation
- Verify span created with diagram length

### 6.5 MCP Tool Invocation

**File:** `src/benedict/mcp/server.py`

**Instrumentation Point:**

- Span name: `mcp.tool.{tool_name}` (e.g., `mcp.tool.ask_benedict`)
- Start span when tool request received
- Attributes: `mcp.tool_name`, `mcp.request_id`
- End span after tool response sent

**Implementation Strategy:**

```python
async def handle_tool_call(self, tool_name: str, arguments: dict) -> dict:
    with tracer.start_span(f"mcp.tool.{tool_name}") as span:
        span.set_attribute("peer.service", "mcp")
        span.set_attribute("mcp.tool_name", tool_name)
        
        try:
            # Existing tool dispatch logic
            if tool_name == "ask_benedict":
                result = await self._handle_ask_benedict(arguments)
            elif tool_name == "search_code":
                result = await self._handle_search_code(arguments)
            # ... other tools
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
            
            return result
            
        except Exception as e:
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(e))
            raise
```

**Testing:**
- Mock MCP tool dispatch
- Verify span created with tool name
- Verify error span when tool not found or execution fails

## 7. Tracer Injection Pattern

All components must receive a tracer via dependency injection (following #19's protocol):

```python
# In main.py (composition root)
from benedict.protocols import create_tracer

tracer = create_tracer(enabled=os.getenv("BENEDICT_OTEL_ENABLED", "false") == "true")

# Inject into components
agent = RepoAgent(
    llm=llm,
    tracer=tracer,
    ...
)

slack_app = create_slack_app(
    agent=agent,
    tracer=tracer,
    ...
)
```

## 8. Testing Strategy

### Unit Tests

Each instrumented component gets a test suite:

**Test File:** `tests/unit/test_network_tracing.py`

**Test Cases:**

1. **Slack:**
   - `test_slack_socket_mode_span_created()`
   - `test_slack_web_api_span_created()`
   - `test_slack_error_span_on_exception()`

2. **Anthropic:**
   - `test_anthropic_span_created()`
   - `test_anthropic_error_span_on_429()`
   - `test_anthropic_error_span_on_timeout()`

3. **GitHub:**
   - `test_gh_span_created_success()`
   - `test_gh_span_created_nonzero_exit()`
   - `test_gh_span_timeout()`
   - `test_gh_span_not_found()`

4. **mermaid.ink:**
   - `test_mermaid_span_created()`
   - `test_mermaid_error_span_on_exception()`

5. **MCP:**
   - `test_mcp_tool_span_created()`
   - `test_mcp_tool_error_span_unknown_tool()`
   - `test_mcp_tool_error_span_execution_failure()`

**Test Infrastructure (from #19):**

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

@pytest.fixture
def in_memory_tracer():
    """Fixture providing in-memory tracer for tests."""
    provider = TracerProvider()
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    
    tracer = provider.get_tracer(__name__)
    
    yield tracer, exporter
    
    # Cleanup
    exporter.clear()

def test_anthropic_span_created(in_memory_tracer, mock_anthropic_client):
    tracer, exporter = in_memory_tracer
    
    llm = ClaudeLLM(tracer=tracer)
    llm.client = mock_anthropic_client
    
    llm.generate([{"role": "user", "content": "Hello"}])
    
    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "anthropic.messages.create"
    assert spans[0].attributes["model"] == "claude-3-5-sonnet-20241022"
```

### Integration Tests

**Manual Test:** Start Benedict with OTel enabled, trigger each surface, view in Jaeger:

```bash
# Terminal 1: Start Jaeger
docker run -d --name jaeger \
  -p 16686:16686 \
  -p 4317:4317 \
  jaegertracing/all-in-one:latest

# Terminal 2: Start Benedict with OTel
export BENEDICT_OTEL_ENABLED=true
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
python -m benedict.main

# Terminal 3: Trigger Slack mention
# (mention @benedict in Slack)

# Terminal 4: View traces
open http://localhost:16686
```

**Expected Result:** Trace shows:
- `slack.socket_mode.receive_event` (parent)
  - `anthropic.messages.create` (child, if LLM called)
  - `gh.subprocess.run` (child, if GitHub tool used)
  - `slack.web_api.chat.postMessage` (child, when replying)

## 9. Privacy and Security

### Redaction Requirements

Following existing `_redact_tokens()` pattern in `github_tools.py`:

```python
import re

# Token patterns to redact
_TOKEN_PATTERNS = [
    re.compile(r"(ghp_|gho_|ghu_|ghs_|ghr_|github_pat_)[A-Za-z0-9_]+"),  # GitHub
    re.compile(r"(xoxb-|xoxp-|xapp-)[A-Za-z0-9-]+"),  # Slack
    re.compile(r"sk-ant-[A-Za-z0-9-]+"),  # Anthropic
]

def _redact_span_attribute(value: str) -> str:
    """Redact sensitive tokens from span attributes."""
    for pattern in _TOKEN_PATTERNS:
        value = pattern.sub("[REDACTED]", value)
    return value
```

### What to Include vs Exclude

| Data | Include | Exclude |
|------|---------|---------|
| Model name | ✅ | |
| HTTP status code | ✅ | |
| Exit code | ✅ | |
| Tool name | ✅ | |
| Channel ID | ✅ | |
| User ID | ✅ | |
| Timing data | ✅ | |
| Tokens/API keys | | ❌ |
| Prompt content | | ❌ (defer to #21) |
| Response content | | ❌ (defer to #21) |
| File contents | | ❌ |
| Repository URLs | ✅ | |

### Operator Disclosure

Update `SECURITY.md` (or create if missing):

```markdown
## Observability and Tracing

Benedict supports optional OpenTelemetry tracing for operators to debug network calls.

**What is traced:**
- Slack events and API calls (channel ID, event type, no message content)
- Anthropic API calls (model name, timing, status code, no prompts/responses)
- GitHub CLI calls (command args, exit code, redacted tokens)
- MCP tool invocations (tool name, timing, no arguments unless debug mode)

**What is NOT traced:**
- Sensitive tokens (Slack, GitHub, Anthropic) are redacted
- Prompt and response content (unless debug mode enabled in #21)
- File contents
- Repository data

**How to enable:** Set `BENEDICT_OTEL_ENABLED=true` and configure OTLP endpoint.
**How to disable:** Omit `BENEDICT_OTEL_ENABLED` or set to `false` (default).

Traces stay on your machine unless you configure an external OTLP exporter.
```

## 10. Success Criteria

### Definition of Done

1. ✅ All five network surfaces instrumented (Slack, Anthropic, `gh`, mermaid, MCP)
2. ✅ Error spans created for failures (HTTP errors, timeouts, non-zero exit codes)
3. ✅ Tokens and secrets redacted from span attributes
4. ✅ Unit tests for each surface with in-memory exporter
5. ✅ Manual test: Slack mention → Jaeger shows trace with child spans
6. ✅ `SECURITY.md` updated with tracing disclosure
7. ✅ No behavior change when `BENEDICT_OTEL_ENABLED=false` (default)

### Acceptance Test

**Scenario:** Slack mention that triggers Anthropic and GitHub CLI

1. User: `@benedict what PRs are open?`
2. Benedict:
   - Receives Slack event → `slack.socket_mode.receive_event` span
   - Calls Anthropic to classify intent → `anthropic.messages.create` span
   - Runs `gh pr list --json title,url` → `gh.subprocess.run` span
   - Replies with formatted list → `slack.web_api.chat.postMessage` span

3. Operator views trace in Jaeger:
   - All four spans visible
   - Timing data shows Anthropic took 2s, `gh` took 500ms
   - Attributes show model name, exit code, channel ID
   - No tokens or prompts visible

**Failure Scenario:** GitHub CLI times out

1. User: `@benedict what PRs are open?`
2. Benedict:
   - `gh pr list` times out after 30s
   - `gh.subprocess.run` span marked as error with `error.message="gh timeout after 30s"`
   - User sees error message in Slack
   - Operator sees error span in Jaeger

## 11. Open Questions and Decisions

### Q1: Should mermaid.ink be traced if no HTTP call is made?

**Decision:** Yes, trace URL generation. Rationale:
- It's a network-like operation (Slack fetches the URL)
- Encoding errors can occur during URL generation
- Provides visibility into diagram rendering pipeline

### Q2: Should we trace individual Anthropic streaming chunks?

**Decision:** No, defer to #21. Rationale:
- This PR focuses on request/response boundaries, not streaming internals
- Streaming chunk tracing is more complex (requires context propagation)
- Current `ClaudeLLM.generate()` does not use streaming

### Q3: Should we add custom samplers for high-volume spans?

**Decision:** No, start with 100% sampling. Rationale:
- Premature optimization
- Benedict is not high-volume (Slack bot, not API)
- If needed later, configure via OTel SDK in #19

### Q4: Should we correlate Slack thread_ts with trace_id?

**Decision:** Yes, but defer implementation to #21. Rationale:
- Useful for cross-referencing Slack threads and traces
- Requires root span at conversation level (not just network level)
- #21 will create parent spans per LLM turn

## 12. Implementation Phases

### Phase 1: Core Instrumentation (Week 1)

1. Add tracer parameter to all components
2. Instrument Slack, Anthropic, GitHub CLI
3. Add redaction logic
4. Unit tests for phase 1 surfaces

### Phase 2: MCP and mermaid.ink (Week 1)

1. Instrument MCP tool dispatch
2. Instrument mermaid URL generation
3. Unit tests for phase 2 surfaces

### Phase 3: Testing and Documentation (Week 1)

1. Manual integration test with Jaeger
2. Update `SECURITY.md`
3. Add observability section to README
4. Code review and refinement

**Total Estimate:** One PR, ~3-5 days of focused work

## 13. Related Work and References

### Related Issues

- [#11 - Epic: Observability and a thin operator UI](https://github.com/mkarots/benedict/issues/11)
- [#19 - Observability 1: OpenTelemetry foundation](https://github.com/mkarots/benedict/issues/19) (prerequisite)
- [#21 - Observability 3: Trace every LLM cycle and tool loop](https://github.com/mkarots/benedict/issues/21) (builds on this)
- [#22 - Operator UI: thin browser or macOS app](https://github.com/mkarots/benedict/issues/22)

### External References

- [OpenTelemetry Semantic Conventions - HTTP](https://opentelemetry.io/docs/specs/semconv/http/)
- [OpenTelemetry Semantic Conventions - Process](https://opentelemetry.io/docs/specs/semconv/process/)
- [OpenTelemetry Python SDK](https://opentelemetry.io/docs/instrumentation/python/)
- [Jaeger - Open Source Tracing](https://www.jaegertracing.io/)

### Code References

| File | Purpose |
|------|---------|
| `src/benedict/slack_app.py` | Slack event handlers and `say()` calls |
| `src/benedict/llm/llm_claude.py` | Anthropic API integration |
| `src/benedict/commands/github_tools.py` | GitHub CLI subprocess execution |
| `src/benedict/utils/slack_formatter.py` | mermaid.ink URL generation |
| `src/benedict/mcp/server.py` | MCP tool dispatch |
| `src/benedict/main.py` | Composition root (tracer injection) |
| `src/benedict/mcp/server.py` | MCP composition root (tracer injection) |

## 14. Appendix: Example Trace

### Trace Structure (JSON)

```json
{
  "traceId": "abc123def456",
  "spans": [
    {
      "spanId": "span-001",
      "name": "slack.socket_mode.receive_event",
      "startTime": "2026-08-19T10:00:00.000Z",
      "endTime": "2026-08-19T10:00:03.500Z",
      "attributes": {
        "event.type": "app_mention",
        "channel.id": "C12345ABC",
        "user.id": "U67890DEF"
      },
      "status": "OK"
    },
    {
      "spanId": "span-002",
      "parentSpanId": "span-001",
      "name": "anthropic.messages.create",
      "startTime": "2026-08-19T10:00:00.100Z",
      "endTime": "2026-08-19T10:00:02.100Z",
      "attributes": {
        "peer.service": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 2000,
        "http.status_code": 200
      },
      "status": "OK"
    },
    {
      "spanId": "span-003",
      "parentSpanId": "span-001",
      "name": "gh.subprocess.run",
      "startTime": "2026-08-19T10:00:02.200Z",
      "endTime": "2026-08-19T10:00:02.700Z",
      "attributes": {
        "peer.service": "github",
        "subprocess.argv": ["pr", "list", "--json", "title,url"],
        "subprocess.exit_code": 0,
        "subprocess.timeout": 30
      },
      "status": "OK"
    },
    {
      "spanId": "span-004",
      "parentSpanId": "span-001",
      "name": "slack.web_api.chat.postMessage",
      "startTime": "2026-08-19T10:00:03.000Z",
      "endTime": "2026-08-19T10:00:03.500Z",
      "attributes": {
        "channel.id": "C12345ABC",
        "thread_ts": "1629360000.123456"
      },
      "status": "OK"
    }
  ]
}
```

### Jaeger UI View

```
slack.socket_mode.receive_event  [====================================] 3.5s
  ├─ anthropic.messages.create   [====================            ]   2.0s
  ├─ gh.subprocess.run           [====                            ]   0.5s
  └─ slack.web_api.chat.postMessage [==                          ]   0.5s
```

## 15. Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-08-19 | Cloud Agent | Initial design document |

---

**Document Status:** Ready for Review  
**Next Steps:** Await #19 completion, then implement instrumentation in this order: Slack → Anthropic → GitHub → mermaid → MCP
