"""Tests for DocumentSync functionality."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from truthgit import TruthRepository
from truthgit.sync import (
    DocumentSync,
    FileType,
    SyncedFile,
    SyncResult,
    SyncState,
)


class TestSyncedFile:
    """Test SyncedFile dataclass."""

    def test_to_dict_from_dict(self):
        sf = SyncedFile(
            path="/docs/readme.md",
            file_type=FileType.MARKDOWN,
            content_hash="abc123",
            last_synced="2024-01-01T00:00:00",
            claims_extracted=5,
            domain="documentation",
        )
        data = sf.to_dict()
        restored = SyncedFile.from_dict(data)

        assert restored.path == sf.path
        assert restored.file_type == sf.file_type
        assert restored.content_hash == sf.content_hash
        assert restored.claims_extracted == sf.claims_extracted


class TestSyncState:
    """Test SyncState dataclass."""

    def test_empty_state(self):
        state = SyncState()
        assert state.version == "1.0.0"
        assert state.last_full_sync is None
        assert state.files == {}

    def test_to_dict_from_dict(self):
        state = SyncState(
            last_full_sync="2024-01-01T00:00:00",
            watch_paths=["docs/", "README.md"],
            domain_mappings={"api/": "api"},
        )
        data = state.to_dict()
        restored = SyncState.from_dict(data)

        assert restored.last_full_sync == state.last_full_sync
        assert restored.watch_paths == state.watch_paths
        assert restored.domain_mappings == state.domain_mappings


class TestDocumentSync:
    """Test DocumentSync class."""

    def test_init(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = TruthRepository(Path(tmpdir) / ".truth")
            repo.init()

            sync = DocumentSync(repo)
            assert sync.repo == repo
            assert sync.use_local is True

    def test_scan_finds_markdown(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create repo
            repo = TruthRepository(Path(tmpdir) / ".truth")
            repo.init()

            # Create test files
            docs_dir = Path(tmpdir) / "docs"
            docs_dir.mkdir()
            (docs_dir / "readme.md").write_text("# Test\n\nThis is a test.")
            (docs_dir / "guide.md").write_text("# Guide\n\nUser guide.")
            (docs_dir / "ignore.pyc").write_text("binary")

            sync = DocumentSync(repo)
            files = sync.scan(str(docs_dir))

            assert len(files) == 2
            assert all(f.suffix == ".md" for f in files)

    def test_scan_ignores_git_and_pycache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = TruthRepository(Path(tmpdir) / ".truth")
            repo.init()

            # Create test structure
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()
            (git_dir / "config").write_text("git config")

            cache_dir = Path(tmpdir) / "__pycache__"
            cache_dir.mkdir()
            (cache_dir / "module.pyc").write_text("cached")

            (Path(tmpdir) / "readme.md").write_text("# Readme")

            sync = DocumentSync(repo)
            files = sync.scan(tmpdir)

            # Should only find readme.md
            assert len(files) == 1
            assert files[0].name == "readme.md"

    def test_detect_domain_api(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = TruthRepository(Path(tmpdir) / ".truth")
            repo.init()

            sync = DocumentSync(repo)

            assert sync._detect_domain(Path("/project/api/endpoints.md")) == "api"
            assert sync._detect_domain(Path("/project/guide/intro.md")) == "guide"
            assert sync._detect_domain(Path("/project/readme.md")) == "overview"
            assert sync._detect_domain(Path("/project/other.md")) == "documentation"

    def test_set_domain_mapping(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = TruthRepository(Path(tmpdir) / ".truth")
            repo.init()

            sync = DocumentSync(repo)
            sync.set_domain_mapping("mcp/", "mcp.protocol")

            assert sync.state.domain_mappings["mcp/"] == "mcp.protocol"
            assert sync._detect_domain(Path("/project/mcp/tools.md")) == "mcp.protocol"

    def test_get_changed_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = TruthRepository(Path(tmpdir) / ".truth")
            repo.init()

            # Create file
            test_file = Path(tmpdir) / "test.md"
            test_file.write_text("Initial content")

            sync = DocumentSync(repo)

            # First scan - all new
            files = sync.scan(tmpdir)
            new, changed, deleted = sync.get_changed_files(files)
            assert len(new) == 1
            assert len(changed) == 0
            assert len(deleted) == 0

            # Mark as synced
            sync.state.files[str(test_file)] = SyncedFile(
                path=str(test_file),
                file_type=FileType.MARKDOWN,
                content_hash=sync._file_hash(test_file),
                last_synced="2024-01-01T00:00:00",
                claims_extracted=1,
            )

            # No changes
            files = sync.scan(tmpdir)
            new, changed, deleted = sync.get_changed_files(files)
            assert len(new) == 0
            assert len(changed) == 0

            # Modify file
            test_file.write_text("Modified content")
            files = sync.scan(tmpdir)
            new, changed, deleted = sync.get_changed_files(files)
            assert len(new) == 0
            assert len(changed) == 1

    def test_diff(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = TruthRepository(Path(tmpdir) / ".truth")
            repo.init()

            # Create files
            (Path(tmpdir) / "new.md").write_text("New file")

            sync = DocumentSync(repo)
            diff = sync.diff(tmpdir)

            assert len(diff["new"]) == 1
            assert len(diff["changed"]) == 0
            assert len(diff["deleted"]) == 0

    def test_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = TruthRepository(Path(tmpdir) / ".truth")
            repo.init()

            sync = DocumentSync(repo)
            status = sync.status()

            assert status["initialized"] is False
            assert status["files_tracked"] == 0
            assert status["total_claims"] == 0

    @patch.object(DocumentSync, "_process_file")
    def test_sync(self, mock_process):
        """Test sync with mocked file processing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = TruthRepository(Path(tmpdir) / ".truth")
            repo.init()

            # Create test file
            test_file = Path(tmpdir) / "test.md"
            test_file.write_text("# Test\n\nThis is a test document.")

            # Mock processing
            mock_process.return_value = SyncedFile(
                path=str(test_file),
                file_type=FileType.MARKDOWN,
                content_hash="abc123",
                last_synced="2024-01-01T00:00:00",
                claims_extracted=2,
            )

            sync = DocumentSync(repo)
            result = sync.sync(tmpdir)

            assert isinstance(result, SyncResult)
            assert result.files_scanned >= 1
            assert result.files_new >= 1
            assert mock_process.called


class TestSyncResult:
    """Test SyncResult dataclass."""

    def test_sync_result_creation(self):
        result = SyncResult(
            files_scanned=10,
            files_changed=2,
            files_new=3,
            files_deleted=1,
            claims_extracted=15,
        )
        assert result.files_scanned == 10
        assert result.claims_extracted == 15
        assert result.errors == []
