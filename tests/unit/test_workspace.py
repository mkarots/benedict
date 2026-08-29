"""Tests for workspace management.

Tests WorkspaceManager and ActionLogger functionality.
"""

from pathlib import Path

from benedict.workspace import WorkspaceManager, ActionLogger


class TestWorkspaceManager:
    """Tests for WorkspaceManager."""

    def test_initialization(self, temp_dir):
        """Test workspace manager initialization."""
        manager = WorkspaceManager(workspaces_dir=str(temp_dir))

        assert manager.workspaces_dir == Path(temp_dir).resolve()
        assert manager.workspaces_dir.exists()

    def test_get_workspace_path(self, temp_dir):
        """Test getting workspace path for a channel."""
        manager = WorkspaceManager(workspaces_dir=str(temp_dir))

        path = manager.get_workspace_path("C123456")

        assert path is not None
        assert isinstance(path, Path)
        assert "C123456" in str(path)

    def test_workspace_creation(self, temp_dir):
        """Test that workspace directory is created."""
        manager = WorkspaceManager(workspaces_dir=str(temp_dir))

        path = manager.get_workspace_path("C123456")

        assert path.exists()

    def test_multiple_workspaces(self, temp_dir):
        """Test managing multiple workspaces."""
        manager = WorkspaceManager(workspaces_dir=str(temp_dir))

        path1 = manager.get_workspace_path("C111111")
        path2 = manager.get_workspace_path("C222222")

        assert path1 != path2
        assert "C111111" in str(path1)
        assert "C222222" in str(path2)

    def test_same_workspace_for_same_channel(self, temp_dir):
        """Test that same channel gets same workspace."""
        manager = WorkspaceManager(workspaces_dir=str(temp_dir))

        path1 = manager.get_workspace_path("C123456")
        path2 = manager.get_workspace_path("C123456")

        assert path1 == path2


class TestActionLogger:
    """Tests for ActionLogger."""

    def test_initialization(self, temp_dir):
        """Test action logger initialization."""
        logger = ActionLogger(workspace_path=temp_dir)

        assert logger.workspace_path == Path(temp_dir)
        assert logger.log_file == Path(temp_dir) / "workspace_log.json"

    def test_log_action(self, temp_dir):
        """Test logging an action."""
        logger = ActionLogger(workspace_path=temp_dir)

        logger.log_action("test_action", "code", resource="example-org/repo")

        assert logger.log_file.exists()
        content = logger.log_file.read_text()
        assert "test_action" in content

    def test_multiple_actions(self, temp_dir):
        """Test logging multiple actions."""
        logger = ActionLogger(workspace_path=temp_dir)

        logger.log_action("action1", "code", resource="repo1")
        logger.log_action("action2", "code", resource="repo2")

        content = logger.log_file.read_text()
        assert "action1" in content
        assert "action2" in content

    def test_get_recent_actions(self, temp_dir):
        """Test retrieving recent actions."""
        logger = ActionLogger(workspace_path=temp_dir)

        logger.log_action("action1", "code")
        logger.log_action("action2", "code")
        logger.log_action("action3", "code")

        recent = logger.get_recent_actions(limit=2)
        assert len(recent) == 2
        assert recent[0]["action"] == "action3"
        assert recent[1]["action"] == "action2"
