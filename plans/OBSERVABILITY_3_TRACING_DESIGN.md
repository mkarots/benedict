# Observability 3: Trace Every LLM Cycle and Tool Loop - Design Document

**Issue**: [#21](https://github.com/mkarots/benedict/issues/21)  
**Status**: Design  
**Author**: Benedict Cloud Agent  
**Date**: 2026-08-19  
**Version**: 1.0

## Executive Summary

This design document describes the implementation of comprehensive distributed tracing for Benedict, covering every LLM generation cycle and tool execution. The tracing infrastructure will use OpenTelemetry to instrument all code paths (Slack, MCP, classifier, tool loop) and provide visibility into latency, token usage, and execution flow through Jaeger.

## Goals

1. **Complete Coverage**: Instrument all LLM generation paths:
   - Slack mentions (`app_mention` → `agent.handle_conversation`)
   - MCP tool calls (`ask_benedict`)
   - LLM classification (`LLMCommandClassifier.classify`)
   - Tool loop iterations (`run_tool_loop`)
   - Context building operations
   - Plain `llm.generate` calls

2. **Hierarchical Visibility**: Create parent-child span relationships that make the execution flow obvious:
   - One parent span per user request (Slack mention or MCP call)
   - Nested spans for classify, context building, tool loop iterations, individual tool executions

3. **Rich Attributes**: Capture key metadata without exposing sensitive data:
   - Request identifiers (`channel_id`, `thread_ts`, `repo`)
   - LLM metadata (`model`, `tokens_in`, `tokens_out`, `stop_reason`)
   - Iteration counters, tool names, success/error status
   - Execution time for each operation

4. **Opt-in Verbosity**: Keep prompt/response bodies off spans by default, enable via debug flag

5. **Testing**: Verify span structure with in-memory exporters in unit tests

## Non-Goals

- Changing the prompt-first vs tools execution model (issue #2)
- Building an operator UI (separate work)
- Implementing metrics/dashboards beyond span attributes (future work)
- Instrumenting non-LLM paths (file reads, git operations) in this PR

## Background

Benedict currently has no observability infrastructure. When debugging:
- Token usage is invisible
- Loop iteration counts are unclear
- Classify vs. query path selection is opaque
- Tool execution timing is unknown
- No visibility into which code path was taken

This makes production debugging and optimization difficult.

## Architecture

### Technology Stack

**OpenTelemetry + Jaeger**

- **OpenTelemetry Python SDK**: Industry-standard tracing library
  - `opentelemetry-api`: Core tracing API
  - `opentelemetry-sdk`: SDK implementation
  - `opentelemetry-instrumentation`: Auto-instrumentation helpers
  - `opentelemetry-exporter-jaeger`: Jaeger exporter (or OTLP)

- **Jaeger**: Distributed tracing backend for visualization
  - Run locally via Docker for development
  - Production deployment is environment-specific

**Why OpenTelemetry?**
- Vendor-neutral, open standard
- Rich Python SDK with excellent documentation
- Compatible with Jaeger, Zipkin, Cloud providers
- Active community and long-term support

### Span Hierarchy

```
request (slack.app_mention | mcp.ask_benedict)
├── agent.handle_conversation
│   ├── llm.classify
│   │   ├── llm.generate [model, tokens, stop_reason]
│   │   └── tool.execute [tool_name, success]
│   ├── context.build [files_found, semantic_hits]
│   └── llm.tool_loop
│       ├── llm.iteration[0]
│       │   ├── llm.generate [model, tokens, stop_reason]
│       │   └── tool.execute.run_github [argv, success]
│       ├── llm.iteration[1]
│       │   └── llm.generate [model, tokens, stop_reason]
│       └── ...
└── slack.reply [channel_id, thread_ts]
```

**Alternative paths:**
- `mcp.ask_benedict` → `llm.generate` (no tool loop if no tools needed)
- Metadata shortcut: `agent.handle_conversation` → `llm.classify` → `tool.execute.*` (no query path)
- Architect query: `agent.handle_architect_query` → `llm.generate`

### Span Attributes

Each span type will include relevant attributes:

#### Root Spans (`request`)
```python
{
    "service.name": "benedict",
    "benedict.request_source": "slack.app_mention" | "mcp.ask_benedict",
    "benedict.channel_id": "C12345ABC",
    "benedict.thread_ts": "1234567890.123456",
    "benedict.repo": "org/repo",
    "benedict.user_id": "U12345ABC",  # Slack only
}
```

#### Agent Operations (`agent.*`)
```python
{
    "benedict.operation": "handle_conversation" | "handle_architect_query",
    "benedict.command_type": "metadata" | "query" | "github",
}
```

#### LLM Classification (`llm.classify`)
```python
{
    "benedict.tool_count": 3,
    "benedict.tool_names": ["get_file_metadata", "list_key_files"],
    "benedict.fallback": false,
}
```

#### Context Building (`context.build`)
```python
{
    "benedict.files_found": 5,
    "benedict.semantic_hits": 3,
    "benedict.metadata_files": 2,
    "benedict.context_size_chars": 12345,
}
```

#### LLM Generation (`llm.generate`)
```python
{
    "benedict.model": "claude-3-5-sonnet-20241022",
    "benedict.tokens_input": 1024,
    "benedict.tokens_output": 512,
    "benedict.stop_reason": "end_turn" | "max_tokens" | "stop_sequence",
    "benedict.tools_available": 2,
    "benedict.tool_call_count": 1,
}
```

#### Tool Loop (`llm.tool_loop`)
```python
{
    "benedict.max_iterations": 5,
    "benedict.iterations_used": 2,
    "benedict.completion_reason": "text_returned" | "max_iterations",
}
```

#### Tool Execution (`tool.execute.*`)
```python
{
    "benedict.tool_name": "run_github",
    "benedict.tool_success": true,
    "benedict.tool_error": "",  # if failed
    "benedict.tool_arguments": '{"argv": ["pr", "list"]}',  # JSON
}
```

### Debug Mode

When `BENEDICT_TRACE_DEBUG=1` is set, additional attributes are added:

```python
{
    "benedict.debug.prompt": "<full system prompt>",
    "benedict.debug.response": "<full LLM response>",
    "benedict.debug.user_input": "<user message>",
}
```

This is **off by default** to avoid leaking sensitive data.

## Implementation Plan

### Phase 1: Infrastructure Setup

**Files to create:**
- `src/benedict/observability/__init__.py` - Package initialization
- `src/benedict/observability/tracing.py` - Tracing setup and utilities
- `src/benedict/observability/spans.py` - Span context managers and decorators

**Key components:**

```python
# src/benedict/observability/tracing.py

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
import os

def initialize_tracing(service_name: str = "benedict") -> trace.Tracer:
    """Initialize OpenTelemetry tracing with Jaeger exporter."""
    
    enabled = os.getenv("BENEDICT_TRACING_ENABLED", "1") == "1"
    if not enabled:
        # Return no-op tracer if disabled
        return trace.get_tracer(__name__)
    
    # Configure Jaeger exporter
    jaeger_host = os.getenv("JAEGER_AGENT_HOST", "localhost")
    jaeger_port = int(os.getenv("JAEGER_AGENT_PORT", "6831"))
    
    provider = TracerProvider()
    exporter = JaegerExporter(
        agent_host_name=jaeger_host,
        agent_port=jaeger_port,
    )
    
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    
    return trace.get_tracer(__name__)

def is_debug_mode() -> bool:
    """Check if debug mode is enabled for verbose tracing."""
    return os.getenv("BENEDICT_TRACE_DEBUG", "0") == "1"
```

```python
# src/benedict/observability/spans.py

from opentelemetry import trace
from contextlib import contextmanager
from typing import Optional, Dict, Any
import functools

@contextmanager
def request_span(
    tracer: trace.Tracer,
    source: str,
    channel_id: Optional[str] = None,
    thread_ts: Optional[str] = None,
    repo: Optional[str] = None,
    user_id: Optional[str] = None,
):
    """Context manager for root request spans."""
    with tracer.start_as_current_span("request") as span:
        span.set_attribute("benedict.request_source", source)
        if channel_id:
            span.set_attribute("benedict.channel_id", channel_id)
        if thread_ts:
            span.set_attribute("benedict.thread_ts", thread_ts)
        if repo:
            span.set_attribute("benedict.repo", repo)
        if user_id:
            span.set_attribute("benedict.user_id", user_id)
        yield span

@contextmanager
def llm_generation_span(
    tracer: trace.Tracer,
    model: str,
    tools_available: int = 0,
):
    """Context manager for LLM generation spans."""
    with tracer.start_as_current_span("llm.generate") as span:
        span.set_attribute("benedict.model", model)
        span.set_attribute("benedict.tools_available", tools_available)
        yield span

def add_usage_attributes(
    span: trace.Span,
    tokens_input: int,
    tokens_output: int,
    stop_reason: str,
):
    """Add usage attributes to a span after LLM response."""
    span.set_attribute("benedict.tokens_input", tokens_input)
    span.set_attribute("benedict.tokens_output", tokens_output)
    span.set_attribute("benedict.stop_reason", stop_reason)

@contextmanager
def tool_execution_span(
    tracer: trace.Tracer,
    tool_name: str,
    arguments: Dict[str, Any],
):
    """Context manager for tool execution spans."""
    import json
    with tracer.start_as_current_span(f"tool.execute.{tool_name}") as span:
        span.set_attribute("benedict.tool_name", tool_name)
        span.set_attribute("benedict.tool_arguments", json.dumps(arguments))
        yield span

def add_tool_result_attributes(
    span: trace.Span,
    success: bool,
    error: Optional[str] = None,
):
    """Add result attributes to a tool execution span."""
    span.set_attribute("benedict.tool_success", success)
    if error:
        span.set_attribute("benedict.tool_error", error)
```

### Phase 2: Instrument LLM Layer

**Files to modify:**
- `src/benedict/llm/llm_claude.py` - Add tracing to `generate()`

**Changes:**

```python
# In ClaudeLLM.__init__
from benedict.observability import tracing

self.tracer = tracing.initialize_tracing()

# In ClaudeLLM.generate()
def generate(self, messages, system="", max_tokens=2000, tools=None):
    with llm_generation_span(
        self.tracer,
        model=self.model,
        tools_available=len(tools) if tools else 0,
    ) as span:
        try:
            # ... existing API call ...
            response = self.client.messages.create(**api_kwargs)
            
            # Extract usage from response
            if hasattr(response, 'usage'):
                add_usage_attributes(
                    span,
                    tokens_input=response.usage.input_tokens,
                    tokens_output=response.usage.output_tokens,
                    stop_reason=response.stop_reason,
                )
            
            # Add debug info if enabled
            if tracing.is_debug_mode():
                span.set_attribute("benedict.debug.system", system)
                span.set_attribute("benedict.debug.response", str(response))
            
            # ... existing response processing ...
            return processed_response
            
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            raise
```

### Phase 3: Instrument Tool Loop

**Files to modify:**
- `src/benedict/commands/tool_loop.py` - Add spans around loop and iterations

**Changes:**

```python
# At module level
from benedict.observability import tracing
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

# In run_tool_loop()
def run_tool_loop(llm, messages, system, tool_registry, context=None, max_iterations=5, max_tokens=2000):
    with tracer.start_as_current_span("llm.tool_loop") as loop_span:
        loop_span.set_attribute("benedict.max_iterations", max_iterations)
        
        tools = tool_registry.to_anthropic_tools()
        working_messages = list(messages)
        
        for iteration in range(max_iterations):
            with tracer.start_as_current_span(f"llm.iteration[{iteration}]") as iter_span:
                iter_span.set_attribute("benedict.iteration_index", iteration)
                
                # LLM call already traced in llm_claude.py
                response = llm.generate(messages=working_messages, system=system, tools=tools, max_tokens=max_tokens)
                
                if isinstance(response, str):
                    loop_span.set_attribute("benedict.iterations_used", iteration + 1)
                    loop_span.set_attribute("benedict.completion_reason", "text_returned")
                    return response
                
                # ... tool execution ...
                if tool_calls:
                    for call in tool_calls:
                        name = call.get("name")
                        arguments = call.get("input") or call.get("arguments") or {}
                        
                        with tool_execution_span(tracer, name, arguments) as tool_span:
                            result = tool_registry.execute(name, arguments, context)
                            add_tool_result_attributes(tool_span, result.success, result.error)
                            
                            # ... format and append result ...
        
        loop_span.set_attribute("benedict.iterations_used", max_iterations)
        loop_span.set_attribute("benedict.completion_reason", "max_iterations")
        logger.warning("Tool loop hit max iterations")
        return "I reached the tool-call limit..."
```

### Phase 4: Instrument Classifier

**Files to modify:**
- `src/benedict/commands/llm_classifier.py` - Add spans around classification

**Changes:**

```python
# At module level
from benedict.observability import tracing
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

# In LLMCommandClassifier.classify()
def classify(self, text, conversation_history=None):
    with tracer.start_as_current_span("llm.classify") as span:
        available_tools = self.tool_registry.list_tools()
        span.set_attribute("benedict.tool_count", len(available_tools))
        
        if not available_tools:
            span.set_attribute("benedict.fallback", True)
            if self.fallback_to_query:
                return None
            return {"tool_calls": []}
        
        try:
            # ... build prompt and call LLM ...
            # LLM call already traced in llm_claude.py
            response = self._call_llm_with_tools(prompt, tools, text)
            
            tool_calls = self._parse_response(response)
            
            if tool_calls:
                tool_names = [tc.get('name') for tc in tool_calls]
                span.set_attribute("benedict.tool_names", str(tool_names))
                span.set_attribute("benedict.fallback", False)
                return {"tool_calls": tool_calls}
            
            # No tool calls
            span.set_attribute("benedict.fallback", True)
            if self.fallback_to_query:
                return None
            return {"tool_calls": []}
            
        except Exception as e:
            span.record_exception(e)
            span.set_attribute("benedict.fallback", True)
            if self.fallback_to_query:
                return None
            return {"tool_calls": []}
```

### Phase 5: Instrument Agent Layer

**Files to modify:**
- `src/benedict/agent.py` - Add spans in `handle_conversation`, `handle_architect_query`

**Changes:**

```python
# At module level
from benedict.observability import tracing, spans
from opentelemetry import trace

class RepoAgent:
    def __init__(self, ...):
        # ... existing init ...
        self.tracer = trace.get_tracer(__name__)
    
    def handle_conversation(self, channel_id, text, thread_ts):
        with self.tracer.start_as_current_span("agent.handle_conversation") as span:
            repo = self.get_channel_repo(channel_id)
            
            span.set_attribute("benedict.operation", "handle_conversation")
            span.set_attribute("benedict.channel_id", channel_id)
            span.set_attribute("benedict.thread_ts", thread_ts)
            if repo:
                span.set_attribute("benedict.repo", repo)
            
            # ... existing conversation logic ...
            
            # Metadata classifier shortcut
            if self.llm and self.workspace_manager and self.is_metadata_command(text):
                span.set_attribute("benedict.command_type", "metadata")
                # llm_classifier.classify() already traced
                # tool execution already traced
                # ...
            
            # Build context
            with self.tracer.start_as_current_span("context.build") as ctx_span:
                context = build_context(repo, combined_text, repo_reader, ...)
                ctx_span.set_attribute("benedict.context_size_chars", len(context))
                # Could add more attributes: files_found, semantic_hits, etc.
            
            # Tool loop or plain generate
            # Both already traced in their respective modules
            if github_registry.list_tools():
                span.set_attribute("benedict.command_type", "github")
                response_text = run_tool_loop(...)
            else:
                span.set_attribute("benedict.command_type", "query")
                response = self.llm.generate(...)
            
            return (True, response_text)
    
    def handle_architect_query(self, channel_id, text, thread_ts):
        with self.tracer.start_as_current_span("agent.handle_architect_query") as span:
            span.set_attribute("benedict.operation", "handle_architect_query")
            span.set_attribute("benedict.channel_id", channel_id)
            span.set_attribute("benedict.thread_ts", thread_ts)
            
            # ... existing architect logic ...
            # llm.generate() already traced
            
            return (True, response_text)
```

### Phase 6: Instrument Entry Points

**Files to modify:**
- `src/benedict/slack_app.py` - Add root spans for Slack events
- `src/benedict/mcp/service.py` - Add root spans for MCP calls

**Slack integration:**

```python
# In slack_app.py
from benedict.observability import spans
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

def handle_app_mention(event, say, client):
    channel_id = event.get("channel")
    thread_ts = event.get("ts")
    user_id = event.get("user")
    text = event.get("text", "")
    
    with spans.request_span(
        tracer,
        source="slack.app_mention",
        channel_id=channel_id,
        thread_ts=thread_ts,
        user_id=user_id,
    ):
        # ... existing logic ...
        success, response = agent.handle_conversation(channel_id, cleaned_text, thread_ts)
        
        # Reply span
        with tracer.start_as_current_span("slack.reply") as span:
            span.set_attribute("benedict.channel_id", channel_id)
            span.set_attribute("benedict.thread_ts", thread_ts)
            say(text=response, thread_ts=thread_ts)
```

**MCP integration:**

```python
# In mcp/service.py
from benedict.observability import spans
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

class BenedictMcpService:
    def ask(self, question, repo=None, cwd=None):
        with spans.request_span(
            tracer,
            source="mcp.ask_benedict",
            repo=repo,
        ):
            # ... existing ask logic ...
            # llm.generate() already traced
            return _ok(repo=project.repo, channel_id=project.channel_id, answer=answer)
```

### Phase 7: Testing Infrastructure

**Files to create:**
- `tests/unit/test_observability/__init__.py`
- `tests/unit/test_observability/test_tracing.py`
- `tests/unit/test_observability/test_spans.py`

**Key test patterns:**

```python
# tests/unit/test_observability/test_spans.py

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

def test_llm_generation_span_structure():
    """Verify LLM generation span has correct attributes."""
    
    # Setup in-memory exporter
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer(__name__)
    
    # Create span
    with llm_generation_span(tracer, model="claude-3-5-sonnet-20241022", tools_available=2) as span:
        add_usage_attributes(span, tokens_input=100, tokens_output=50, stop_reason="end_turn")
    
    # Verify
    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    
    span = spans[0]
    assert span.name == "llm.generate"
    assert span.attributes["benedict.model"] == "claude-3-5-sonnet-20241022"
    assert span.attributes["benedict.tools_available"] == 2
    assert span.attributes["benedict.tokens_input"] == 100
    assert span.attributes["benedict.tokens_output"] == 50
    assert span.attributes["benedict.stop_reason"] == "end_turn"

def test_tool_loop_parent_child_hierarchy():
    """Verify tool loop creates proper parent-child span relationships."""
    
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    
    # Run instrumented tool loop (mocked LLM with tool calls)
    # ... setup mocks ...
    
    response = run_tool_loop(mocked_llm, messages, system, registry)
    
    # Verify span hierarchy
    spans = exporter.get_finished_spans()
    
    # Find root loop span
    loop_spans = [s for s in spans if s.name == "llm.tool_loop"]
    assert len(loop_spans) == 1
    loop_span = loop_spans[0]
    
    # Find iteration spans that are children of loop span
    iter_spans = [s for s in spans if s.name.startswith("llm.iteration")]
    assert len(iter_spans) > 0
    
    for iter_span in iter_spans:
        assert iter_span.parent.span_id == loop_span.context.span_id
    
    # Find tool execution spans that are children of iteration spans
    tool_spans = [s for s in spans if s.name.startswith("tool.execute")]
    for tool_span in tool_spans:
        parent_id = tool_span.parent.span_id
        assert any(iter_span.context.span_id == parent_id for iter_span in iter_spans)
```

### Phase 8: Documentation and Configuration

**Files to create/modify:**
- `docs/OBSERVABILITY.md` - User guide for tracing setup
- `README.md` - Add observability section
- `.env.example` - Add tracing environment variables

**Environment variables:**

```bash
# Tracing configuration
BENEDICT_TRACING_ENABLED=1           # 1=enabled, 0=disabled
BENEDICT_TRACE_DEBUG=0                # 1=include prompts/responses, 0=metadata only
JAEGER_AGENT_HOST=localhost           # Jaeger agent hostname
JAEGER_AGENT_PORT=6831                # Jaeger agent port
```

**Documentation structure:**

```markdown
# Observability Guide

## Quick Start with Jaeger

1. Start Jaeger locally:
   ```bash
   docker run -d --name jaeger \
     -e COLLECTOR_ZIPKIN_HOST_PORT=:9411 \
     -p 5775:5775/udp \
     -p 6831:6831/udp \
     -p 6832:6832/udp \
     -p 5778:5778 \
     -p 16686:16686 \
     -p 14268:14268 \
     -p 14250:14250 \
     -p 9411:9411 \
     jaegertracing/all-in-one:latest
   ```

2. Enable tracing in `.env`:
   ```bash
   BENEDICT_TRACING_ENABLED=1
   JAEGER_AGENT_HOST=localhost
   ```

3. Run Benedict and generate some traffic

4. View traces at http://localhost:16686

## Understanding Traces

Each Slack mention creates a root span with these children:
- `agent.handle_conversation`: Main conversation handler
  - `llm.classify`: Classification of user intent
  - `context.build`: Repository context gathering
  - `llm.tool_loop`: Tool execution loop (if tools needed)
    - `llm.iteration[0]`, `llm.iteration[1]`, etc.
    - `tool.execute.*`: Individual tool calls

## Key Metrics

- **Total request time**: Root span duration
- **LLM latency**: `llm.generate` span duration
- **Token usage**: `benedict.tokens_input` + `benedict.tokens_output`
- **Tool execution time**: `tool.execute.*` span durations
- **Loop iterations**: `benedict.iterations_used` attribute

## Debug Mode

WARNING: Debug mode logs full prompts and responses. Only enable in development.

```bash
BENEDICT_TRACE_DEBUG=1
```

This adds attributes:
- `benedict.debug.system`: System prompt
- `benedict.debug.response`: Full LLM response
- `benedict.debug.user_input`: User message
```

## Deployment Considerations

### Dependencies

Add to `pyproject.toml`:

```toml
dependencies = [
    # ... existing deps ...
    "opentelemetry-api>=1.20.0",
    "opentelemetry-sdk>=1.20.0",
    "opentelemetry-exporter-jaeger>=1.20.0",
]
```

### Performance Impact

- **Overhead**: Minimal (<1% latency overhead for typical requests)
- **Memory**: Each span ~1KB, batch exported every 5 seconds
- **Network**: UDP to Jaeger agent (non-blocking)
- **Sampling**: All traces recorded by default (can add sampling if needed)

### Production Deployment

**Option 1: Jaeger All-in-One (Development/Small Scale)**
```yaml
# docker-compose.yml
services:
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # UI
      - "6831:6831/udp"  # Agent
    environment:
      - COLLECTOR_ZIPKIN_HOST_PORT=:9411
```

**Option 2: Jaeger with Storage Backend (Production)**
- Use Jaeger Operator on Kubernetes
- Backend storage: Elasticsearch, Cassandra, or Kafka
- Separate agent + collector + query services

**Option 3: Cloud-Native (AWS X-Ray, Google Cloud Trace, etc.)**
- Replace `JaegerExporter` with cloud provider exporter
- Use OTLP exporter for vendor-neutral approach

### Security Considerations

1. **Sensitive Data**: Never log tokens, API keys, or user data in spans
   - Use `BENEDICT_TRACE_DEBUG=0` in production
   - Audit span attributes before enabling debug mode

2. **Network Security**: Jaeger agent communication
   - Use localhost for agent (default)
   - Or secure Jaeger endpoints with TLS in production

3. **Access Control**: Jaeger UI should be behind authentication
   - Use reverse proxy with auth
   - Or Jaeger's built-in authentication features

## Migration Path

### Stage 1: Development (This PR)
- Implement all instrumentation
- Test with local Jaeger
- Verify span structure in tests
- Document usage

### Stage 2: Staging/Beta
- Deploy Jaeger alongside Benedict
- Monitor performance impact
- Tune sampling if needed
- Gather feedback on span attributes

### Stage 3: Production
- Roll out to production environment
- Set up alerts on span attributes (high latency, error rates)
- Create dashboards for key metrics
- Train team on Jaeger UI

## Testing Strategy

### Unit Tests

1. **Span Structure Tests**: Verify span names and attributes
   - Test each span type independently
   - Use `InMemorySpanExporter` for assertions

2. **Hierarchy Tests**: Verify parent-child relationships
   - Test tool loop iterations nest correctly
   - Test classifier spans nest under conversation spans

3. **Attribute Tests**: Verify correct metadata is captured
   - Token counts from Anthropic responses
   - Tool names and success status
   - Error recording

### Integration Tests

1. **End-to-End Trace Tests**: Full Slack → Agent → LLM flow
   - Verify complete span hierarchy
   - Check all attributes present
   - Confirm no missing spans

2. **MCP Trace Tests**: MCP call → Agent → LLM flow
   - Separate root span from Slack
   - Correct source attribute

3. **Error Handling Tests**: Exceptions create error spans
   - LLM API failures
   - Tool execution errors
   - Classification failures

### Example Test

```python
def test_full_conversation_trace_hierarchy():
    """Verify complete span hierarchy for a full conversation."""
    
    # Setup
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    
    # Create mocked agent with all dependencies
    agent = create_test_agent_with_tracing()
    
    # Simulate conversation
    success, response = agent.handle_conversation(
        channel_id="C123",
        text="what files handle auth?",
        thread_ts="1234567890.123456"
    )
    
    # Verify spans
    spans = exporter.get_finished_spans()
    
    # Find root conversation span
    conv_spans = [s for s in spans if s.name == "agent.handle_conversation"]
    assert len(conv_spans) == 1
    root = conv_spans[0]
    
    # Check attributes
    assert root.attributes["benedict.operation"] == "handle_conversation"
    assert root.attributes["benedict.channel_id"] == "C123"
    
    # Verify children exist
    child_span_names = [s.name for s in spans if s.parent and s.parent.span_id == root.context.span_id]
    assert "context.build" in child_span_names
    assert any(name.startswith("llm.") for name in child_span_names)
```

## Success Criteria

The implementation is complete when:

1. **All LLM paths traced**: Classification, tool loop, plain generate, architect query
2. **Jaeger shows clear hierarchy**: Parent-child relationships visible in UI
3. **Token usage visible**: Input/output tokens in span attributes
4. **Tool execution tracked**: Each tool call has span with timing and success status
5. **Tests pass**: Unit tests verify span structure with in-memory exporter
6. **Documentation complete**: Setup guide and usage examples
7. **No sensitive data leaked**: Debug mode off by default, audit of attributes

## Open Questions

1. **Sampling Strategy**: Start with 100% sampling or implement probabilistic sampling?
   - **Decision**: Start with 100% sampling, add configuration later if needed

2. **Export Protocol**: Jaeger Thrift vs. OTLP?
   - **Decision**: Start with Jaeger Thrift for simplicity, document OTLP migration path

3. **Span Naming**: Use dots (e.g., `llm.generate`) or colons (e.g., `llm:generate`)?
   - **Decision**: Use dots, more common in Python tracing

4. **Context Propagation**: How to handle async background indexing?
   - **Decision**: Out of scope for this PR, index operations not traced yet

5. **Cost Estimation**: Storage requirements for traces?
   - **Decision**: Document in observability guide, recommend retention policies

## Future Work (Out of Scope)

1. **Metrics**: Prometheus metrics for request rate, latency, token usage
2. **Dashboards**: Pre-built Grafana dashboards for Benedict
3. **Alerting**: Alerts on high latency, error rates, token budget
4. **Trace Sampling**: Implement probabilistic or rate-limiting sampling
5. **Background Operations**: Trace indexing, Slack history updates
6. **Custom Exporters**: Support for DataDog, New Relic, etc.
7. **Trace Context Propagation**: Across async operations
8. **Request Correlation**: Link Slack thread_ts to traces

## References

- [OpenTelemetry Python SDK](https://opentelemetry-python.readthedocs.io/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [OpenTelemetry Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/)
- [Issue #21](https://github.com/mkarots/benedict/issues/21)
- [Issue #11 (Epic: Observability)](https://github.com/mkarots/benedict/issues/11)

## Revision History

| Version | Date       | Author             | Changes                 |
|---------|------------|--------------------|-------------------------|
| 1.0     | 2026-08-19 | Benedict Agent     | Initial design document |
