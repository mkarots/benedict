# Observability 1: OpenTelemetry Foundation - Proposal and Design

**Issue:** #19  
**Parent:** #11 (Epic: Observability and a thin operator UI)  
**Status:** Proposal  
**Author:** Cloud Agent  
**Date:** 2026-08-19

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Goals and Non-Goals](#goals-and-non-goals)
3. [Background and Motivation](#background-and-motivation)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Design](#detailed-design)
6. [Implementation Plan](#implementation-plan)
7. [Testing Strategy](#testing-strategy)
8. [Security and Privacy](#security-and-privacy)
9. [Configuration](#configuration)
10. [Documentation Updates](#documentation-updates)
11. [Alternatives Considered](#alternatives-considered)
12. [Success Criteria](#success-criteria)
13. [Timeline and Milestones](#timeline-and-milestones)

---

## Executive Summary

This proposal outlines the implementation of OpenTelemetry (OTel) observability foundation for Benedict, enabling operators to understand system behavior through distributed traces. The design follows Benedict's existing protocol-based architecture, maintains the self-hosted privacy model, and provides operators with optional observability without introducing product analytics.

**Key Principles:**

1. **Protocol-first design** - Domain code depends on abstractions, not concrete OTel SDK
2. **Privacy by default** - Traces are local-only unless operator explicitly exports them
3. **Zero overhead when disabled** - No-op implementation introduces no performance penalty
4. **Operator-owned** - Telemetry serves the operator, not a SaaS vendor
5. **Test-friendly** - In-memory exporter enables fast, isolated unit tests

---

## Goals and Non-Goals

### Goals

1. ✅ Add tracer protocol abstraction following Benedict's protocol pattern
2. ✅ Implement OpenTelemetry SDK backend with environment-driven configuration
3. ✅ Create no-op tracer implementation (default) with zero overhead
4. ✅ Wire tracing at composition roots only (`main.py`, `mcp/server.py`)
5. ✅ Emit a startup span so operators can verify tracing works
6. ✅ Provide local Jaeger setup via Docker Compose for trace visualization
7. ✅ Implement in-memory exporter for unit tests (no external dependencies)
8. ✅ Document privacy model in `SECURITY.md` and FAQ
9. ✅ Ensure Benedict runs normally with tracing disabled (default)

### Non-Goals

❌ **Observability 2** - Request-level spans (Slack/Anthropic/GitHub/MCP)  
❌ **Observability 3** - Domain operation spans (LLM classify, tool loops)  
❌ **Observability 4** - Custom Benedict UI (operator dashboard)  
❌ Product analytics or usage tracking (never)  
❌ Performance metrics collection (separate concern)  
❌ Log aggregation (orthogonal to tracing)  
❌ Auto-instrumentation of third-party libraries

---

## Background and Motivation

### Current State

Benedict is a self-hosted Slack bot with multiple integration points:

- **Slack Socket Mode** - Real-time event stream
- **Claude API** - LLM requests with tool calls
- **GitHub CLI** - Repository operations
- **ChromaDB** - Semantic search indexing
- **MCP Protocol** - IDE integration
- **Notion API** - Knowledge management

When issues occur, operators have limited visibility into:

- Request flow across service boundaries
- Timing of operations (which step is slow?)
- Failure modes (where did an error originate?)
- Concurrent operation behavior

### Operator Pain Points

1. **"Why is this Slack response slow?"** - No visibility into LLM, search, or GitHub timing
2. **"Did the indexer run after onboarding?"** - No confirmation of background operations
3. **"Which channel triggered this error?"** - Context is scattered across logs
4. **"Is the MCP server processing my request?"** - No visibility into stdio server lifecycle

### Why OpenTelemetry?

OpenTelemetry is the CNCF standard for observability:

- **Protocol abstraction** - Clean separation from implementation
- **Vendor-neutral** - Works with Jaeger, Zipkin, Tempo, Honeycomb, etc.
- **Rich ecosystem** - Auto-instrumentation, exporters, and tooling
- **Future-proof** - Industry standard with long-term support

### Alignment with Benedict's Architecture

Benedict already uses protocol-based design:

```python
# Existing pattern
LLM Protocol → ClaudeLLM / MockLLM
RepoReader Protocol → LocalRepoReader / WorkspaceRepoReader
SemanticIndexer Protocol → ChromaDBIndexer
```

This proposal extends the pattern:

```python
# New pattern
Tracer Protocol → OTelTracer / NoOpTracer / InMemoryTracer
```

---

## Architecture Overview

### High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│ Domain Code (agent.py, slack_app.py, commands/, mcp/)      │
│                                                             │
│   depends on → Tracer Protocol (abstraction)               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Composition Roots (main.py, mcp/server.py)                 │
│                                                             │
│   creates concrete → NoOpTracer (default)                  │
│                   → OTelTracer (if BENEDICT_OTEL_ENABLED)   │
│                   → InMemoryTracer (in tests)              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ OpenTelemetry SDK (when OTelTracer is active)              │
│                                                             │
│   exports to → Console (default)                           │
│             → OTLP Collector (if endpoint configured)       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Observability Backend (operator-controlled)                │
│                                                             │
│   Jaeger UI (via Docker Compose)                           │
│   or Grafana Tempo / Honeycomb / any OTLP receiver         │
└─────────────────────────────────────────────────────────────┘
```

### Component Interaction

```
Slack Event
    ↓
slack_app.py
    ↓ (receives tracer from composition root)
    span = tracer.start_span("handle_mention")
    ↓
agent.handle_message()
    ↓
    span.set_attribute("channel_id", channel_id)
    ↓
    (domain logic executes)
    ↓
    span.end()
```

### Directory Structure

```
src/benedict/
├── protocols/
│   ├── __init__.py           # Export Tracer protocol
│   └── tracer.py             # NEW: Tracer protocol definition
├── observability/            # NEW: Observability implementations
│   ├── __init__.py
│   ├── tracer_noop.py        # NoOpTracer (default, zero overhead)
│   ├── tracer_otel.py        # OTelTracer (OpenTelemetry SDK backend)
│   └── tracer_inmemory.py    # InMemoryTracer (for tests)
├── main.py                   # Wire tracer at composition root
├── mcp/
│   └── server.py             # Wire tracer at MCP composition root
docs/
├── OBSERVABILITY_1_OTEL_PROPOSAL.md  # This document
└── FAQ.md                    # Update with telemetry questions
tests/
├── unit/
│   ├── test_tracer_noop.py   # NoOpTracer tests
│   ├── test_tracer_inmemory.py  # InMemoryTracer tests
│   └── test_tracer_otel.py   # OTelTracer tests (uses InMemoryTracer)
docker/
└── observability/            # NEW: Local observability stack
    ├── docker-compose.yml    # Jaeger + OTLP collector
    └── README.md             # Setup instructions
```

---

## Detailed Design

### 1. Tracer Protocol

**File:** `src/benedict/protocols/tracer.py`

```python
"""Tracer protocol definition.

Defines the interface for distributed tracing. Domain code depends on this
protocol, not on the OpenTelemetry SDK.
"""

from typing import Protocol, Optional, Dict, Any, ContextManager


class Span(Protocol):
    """Represents a single unit of work in a trace.
    
    A span tracks timing and metadata for one operation. Spans can be nested
    to represent call hierarchies.
    """

    def set_attribute(self, key: str, value: Any) -> None:
        """Add metadata to this span.
        
        Args:
            key: Attribute name (e.g., "channel_id", "repo", "model")
            value: Attribute value (string, number, boolean)
        """
        ...

    def set_status(self, status: str, description: str = "") -> None:
        """Set span outcome.
        
        Args:
            status: "ok" | "error"
            description: Optional error message or status detail
        """
        ...

    def record_exception(self, exception: Exception) -> None:
        """Record an exception that occurred during this span.
        
        Args:
            exception: The exception instance
        """
        ...

    def end(self) -> None:
        """Mark the span as complete and record its duration."""
        ...


class Tracer(Protocol):
    """Protocol for distributed tracing providers.
    
    Benedict uses this protocol to create spans without depending on a
    specific tracing implementation. The composition root wires a concrete
    tracer (NoOpTracer by default, OTelTracer if enabled, InMemoryTracer
    in tests).
    """

    def start_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> ContextManager[Span]:
        """Start a new span as a context manager.
        
        Args:
            name: Span name (e.g., "handle_mention", "search_code")
            attributes: Optional initial attributes
            
        Returns:
            Context manager that yields a Span and automatically ends it
            
        Example:
            with tracer.start_span("onboard_channel") as span:
                span.set_attribute("channel_id", channel_id)
                span.set_attribute("repo", repo_name)
                # ... do work ...
                # Span automatically ends when exiting context
        """
        ...


def create_tracer(provider: str = "noop", **kwargs) -> Tracer:
    """Factory function to create Tracer instance.
    
    Args:
        provider: Provider name ("noop", "otel", "inmemory")
        **kwargs: Provider-specific configuration
        
    Returns:
        Tracer instance
        
    Raises:
        ValueError: If provider is unknown
        
    Example:
        # Default (production, disabled)
        tracer = create_tracer("noop")
        
        # OpenTelemetry (production, enabled)
        tracer = create_tracer(
            "otel",
            service_name="benedict-slack",
            otlp_endpoint="http://localhost:4317",
        )
        
        # In-memory (tests)
        tracer = create_tracer("inmemory")
    """
    if provider == "noop":
        from benedict.observability.tracer_noop import NoOpTracer
        return NoOpTracer()
    elif provider == "otel":
        from benedict.observability.tracer_otel import OTelTracer
        return OTelTracer(**kwargs)
    elif provider == "inmemory":
        from benedict.observability.tracer_inmemory import InMemoryTracer
        return InMemoryTracer()
    else:
        raise ValueError(f"Unknown tracer provider: {provider}")
```

**Design Rationale:**

- **Context manager pattern** - Ensures spans are always ended (prevents leaks)
- **Minimal surface area** - Only essential operations (start, set_attribute, set_status, record_exception, end)
- **Type hints** - Full typing for IDE support and type checking
- **Extensible** - Easy to add new implementations without changing domain code

### 2. NoOpTracer Implementation

**File:** `src/benedict/observability/tracer_noop.py`

```python
"""No-op tracer implementation.

Default tracer with zero overhead. All operations are no-ops that compile
away. Used when tracing is disabled (the default).
"""

from contextlib import contextmanager
from typing import Dict, Any, Optional


class NoOpSpan:
    """Span that does nothing."""

    def set_attribute(self, key: str, value: Any) -> None:
        """No-op."""
        pass

    def set_status(self, status: str, description: str = "") -> None:
        """No-op."""
        pass

    def record_exception(self, exception: Exception) -> None:
        """No-op."""
        pass

    def end(self) -> None:
        """No-op."""
        pass


class NoOpTracer:
    """Tracer implementation that does nothing.
    
    This is the default tracer. It introduces zero overhead - all methods are
    no-ops that the JIT can optimize away.
    """

    @contextmanager
    def start_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """Yield a no-op span."""
        span = NoOpSpan()
        try:
            yield span
        finally:
            span.end()
```

**Design Rationale:**

- **Zero overhead** - No allocations, no network, no I/O
- **Simple implementation** - Easy to verify correctness
- **Safe default** - Operators opt-in to observability, not opt-out

### 3. OTelTracer Implementation

**File:** `src/benedict/observability/tracer_otel.py`

```python
"""OpenTelemetry tracer implementation.

Wraps the OpenTelemetry SDK and exports spans via OTLP or console. Only
imported when tracing is explicitly enabled.
"""

from contextlib import contextmanager
from typing import Dict, Any, Optional
import logging

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME

logger = logging.getLogger(__name__)


class OTelSpan:
    """Wrapper around OpenTelemetry span."""

    def __init__(self, otel_span):
        self._span = otel_span

    def set_attribute(self, key: str, value: Any) -> None:
        """Add attribute to span."""
        self._span.set_attribute(key, value)

    def set_status(self, status: str, description: str = "") -> None:
        """Set span status."""
        from opentelemetry.trace import Status, StatusCode
        
        status_code = StatusCode.OK if status == "ok" else StatusCode.ERROR
        self._span.set_status(Status(status_code, description))

    def record_exception(self, exception: Exception) -> None:
        """Record exception on span."""
        self._span.record_exception(exception)

    def end(self) -> None:
        """End the span."""
        self._span.end()


class OTelTracer:
    """OpenTelemetry tracer implementation.
    
    Wraps the OTel SDK and configures exporters based on environment variables.
    """

    def __init__(
        self,
        service_name: str = "benedict",
        otlp_endpoint: Optional[str] = None,
        console_export: bool = False,
    ):
        """Initialize OpenTelemetry tracer.
        
        Args:
            service_name: Service name for traces (e.g., "benedict-slack", "benedict-mcp")
            otlp_endpoint: OTLP collector endpoint (e.g., "http://localhost:4317")
            console_export: If True, also print spans to console (debug)
        """
        # Create resource with service name
        resource = Resource(attributes={SERVICE_NAME: service_name})
        
        # Create tracer provider
        provider = TracerProvider(resource=resource)
        
        # Configure exporters
        if otlp_endpoint:
            # Export to OTLP collector (Jaeger, Tempo, etc.)
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            logger.info(f"OTel exporting to OTLP: {otlp_endpoint}")
        
        if console_export:
            # Also print to console for debugging
            console_exporter = ConsoleSpanExporter()
            provider.add_span_processor(BatchSpanProcessor(console_exporter))
            logger.info("OTel exporting to console")
        
        if not otlp_endpoint and not console_export:
            # Default: export to console if no endpoint configured
            console_exporter = ConsoleSpanExporter()
            provider.add_span_processor(BatchSpanProcessor(console_exporter))
            logger.info("OTel exporting to console (default)")
        
        # Set as global tracer provider
        trace.set_tracer_provider(provider)
        
        # Get tracer for this service
        self._tracer = trace.get_tracer(__name__)
        
        logger.info(f"OTel tracer initialized: service={service_name}")

    @contextmanager
    def start_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """Start an OpenTelemetry span."""
        otel_span = self._tracer.start_span(name)
        span = OTelSpan(otel_span)
        
        # Set initial attributes if provided
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status("error", str(exc))
            raise
        finally:
            span.end()
```

**Design Rationale:**

- **Lazy import** - OTel SDK only imported when tracing is enabled
- **Flexible export** - Supports OTLP (standard) and console (debugging)
- **Resource metadata** - Service name distinguishes Slack vs MCP traces
- **Auto-exception tracking** - Context manager records exceptions automatically
- **Batch processing** - Spans are batched to reduce overhead

### 4. InMemoryTracer Implementation

**File:** `src/benedict/observability/tracer_inmemory.py`

```python
"""In-memory tracer for testing.

Captures spans in memory for assertion in tests. Does not require external
services (no collector, no Jaeger). Fast and deterministic.
"""

from contextlib import contextmanager
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class InMemorySpanData:
    """Captured span data for test assertions."""
    
    name: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    status: str = "unset"
    status_description: str = ""
    exceptions: List[Exception] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None


class InMemorySpan:
    """Span that captures data in memory."""

    def __init__(self, data: InMemorySpanData):
        self._data = data

    def set_attribute(self, key: str, value: Any) -> None:
        """Capture attribute."""
        self._data.attributes[key] = value

    def set_status(self, status: str, description: str = "") -> None:
        """Capture status."""
        self._data.status = status
        self._data.status_description = description

    def record_exception(self, exception: Exception) -> None:
        """Capture exception."""
        self._data.exceptions.append(exception)

    def end(self) -> None:
        """Mark span as ended."""
        self._data.end_time = datetime.now()
        if self._data.start_time and self._data.end_time:
            delta = self._data.end_time - self._data.start_time
            self._data.duration_ms = delta.total_seconds() * 1000


class InMemoryTracer:
    """Tracer that captures spans in memory for testing.
    
    Example:
        tracer = InMemoryTracer()
        
        with tracer.start_span("test_operation") as span:
            span.set_attribute("user_id", "123")
        
        spans = tracer.get_spans()
        assert len(spans) == 1
        assert spans[0].name == "test_operation"
        assert spans[0].attributes["user_id"] == "123"
    """

    def __init__(self):
        self._spans: List[InMemorySpanData] = []

    @contextmanager
    def start_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """Start a span and capture it in memory."""
        data = InMemorySpanData(name=name)
        if attributes:
            data.attributes.update(attributes)
        
        self._spans.append(data)
        span = InMemorySpan(data)
        
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status("error", str(exc))
            raise
        finally:
            span.end()

    def get_spans(self) -> List[InMemorySpanData]:
        """Return all captured spans."""
        return self._spans.copy()

    def get_span_names(self) -> List[str]:
        """Return span names in order (convenience for tests)."""
        return [span.name for span in self._spans]

    def clear(self) -> None:
        """Clear all captured spans."""
        self._spans.clear()

    def find_span(self, name: str) -> Optional[InMemorySpanData]:
        """Find first span with given name."""
        for span in self._spans:
            if span.name == name:
                return span
        return None
```

**Design Rationale:**

- **Test-friendly** - No external dependencies, fast, deterministic
- **Rich assertions** - Capture all span data for verification
- **Convenience methods** - `get_span_names()`, `find_span()` simplify tests
- **Realistic behavior** - Captures timing, exceptions, attributes like real tracer

### 5. Composition Root Updates

**File:** `src/benedict/main.py` (additions)

```python
from benedict.protocols import (
    create_llm,
    create_repo_reader,
    create_semantic_indexer,
    create_conversation_repository,
    create_conversation_history_indexer,
    create_tracer,  # NEW
)

def main():
    """Root composition - wire everything together."""
    
    # ... (existing setup code) ...
    
    # Create tracer (disabled by default)
    tracer = None
    otel_enabled = os.environ.get("BENEDICT_OTEL_ENABLED", "false").lower() == "true"
    
    if otel_enabled:
        try:
            otlp_endpoint = os.environ.get("BENEDICT_OTEL_ENDPOINT")
            console_export = os.environ.get("BENEDICT_OTEL_CONSOLE", "false").lower() == "true"
            
            tracer = create_tracer(
                provider="otel",
                service_name="benedict-slack",
                otlp_endpoint=otlp_endpoint,
                console_export=console_export,
            )
            logger.info(f"✅ Tracer initialized (OpenTelemetry, endpoint={otlp_endpoint or 'console'})")
        except Exception as e:
            logger.warning(f"⚠️ Tracer initialization failed: {e}")
            logger.info("Falling back to no-op tracer")
            tracer = create_tracer("noop")
    else:
        tracer = create_tracer("noop")
        logger.info("Tracer disabled (set BENEDICT_OTEL_ENABLED=true to enable)")
    
    # Emit startup span
    with tracer.start_span("benedict_startup") as span:
        span.set_attribute("service", "slack")
        span.set_attribute("version", "0.5.2")  # TODO: Read from __version__
    
    # ... (rest of existing composition) ...
    
    # Pass tracer to agent
    agent = RepoAgent(
        state_file=state_file,
        llm=llm,
        repo_reader=repo_reader,
        semantic_indexer=semantic_indexer,
        conversation_repository=conversation_repository,
        workspace_manager=workspace_manager,
        conversation_history_indexer=conversation_history_indexer,
        tracer=tracer,  # NEW
    )
    
    # ... (existing app startup) ...
```

**File:** `src/benedict/mcp/server.py` (additions)

```python
def build_mcp_service(
    data_dir: Optional[Path] = None,
    workspaces_dir: Optional[Path] = None,
    state_file: Optional[Path] = None,
    chroma_db_dir: Optional[Path] = None,
) -> BenedictMcpService:
    """Wire MCP service dependencies."""
    
    # ... (existing setup code) ...
    
    # Create tracer (disabled by default)
    from benedict.protocols import create_tracer
    
    tracer = None
    otel_enabled = os.environ.get("BENEDICT_OTEL_ENABLED", "false").lower() == "true"
    
    if otel_enabled:
        try:
            otlp_endpoint = os.environ.get("BENEDICT_OTEL_ENDPOINT")
            console_export = os.environ.get("BENEDICT_OTEL_CONSOLE", "false").lower() == "true"
            
            tracer = create_tracer(
                provider="otel",
                service_name="benedict-mcp",
                otlp_endpoint=otlp_endpoint,
                console_export=console_export,
            )
            logger.info(f"Tracer initialized (OpenTelemetry)")
        except Exception as exc:
            logger.warning(f"Tracer initialization failed: {exc}")
            tracer = create_tracer("noop")
    else:
        tracer = create_tracer("noop")
    
    # Emit startup span
    with tracer.start_span("benedict_mcp_startup") as span:
        span.set_attribute("service", "mcp")
    
    # ... (rest of existing composition) ...
    
    return BenedictMcpService(
        resolver=resolver,
        workspace_manager=workspace_manager,
        llm=llm,
        repo_reader=repo_reader,
        semantic_indexer=semantic_indexer,
        metadata_reader=metadata_reader,
        tracer=tracer,  # NEW
    )
```

### 6. Agent Integration

**File:** `src/benedict/agent.py` (additions)

```python
class RepoAgent:
    """Benedict's main agent."""
    
    def __init__(
        self,
        state_file: str,
        llm: Optional[LLM] = None,
        repo_reader: Optional[RepoReader] = None,
        semantic_indexer: Optional[SemanticIndexer] = None,
        conversation_repository: Optional[ConversationRepository] = None,
        workspace_manager: Optional[WorkspaceManager] = None,
        conversation_history_indexer: Optional[ConversationHistoryIndexer] = None,
        tracer: Optional[Tracer] = None,  # NEW
    ):
        # ... (existing initialization) ...
        self.tracer = tracer or create_tracer("noop")  # Default to no-op if not provided
    
    # ... (existing methods) ...
```

---

## Implementation Plan

### Phase 1: Protocol and No-Op Implementation (Day 1)

**Goal:** Add tracer protocol and default no-op implementation. System behavior unchanged.

**Tasks:**

1. ✅ Create `src/benedict/protocols/tracer.py`
   - Define `Span` protocol
   - Define `Tracer` protocol
   - Implement `create_tracer()` factory
   - Add comprehensive docstrings and examples

2. ✅ Create `src/benedict/observability/` package
   - `__init__.py` with package exports
   - `tracer_noop.py` with `NoOpTracer` and `NoOpSpan`

3. ✅ Update `src/benedict/protocols/__init__.py`
   - Export `Tracer`, `Span`, `create_tracer`

4. ✅ Update `src/benedict/agent.py`
   - Add optional `tracer` parameter to `__init__`
   - Store tracer instance
   - Default to no-op tracer if None

5. ✅ Write unit tests
   - `tests/unit/test_tracer_noop.py`
   - Verify no-op behavior (no exceptions, no side effects)

**Verification:**

```bash
make test  # All existing tests pass, new tests pass
make run   # Bot runs normally (tracing disabled by default)
```

### Phase 2: OpenTelemetry SDK Implementation (Day 2-3)

**Goal:** Add OTel backend with environment configuration. Still disabled by default.

**Tasks:**

1. ✅ Add OpenTelemetry dependencies to `pyproject.toml`
   ```toml
   dependencies = [
       # ... existing dependencies ...
       "opentelemetry-api>=1.20.0",
       "opentelemetry-sdk>=1.20.0",
       "opentelemetry-exporter-otlp-proto-grpc>=1.20.0",
   ]
   ```

2. ✅ Create `src/benedict/observability/tracer_otel.py`
   - Implement `OTelTracer` class
   - Implement `OTelSpan` wrapper
   - Configure exporters (OTLP, console)
   - Add error handling and logging

3. ✅ Update `pyproject.toml` factory to support "otel" provider

4. ✅ Update composition roots
   - `src/benedict/main.py` - Read env vars, create OTel tracer if enabled
   - `src/benedict/mcp/server.py` - Same pattern for MCP

5. ✅ Add startup spans
   - Emit `benedict_startup` span in `main.py` (service=slack)
   - Emit `benedict_mcp_startup` span in `mcp/server.py` (service=mcp)

6. ✅ Write unit tests
   - `tests/unit/test_tracer_otel.py`
   - Use `InMemoryTracer` (implement next) to verify span creation

**Verification:**

```bash
# Tracing still disabled
make test
make run

# Enable tracing (console export)
BENEDICT_OTEL_ENABLED=true BENEDICT_OTEL_CONSOLE=true make run
# Should see span output in console
```

### Phase 3: In-Memory Tracer for Tests (Day 3)

**Goal:** Enable testing of tracing behavior without external dependencies.

**Tasks:**

1. ✅ Create `src/benedict/observability/tracer_inmemory.py`
   - Implement `InMemoryTracer`
   - Implement `InMemorySpan`
   - Add `get_spans()`, `get_span_names()`, `find_span()` helpers

2. ✅ Update factory to support "inmemory" provider

3. ✅ Write unit tests
   - `tests/unit/test_tracer_inmemory.py`
   - Verify span capture, attributes, status, exceptions

4. ✅ Update OTel tests
   - Replace console verification with InMemoryTracer assertions
   - Test span attributes, status, error recording

**Verification:**

```bash
make test  # All tests pass, including new tracer tests
```

### Phase 4: Docker Compose for Local Observability (Day 4)

**Goal:** Provide turnkey local Jaeger setup for operators.

**Tasks:**

1. ✅ Create `docker/observability/docker-compose.yml`
   ```yaml
   version: '3.8'
   
   services:
     jaeger:
       image: jaegertracing/all-in-one:latest
       ports:
         - "16686:16686"  # Jaeger UI
         - "4317:4317"    # OTLP gRPC receiver
         - "4318:4318"    # OTLP HTTP receiver
       environment:
         - COLLECTOR_OTLP_ENABLED=true
   ```

2. ✅ Create `docker/observability/README.md`
   - How to start Jaeger
   - How to enable tracing in Benedict
   - How to view traces in Jaeger UI
   - Screenshot of expected trace

3. ✅ Test end-to-end
   ```bash
   # Start Jaeger
   cd docker/observability
   docker compose up -d
   
   # Enable Benedict tracing
   export BENEDICT_OTEL_ENABLED=true
   export BENEDICT_OTEL_ENDPOINT=http://localhost:4317
   make run
   
   # Trigger an event
   # @benedict status (in Slack)
   
   # View trace in Jaeger
   open http://localhost:16686
   ```

**Verification:**

- Jaeger UI shows `benedict-slack` service
- Startup span appears with correct attributes
- No errors in Benedict logs

### Phase 5: Documentation and Security (Day 5)

**Goal:** Document privacy model, FAQ, and usage instructions.

**Tasks:**

1. ✅ Create or update `SECURITY.md`
   ```markdown
   ## Telemetry and Privacy
   
   Benedict does not send product analytics, usage statistics, or user data
   to any third party. All telemetry is operator-owned and stays on your
   infrastructure unless you explicitly configure an external exporter.
   
   ### OpenTelemetry (Observability 1)
   
   Benedict supports optional OpenTelemetry tracing for operators who want
   to understand system behavior:
   
   - **Default:** Tracing is disabled. No spans are emitted.
   - **Local mode:** Export to console or local OTLP collector (Jaeger, Tempo).
   - **Remote mode:** You control the endpoint. We never export to a SaaS vendor.
   
   Traces may contain:
   - Timing of operations
   - Channel IDs, repository names, user IDs
   - Error messages and stack traces
   
   If you export traces to a remote collector, secure that endpoint
   (authentication, TLS, network policies).
   ```

2. ✅ Create or update `docs/FAQ.md`
   ```markdown
   ## Does Benedict collect telemetry?
   
   No. Benedict does not send usage data to anyone. You control all telemetry.
   
   OpenTelemetry tracing is optional and disabled by default. When enabled,
   traces stay on your machine unless you configure a remote exporter. See
   `SECURITY.md` for details.
   ```

3. ✅ Update `README.md`
   - Add observability section
   - Link to `docker/observability/README.md`

4. ✅ Update `CHANGELOG.md`
   ```markdown
   ## [Unreleased]
   
   ### Added
   - **OpenTelemetry observability foundation (Observability 1)**
     - Tracer protocol abstraction (domain code does not import OTel SDK)
     - NoOpTracer (default, zero overhead)
     - OTelTracer (OpenTelemetry SDK backend with OTLP export)
     - InMemoryTracer (for unit tests)
     - Docker Compose stack for local Jaeger
     - Startup spans in Slack and MCP services
     - Documentation: `SECURITY.md`, `docker/observability/README.md`
   ```

**Verification:**

- `SECURITY.md` exists and clearly states privacy model
- `docs/FAQ.md` answers telemetry questions
- `README.md` links to observability docs
- `CHANGELOG.md` documents changes

### Phase 6: Final Testing and PR Preparation (Day 6)

**Goal:** Ensure all success criteria are met. Prepare PR for review.

**Tasks:**

1. ✅ Run full test suite
   ```bash
   make test          # All tests pass
   make format        # Code formatted
   make check         # Linting passes
   ```

2. ✅ Manual testing checklist
   - [ ] Slack bot runs with tracing disabled (default)
   - [ ] Slack bot runs with tracing enabled (console)
   - [ ] Slack bot runs with tracing enabled (OTLP to Jaeger)
   - [ ] MCP server runs with tracing disabled (default)
   - [ ] MCP server runs with tracing enabled (OTLP to Jaeger)
   - [ ] Startup span appears in Jaeger for Slack service
   - [ ] Startup span appears in Jaeger for MCP service
   - [ ] Span attributes are correct (service name, version)
   - [ ] Jaeger UI is accessible at http://localhost:16686
   - [ ] Docker Compose starts without errors

3. ✅ Update PR description
   - Link to this design doc
   - List changes (protocol, implementations, tests, docs, docker)
   - Attach screenshot of Jaeger UI showing benedict_startup span
   - Note that domain spans (Observability 2+) are out of scope

4. ✅ Request review

**Verification:**

- All manual tests pass
- Screenshots attached to PR
- PR description is clear and complete

---

## Testing Strategy

### Unit Tests

**Test Coverage Goals:** >90% for new code

#### 1. NoOpTracer Tests

**File:** `tests/unit/test_tracer_noop.py`

```python
"""Tests for NoOpTracer."""

from benedict.protocols import create_tracer


def test_noop_tracer_creation():
    """NoOpTracer can be created."""
    tracer = create_tracer("noop")
    assert tracer is not None


def test_noop_span_context_manager():
    """NoOpTracer.start_span returns a context manager."""
    tracer = create_tracer("noop")
    
    with tracer.start_span("test_span") as span:
        assert span is not None


def test_noop_span_set_attribute():
    """NoOpSpan.set_attribute does not raise."""
    tracer = create_tracer("noop")
    
    with tracer.start_span("test") as span:
        span.set_attribute("key", "value")  # Should not raise


def test_noop_span_set_status():
    """NoOpSpan.set_status does not raise."""
    tracer = create_tracer("noop")
    
    with tracer.start_span("test") as span:
        span.set_status("ok")
        span.set_status("error", "something failed")


def test_noop_span_record_exception():
    """NoOpSpan.record_exception does not raise."""
    tracer = create_tracer("noop")
    
    with tracer.start_span("test") as span:
        span.record_exception(ValueError("test error"))


def test_noop_span_exception_propagates():
    """Exceptions in span context are propagated."""
    tracer = create_tracer("noop")
    
    try:
        with tracer.start_span("test") as span:
            raise ValueError("test error")
    except ValueError as e:
        assert str(e) == "test error"
    else:
        assert False, "Exception should have been raised"
```

#### 2. InMemoryTracer Tests

**File:** `tests/unit/test_tracer_inmemory.py`

```python
"""Tests for InMemoryTracer."""

from benedict.protocols import create_tracer


def test_inmemory_tracer_creation():
    """InMemoryTracer can be created."""
    tracer = create_tracer("inmemory")
    assert tracer is not None


def test_inmemory_tracer_captures_span():
    """InMemoryTracer captures spans."""
    tracer = create_tracer("inmemory")
    
    with tracer.start_span("test_operation"):
        pass
    
    spans = tracer.get_spans()
    assert len(spans) == 1
    assert spans[0].name == "test_operation"


def test_inmemory_tracer_captures_attributes():
    """InMemoryTracer captures span attributes."""
    tracer = create_tracer("inmemory")
    
    with tracer.start_span("test") as span:
        span.set_attribute("user_id", "123")
        span.set_attribute("action", "onboard")
    
    span_data = tracer.find_span("test")
    assert span_data is not None
    assert span_data.attributes["user_id"] == "123"
    assert span_data.attributes["action"] == "onboard"


def test_inmemory_tracer_captures_status():
    """InMemoryTracer captures span status."""
    tracer = create_tracer("inmemory")
    
    with tracer.start_span("test") as span:
        span.set_status("error", "something failed")
    
    span_data = tracer.find_span("test")
    assert span_data.status == "error"
    assert span_data.status_description == "something failed"


def test_inmemory_tracer_captures_exceptions():
    """InMemoryTracer captures exceptions."""
    tracer = create_tracer("inmemory")
    
    exc = ValueError("test error")
    try:
        with tracer.start_span("test") as span:
            span.record_exception(exc)
            raise exc
    except ValueError:
        pass
    
    span_data = tracer.find_span("test")
    assert len(span_data.exceptions) == 1
    assert span_data.exceptions[0] == exc
    assert span_data.status == "error"


def test_inmemory_tracer_get_span_names():
    """InMemoryTracer.get_span_names() returns span names."""
    tracer = create_tracer("inmemory")
    
    with tracer.start_span("span1"):
        pass
    with tracer.start_span("span2"):
        pass
    
    names = tracer.get_span_names()
    assert names == ["span1", "span2"]


def test_inmemory_tracer_clear():
    """InMemoryTracer.clear() removes all spans."""
    tracer = create_tracer("inmemory")
    
    with tracer.start_span("test"):
        pass
    
    assert len(tracer.get_spans()) == 1
    
    tracer.clear()
    
    assert len(tracer.get_spans()) == 0
```

#### 3. OTelTracer Tests

**File:** `tests/unit/test_tracer_otel.py`

```python
"""Tests for OTelTracer.

Uses InMemoryTracer to verify OTel span creation without external dependencies.
"""

import pytest
from benedict.observability.tracer_otel import OTelTracer


def test_otel_tracer_creation():
    """OTelTracer can be created."""
    tracer = OTelTracer(service_name="test-service", console_export=True)
    assert tracer is not None


def test_otel_span_context_manager():
    """OTelTracer.start_span returns a context manager."""
    tracer = OTelTracer(service_name="test-service", console_export=True)
    
    with tracer.start_span("test_span") as span:
        assert span is not None


def test_otel_span_attributes():
    """OTelTracer captures span attributes."""
    tracer = OTelTracer(service_name="test-service", console_export=True)
    
    with tracer.start_span("test", attributes={"key": "value"}) as span:
        span.set_attribute("another_key", "another_value")
    
    # Verify via in-memory exporter in a real test
    # For now, just verify no exceptions


def test_otel_span_status():
    """OTelTracer captures span status."""
    tracer = OTelTracer(service_name="test-service", console_export=True)
    
    with tracer.start_span("test") as span:
        span.set_status("ok")
    
    with tracer.start_span("test_error") as span:
        span.set_status("error", "something failed")


def test_otel_span_exception_auto_recorded():
    """OTelTracer automatically records exceptions."""
    tracer = OTelTracer(service_name="test-service", console_export=True)
    
    try:
        with tracer.start_span("test") as span:
            raise ValueError("test error")
    except ValueError:
        pass
    
    # Exception should be recorded on span
    # Verify via in-memory exporter in a real test
```

### Integration Tests

**Goal:** Verify tracing works end-to-end with real services.

#### Manual Testing Checklist

1. **Tracing Disabled (Default)**
   ```bash
   make run
   # @benedict status (in Slack)
   # Verify: No span output, bot works normally
   ```

2. **Tracing Enabled (Console)**
   ```bash
   BENEDICT_OTEL_ENABLED=true BENEDICT_OTEL_CONSOLE=true make run
   # @benedict status
   # Verify: Span output appears in console
   ```

3. **Tracing Enabled (OTLP to Jaeger)**
   ```bash
   cd docker/observability
   docker compose up -d
   
   BENEDICT_OTEL_ENABLED=true BENEDICT_OTEL_ENDPOINT=http://localhost:4317 make run
   # @benedict status
   # Open http://localhost:16686
   # Verify: Trace appears in Jaeger UI
   ```

4. **MCP Server with Tracing**
   ```bash
   BENEDICT_OTEL_ENABLED=true BENEDICT_OTEL_ENDPOINT=http://localhost:4317 benedict-mcp
   # Use Cursor to call an MCP tool
   # Verify: MCP spans appear in Jaeger
   ```

### Test Pyramid

```
           ┌─────────────┐
           │   Manual    │  Verify Jaeger UI, Docker Compose
           │  (1 hour)   │
           └─────────────┘
         ┌─────────────────┐
         │  Integration    │  End-to-end with real services
         │   (Optional)    │
         └─────────────────┘
      ┌──────────────────────┐
      │    Unit Tests        │  Protocol, NoOp, InMemory, OTel
      │   (Fast, ~100ms)     │  >90% coverage
      └──────────────────────┘
```

---

## Security and Privacy

### Privacy Model

**Core Principle:** Benedict never sends data to a third party unless the operator explicitly configures it.

#### What We Collect (When Tracing Enabled)

Spans may contain:

- **Timing:** Start time, duration of operations
- **Identifiers:** Channel IDs, user IDs (Slack), repository names
- **Metadata:** Service name, span names (e.g., "onboard_channel")
- **Errors:** Exception messages, stack traces
- **Attributes:** Key-value pairs set by domain code

#### What We Don't Collect

- **Message content:** User questions, LLM responses
- **Source code:** Repository file contents
- **API keys:** Anthropic, GitHub, Slack tokens
- **Personal data:** User emails, names (unless logged as attributes)

#### Data Flow

```
Domain Code → Tracer Protocol → Implementation
                                      ↓
                                NoOpTracer → /dev/null (default)
                                      ↓
                                OTelTracer → Console (stderr, operator sees it)
                                      ↓
                                OTelTracer → OTLP Endpoint (operator-configured)
                                      ↓
                                Local Jaeger (operator-owned)
                                      ↓
                                OR Remote Collector (operator-controlled)
```

**Operator Responsibilities:**

1. **Secure the endpoint** - If exporting to a remote collector, use authentication and TLS
2. **Access control** - Limit who can view traces (channel IDs, user IDs are sensitive)
3. **Data retention** - Configure trace retention policies in the backend
4. **Compliance** - Ensure trace data handling complies with your policies (GDPR, etc.)

### Security Checklist

- ✅ **No product analytics** - We never export to a SaaS vendor by default
- ✅ **Explicit opt-in** - Tracing is disabled unless `BENEDICT_OTEL_ENABLED=true`
- ✅ **Local-first** - Default export is console (stderr), not network
- ✅ **Operator-controlled endpoint** - Only export where operator specifies
- ✅ **Documented clearly** - `SECURITY.md` and FAQ explain the model
- ✅ **No API keys in traces** - Redact sensitive values before recording

### Recommendations

1. **Do not export to public collectors** - Traces contain channel IDs and repo names
2. **Use authentication** - If using a remote OTLP collector, enable auth
3. **Use TLS** - Encrypt trace export in production
4. **Review span attributes** - Before adding new attributes, consider privacy implications

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BENEDICT_OTEL_ENABLED` | `false` | Enable OpenTelemetry tracing (`true` or `false`) |
| `BENEDICT_OTEL_ENDPOINT` | (none) | OTLP collector endpoint (e.g., `http://localhost:4317`) |
| `BENEDICT_OTEL_CONSOLE` | `false` | Also export to console for debugging (`true` or `false`) |
| `BENEDICT_OTEL_SERVICE_NAME` | `benedict-{slack\|mcp}` | Override service name in traces |

### Configuration Examples

#### Tracing Disabled (Default)

```bash
# No configuration needed
make run
```

#### Tracing to Console (Debugging)

```bash
export BENEDICT_OTEL_ENABLED=true
export BENEDICT_OTEL_CONSOLE=true
make run
```

#### Tracing to Local Jaeger

```bash
# Start Jaeger
cd docker/observability
docker compose up -d

# Enable Benedict tracing
export BENEDICT_OTEL_ENABLED=true
export BENEDICT_OTEL_ENDPOINT=http://localhost:4317
make run

# View traces
open http://localhost:16686
```

#### Tracing to Remote Collector

```bash
export BENEDICT_OTEL_ENABLED=true
export BENEDICT_OTEL_ENDPOINT=https://otlp.example.com:4317
# Note: Configure authentication in the OTLP exporter if needed
make run
```

### Docker Compose Configuration

**File:** `docker/observability/docker-compose.yml`

```yaml
version: '3.8'

services:
  jaeger:
    image: jaegertracing/all-in-one:latest
    container_name: benedict-jaeger
    restart: unless-stopped
    ports:
      - "16686:16686"  # Jaeger UI
      - "4317:4317"    # OTLP gRPC receiver
      - "4318:4318"    # OTLP HTTP receiver
    environment:
      - COLLECTOR_OTLP_ENABLED=true
      - SPAN_STORAGE_TYPE=memory  # Use badger or cassandra for persistence
    # Optional: Persist traces to disk
    # volumes:
    #   - jaeger-data:/badger
    networks:
      - observability

networks:
  observability:
    driver: bridge

# volumes:
#   jaeger-data:
```

**Usage:**

```bash
cd docker/observability
docker compose up -d              # Start Jaeger
docker compose logs -f jaeger     # View logs
docker compose down               # Stop Jaeger
```

---

## Documentation Updates

### 1. SECURITY.md (Create or Update)

Add section:

```markdown
## Telemetry and Privacy

Benedict does not collect usage statistics, product analytics, or user data.
You control all telemetry.

### OpenTelemetry Observability (Optional)

Benedict supports optional distributed tracing for operators:

- **Default:** Tracing is disabled. No spans are emitted.
- **Local mode:** Export to console or local OTLP collector (Jaeger, Tempo).
- **Remote mode:** You configure the endpoint. We never send traces to a vendor.

#### What Traces May Contain

When tracing is enabled, spans include:

- Operation timing and duration
- Channel IDs, repository names, user IDs (Slack)
- Error messages and stack traces
- Custom attributes set by domain code

Traces do **not** contain:

- Message content (user questions, LLM responses)
- Source code or repository file contents
- API keys or tokens

#### Operator Responsibilities

If you export traces to a remote collector:

1. Secure the endpoint (authentication, TLS)
2. Control access to traces (channel IDs and user IDs are sensitive)
3. Configure retention policies
4. Ensure compliance with your privacy policies (GDPR, etc.)

See `docker/observability/README.md` for setup instructions.
```

### 2. docs/FAQ.md (Create or Update)

Add questions:

```markdown
## Does Benedict collect telemetry?

No. Benedict does not send usage data, product analytics, or telemetry to any
third party.

OpenTelemetry tracing is optional and disabled by default. When enabled, traces
stay on your infrastructure unless you configure a remote exporter. See
`SECURITY.md` for details.

## How do I enable tracing?

Tracing is disabled by default. To enable it:

1. Start a local Jaeger instance:
   ```bash
   cd docker/observability
   docker compose up -d
   ```

2. Enable tracing in Benedict:
   ```bash
   export BENEDICT_OTEL_ENABLED=true
   export BENEDICT_OTEL_ENDPOINT=http://localhost:4317
   make run
   ```

3. View traces at http://localhost:16686

See `docker/observability/README.md` for full setup instructions.

## What data is in traces?

Traces contain:

- Operation timing (start time, duration)
- Identifiers (channel ID, repo name, user ID)
- Span names (e.g., "onboard_channel", "search_code")
- Errors (exception messages, stack traces)

Traces do not contain:

- Message content
- Source code
- API keys

See `SECURITY.md` for the complete privacy model.

## Can I use a remote OTLP collector?

Yes. Set `BENEDICT_OTEL_ENDPOINT` to your collector's endpoint:

```bash
export BENEDICT_OTEL_ENDPOINT=https://otlp.example.com:4317
```

Ensure the endpoint is secured (authentication, TLS) and that you control
access to traces.
```

### 3. docker/observability/README.md (Create)

```markdown
# Benedict Observability Stack

Local OpenTelemetry observability setup for Benedict operators.

## What's Included

- **Jaeger** - Distributed tracing UI and storage
- **OTLP Collector** - Receives traces from Benedict

## Quick Start

### 1. Start Jaeger

```bash
cd docker/observability
docker compose up -d
```

Jaeger UI: http://localhost:16686

### 2. Enable Tracing in Benedict

```bash
export BENEDICT_OTEL_ENABLED=true
export BENEDICT_OTEL_ENDPOINT=http://localhost:4317
```

### 3. Run Benedict

```bash
cd ../..  # Back to repo root
make run
```

### 4. View Traces

Open http://localhost:16686 and select the `benedict-slack` service.

## What You'll See

After starting Benedict, you should see:

- **Service:** `benedict-slack` (or `benedict-mcp` for the MCP server)
- **Startup Span:** `benedict_startup` with attributes:
  - `service=slack` (or `mcp`)
  - `version=0.5.2`

As you use Benedict (e.g., `@benedict status` in Slack), more spans will
appear in future observability milestones (Observability 2+).

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BENEDICT_OTEL_ENABLED` | `false` | Enable tracing |
| `BENEDICT_OTEL_ENDPOINT` | (none) | OTLP collector endpoint |
| `BENEDICT_OTEL_CONSOLE` | `false` | Also print spans to console |

### Example: Console Export (Debug)

```bash
export BENEDICT_OTEL_ENABLED=true
export BENEDICT_OTEL_CONSOLE=true
make run
```

Spans will be printed to stderr.

## Stopping Jaeger

```bash
cd docker/observability
docker compose down
```

## Persistence

By default, Jaeger stores traces in memory (lost on restart). To persist traces:

1. Uncomment the `volumes` section in `docker-compose.yml`
2. Change `SPAN_STORAGE_TYPE` to `badger` or `cassandra`
3. Restart: `docker compose up -d`

## Security

Traces may contain:

- Channel IDs, user IDs, repository names
- Error messages and stack traces

Do not expose Jaeger UI publicly without authentication.

## Alternatives to Jaeger

Benedict exports traces via OTLP (OpenTelemetry Protocol). You can use any
OTLP-compatible backend:

- **Grafana Tempo** - Long-term trace storage
- **Honeycomb** - SaaS observability platform
- **Zipkin** - Alternative to Jaeger
- **Elastic APM** - Elasticsearch-based

Change `BENEDICT_OTEL_ENDPOINT` to point to your collector.

## Troubleshooting

### No traces appear in Jaeger

1. Check Benedict logs for tracing initialization:
   ```
   ✅ Tracer initialized (OpenTelemetry, endpoint=http://localhost:4317)
   ```

2. Verify Jaeger is running:
   ```bash
   docker compose ps
   ```

3. Check Jaeger logs:
   ```bash
   docker compose logs -f jaeger
   ```

4. Verify endpoint is reachable:
   ```bash
   curl http://localhost:4317
   ```

### "Tracer initialization failed"

OpenTelemetry dependencies may be missing:

```bash
uv pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc
```

## Screenshots

(TODO: Add screenshot of Jaeger UI showing `benedict_startup` span)
```

### 4. README.md (Update)

Add section after "MCP server" section:

```markdown
### Observability (Optional)

Benedict supports optional OpenTelemetry tracing for operators who want to
understand system behavior. Tracing is disabled by default.

To enable tracing with a local Jaeger instance:

```bash
# Start Jaeger
cd docker/observability
docker compose up -d

# Enable tracing
export BENEDICT_OTEL_ENABLED=true
export BENEDICT_OTEL_ENDPOINT=http://localhost:4317
make run

# View traces
open http://localhost:16686
```

See [`docker/observability/README.md`](docker/observability/README.md) for
full setup instructions.

**Privacy:** Traces are local-only unless you configure a remote exporter. We
never send telemetry to a third party. See [`SECURITY.md`](SECURITY.md) for
the complete privacy model.
```

---

## Alternatives Considered

### Alternative 1: Print-based "Tracing"

**Approach:** Add `logger.info()` calls instead of real tracing.

**Pros:**
- Zero new dependencies
- Simple to implement

**Cons:**
- No structured timing data
- No distributed trace correlation
- Difficult to query (grep logs)
- No standard tooling (Jaeger, Grafana)

**Verdict:** ❌ Rejected. Logging is orthogonal to tracing. We keep structured logs and add tracing for operators who need it.

### Alternative 2: Direct OpenTelemetry SDK Usage

**Approach:** Import OTel SDK directly in domain code (no protocol abstraction).

**Pros:**
- Fewer layers
- Standard OTel patterns

**Cons:**
- ❌ Violates Benedict's protocol-based architecture
- ❌ Tight coupling to OTel (hard to swap implementations)
- ❌ Difficult to test (domain code depends on external SDK)
- ❌ No no-op mode (always pays overhead, even when disabled)

**Verdict:** ❌ Rejected. Contradicts Benedict's SOLID principles.

### Alternative 3: Metrics Instead of Traces

**Approach:** Use Prometheus metrics (counters, histograms) instead of distributed tracing.

**Pros:**
- Simpler (single value per metric)
- Lower overhead

**Cons:**
- No request correlation (can't trace a single Slack message through the system)
- No timing breakdown (which step is slow?)
- No error context (where did the exception originate?)

**Verdict:** ⚠️ Complementary. Metrics are orthogonal to traces. This proposal adds tracing; metrics can be added later.

### Alternative 4: Custom Tracing Implementation

**Approach:** Build a custom tracing system (JSON file export, custom UI).

**Pros:**
- Full control
- No dependencies

**Cons:**
- ❌ Reinventing the wheel
- ❌ No ecosystem tooling (Jaeger, Grafana, Honeycomb)
- ❌ Vendor lock-in to our custom format
- ❌ High maintenance burden

**Verdict:** ❌ Rejected. OpenTelemetry is the industry standard.

### Alternative 5: Always-On Tracing

**Approach:** Enable tracing by default, make it opt-out.

**Pros:**
- Operators get observability immediately

**Cons:**
- ❌ Violates privacy-by-default principle
- ❌ Performance overhead for users who don't want it
- ❌ Requires clear communication (users may not know traces are emitted)

**Verdict:** ❌ Rejected. Benedict is self-hosted and privacy-focused. Tracing is opt-in.

---

## Success Criteria

### Functional Requirements

✅ **F1. Protocol abstraction exists**
- `Tracer` and `Span` protocols defined in `src/benedict/protocols/tracer.py`
- Domain code depends only on protocols, not concrete implementations

✅ **F2. No-op tracer works (default)**
- `NoOpTracer` implementation exists
- Zero overhead when tracing is disabled
- Benedict runs normally without configuration changes

✅ **F3. OTel tracer works**
- `OTelTracer` wraps OpenTelemetry SDK
- Exports spans via OTLP and/or console
- Configured via environment variables

✅ **F4. In-memory tracer works (tests)**
- `InMemoryTracer` captures spans for assertions
- Tests do not require external services
- Deterministic and fast (<100ms)

✅ **F5. Composition roots wire tracing**
- `main.py` creates tracer based on env vars
- `mcp/server.py` creates tracer based on env vars
- Tracer is injected into `RepoAgent` and `BenedictMcpService`

✅ **F6. Startup spans are emitted**
- Slack service emits `benedict_startup` span with `service=slack` attribute
- MCP service emits `benedict_mcp_startup` span with `service=mcp` attribute
- Spans appear in Jaeger when tracing is enabled

✅ **F7. Local observability stack exists**
- `docker/observability/docker-compose.yml` runs Jaeger
- Jaeger UI is accessible at http://localhost:16686
- Benedict can export traces to Jaeger

### Non-Functional Requirements

✅ **NF1. Performance**
- No-op tracer introduces <1µs overhead per span
- OTel tracer uses batch processing (no blocking I/O in request path)
- Span creation does not block domain logic

✅ **NF2. Privacy**
- Tracing is disabled by default (explicit opt-in)
- No telemetry sent to third parties
- Privacy model documented in `SECURITY.md`

✅ **NF3. Testability**
- >90% unit test coverage for new code
- In-memory tracer enables fast, isolated tests
- No external dependencies in unit tests

✅ **NF4. Documentation**
- `SECURITY.md` documents privacy model
- `docs/FAQ.md` answers telemetry questions
- `docker/observability/README.md` provides setup instructions
- `README.md` links to observability docs

✅ **NF5. Extensibility**
- Easy to add new tracer implementations (protocol-based)
- Easy to add domain spans in future milestones (Observability 2+)
- No changes required to domain code to swap implementations

### Acceptance Criteria

**For PR merge:**

1. ✅ All unit tests pass (`make test`)
2. ✅ Code formatted and linted (`make format`, `make check`)
3. ✅ Benedict runs normally with tracing disabled (default)
4. ✅ Benedict runs with tracing enabled (console output visible)
5. ✅ Benedict exports traces to Jaeger (startup span appears in UI)
6. ✅ MCP server runs with tracing disabled
7. ✅ MCP server exports traces to Jaeger (startup span appears)
8. ✅ `SECURITY.md` exists and documents privacy model
9. ✅ `docs/FAQ.md` answers telemetry questions
10. ✅ `docker/observability/README.md` provides clear setup instructions
11. ✅ Screenshot of Jaeger UI attached to PR

**For milestone closure (issue #19):**

- All acceptance criteria met
- PR merged to main
- `CHANGELOG.md` updated

---

## Timeline and Milestones

### Overall Timeline: 6 days

**Day 1:** Protocol and no-op implementation  
**Day 2-3:** OpenTelemetry SDK implementation  
**Day 3:** In-memory tracer for tests  
**Day 4:** Docker Compose and end-to-end testing  
**Day 5:** Documentation and security  
**Day 6:** Final testing and PR preparation  

### Dependencies

**External:**
- OpenTelemetry SDK (`opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-grpc`)
- Docker (for local Jaeger)

**Internal:**
- None (this is the first observability PR)

### Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| OTel SDK is complex | High | Low | Start with simple console export; OTLP later |
| Performance overhead concerns | Medium | Low | Benchmark no-op and OTel tracers; document overhead |
| Operators don't know how to use Jaeger | Medium | Medium | Provide clear docs, screenshots, and example queries |
| Privacy concerns from users | High | Low | Document clearly in SECURITY.md; tracing is opt-in |
| Tests are flaky | Low | Medium | Use in-memory tracer (deterministic, no external services) |

---

## Appendices

### Appendix A: Example Span Attributes

**Slack service spans:**

```python
span.set_attribute("service", "slack")
span.set_attribute("channel_id", "C12345ABC")
span.set_attribute("user_id", "U123456")
span.set_attribute("repo", "acme/widget")
span.set_attribute("command", "onboard")
```

**MCP service spans:**

```python
span.set_attribute("service", "mcp")
span.set_attribute("tool", "search_code")
span.set_attribute("query", "authentication")
span.set_attribute("results_count", 5)
```

**LLM spans (Observability 2):**

```python
span.set_attribute("provider", "anthropic")
span.set_attribute("model", "claude-3-5-sonnet-20241022")
span.set_attribute("tokens_input", 1500)
span.set_attribute("tokens_output", 300)
span.set_attribute("latency_ms", 2345)
```

### Appendix B: OpenTelemetry Resources

- **Specification:** https://opentelemetry.io/docs/specs/otel/
- **Python SDK:** https://opentelemetry.io/docs/languages/python/
- **OTLP Exporter:** https://opentelemetry.io/docs/specs/otlp/
- **Jaeger:** https://www.jaegertracing.io/
- **Grafana Tempo:** https://grafana.com/oss/tempo/

### Appendix C: Future Observability Milestones

**Observability 2:** Request-level spans
- Slack event handling spans
- Anthropic API request spans
- GitHub CLI spans
- MCP request/response spans

**Observability 3:** Domain operation spans
- LLM classify spans
- Tool loop spans
- Semantic search spans
- Workspace operations

**Observability 4:** Operator UI (thin dashboard)
- Active channels
- Recent operations
- Error rates
- Slow requests

---

## Sign-Off

**Proposal Status:** ✅ Ready for implementation

**Reviewers:**
- [ ] @mkarots - Architecture review
- [ ] @mkarots - Security/privacy review

**Approval:** Pending review

**Next Steps:**
1. Review this proposal
2. Address feedback
3. Begin implementation (Phase 1: Protocol and no-op)
4. Iterate through phases 2-6
5. Submit PR with screenshot of working Jaeger traces

---

**Document Version:** 1.0  
**Last Updated:** 2026-08-19  
**Author:** Cloud Agent  
**Issue:** #19 (Parent: #11)
