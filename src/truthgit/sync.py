"""
TruthGit Sync - Synchronize verified knowledge with documentation.

This module enables:
1. Scanning repositories for documentation files
2. Tracking changes to documentation
3. Auto-extracting claims when docs change
4. Maintaining sync state between code and truth

Usage:
    from truthgit.sync import DocumentSync

    sync = DocumentSync(repo)
    sync.scan("docs/")           # Scan for documentation
    sync.sync()                  # Extract claims from changed files
    sync.watch("docs/")          # Watch for changes (continuous)
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from .extractor import KnowledgeExtractor

if TYPE_CHECKING:
    from .objects import Claim
    from .repository import TruthRepository


class FileType(Enum):
    """Supported documentation file types."""

    MARKDOWN = "markdown"
    RST = "rst"
    TEXT = "text"
    PYTHON_DOCSTRING = "python"
    YAML = "yaml"
    JSON = "json"


# File extensions to type mapping
EXTENSION_MAP = {
    ".md": FileType.MARKDOWN,
    ".markdown": FileType.MARKDOWN,
    ".mdx": FileType.MARKDOWN,  # MDX (Markdown + JSX)
    ".rst": FileType.RST,
    ".txt": FileType.TEXT,
    ".py": FileType.PYTHON_DOCSTRING,
    ".yaml": FileType.YAML,
    ".yml": FileType.YAML,
    ".json": FileType.JSON,
}

# Default patterns to ignore
DEFAULT_IGNORE = [
    ".git",
    ".truth",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".env",
    "*.pyc",
    "*.pyo",
    ".DS_Store",
]


@dataclass
class SyncedFile:
    """Represents a synced documentation file."""

    path: str
    file_type: FileType
    content_hash: str
    last_synced: str
    claims_extracted: int
    claim_hashes: list[str] = field(default_factory=list)
    domain: str = "general"
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "file_type": self.file_type.value,
            "content_hash": self.content_hash,
            "last_synced": self.last_synced,
            "claims_extracted": self.claims_extracted,
            "claim_hashes": self.claim_hashes,
            "domain": self.domain,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SyncedFile:
        return cls(
            path=data["path"],
            file_type=FileType(data["file_type"]),
            content_hash=data["content_hash"],
            last_synced=data["last_synced"],
            claims_extracted=data["claims_extracted"],
            claim_hashes=data.get("claim_hashes", []),
            domain=data.get("domain", "general"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SyncState:
    """State of documentation synchronization."""

    version: str = "1.0.0"
    last_full_sync: str | None = None
    files: dict[str, SyncedFile] = field(default_factory=dict)
    watch_paths: list[str] = field(default_factory=list)
    domain_mappings: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "last_full_sync": self.last_full_sync,
            "files": {k: v.to_dict() for k, v in self.files.items()},
            "watch_paths": self.watch_paths,
            "domain_mappings": self.domain_mappings,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SyncState:
        files = {k: SyncedFile.from_dict(v) for k, v in data.get("files", {}).items()}
        return cls(
            version=data.get("version", "1.0.0"),
            last_full_sync=data.get("last_full_sync"),
            files=files,
            watch_paths=data.get("watch_paths", []),
            domain_mappings=data.get("domain_mappings", {}),
        )


@dataclass
class SyncResult:
    """Result of a sync operation."""

    files_scanned: int
    files_changed: int
    files_new: int
    files_deleted: int
    claims_extracted: int
    errors: list[str] = field(default_factory=list)
    synced_files: list[SyncedFile] = field(default_factory=list)


class DocumentSync:
    """
    Synchronize documentation with TruthGit repository.

    This class handles:
    1. Scanning directories for documentation files
    2. Detecting changes since last sync
    3. Extracting claims from changed/new files
    4. Tracking sync state
    """

    def __init__(
        self,
        repository: TruthRepository,
        use_local: bool = True,
        parser_model: str = "llama3",
    ):
        """
        Initialize DocumentSync.

        Args:
            repository: TruthGit repository
            use_local: Use local LLM (Ollama) for extraction
            parser_model: Model to use for parsing
        """
        self.repo = repository
        self.use_local = use_local
        self.parser_model = parser_model
        self.sync_dir = self.repo.root / "sync"
        self.state_file = self.sync_dir / "state.json"
        self._state: SyncState | None = None
        self._extractor: KnowledgeExtractor | None = None

    @property
    def extractor(self) -> KnowledgeExtractor:
        """Lazy-load extractor."""
        if self._extractor is None:
            self._extractor = KnowledgeExtractor(
                self.repo,
                parser_model=self.parser_model,
                use_local=self.use_local,
            )
        return self._extractor

    @property
    def state(self) -> SyncState:
        """Load or create sync state."""
        if self._state is None:
            self._state = self._load_state()
        return self._state

    def _load_state(self) -> SyncState:
        """Load sync state from disk."""
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                return SyncState.from_dict(data)
            except (json.JSONDecodeError, KeyError):
                pass
        return SyncState()

    def _save_state(self):
        """Save sync state to disk."""
        self.sync_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self.state.to_dict(), indent=2))

    def _file_hash(self, path: Path) -> str:
        """Calculate hash of file contents."""
        content = path.read_bytes()
        return hashlib.sha256(content).hexdigest()

    def _should_ignore(self, path: Path, ignore_patterns: list[str]) -> bool:
        """Check if path should be ignored."""
        path_str = str(path)
        name = path.name

        for pattern in ignore_patterns:
            if pattern.startswith("*"):
                # Wildcard pattern
                if name.endswith(pattern[1:]):
                    return True
            elif pattern in path_str:
                return True
            elif name == pattern:
                return True

        return False

    def _detect_domain(self, path: Path) -> str:
        """Detect domain from file path."""
        path_str = str(path).lower()

        # Check domain mappings first
        for pattern, domain in self.state.domain_mappings.items():
            if pattern in path_str:
                return domain

        # Auto-detect from path
        if "api" in path_str:
            return "api"
        elif "guide" in path_str or "tutorial" in path_str:
            return "guide"
        elif "reference" in path_str:
            return "reference"
        elif "spec" in path_str or "specification" in path_str:
            return "specification"
        elif any(x in path_str for x in ["readme", "getting-started", "quickstart"]):
            return "overview"

        return "documentation"

    def _extract_docstrings(self, content: str) -> str:
        """Extract docstrings from Python file."""
        import ast

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return ""

        docstrings = []

        # Module docstring
        if ast.get_docstring(tree):
            docstrings.append(ast.get_docstring(tree))

        # Class and function docstrings
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                docstring = ast.get_docstring(node)
                if docstring:
                    docstrings.append(f"{node.name}: {docstring}")

        return "\n\n".join(docstrings)

    def _read_file_content(self, path: Path, file_type: FileType) -> str:
        """Read and preprocess file content based on type."""
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = path.read_text(encoding="latin-1")

        if file_type == FileType.PYTHON_DOCSTRING:
            return self._extract_docstrings(content)
        elif file_type == FileType.JSON:
            # For JSON, extract descriptions and comments if present
            try:
                data = json.loads(content)
                return self._extract_json_docs(data)
            except json.JSONDecodeError:
                return content
        else:
            return content

    def _extract_json_docs(self, data: dict | list, prefix: str = "") -> str:
        """Extract documentation from JSON structure."""
        docs = []

        if isinstance(data, dict):
            for key in ["description", "summary", "help", "doc", "title"]:
                if key in data and isinstance(data[key], str):
                    docs.append(f"{prefix}{key}: {data[key]}")

            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    nested = self._extract_json_docs(value, f"{prefix}{key}.")
                    if nested:
                        docs.append(nested)

        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    nested = self._extract_json_docs(item, f"{prefix}[{i}].")
                    if nested:
                        docs.append(nested)

        return "\n".join(docs)

    def scan(
        self,
        paths: str | list[str],
        ignore: list[str] | None = None,
        extensions: list[str] | None = None,
    ) -> list[Path]:
        """
        Scan directories for documentation files.

        Args:
            paths: Directory or list of directories to scan
            ignore: Patterns to ignore (default: common dev dirs)
            extensions: File extensions to include (default: all supported)

        Returns:
            List of found documentation files
        """
        if isinstance(paths, str):
            paths = [paths]

        ignore_patterns = (ignore or []) + DEFAULT_IGNORE
        allowed_extensions = set(extensions or EXTENSION_MAP.keys())

        found_files = []

        for path_str in paths:
            base_path = Path(path_str)

            if not base_path.exists():
                continue

            if base_path.is_file():
                if base_path.suffix in allowed_extensions:
                    found_files.append(base_path)
                continue

            # Walk directory
            for root, dirs, files in os.walk(base_path):
                root_path = Path(root)

                # Filter directories
                dirs[:] = [
                    d for d in dirs if not self._should_ignore(root_path / d, ignore_patterns)
                ]

                # Filter files
                for file in files:
                    file_path = root_path / file
                    if self._should_ignore(file_path, ignore_patterns):
                        continue
                    if file_path.suffix in allowed_extensions:
                        found_files.append(file_path)

        # Update watch paths
        for path_str in paths:
            if path_str not in self.state.watch_paths:
                self.state.watch_paths.append(path_str)
        self._save_state()

        return found_files

    def get_changed_files(self, files: list[Path]) -> tuple[list[Path], list[Path], list[str]]:
        """
        Detect which files have changed since last sync.

        Returns:
            Tuple of (new_files, changed_files, deleted_paths)
        """
        new_files = []
        changed_files = []
        current_paths = {str(f) for f in files}

        for file_path in files:
            path_str = str(file_path)
            current_hash = self._file_hash(file_path)

            if path_str not in self.state.files:
                new_files.append(file_path)
            elif self.state.files[path_str].content_hash != current_hash:
                changed_files.append(file_path)

        # Find deleted files
        deleted_paths = [path for path in self.state.files.keys() if path not in current_paths]

        return new_files, changed_files, deleted_paths

    def sync(
        self,
        paths: str | list[str] | None = None,
        force: bool = False,
        auto_verify: bool = False,
        on_progress: Callable[[str, int, int], None] | None = None,
    ) -> SyncResult:
        """
        Synchronize documentation with TruthGit.

        Args:
            paths: Paths to sync (default: previously watched paths)
            force: Force re-sync of all files
            auto_verify: Automatically verify extracted claims
            on_progress: Callback for progress updates (message, current, total)

        Returns:
            SyncResult with statistics
        """
        # Use watch paths if none specified
        if paths is None:
            paths = self.state.watch_paths

        if not paths:
            return SyncResult(
                files_scanned=0,
                files_changed=0,
                files_new=0,
                files_deleted=0,
                claims_extracted=0,
                errors=["No paths specified. Run scan() first or provide paths."],
            )

        # Scan for files
        all_files = self.scan(paths)

        if force:
            new_files = all_files
            changed_files = []
            deleted_paths = []
        else:
            new_files, changed_files, deleted_paths = self.get_changed_files(all_files)

        files_to_process = new_files + changed_files
        total_files = len(files_to_process)
        result = SyncResult(
            files_scanned=len(all_files),
            files_changed=len(changed_files),
            files_new=len(new_files),
            files_deleted=len(deleted_paths),
            claims_extracted=0,
        )

        # Process files
        for i, file_path in enumerate(files_to_process):
            if on_progress:
                on_progress(f"Processing {file_path.name}", i + 1, total_files)

            try:
                synced_file = self._process_file(file_path, auto_verify)
                self.state.files[str(file_path)] = synced_file
                result.claims_extracted += synced_file.claims_extracted
                result.synced_files.append(synced_file)
            except Exception as e:
                result.errors.append(f"{file_path}: {e}")

        # Remove deleted files from state
        for path in deleted_paths:
            if path in self.state.files:
                del self.state.files[path]

        # Update state
        self.state.last_full_sync = datetime.now().isoformat()
        self._save_state()

        return result

    def _process_file(self, file_path: Path, auto_verify: bool = False) -> SyncedFile:
        """Process a single file and extract claims."""
        file_type = EXTENSION_MAP.get(file_path.suffix, FileType.TEXT)
        content = self._read_file_content(file_path, file_type)
        domain = self._detect_domain(file_path)

        # Skip empty content
        if not content.strip():
            return SyncedFile(
                path=str(file_path),
                file_type=file_type,
                content_hash=self._file_hash(file_path),
                last_synced=datetime.now().isoformat(),
                claims_extracted=0,
                domain=domain,
            )

        # Extract claims
        claims = self.extractor.ingest_document(
            document=content,
            domain=domain,
            auto_verify=auto_verify,
        )

        return SyncedFile(
            path=str(file_path),
            file_type=file_type,
            content_hash=self._file_hash(file_path),
            last_synced=datetime.now().isoformat(),
            claims_extracted=len(claims),
            claim_hashes=[c.hash for c in claims],
            domain=domain,
            metadata={
                "content_length": len(content),
                "file_name": file_path.name,
            },
        )

    def watch(
        self,
        paths: str | list[str] | None = None,
        interval: float = 2.0,
        auto_verify: bool = False,
        on_change: Callable[[SyncResult], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ):
        """
        Watch directories for changes and auto-sync.

        Args:
            paths: Paths to watch (default: previously watched)
            interval: Check interval in seconds
            auto_verify: Auto-verify new claims
            on_change: Callback when changes are synced
            on_error: Callback on errors

        Note: This is a blocking operation. Use in a separate thread or process.
        """
        if paths is None:
            paths = self.state.watch_paths

        if not paths:
            raise ValueError("No paths to watch. Run scan() first or provide paths.")

        print(f"Watching {paths} for changes (Ctrl+C to stop)...")

        try:
            while True:
                all_files = self.scan(paths)
                new_files, changed_files, deleted_paths = self.get_changed_files(all_files)

                if new_files or changed_files or deleted_paths:
                    try:
                        result = self.sync(paths, auto_verify=auto_verify)
                        if on_change:
                            on_change(result)
                        else:
                            print(
                                f"Synced: {result.files_new} new, "
                                f"{result.files_changed} changed, "
                                f"{result.claims_extracted} claims"
                            )
                    except Exception as e:
                        if on_error:
                            on_error(e)
                        else:
                            print(f"Error: {e}")

                time.sleep(interval)

        except KeyboardInterrupt:
            print("\nStopped watching.")

    def status(self) -> dict:
        """Get sync status."""
        return {
            "initialized": self.sync_dir.exists(),
            "last_full_sync": self.state.last_full_sync,
            "files_tracked": len(self.state.files),
            "watch_paths": self.state.watch_paths,
            "total_claims": sum(f.claims_extracted for f in self.state.files.values()),
            "domains": list(set(f.domain for f in self.state.files.values() if f.domain)),
        }

    def set_domain_mapping(self, pattern: str, domain: str):
        """
        Set a domain mapping for paths matching a pattern.

        Args:
            pattern: Path pattern to match
            domain: Domain to assign
        """
        self.state.domain_mappings[pattern] = domain
        self._save_state()

    def get_claims_for_file(self, file_path: str) -> list[Claim]:
        """Get all claims extracted from a specific file."""
        from .objects import ObjectType

        if file_path not in self.state.files:
            return []

        synced_file = self.state.files[file_path]
        claims = []

        for claim_hash in synced_file.claim_hashes:
            claim = self.repo.load(ObjectType.CLAIM, claim_hash)
            if claim:
                claims.append(claim)

        return claims

    def diff(self, paths: str | list[str] | None = None) -> dict:
        """
        Show what would change on next sync.

        Returns:
            Dict with new, changed, and deleted file lists
        """
        if paths is None:
            paths = self.state.watch_paths

        if not paths:
            return {"new": [], "changed": [], "deleted": [], "unchanged": []}

        all_files = self.scan(paths)
        new_files, changed_files, deleted_paths = self.get_changed_files(all_files)

        unchanged = [str(f) for f in all_files if f not in new_files and f not in changed_files]

        return {
            "new": [str(f) for f in new_files],
            "changed": [str(f) for f in changed_files],
            "deleted": deleted_paths,
            "unchanged": unchanged,
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def sync_docs(
    doc_path: str,
    repo_path: str = ".truth",
    force: bool = False,
    auto_verify: bool = False,
) -> SyncResult:
    """
    Convenience function to sync documentation.

    Args:
        doc_path: Path to documentation directory
        repo_path: Path to truth repository
        force: Force re-sync all files
        auto_verify: Auto-verify extracted claims

    Returns:
        SyncResult with statistics
    """
    from .repository import TruthRepository

    repo = TruthRepository(repo_path)
    if not repo.is_initialized():
        repo.init()

    sync = DocumentSync(repo)
    return sync.sync(doc_path, force=force, auto_verify=auto_verify)
