# Metadata Location Design Document

**Issue:** [#12](https://github.com/mkarots/benedict/issues/12) - Stop writing `.metadata.benedict` into the user's project tree

**Status:** Design  
**Author:** Cloud Agent  
**Created:** 2026-08-19  
**Last Updated:** 2026-08-19

---

## Executive Summary

Benedict currently writes `.metadata.benedict` files directly into the user's repository tree, polluting their git working directory with untracked files. This design proposes moving generated metadata to a sidecar overlay structure that keeps Benedict's internal files separate from the user's source code while maintaining full backward compatibility with existing functionality.

**Recommended Solution:** **Option A - Workspace Sidecar** with automatic migration of existing in-tree metadata files.

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Current State Analysis](#current-state-analysis)
3. [Requirements](#requirements)
4. [Solution Options](#solution-options)
5. [Recommended Solution](#recommended-solution)
6. [Implementation Plan](#implementation-plan)
7. [Migration Strategy](#migration-strategy)
8. [Testing Strategy](#testing-strategy)
9. [Open Questions & Decisions](#open-questions--decisions)
10. [Appendix](#appendix)

---

## Problem Statement

### The Issue

When users onboard a repository with the default symlink workspace mode (`BENEDICT_WORKSPACE_COPY_MODE=symlink`), Benedict generates `.metadata.benedict` files in every directory during indexing. Since the workspace uses symlinks, these writes go directly into the user's actual repository clone, creating untracked files that:

1. Show up in `git status` as untracked
2. Require manual `.gitignore` entries
3. May accidentally get committed
4. Create friction in the onboarding experience
5. Violate user expectations about tool cleanliness

### Why This Matters

- **User Experience:** Users expect development tools to be non-invasive
- **Git Hygiene:** Generated files should not pollute version control
- **Professionalism:** Benedict should follow best practices for tool design
- **Scale:** This affects every directory in every onboarded repository

### Non-Issues

The following are **intentional** and not part of this design:

- `.benedict.method.yaml` files (these are deliberate project artifacts)
- User-created metadata files (if users want to commit metadata)
- Copy mode (`BENEDICT_WORKSPACE_COPY_MODE=copy`) already contains writes

---

## Current State Analysis

### Write Paths

#### Primary Writer: `MetadataGenerator.write_metadata()`

**Location:** `src/benedict/metadata/metadata_generator.py:80-105`

```python
def write_metadata(self, directory: Path, metadata: Dict[str, Any]) -> None:
    """Write .metadata.benedict file to directory."""
    directory = Path(directory)
    metadata_file = directory / ".metadata.benedict"  # HARDCODED IN-TREE
    
    if metadata_file.exists() and metadata_file.is_dir():
        logger.debug(f".metadata.benedict path exists as directory, skipping")
        return
    
    try:
        with open(metadata_file, "w", encoding="utf-8") as f:
            yaml.dump(metadata, f, default_flow_style=False, allow_unicode=True)
        logger.debug(f"Wrote .metadata.benedict to {metadata_file}")
    except Exception as e:
        logger.error(f"Error writing .metadata.benedict: {e}")
        raise
```

**Call Sites:**

| Component | Location | Trigger | What It Writes |
|-----------|----------|---------|----------------|
| `RepoAgent` (onboard) | `src/benedict/agent.py:329-334` | User runs `@agent onboard repo <repo>` | Root `.metadata.benedict` for workspace/repo |
| `SemanticIndexerChromaDB` | `src/benedict/semantic_indexer/semantic_indexer_chromadb.py:823-914` | Index or update index | Recursive `.metadata.benedict` for all non-skipped directories |

**Key Insight:** There is exactly **one** hardcoded write location. All metadata generation flows through `MetadataGenerator.write_metadata()`.

### Read Paths

#### Primary Reader: `MetadataReader.read_metadata()`

**Location:** `src/benedict/metadata/metadata_reader.py:94-127`

```python
def read_metadata(self, directory: Path) -> Optional[Dict[str, Any]]:
    """Read metadata from directory."""
    directory = Path(directory)
    
    # Check for env var or explicit metadata file path
    if self.metadata_file_path:
        metadata_file = Path(self.metadata_file_path)
        if not metadata_file.is_absolute():
            metadata_file = directory / metadata_file
    else:
        metadata_file = directory / ".metadata.benedict"  # DEFAULT IN-TREE
    
    if not metadata_file.exists():
        return None
    
    try:
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = yaml.safe_load(f)
        logger.debug(f"Read .metadata.benedict from {metadata_file}")
        return metadata
    except Exception as e:
        logger.warning(f"Error reading metadata file: {e}")
        return None
```

**Key Insight:** Reader already supports `BENEDICT_METADATA_FILE` env var override, but:
- It only works for a **single file**, not a directory tree
- The writer **ignores** this env var
- The override is relative to the query directory, not a global root

#### Additional Readers

1. **Semantic Indexer** (`semantic_indexer_chromadb.py:743-821`)
   - Walks parent directories looking for `.metadata.benedict`
   - Used to enhance file embeddings with metadata context

2. **MCP Service** (`mcp/service.py:75-96`)
   - Reads root metadata for `get_repository_summary`
   - Expects metadata at `project.repo_path / ".metadata.benedict"`

3. **Metadata Tools** (`commands/metadata_tools.py`)
   - `GetFileMetadataTool`, `ListKeyFilesTool`, `GetRepositorySummaryTool`
   - Read-only operations via `MetadataReader`

4. **Search Functionality** (`metadata_reader.py:149-218`)
   - `MetadataReader.search_metadata()` uses `rglob(".metadata.benedict")`
   - Scoped by repo to prevent context leakage

### Workspace System

**Location:** `src/benedict/workspace/workspace_manager.py:74-130`

```python
def add_resource(self, context_id: str, resource_type: str, 
                 source_path: str, name: str, content_type: Optional[str] = None) -> str:
    """Add resource to workspace (symlink or copy)."""
    workspace_path = self.get_workspace_path(context_id)
    target_path = workspace_path / name
    source = Path(source_path).resolve()
    
    # Create symlink or copy based on copy_mode
    if self.copy_mode == "symlink":
        target_path.symlink_to(source)  # DEFAULT - WRITES THROUGH TO SOURCE
    else:
        shutil.copytree(source, target_path)  # COPY MODE - CONTAINED
```

**Key Insight:** Default `symlink` mode causes writes through `workspace_path/repo` to modify the user's actual repository.

### Configuration

Current environment variables:

```bash
BENEDICT_DATA_DIR          # Base data directory (default: repo root)
BENEDICT_WORKSPACES_DIR    # Workspaces directory (default: {data_dir}/workspaces)
BENEDICT_WORKSPACE_COPY_MODE  # "symlink" (default) or "copy"
BENEDICT_CHROMA_DB_DIR     # ChromaDB directory (default: {data_dir}/.chroma_db)
BENEDICT_METADATA_FILE     # Single metadata file override (NOT USED BY WRITER)
```

---

## Requirements

### Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR1 | Metadata files MUST NOT appear in user's git working tree by default | **CRITICAL** |
| FR2 | All existing read paths (MCP, semantic indexer, tools) MUST continue to work | **CRITICAL** |
| FR3 | Metadata MUST be associated with the correct directory in the repo tree | **CRITICAL** |
| FR4 | Solution MUST support incremental index updates | **HIGH** |
| FR5 | Solution MUST work with both symlink and copy workspace modes | **HIGH** |
| FR6 | Existing onboarded repositories MUST migrate automatically or with clear guidance | **HIGH** |
| FR7 | Users SHOULD be able to opt into in-tree metadata (future enhancement) | **MEDIUM** |
| FR8 | System SHOULD clean up existing in-tree `.metadata.benedict` files | **MEDIUM** |

### Non-Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR1 | Solution MUST NOT require changes to 20+ call sites | **HIGH** |
| NFR2 | Solution SHOULD minimize breaking changes to public APIs | **HIGH** |
| NFR3 | Implementation MUST follow SOLID principles | **HIGH** |
| NFR4 | Solution SHOULD be testable via unit tests | **HIGH** |
| NFR5 | Migration SHOULD be automatic and transparent | **MEDIUM** |

---

## Solution Options

### Option A: Workspace Sidecar ⭐ **RECOMMENDED**

**Concept:** Store metadata in a parallel tree structure within the workspace, separate from the repository symlink.

```
workspaces/
  C123ABC456/                    # Slack channel_id workspace
    repo-name/                   # Symlink to user's actual repo
    .benedict/                   # NEW: Benedict internal files
      metadata/                  # NEW: Metadata overlay tree
        .metadata.benedict       # Root metadata
        src/
          .metadata.benedict     # Directory metadata
          commands/
            .metadata.benedict   # Nested directory metadata
    workspace_log.json           # Existing action log
```

**Pros:**
- ✅ **Keeps metadata next to the workspace** (logical proximity)
- ✅ **Clean separation** from user's source tree
- ✅ **Simple path mapping**: `workspace/repo/src/foo` → `workspace/.benedict/metadata/src/foo/.metadata.benedict`
- ✅ **Survives across sessions** (persisted with workspace)
- ✅ **Natural cleanup**: Deleting workspace removes metadata
- ✅ **Supports multi-repo workspaces** (each repo's metadata is separate)

**Cons:**
- ⚠️ Metadata lost if workspace is deleted (can be regenerated)
- ⚠️ Requires path translation logic in readers

**Implementation Complexity:** **MEDIUM**

### Option B: Data Directory Store

**Concept:** Store metadata under `BENEDICT_DATA_DIR` with repo-specific subdirectories.

```
{BENEDICT_DATA_DIR}/
  .chroma_db/                    # Existing ChromaDB data
  metadata/                      # NEW: Metadata store
    {repo_hash_1}/               # Keyed by stable repo identifier
      .metadata.benedict         # Root
      src/
        .metadata.benedict
    {repo_hash_2}/
      .metadata.benedict
  workspaces/                    # Existing workspaces
  state.json                     # Existing state
```

**Pros:**
- ✅ **Survives workspace recreation** (persistent across sessions)
- ✅ **Centralized storage** (easier backup)
- ✅ **Works with transient workspaces**

**Cons:**
- ⚠️ **Requires stable repo key** (what if repo path changes?)
- ⚠️ **More complex path mapping** (need to know which workspace → which metadata tree)
- ⚠️ **Orphan risk** (metadata persists even after offboarding)
- ⚠️ **Harder to debug** (metadata divorced from workspace context)

**Implementation Complexity:** **HIGH**

### Option C: Auto-Gitignore (Rejected)

**Concept:** Keep in-tree metadata but automatically append `.metadata.benedict` to `.gitignore`.

**Why Rejected:**
- ❌ Still pollutes user's working tree
- ❌ Mutates user-owned files without explicit consent
- ❌ Doesn't help if files already committed
- ❌ Poor user experience (files still appear until ignored)
- ❌ Not a real fix, just a workaround

### Option D: Copy Mode Only (Rejected)

**Concept:** Require users to use `BENEDICT_WORKSPACE_COPY_MODE=copy`.

**Why Rejected:**
- ❌ Expensive (full repository copy)
- ❌ Poor default behavior
- ❌ Easy to forget
- ❌ Doesn't fix symlink mode (the default)
- ❌ Wastes disk space

---

## Recommended Solution

**Selected Option:** **A - Workspace Sidecar**

### Architecture

#### Directory Structure

```
workspaces/
  {channel_id}/
    {repo}/                           # Symlink to user's repository
    .benedict/                        # NEW: Hidden directory for Benedict internals
      metadata/                       # NEW: Metadata overlay directory
        .metadata.benedict            # Root metadata (for repo itself)
        src/                          # Mirrors repository structure
          .metadata.benedict          # Metadata for src/ directory
          benedict/
            .metadata.benedict        # Metadata for src/benedict/
            metadata/
              .metadata.benedict      # Metadata for src/benedict/metadata/
    workspace_log.json                # Existing action log (unchanged)
```

**Key Design Principles:**
1. **Mirror Structure:** Metadata tree mirrors repository structure exactly
2. **Hidden Directory:** `.benedict/` is hidden to reduce clutter
3. **Future Extensibility:** `.benedict/` can hold other internal files (cache, temp files, etc.)
4. **Logical Grouping:** All Benedict-generated files in one place

#### Path Translation

**Core Algorithm:**

```python
def get_metadata_path(repo_dir: Path, workspace_root: Path) -> Path:
    """
    Translate a repository directory path to its metadata overlay path.
    
    Args:
        repo_dir: Path to directory within repository (e.g., workspace/repo/src/foo)
        workspace_root: Path to workspace root (e.g., workspace)
    
    Returns:
        Path to metadata file (e.g., workspace/.benedict/metadata/src/foo/.metadata.benedict)
    """
    # Get relative path from workspace root
    rel_path = repo_dir.relative_to(workspace_root)
    
    # Remove the repo name from the beginning
    path_parts = rel_path.parts
    if len(path_parts) > 0:
        # path_parts[0] is the repo name, path_parts[1:] is the dir structure
        rel_path_in_repo = Path(*path_parts[1:]) if len(path_parts) > 1 else Path(".")
    else:
        rel_path_in_repo = Path(".")
    
    # Construct metadata path
    metadata_dir = workspace_root / ".benedict" / "metadata" / rel_path_in_repo
    metadata_file = metadata_dir / ".metadata.benedict"
    
    return metadata_file
```

**Example Translations:**

| Repository Directory | Metadata File Location |
|---------------------|------------------------|
| `workspace/repo/` | `workspace/.benedict/metadata/.metadata.benedict` |
| `workspace/repo/src/` | `workspace/.benedict/metadata/src/.metadata.benedict` |
| `workspace/repo/src/benedict/metadata/` | `workspace/.benedict/metadata/src/benedict/metadata/.metadata.benedict` |

### Component Changes

#### 1. MetadataGenerator (Writer)

**File:** `src/benedict/metadata/metadata_generator.py`

**Changes:**

```python
class MetadataGenerator:
    def __init__(self, workspace_root: Optional[Path] = None, 
                 use_sidecar: bool = True):
        """
        Initialize metadata generator.
        
        Args:
            workspace_root: Optional workspace root for sidecar mode
            use_sidecar: If True, use sidecar overlay; if False, use in-tree (legacy)
        """
        self.handlers = { ... }
        self.workspace_root = workspace_root
        self.use_sidecar = use_sidecar
        logger.debug(f"Initialized MetadataGenerator (sidecar={use_sidecar})")
    
    def write_metadata(self, directory: Path, metadata: Dict[str, Any]) -> None:
        """Write .metadata.benedict file."""
        directory = Path(directory)
        
        if self.use_sidecar and self.workspace_root:
            # NEW: Sidecar mode
            metadata_file = self._get_sidecar_path(directory)
            # Ensure parent directories exist
            metadata_file.parent.mkdir(parents=True, exist_ok=True)
        else:
            # LEGACY: In-tree mode
            metadata_file = directory / ".metadata.benedict"
        
        # Check for conflicts
        if metadata_file.exists() and metadata_file.is_dir():
            logger.debug(f"Metadata path exists as directory, skipping")
            return
        
        try:
            with open(metadata_file, "w", encoding="utf-8") as f:
                yaml.dump(metadata, f, default_flow_style=False, 
                         allow_unicode=True, sort_keys=False)
            logger.debug(f"Wrote metadata to {metadata_file}")
        except Exception as e:
            logger.error(f"Error writing metadata: {e}")
            raise
    
    def _get_sidecar_path(self, directory: Path) -> Path:
        """Get sidecar metadata path for a directory."""
        if not self.workspace_root:
            raise ValueError("workspace_root required for sidecar mode")
        
        rel_path = directory.relative_to(self.workspace_root)
        path_parts = rel_path.parts
        
        # Remove repo name (first component)
        if len(path_parts) > 0:
            rel_path_in_repo = Path(*path_parts[1:]) if len(path_parts) > 1 else Path(".")
        else:
            rel_path_in_repo = Path(".")
        
        metadata_dir = self.workspace_root / ".benedict" / "metadata" / rel_path_in_repo
        return metadata_dir / ".metadata.benedict"
```

**Testing:**
- Unit tests for path translation with various directory depths
- Test both sidecar and legacy modes
- Test edge cases (root directory, deeply nested paths)

#### 2. MetadataReader (Reader)

**File:** `src/benedict/metadata/metadata_reader.py`

**Changes:**

```python
class MetadataReader:
    def __init__(self, metadata_file_path: Optional[str] = None,
                 workspace_root: Optional[Path] = None,
                 use_sidecar: bool = True):
        """
        Initialize metadata reader.
        
        Args:
            metadata_file_path: Optional explicit metadata file path (legacy override)
            workspace_root: Optional workspace root for sidecar mode
            use_sidecar: If True, look for sidecar metadata first; fallback to in-tree
        """
        self.metadata_file_path = metadata_file_path or os.environ.get("BENEDICT_METADATA_FILE")
        self.workspace_root = workspace_root
        self.use_sidecar = use_sidecar
    
    def read_metadata(self, directory: Path) -> Optional[Dict[str, Any]]:
        """Read metadata from directory."""
        directory = Path(directory)
        
        # Priority 1: Explicit override (legacy env var)
        if self.metadata_file_path:
            metadata_file = Path(self.metadata_file_path)
            if not metadata_file.is_absolute():
                metadata_file = directory / metadata_file
            return self._read_file(metadata_file)
        
        # Priority 2: Sidecar metadata (new default)
        if self.use_sidecar and self.workspace_root:
            sidecar_file = self._get_sidecar_path(directory)
            metadata = self._read_file(sidecar_file)
            if metadata is not None:
                return metadata
        
        # Priority 3: In-tree fallback (backward compatibility)
        in_tree_file = directory / ".metadata.benedict"
        return self._read_file(in_tree_file)
    
    def _read_file(self, metadata_file: Path) -> Optional[Dict[str, Any]]:
        """Read metadata from a specific file."""
        if not metadata_file.exists():
            return None
        
        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = yaml.safe_load(f)
            logger.debug(f"Read metadata from {metadata_file}")
            return metadata
        except Exception as e:
            logger.warning(f"Error reading metadata file {metadata_file}: {e}")
            return None
    
    def _get_sidecar_path(self, directory: Path) -> Path:
        """Get sidecar metadata path for a directory."""
        if not self.workspace_root:
            raise ValueError("workspace_root required for sidecar mode")
        
        rel_path = directory.relative_to(self.workspace_root)
        path_parts = rel_path.parts
        
        if len(path_parts) > 0:
            rel_path_in_repo = Path(*path_parts[1:]) if len(path_parts) > 1 else Path(".")
        else:
            rel_path_in_repo = Path(".")
        
        metadata_dir = self.workspace_root / ".benedict" / "metadata" / rel_path_in_repo
        return metadata_dir / ".metadata.benedict"
```

**Backward Compatibility:**
- ✅ Tries sidecar location first
- ✅ Falls back to in-tree location automatically
- ✅ Respects legacy `BENEDICT_METADATA_FILE` env var
- ✅ No breaking changes for existing code

**Testing:**
- Test fallback chain (sidecar → in-tree → none)
- Test with existing in-tree metadata
- Test with new sidecar metadata
- Test mixed scenarios

#### 3. Semantic Indexer

**File:** `src/benedict/semantic_indexer/semantic_indexer_chromadb.py`

**Changes:**

```python
class ChromaDBSemanticIndexer:
    def __init__(self, persist_directory: str = "./.chroma_db",
                 metadata_generator: Optional[MetadataGenerator] = None,
                 change_detector: Optional[RepoChangeDetector] = None):
        """Initialize ChromaDB semantic indexer."""
        # ... existing initialization ...
        self.metadata_generator = metadata_generator or MetadataGenerator()
        # NOTE: Workspace root will be passed to metadata_generator 
        # when index_repository() is called
    
    def index_repository(self, repo: str, repo_reader: RepoReader,
                        workspace_path: Optional[Path] = None,
                        force: bool = False) -> None:
        """Index a repository."""
        # ... existing indexing logic ...
        
        # Generate metadata overlays if workspace_path provided
        if workspace_path:
            # Configure metadata generator with workspace context
            self.metadata_generator.workspace_root = workspace_path
            self.metadata_generator.use_sidecar = True
            
            self._generate_metadata_overlays(repo, repo_reader, workspace_path)
    
    def _get_file_metadata_text(self, file_path: str, workspace_path: Path, 
                                repo: str) -> Optional[str]:
        """Get file metadata text for embeddings."""
        try:
            repo_path = workspace_path / repo
            file_full_path = repo_path / file_path
            
            if not file_full_path.exists():
                return None
            
            # Walk up directory tree looking for metadata
            current_dir = file_full_path.parent
            metadata_reader = MetadataReader(workspace_root=workspace_path, 
                                            use_sidecar=True)
            
            while current_dir != repo_path.parent:
                metadata = metadata_reader.read_metadata(current_dir)
                if metadata:
                    # Extract file-specific metadata
                    files = metadata.get("files", [])
                    file_name = file_full_path.name
                    
                    for file_info in files:
                        if file_info.get("name") == file_name:
                            # Build metadata text
                            # ... existing logic ...
                            return metadata_text
                
                current_dir = current_dir.parent
            
            return None
        except Exception as e:
            logger.debug(f"Error getting file metadata: {e}")
            return None
```

**Testing:**
- Test metadata generation creates sidecar files
- Test file metadata lookup uses sidecar paths
- Test fallback to in-tree metadata for migrated repos

#### 4. Main Composition Root

**File:** `src/benedict/main.py`

**Changes:**

```python
def main():
    """Entry point."""
    # ... existing initialization ...
    
    # Initialize workspace manager
    workspace_manager = WorkspaceManager(
        workspaces_dir=workspaces_dir,
        copy_mode=workspace_copy_mode
    )
    
    # Initialize metadata generator with sidecar mode
    # NOTE: workspace_root will be set per-operation by the indexer/agent
    metadata_generator = MetadataGenerator(
        workspace_root=None,  # Set dynamically per-workspace
        use_sidecar=True      # Default to sidecar mode
    )
    
    # Initialize metadata reader with sidecar mode
    metadata_reader = MetadataReader(
        workspace_root=None,  # Set dynamically per-workspace
        use_sidecar=True      # Default to sidecar mode
    )
    
    # ... rest of initialization ...
```

**Note:** The workspace root is set **dynamically** per-operation because different workspaces (channels) have different roots.

#### 5. MCP Service

**File:** `src/benedict/mcp/service.py`

**Changes:**

```python
class BenedictMcpService:
    def get_repository_summary(self, repo: Optional[str] = None, 
                               cwd: Optional[Path] = None) -> Dict[str, Any]:
        """Return root metadata summary."""
        try:
            project = self._resolver.resolve(repo=repo, cwd=cwd)
        except ProjectResolutionError as exc:
            return _err(exc.message)
        
        # Configure metadata reader for this project's workspace
        workspace_path = self._workspace_manager.get_workspace_path(project.channel_id)
        reader = MetadataReader(workspace_root=workspace_path, use_sidecar=True)
        
        metadata = reader.read_metadata(project.repo_path)
        if not metadata:
            return _err(
                f"No `.metadata.benedict` found for `{project.repo}`.",
                repo=project.repo,
                channel_id=project.channel_id,
            )
        return _ok(
            repo=project.repo,
            channel_id=project.channel_id,
            summary=metadata.get("summary"),
            purpose=metadata.get("purpose"),
        )
```

**Testing:**
- Test MCP tools read from sidecar locations
- Test fallback to in-tree metadata
- Integration tests with real workspace setup

---

## Implementation Plan

### Phase 1: Core Infrastructure (Week 1)

**Goal:** Implement sidecar path translation without breaking existing functionality.

**Tasks:**

1. **Add sidecar support to `MetadataGenerator`**
   - [ ] Add `workspace_root` and `use_sidecar` parameters to `__init__`
   - [ ] Implement `_get_sidecar_path()` method
   - [ ] Update `write_metadata()` to support both modes
   - [ ] Add configuration via environment variable `BENEDICT_METADATA_SIDECAR` (default: true)

2. **Add sidecar support to `MetadataReader`**
   - [ ] Add `workspace_root` and `use_sidecar` parameters to `__init__`
   - [ ] Implement `_get_sidecar_path()` method
   - [ ] Update `read_metadata()` with fallback chain
   - [ ] Update `search_metadata()` to search both locations

3. **Unit Tests**
   - [ ] Test path translation with various directory structures
   - [ ] Test write to sidecar location
   - [ ] Test read fallback (sidecar → in-tree → none)
   - [ ] Test edge cases (root, nested, special characters)

**Success Criteria:**
- All existing tests pass
- New unit tests achieve 90%+ coverage
- Both modes (sidecar and in-tree) work correctly

### Phase 2: Integration (Week 2)

**Goal:** Update all consumers to use sidecar mode.

**Tasks:**

1. **Update `SemanticIndexerChromaDB`**
   - [ ] Pass workspace_root to metadata_generator during indexing
   - [ ] Update `_get_file_metadata_text()` to use sidecar-aware reader
   - [ ] Update `_generate_metadata_overlays()` to use sidecar mode

2. **Update `RepoAgent`**
   - [ ] Configure metadata_generator with workspace context during onboard
   - [ ] Update metadata generation calls to use sidecar mode

3. **Update `BenedictMcpService`**
   - [ ] Configure metadata_reader with workspace context per-project
   - [ ] Update all MCP tools to use workspace-aware reader

4. **Update `main.py` composition root**
   - [ ] Initialize components with sidecar mode enabled
   - [ ] Add configuration documentation

**Success Criteria:**
- All integration points use sidecar mode
- Backward compatibility maintained (reads old in-tree files)
- All existing tests pass
- MCP integration tests pass

### Phase 3: Migration & Cleanup (Week 3)

**Goal:** Migrate existing metadata and clean up old files.

**Tasks:**

1. **Implement migration utility**
   - [ ] Create `benedict/metadata/migrate.py` script
   - [ ] Scan workspace for in-tree `.metadata.benedict` files
   - [ ] Copy to sidecar locations
   - [ ] Optionally delete source files (with confirmation)

2. **Auto-migration in indexer**
   - [ ] Detect in-tree metadata during index operations
   - [ ] Automatically migrate to sidecar on first write
   - [ ] Log migration actions

3. **Documentation**
   - [ ] Update architecture docs
   - [ ] Update user-facing docs (README, setup guides)
   - [ ] Add migration guide
   - [ ] Document environment variables

4. **Cleanup utilities**
   - [ ] Add command `@agent clean metadata` to remove in-tree files
   - [ ] Add command `@agent migrate metadata` to force migration

**Success Criteria:**
- Migration script works correctly
- Auto-migration is transparent to users
- Documentation is complete and accurate
- Users can clean up old files easily

### Phase 4: Testing & Validation (Week 4)

**Goal:** Ensure robustness and backward compatibility.

**Tasks:**

1. **Integration Testing**
   - [ ] Test full onboard → index → query flow with sidecar
   - [ ] Test migration from in-tree to sidecar
   - [ ] Test mixed environment (some repos migrated, some not)
   - [ ] Test MCP tools with sidecar metadata

2. **Performance Testing**
   - [ ] Benchmark read/write operations (sidecar vs in-tree)
   - [ ] Test with large repositories (1000+ directories)
   - [ ] Verify no performance regression

3. **User Acceptance Testing**
   - [ ] Test onboarding new repository (should not pollute git)
   - [ ] Test `git status` in onboarded repo (should be clean)
   - [ ] Test update index (should use sidecar)
   - [ ] Test MCP operations (should work transparently)

4. **Edge Cases**
   - [ ] Test workspace deletion and recreation
   - [ ] Test repo rename scenarios
   - [ ] Test concurrent access (multiple processes)
   - [ ] Test error recovery (partial writes, disk full, etc.)

**Success Criteria:**
- All integration tests pass
- No performance regression
- `git status` is clean in onboarded repos
- Edge cases handled gracefully

---

## Migration Strategy

### Automatic Migration

**Trigger:** First write operation after upgrade (index, update index, onboard)

**Algorithm:**

```python
def migrate_metadata_to_sidecar(workspace_path: Path, repo: str) -> None:
    """
    Migrate in-tree metadata to sidecar locations.
    
    Args:
        workspace_path: Path to workspace root
        repo: Repository name
    """
    repo_path = workspace_path / repo
    if not repo_path.exists():
        return
    
    logger.info(f"Migrating metadata for {repo} to sidecar locations...")
    
    migrated_count = 0
    
    # Find all in-tree .metadata.benedict files
    for in_tree_file in repo_path.rglob(".metadata.benedict"):
        # Skip if in .benedict directory (already a sidecar)
        if ".benedict" in in_tree_file.parts:
            continue
        
        try:
            # Read existing metadata
            with open(in_tree_file, "r", encoding="utf-8") as f:
                metadata = yaml.safe_load(f)
            
            # Determine sidecar location
            directory = in_tree_file.parent
            generator = MetadataGenerator(workspace_root=workspace_path, use_sidecar=True)
            
            # Write to sidecar location
            generator.write_metadata(directory, metadata)
            
            # Optionally delete in-tree file (with safety check)
            if not in_tree_file.is_symlink():  # Don't delete symlinks
                in_tree_file.unlink()
                logger.debug(f"Migrated and removed: {in_tree_file}")
            
            migrated_count += 1
        
        except Exception as e:
            logger.warning(f"Error migrating {in_tree_file}: {e}")
            continue
    
    logger.info(f"Migration complete: {migrated_count} metadata files migrated for {repo}")
```

**Safety:**
- Only migrates files within workspace directories (never touches source repos)
- Validates file contents before migration
- Atomic operations (write new before deleting old)
- Extensive logging for troubleshooting

### Manual Migration

Users can trigger migration explicitly:

```bash
# Command in Slack
@agent migrate metadata

# CLI utility
python -m benedict.metadata.migrate --workspace ./workspaces/C123ABC
```

### Rollback Plan

If issues arise, users can:

1. **Keep in-tree metadata:**
   ```bash
   export BENEDICT_METADATA_SIDECAR=false
   ```

2. **Restore from backup:**
   - Metadata is never deleted until after successful migration
   - Sidecar and in-tree can coexist temporarily

3. **Regenerate metadata:**
   ```bash
   @agent update index force
   ```

---

## Testing Strategy

### Unit Tests

**Coverage Target:** 90%+ for modified files

**Key Test Cases:**

1. **Path Translation**
   ```python
   def test_get_sidecar_path_root():
       """Test sidecar path for root directory."""
       generator = MetadataGenerator(workspace_root=Path("/ws"), use_sidecar=True)
       path = generator._get_sidecar_path(Path("/ws/repo"))
       assert path == Path("/ws/.benedict/metadata/.metadata.benedict")
   
   def test_get_sidecar_path_nested():
       """Test sidecar path for nested directory."""
       generator = MetadataGenerator(workspace_root=Path("/ws"), use_sidecar=True)
       path = generator._get_sidecar_path(Path("/ws/repo/src/foo"))
       assert path == Path("/ws/.benedict/metadata/src/foo/.metadata.benedict")
   ```

2. **Write Operations**
   ```python
   def test_write_sidecar_creates_directory():
       """Test that sidecar write creates parent directories."""
       generator = MetadataGenerator(workspace_root=tmp_path, use_sidecar=True)
       metadata = {"content_type": "code", "summary": "Test"}
       
       repo_dir = tmp_path / "repo" / "src" / "foo"
       repo_dir.mkdir(parents=True)
       
       generator.write_metadata(repo_dir, metadata)
       
       expected_path = tmp_path / ".benedict" / "metadata" / "src" / "foo" / ".metadata.benedict"
       assert expected_path.exists()
   ```

3. **Read Fallback**
   ```python
   def test_read_fallback_to_in_tree():
       """Test reader falls back to in-tree if sidecar not found."""
       reader = MetadataReader(workspace_root=tmp_path, use_sidecar=True)
       
       # Create only in-tree metadata
       in_tree_file = tmp_path / "repo" / ".metadata.benedict"
       in_tree_file.parent.mkdir(parents=True)
       with open(in_tree_file, "w") as f:
           yaml.dump({"summary": "In-tree metadata"}, f)
       
       metadata = reader.read_metadata(tmp_path / "repo")
       assert metadata is not None
       assert metadata["summary"] == "In-tree metadata"
   ```

### Integration Tests

**Key Test Scenarios:**

1. **Full Onboard Flow**
   ```python
   def test_onboard_with_sidecar(agent, workspace_manager):
       """Test onboarding creates sidecar metadata, not in-tree."""
       repo_path = create_test_repo()
       
       agent.handle_onboard("C123", "test-repo", repo_path)
       
       # Assert: No .metadata.benedict in source repo
       assert not (repo_path / ".metadata.benedict").exists()
       
       # Assert: Metadata exists in sidecar
       workspace_path = workspace_manager.get_workspace_path("C123")
       sidecar_file = workspace_path / ".benedict" / "metadata" / ".metadata.benedict"
       assert sidecar_file.exists()
   ```

2. **Index with Sidecar**
   ```python
   def test_index_uses_sidecar(indexer, workspace_manager, repo_reader):
       """Test indexing creates sidecar metadata."""
       workspace_path = workspace_manager.get_workspace_path("C123")
       
       indexer.index_repository("test-repo", repo_reader, workspace_path)
       
       # Assert: Sidecar metadata exists
       metadata_dir = workspace_path / ".benedict" / "metadata"
       assert metadata_dir.exists()
       assert len(list(metadata_dir.rglob(".metadata.benedict"))) > 0
       
       # Assert: No in-tree metadata in source repo
       repo_path = workspace_path / "test-repo"
       in_tree_files = list(repo_path.rglob(".metadata.benedict"))
       # Filter out any in .benedict directory
       in_tree_files = [f for f in in_tree_files if ".benedict" not in f.parts]
       assert len(in_tree_files) == 0
   ```

3. **Migration**
   ```python
   def test_migration_from_in_tree(workspace_manager):
       """Test migration moves in-tree to sidecar."""
       workspace_path = workspace_manager.get_workspace_path("C123")
       repo_path = workspace_path / "test-repo"
       repo_path.mkdir(parents=True)
       
       # Create in-tree metadata
       in_tree_file = repo_path / "src" / ".metadata.benedict"
       in_tree_file.parent.mkdir(parents=True)
       metadata = {"summary": "Old metadata"}
       with open(in_tree_file, "w") as f:
           yaml.dump(metadata, f)
       
       # Run migration
       migrate_metadata_to_sidecar(workspace_path, "test-repo")
       
       # Assert: Sidecar exists with same content
       sidecar_file = workspace_path / ".benedict" / "metadata" / "src" / ".metadata.benedict"
       assert sidecar_file.exists()
       with open(sidecar_file) as f:
           migrated = yaml.safe_load(f)
       assert migrated["summary"] == "Old metadata"
       
       # Assert: In-tree removed
       assert not in_tree_file.exists()
   ```

### System Tests

**Scenario:** Fresh Onboard (Happy Path)

1. User runs `@agent onboard repo my-org/my-repo`
2. Benedict creates workspace with symlink
3. Benedict generates root metadata → **sidecar location**
4. User runs `git status` in source repo → **CLEAN** ✅
5. User asks question → semantic search works
6. Benedict indexes repository → generates metadata for all directories → **sidecar locations**
7. User runs `git status` again → **STILL CLEAN** ✅

**Scenario:** Upgrade Migration (Backward Compatibility)

1. User has Benedict running with old version (in-tree metadata)
2. User's repo has many `.metadata.benedict` files (git-ignored)
3. User upgrades Benedict to new version
4. User runs `@agent update index`
5. Benedict detects in-tree metadata
6. Benedict migrates to sidecar automatically
7. Benedict removes in-tree files
8. User runs `git status` → **NOW CLEAN** ✅
9. All queries and MCP tools continue working normally

---

## Open Questions & Decisions

### Q1: Sidecar vs Data Directory?

**Decision:** **Workspace Sidecar (Option A)**

**Rationale:**
- Logical proximity (metadata near the workspace it describes)
- Simpler path mapping (no need for stable repo keys)
- Natural cleanup (deleting workspace removes metadata)
- Supports multi-workspace scenarios cleanly

### Q2: Should `BENEDICT_METADATA_FILE` be replaced?

**Decision:** **Keep but deprecate**

**Rationale:**
- Maintain backward compatibility
- Provide migration path for users relying on it
- Document as deprecated in release notes
- Consider removing in v2.0

**New Environment Variable:**
```bash
BENEDICT_METADATA_SIDECAR=true  # Default: true
```
- If `false`, falls back to in-tree mode (legacy)
- If `true`, uses sidecar overlay

### Q3: Opt-in for in-tree metadata?

**Decision:** **Not in initial release, future enhancement**

**Rationale:**
- MVP should focus on fixing the default case
- In-tree metadata can be added later via configuration
- Use case: Users who want to commit metadata to version control
- Proposed future config:
  ```yaml
  # .benedict.config.yaml (future)
  metadata:
    location: "in-tree"  # or "sidecar" (default)
    commit: true         # generate .gitattributes to commit
  ```

### Q4: Path mapping for nested repos?

**Decision:** **Use relative path from workspace root**

**Example:**
```
workspaces/C123/
  org/repo/           # Nested organization/repo structure
    src/foo/
```

**Sidecar location:**
```
workspaces/C123/.benedict/metadata/repo/src/foo/.metadata.benedict
```

**Rationale:**
- Consistent structure regardless of repo naming
- Supports organizational prefixes (org/repo)
- Clear separation between different repos in same workspace

### Q5: Cleanup of existing in-tree files?

**Decision:** **Automatic cleanup during migration**

**Rationale:**
- Improves user experience (no manual cleanup needed)
- Safe (only deletes after successful migration)
- Logged (users can see what was cleaned up)
- Optional (users can disable via `BENEDICT_MIGRATE_CLEANUP=false`)

**Safety Checks:**
- Only delete files within workspace (never source repos)
- Verify file contents before deletion
- Never delete symlinks
- Atomic operations (write new, verify, delete old)

### Q6: Auto-gitignore as stopgap?

**Decision:** **NO - Go straight to sidecar solution**

**Rationale:**
- Auto-gitignore is a band-aid, not a fix
- Mutating user files without consent is poor UX
- Doesn't help with already-committed files
- Sidecar solution is the right long-term fix
- Implementation timeline is reasonable (4 weeks)

---

## Appendix

### A. Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `BENEDICT_DATA_DIR` | `.` (repo root) | Base data directory |
| `BENEDICT_WORKSPACES_DIR` | `{data_dir}/workspaces` | Workspaces directory |
| `BENEDICT_WORKSPACE_COPY_MODE` | `symlink` | Workspace resource mode (`symlink` or `copy`) |
| `BENEDICT_METADATA_SIDECAR` | `true` | Use sidecar metadata overlay |
| `BENEDICT_METADATA_FILE` | (none) | **DEPRECATED:** Single metadata file override |
| `BENEDICT_MIGRATE_CLEANUP` | `true` | Clean up in-tree files after migration |

### B. File Locations Reference

**Before (In-Tree):**
```
user-repo/                          # User's actual repository
  .metadata.benedict               # ❌ Generated file in user's repo
  src/
    .metadata.benedict             # ❌ Generated file
    commands/
      .metadata.benedict           # ❌ Generated file
  .git/
  .gitignore                       # Must manually add .metadata.benedict
```

**After (Sidecar):**
```
user-repo/                          # User's actual repository (CLEAN)
  src/
    commands/
  .git/
  .gitignore                       # No changes needed

workspaces/C123/
  repo/                            # Symlink to user-repo
  .benedict/
    metadata/
      .metadata.benedict           # ✅ Generated overlay
      src/
        .metadata.benedict         # ✅ Generated overlay
        commands/
          .metadata.benedict       # ✅ Generated overlay
  workspace_log.json
```

### C. API Stability Guarantees

**Stable (No Breaking Changes):**
- `MetadataGenerator.generate_metadata()` - signature unchanged
- `MetadataGenerator.generate_and_write()` - signature unchanged
- `MetadataReader.read_metadata()` - signature unchanged
- `MetadataReader.search_metadata()` - signature unchanged
- All MCP tool APIs - unchanged

**New Parameters (Backward Compatible):**
- `MetadataGenerator.__init__(workspace_root, use_sidecar)`
  - Default: `workspace_root=None, use_sidecar=True`
  - Existing code continues to work
- `MetadataReader.__init__(workspace_root, use_sidecar)`
  - Default: `workspace_root=None, use_sidecar=True`
  - Existing code continues to work

**Deprecated (Still Supported):**
- `BENEDICT_METADATA_FILE` environment variable
  - Still works, but prints deprecation warning
  - Recommended: Remove from your configuration

### D. Related Issues & PRs

- **Issue #12:** Stop writing `.metadata.benedict` into user's project tree (this document)
- **Issue #2:** Prompt-first vs tools design (related but separate concern)

### E. References

- **Architecture:** `plans/ARCHITECTURE.md`
- **Metadata System:** `src/benedict/metadata/`
- **Workspace System:** `src/benedict/workspace/`
- **Semantic Indexer:** `src/benedict/semantic_indexer/`
- **MCP Integration:** `src/benedict/mcp/`

---

## Changelog

| Date | Author | Changes |
|------|--------|---------|
| 2026-08-19 | Cloud Agent | Initial design document |

---

**Document Status:** ✅ Ready for Review

**Next Steps:**
1. Review and approve design
2. Create implementation issues
3. Begin Phase 1 development
4. Establish testing milestones
