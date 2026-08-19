# Operator UI Design Document

**Issue:** [#22 - Operator UI: thin browser or macOS app](https://github.com/mkarots/benedict/issues/22)  
**Status:** Design Phase  
**Last Updated:** 2026-08-19

## 1. Overview

### What

A lightweight operator console for Benedict that provides visibility into system health and operational state. The UI will show:

- Health status of the Slack bot and MCP server processes
- Recent requests, conversations, and workspace activity
- Links to distributed traces (Jaeger integration)
- System metrics and operational diagnostics

### Why

Currently, operators have no direct visibility into Benedict's runtime state without:
- Tailing log files
- Using `ps` commands to check if processes are running
- Manually correlating Slack activity with system behavior
- Debugging issues without trace context

An operator console provides a single pane of glass for observability and troubleshooting.

### When to Use

- Verifying Benedict services are running correctly
- Investigating performance issues or failures
- Understanding recent activity across channels
- Accessing distributed traces for specific requests
- Monitoring workspace health and usage

### Relationship to Observability Milestones

- **Depends on:** Observability 1 ("is tracing up?") for basic health checks
- **Enhanced by:** Observability 2-3 for deep trace links and detailed telemetry
- **Parent:** Issue #11 (Observability infrastructure)

## 2. Non-Goals

### Out of Scope

- **Not a replacement for Slack chat** - Slack remains the primary user interaction surface
- **Not a full APM product** - We're building a thin console, not competing with Jaeger/Datadog
- **Not a chat interface** - Local chat without Slack is deferred to future work
- **Not multi-tenant** - Designed for local operator use, not hosted SaaS
- **Not real-time streaming** - Polling-based updates are sufficient
- **Not authentication/authorization** - Runs locally, trusts localhost access

### Explicitly Deferred

- **OTel instrumentation** - Covered by Observability 1-3, not this issue
- **macOS native app** - Only if browser-only proves insufficient (PR B)
- **Embedded waterfall view** - Initial version links to Jaeger; embedding is optional
- **Chat interface** - Future enhancement, not in initial PR scope
- **Historical analytics** - Focus on recent activity, not long-term trends

## 3. Key Concepts

| Term | Meaning |
|------|---------|
| **Status API** | HTTP endpoint providing system health and process state |
| **Recent Activity** | Last N requests, conversations, and operations |
| **Trace Link** | Deep link to Jaeger UI for a specific trace ID |
| **Health Check** | Probe determining if a process is up and responding |
| **Operator Console** | Browser-based UI for system visibility |
| **Process Monitor** | Component checking if Slack bot and MCP server are alive |

## 4. High-Level Design

### Architecture

```
┌─────────────────────────────────────────┐
│     Browser (Operator Console)          │
│  ┌─────────────────────────────────┐   │
│  │  Status Page                     │   │
│  │  - Process Health               │   │
│  │  - Recent Requests              │   │
│  │  - Workspaces                   │   │
│  │  - Trace Links                  │   │
│  └─────────────────────────────────┘   │
└──────────────┬──────────────────────────┘
               │ HTTP GET /api/status
               │ HTTP GET /api/recent
               │ HTTP GET /api/workspaces
               ▼
┌─────────────────────────────────────────┐
│   Status API Server (new component)     │
│  ┌─────────────────────────────────┐   │
│  │  HTTP Handlers                   │   │
│  │  - GET /api/health              │   │
│  │  - GET /api/status              │   │
│  │  - GET /api/recent              │   │
│  │  - GET /api/workspaces          │   │
│  │  - GET / (static UI)            │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │  Status Monitor                  │   │
│  │  - Process Health Checker       │   │
│  │  - Activity Reader              │   │
│  │  - Workspace Inspector          │   │
│  └─────────────────────────────────┘   │
└──────────────┬──────────────────────────┘
               │ Read state.json
               │ Check process health
               │ Read action logs
               ▼
┌─────────────────────────────────────────┐
│   Existing Benedict Components          │
│  - state.json (channel mappings)        │
│  - Workspaces (action logs)             │
│  - Slack bot process                    │
│  - MCP server process                   │
└─────────────────────────────────────────┘
```

### Component Responsibilities

#### Status API Server (`src/benedict/operator_ui/api_server.py`)

- Serves HTTP status API on configurable port (default: 8765)
- Provides health, status, recent activity, and workspace endpoints
- Serves static HTML/CSS/JS for the browser UI
- Read-only access to Benedict state and logs

#### Status Monitor (`src/benedict/operator_ui/status_monitor.py`)

- Checks if Slack bot and MCP server processes are running
- Reads `state.json` for channel mappings and recent conversations
- Scans workspace directories for recent actions
- Aggregates data for API responses

#### Browser UI (`src/benedict/operator_ui/static/`)

- Single-page HTML application
- Auto-refreshing status display (every 5-10 seconds)
- Tables for recent requests, conversations, workspaces
- Click-through links to Jaeger traces

### Data Flow

#### Health Check Flow

1. Browser polls `GET /api/health` every 10 seconds
2. Status Monitor checks:
   - Is Slack bot process alive? (PID check or HTTP ping)
   - Is MCP server process alive? (PID check or stdio probe)
   - Is ChromaDB accessible?
   - Is state.json readable?
3. API returns JSON: `{ "slack_bot": "up", "mcp_server": "up", "chroma_db": "up", "state_file": "ok" }`

#### Recent Activity Flow

1. Browser requests `GET /api/recent?limit=50`
2. Status Monitor:
   - Reads recent conversations from `state.json`
   - Scans workspace action logs
   - Extracts trace IDs from logs (if OTel enabled)
3. API returns JSON array of recent activities with trace links

#### Workspace Inspection Flow

1. Browser requests `GET /api/workspaces`
2. Status Monitor:
   - Scans `BENEDICT_WORKSPACES_DIR`
   - Reads channel mappings from `state.json`
   - Checks workspace size and last activity time
3. API returns JSON array of workspace summaries

## 5. API Design

### Endpoints

#### `GET /api/health`

**Description:** Quick health check for all Benedict components.

**Response:**
```json
{
  "status": "healthy" | "degraded" | "down",
  "timestamp": "2026-08-19T11:44:00Z",
  "components": {
    "slack_bot": {
      "status": "up" | "down",
      "pid": 12345,
      "uptime_seconds": 3600
    },
    "mcp_server": {
      "status": "up" | "down",
      "pid": 12346,
      "uptime_seconds": 3600
    },
    "chroma_db": {
      "status": "accessible" | "unavailable",
      "path": "/workspace/.chroma_db"
    },
    "state_file": {
      "status": "ok" | "error",
      "path": "/workspace/state.json",
      "last_modified": "2026-08-19T11:30:00Z"
    }
  }
}
```

#### `GET /api/status`

**Description:** Detailed system status and configuration.

**Response:**
```json
{
  "version": "0.5.2",
  "data_dir": "/workspace",
  "workspaces_dir": "/workspace/workspaces",
  "channels_onboarded": 3,
  "active_conversations": 12,
  "indexed_repositories": 3,
  "uptime": {
    "slack_bot": "1h 30m",
    "mcp_server": "1h 25m"
  },
  "configuration": {
    "anthropic_model": "claude-3-5-sonnet-20241022",
    "workspace_copy_mode": "symlink",
    "chunk_size": 2000
  }
}
```

#### `GET /api/recent?limit=50`

**Description:** Recent requests, conversations, and operations.

**Query Parameters:**
- `limit` (optional, default: 50) - Number of recent items to return

**Response:**
```json
{
  "requests": [
    {
      "timestamp": "2026-08-19T11:40:00Z",
      "type": "slack_mention",
      "channel_id": "C12345ABC",
      "channel_name": "eng-backend",
      "user": "U123456",
      "query": "What files handle authentication?",
      "trace_id": "a1b2c3d4e5f6...",
      "trace_url": "http://localhost:16686/trace/a1b2c3d4e5f6...",
      "duration_ms": 2345,
      "status": "success" | "error"
    }
  ],
  "conversations": [
    {
      "thread_ts": "1692451200.123456",
      "channel_id": "C12345ABC",
      "started_at": "2026-08-19T10:00:00Z",
      "last_activity": "2026-08-19T11:35:00Z",
      "message_count": 8,
      "participants": ["U123456", "U789012"]
    }
  ]
}
```

#### `GET /api/workspaces`

**Description:** Status of all onboarded workspaces.

**Response:**
```json
{
  "workspaces": [
    {
      "channel_id": "C12345ABC",
      "channel_name": "eng-backend",
      "repository": "acme/backend",
      "onboarded_at": "2026-08-15T14:30:00Z",
      "onboarded_by": "U123456",
      "last_activity": "2026-08-19T11:35:00Z",
      "workspace_path": "/workspace/workspaces/C12345ABC",
      "workspace_size_mb": 145,
      "indexed": true,
      "index_last_updated": "2026-08-19T09:00:00Z"
    }
  ]
}
```

#### `GET /`

**Description:** Serves the browser-based operator console UI (static HTML).

## 6. UI Design

### Layout

```
┌────────────────────────────────────────────────────────────────┐
│  Benedict Operator Console                    ⟳ Last: 11:44:00 │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  System Health                                                  │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  ● Slack Bot        UP    (PID 12345, 1h 30m uptime)     │ │
│  │  ● MCP Server       UP    (PID 12346, 1h 25m uptime)     │ │
│  │  ● ChromaDB         OK    (/workspace/.chroma_db)        │ │
│  │  ● State File       OK    (last modified 11:30:00)       │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Recent Requests (last 50)                                      │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ Time     Channel      User    Query             Trace    │ │
│  ├──────────────────────────────────────────────────────────┤ │
│  │ 11:40:00 eng-backend  @alice  What files...    [view]    │ │
│  │ 11:35:12 eng-frontend @bob    Where is the...  [view]    │ │
│  │ ...                                                       │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Onboarded Workspaces                                           │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ Channel      Repository    Indexed  Last Activity        │ │
│  ├──────────────────────────────────────────────────────────┤ │
│  │ eng-backend  acme/backend  ✓        11:35:00            │ │
│  │ eng-frontend acme/frontend ✓        11:20:00            │ │
│  │ ...                                                       │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### Visual Design Principles

- **Minimal and functional** - Plain HTML/CSS, no heavy frameworks
- **Auto-refreshing** - Poll APIs every 10 seconds
- **Color-coded status** - Green (up), Yellow (degraded), Red (down)
- **Click-through traces** - Links open Jaeger in new tab
- **Responsive** - Works on desktop browsers (mobile not prioritized)

## 7. Implementation Details

### File Structure

```
src/benedict/operator_ui/
  __init__.py                 # Package exports
  api_server.py               # HTTP server and request handlers
  status_monitor.py           # System health and activity monitoring
  models.py                   # Data models for API responses
  static/
    index.html                # Browser UI
    style.css                 # Minimal CSS
    app.js                    # Auto-refresh logic
```

### Dependencies

**New dependencies:**
- `aiohttp` or `fastapi` - Lightweight HTTP server
- `uvicorn` - ASGI server (if using FastAPI)

**Existing dependencies used:**
- `psutil` - Process monitoring (PID checks, uptime)
- Standard library `json` - Read state.json
- Standard library `pathlib` - Workspace scanning

### Configuration

**New environment variables:**

```bash
BENEDICT_OPERATOR_UI_ENABLED=true          # Enable operator UI (default: false)
BENEDICT_OPERATOR_UI_PORT=8765            # HTTP port (default: 8765)
BENEDICT_OPERATOR_UI_HOST=127.0.0.1       # Bind address (default: localhost)
BENEDICT_JAEGER_URL=http://localhost:16686 # Jaeger UI base URL
```

### Process Architecture Options

#### Option A: Same Process as Slack Bot (Recommended for PR A)

**Pros:**
- Simpler deployment (one process to manage)
- Direct access to in-memory state
- No inter-process communication needed
- Easier to start/stop

**Cons:**
- Adds HTTP server to Slack bot process
- Slight overhead on bot event loop
- Couples operator UI lifecycle to Slack bot

**Implementation:**
- Start HTTP server in `main.py` alongside Slack bot
- Run in background thread or async task

#### Option B: Separate Sidecar Process

**Pros:**
- Clean separation of concerns
- Operator UI can run even if Slack bot restarts
- No impact on bot performance
- Can be disabled without changing bot

**Cons:**
- More complex deployment (two processes)
- Requires reading files to get state (no in-memory access)
- Need process coordination

**Implementation:**
- New entry point: `benedict-operator-ui` command
- Reads `state.json` and workspace files
- Checks bot/MCP PIDs via psutil

**Decision for PR A:** Start with **Option A** (same process) for simplicity. Can refactor to Option B later if performance concerns emerge.

### StatusMonitor Implementation

```python
# src/benedict/operator_ui/status_monitor.py

import psutil
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from benedict.models.conversation import ConversationManager
from benedict.workspace.workspace_manager import WorkspaceManager

class StatusMonitor:
    """Monitors Benedict system health and activity."""
    
    def __init__(
        self,
        data_dir: Path,
        conversation_manager: Optional[ConversationManager] = None,
        workspace_manager: Optional[WorkspaceManager] = None,
    ):
        self.data_dir = data_dir
        self.state_file = data_dir / "state.json"
        self.workspaces_dir = data_dir / "workspaces"
        self.conversation_manager = conversation_manager
        self.workspace_manager = workspace_manager
        
    def check_health(self) -> Dict[str, any]:
        """Check health of all Benedict components."""
        return {
            "status": self._aggregate_status(),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "components": {
                "slack_bot": self._check_slack_bot(),
                "mcp_server": self._check_mcp_server(),
                "chroma_db": self._check_chroma_db(),
                "state_file": self._check_state_file(),
            }
        }
    
    def get_recent_activity(self, limit: int = 50) -> Dict[str, List]:
        """Get recent requests and conversations."""
        return {
            "requests": self._get_recent_requests(limit),
            "conversations": self._get_recent_conversations(limit),
        }
    
    def get_workspaces(self) -> Dict[str, List]:
        """Get status of all onboarded workspaces."""
        return {
            "workspaces": self._scan_workspaces()
        }
    
    def _check_slack_bot(self) -> Dict[str, any]:
        """Check if Slack bot process is running."""
        # Implementation: Check for process with 'benedict' or specific PID
        pass
    
    def _check_mcp_server(self) -> Dict[str, any]:
        """Check if MCP server process is running."""
        # Implementation: Check for 'benedict-mcp' process
        pass
    
    def _check_chroma_db(self) -> Dict[str, any]:
        """Check if ChromaDB is accessible."""
        # Implementation: Try to list collections
        pass
    
    def _check_state_file(self) -> Dict[str, any]:
        """Check if state.json is readable."""
        # Implementation: Try to read and parse state.json
        pass
    
    def _get_recent_requests(self, limit: int) -> List[Dict]:
        """Extract recent requests from action logs."""
        # Implementation: Scan workspace action logs
        pass
    
    def _get_recent_conversations(self, limit: int) -> List[Dict]:
        """Get recent conversation threads from state."""
        # Implementation: Read from conversation_manager or state.json
        pass
    
    def _scan_workspaces(self) -> List[Dict]:
        """Scan all workspace directories for status."""
        # Implementation: Iterate workspaces_dir, check sizes, activity
        pass
    
    def _aggregate_status(self) -> str:
        """Aggregate component health into overall status."""
        # Return "healthy", "degraded", or "down"
        pass
```

### API Server Implementation

```python
# src/benedict/operator_ui/api_server.py

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pathlib import Path
from .status_monitor import StatusMonitor

app = FastAPI(title="Benedict Operator UI")
status_monitor: StatusMonitor = None

def init_api_server(monitor: StatusMonitor):
    """Initialize API server with StatusMonitor."""
    global status_monitor
    status_monitor = monitor

@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return status_monitor.check_health()

@app.get("/api/status")
async def status():
    """Detailed system status."""
    return status_monitor.get_detailed_status()

@app.get("/api/recent")
async def recent(limit: int = 50):
    """Recent activity."""
    return status_monitor.get_recent_activity(limit)

@app.get("/api/workspaces")
async def workspaces():
    """Workspace status."""
    return status_monitor.get_workspaces()

@app.get("/")
async def index():
    """Serve operator console UI."""
    static_dir = Path(__file__).parent / "static"
    return FileResponse(static_dir / "index.html")
```

### Integration with main.py

```python
# src/benedict/main.py

from benedict.operator_ui.api_server import init_api_server, app
from benedict.operator_ui.status_monitor import StatusMonitor
import uvicorn
import threading

def main():
    # ... existing setup ...
    
    # Initialize StatusMonitor
    status_monitor = StatusMonitor(
        data_dir=data_dir,
        conversation_manager=conversation_manager,
        workspace_manager=workspace_manager,
    )
    
    # Start Operator UI if enabled
    operator_ui_enabled = os.getenv("BENEDICT_OPERATOR_UI_ENABLED", "false").lower() == "true"
    if operator_ui_enabled:
        init_api_server(status_monitor)
        port = int(os.getenv("BENEDICT_OPERATOR_UI_PORT", "8765"))
        host = os.getenv("BENEDICT_OPERATOR_UI_HOST", "127.0.0.1")
        
        # Run HTTP server in background thread
        ui_thread = threading.Thread(
            target=uvicorn.run,
            kwargs={"app": app, "host": host, "port": port, "log_level": "warning"},
            daemon=True
        )
        ui_thread.start()
        logger.info(f"Operator UI available at http://{host}:{port}")
    
    # ... start Slack bot as usual ...
```

## 8. Testing Strategy

### Unit Tests

**Test Coverage Requirements (per user rules):**

#### `StatusMonitor` Tests

```python
# tests/unit/operator_ui/test_status_monitor.py

class TestStatusMonitor:
    def test_check_health_all_components_up(self):
        """Happy path: all components healthy."""
        pass
    
    def test_check_health_slack_bot_down(self):
        """Edge case: Slack bot process not found."""
        pass
    
    def test_check_health_state_file_missing(self):
        """Error handling: state.json doesn't exist."""
        pass
    
    def test_get_recent_activity_empty(self):
        """Edge case: no recent activity."""
        pass
    
    def test_get_recent_activity_with_limit(self):
        """Happy path: return limited results."""
        pass
    
    def test_get_workspaces_multiple_channels(self):
        """Happy path: multiple onboarded workspaces."""
        pass
    
    def test_scan_workspaces_corrupted_state(self):
        """Error handling: malformed state.json."""
        pass
```

#### API Endpoint Tests

```python
# tests/unit/operator_ui/test_api_server.py

from fastapi.testclient import TestClient

class TestOperatorUIAPI:
    def test_health_endpoint_returns_json(self):
        """Happy path: /api/health returns valid JSON."""
        pass
    
    def test_recent_endpoint_with_custom_limit(self):
        """Happy path: /api/recent?limit=10."""
        pass
    
    def test_workspaces_endpoint_no_workspaces(self):
        """Edge case: no workspaces onboarded."""
        pass
    
    def test_index_serves_html(self):
        """Happy path: GET / returns HTML."""
        pass
```

### Integration Tests

```python
# tests/integration/test_operator_ui_integration.py

class TestOperatorUIIntegration:
    def test_end_to_end_health_check(self):
        """Start API server, check health via HTTP."""
        pass
    
    def test_workspace_scanning_with_real_state(self):
        """Scan actual workspace directories."""
        pass
```

### Manual Testing Checklist

- [ ] Start Benedict with `BENEDICT_OPERATOR_UI_ENABLED=true`
- [ ] Open `http://localhost:8765` in browser
- [ ] Verify health indicators show green
- [ ] Trigger a Slack mention
- [ ] Confirm new request appears in "Recent Requests"
- [ ] Click trace link (if OTel configured) → opens Jaeger
- [ ] Stop Slack bot → health indicator turns red
- [ ] Restart Slack bot → health indicator returns to green

## 9. Open Questions & Decisions

### Questions to Resolve in PR A

#### Q1: Same process vs separate sidecar?

**Options:**
- A: Run HTTP server in same process as Slack bot (background thread)
- B: Separate `benedict-operator-ui` process

**Recommendation:** Option A for PR A (simpler). Can refactor to B later if needed.

**Decision:** ✅ Option A (same process) for initial implementation.

---

#### Q2: Browser-only or build macOS app in PR A?

**Options:**
- A: Browser-only (open `http://localhost:8765`)
- B: Also build macOS menu bar app / Tauri wrapper

**Recommendation:** Option A for PR A. Evaluate in PR B if browser feels insufficient.

**Decision:** ✅ Option A (browser-only). PR B will add macOS wrapper if needed.

---

#### Q3: Link to Jaeger or embed waterfall?

**Options:**
- A: Simple links to Jaeger UI (external)
- B: Embed trace waterfall in Benedict UI

**Recommendation:** Option A for PR A. Embedding requires trace parsing and rendering.

**Decision:** ✅ Option A (link to Jaeger). Waterfall embedding is optional future work.

---

#### Q4: How to check if processes are running?

**Options:**
- A: PID tracking (write PID files on start, check with psutil)
- B: HTTP health endpoint (Slack bot exposes `/health`)
- C: Process name matching (search for 'benedict' in process list)

**Recommendation:** Option A for robustness. Option B requires adding health endpoint to bot.

**Decision:** ✅ Option A (PID tracking) with fallback to process name matching.

---

#### Q5: Real-time updates or polling?

**Options:**
- A: Polling (browser refreshes every 10 seconds)
- B: WebSocket / Server-Sent Events for real-time

**Recommendation:** Option A for simplicity. Real-time is not critical for operator console.

**Decision:** ✅ Option A (polling). 10-second refresh interval.

---

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| HTTP server slows Slack bot | Medium | Run in background thread; profile performance |
| State file locked during writes | Low | Use read-only file access; retry on lock |
| Traces not available (OTel not configured) | Low | Gracefully handle missing trace IDs; show N/A |
| Process checks fail on non-Linux systems | Medium | Use psutil cross-platform APIs |
| Browser auto-refresh causes flicker | Low | Use JS to update DOM elements instead of full reload |

## 10. Implementation Plan

### PR A: Core Operator UI (This Issue)

**Goal:** Minimal browser UI with health checks and recent activity.

**Tasks:**

1. **StatusMonitor Implementation** (1 day)
   - Create `src/benedict/operator_ui/status_monitor.py`
   - Implement health checking for Slack bot, MCP, ChromaDB, state file
   - Implement recent activity scanning (action logs, conversations)
   - Implement workspace scanning
   - Write unit tests (8+ test cases)

2. **API Server Implementation** (1 day)
   - Create `src/benedict/operator_ui/api_server.py`
   - Implement HTTP endpoints: `/api/health`, `/api/status`, `/api/recent`, `/api/workspaces`, `/`
   - Add FastAPI/aiohttp dependency
   - Write API endpoint tests (5+ test cases)

3. **Browser UI Implementation** (1 day)
   - Create `src/benedict/operator_ui/static/index.html`
   - Create `src/benedict/operator_ui/static/style.css`
   - Create `src/benedict/operator_ui/static/app.js`
   - Implement auto-refreshing (10-second poll)
   - Style with minimal CSS (no frameworks)

4. **Integration with main.py** (0.5 days)
   - Add environment variable checks
   - Start HTTP server in background thread
   - Pass StatusMonitor dependencies
   - Update logging

5. **Documentation** (0.5 days)
   - Update README with operator UI instructions
   - Document environment variables
   - Add troubleshooting section
   - Update CHANGELOG

6. **Testing & Polish** (1 day)
   - Manual testing checklist
   - Integration tests
   - Cross-browser testing (Chrome, Firefox, Safari)
   - Performance profiling (ensure no bot slowdown)

**Total Estimate:** 5 days

**Done When:**
- ✅ Operator can open `http://localhost:8765`
- ✅ UI shows Slack bot and MCP server health (up/down)
- ✅ UI shows recent requests (last 50) with channel, user, query
- ✅ UI shows onboarded workspaces with last activity
- ✅ Clicking trace link opens Jaeger (if trace ID available)
- ✅ All unit tests pass
- ✅ No performance degradation on Slack bot
- ✅ Documentation updated

### PR B: macOS Native App (Future, If Needed)

**Goal:** Optional native macOS menu bar app for operator console.

**Trigger:** Only if browser-only UI proves insufficient after dogfooding PR A.

**Tasks:**
- Evaluate Tauri, Electron, or native Swift
- Wrap existing HTTP API with native UI
- Add menu bar icon with status indicator
- Package as `.app` bundle

**Decision Point:** Defer until PR A is shipped and evaluated in production.

## 11. Acceptance Criteria

### Functional Requirements

- [ ] Operator can open browser UI at configured port (default: `http://localhost:8765`)
- [ ] UI displays health status for: Slack bot, MCP server, ChromaDB, state file
- [ ] UI displays recent requests with: timestamp, channel, user, query summary
- [ ] UI displays onboarded workspaces with: channel, repository, last activity
- [ ] UI provides links to Jaeger traces (when trace IDs available)
- [ ] UI auto-refreshes every 10 seconds
- [ ] API responds within 500ms for all endpoints
- [ ] Operator UI can be disabled via environment variable

### Non-Functional Requirements

- [ ] No measurable performance impact on Slack bot (<5% CPU overhead)
- [ ] UI works in Chrome, Firefox, Safari (latest versions)
- [ ] API gracefully handles missing/corrupted state files
- [ ] Component health checks complete within 2 seconds
- [ ] UI displays meaningful error messages when components are down

### Testing Requirements (per User Rules)

- [ ] Unit tests for StatusMonitor (8+ tests, >80% coverage)
- [ ] Unit tests for API endpoints (5+ tests, >80% coverage)
- [ ] Integration test for end-to-end health check
- [ ] Manual testing checklist completed
- [ ] All tests pass in CI

### Documentation Requirements

- [ ] README updated with operator UI setup instructions
- [ ] Environment variables documented
- [ ] Troubleshooting guide for common issues
- [ ] CHANGELOG entry added
- [ ] Design document (this file) reviewed and approved

## 12. Future Enhancements (Post-PR A)

### Chat Interface

**Description:** Allow operators to chat with Benedict directly in the UI (no Slack required).

**Why:** Useful for local testing and debugging without Slack dependency.

**Scope:** Deferred to separate issue/milestone.

---

### Embedded Trace Waterfall

**Description:** Render distributed traces inline instead of linking to Jaeger.

**Why:** Reduces context switching; better integrated experience.

**Scope:** Requires trace parsing and D3.js/similar. Evaluate after PR A.

---

### Historical Analytics

**Description:** Charts and trends over time (request volume, error rates, workspace growth).

**Why:** Helps identify patterns and capacity planning.

**Scope:** Requires time-series storage. Not in initial scope.

---

### Alerts and Notifications

**Description:** Desktop notifications when components go down or errors spike.

**Why:** Proactive alerting for operators.

**Scope:** Requires notification system. Evaluate after macOS app (PR B).

---

### Multi-Instance Support

**Description:** Monitor multiple Benedict instances from one console.

**Why:** Useful for multi-env deployments (dev, staging, prod).

**Scope:** Requires instance registry and aggregation. Future work.

## 13. References

- **Parent Issue:** [#11 - Observability Infrastructure](https://github.com/mkarots/benedict/issues/11)
- **Dependencies:** Observability 1 (tracing health check)
- **Related Docs:**
  - [ARCHITECTURE.md](./ARCHITECTURE.md) - Current system architecture
  - [README.md](../README.md) - Project overview and setup
  - [CHANGELOG.md](../CHANGELOG.md) - Version history

## 14. Revision History

| Date       | Author   | Changes                        |
|------------|----------|--------------------------------|
| 2026-08-19 | @mkarots | Initial design document        |
