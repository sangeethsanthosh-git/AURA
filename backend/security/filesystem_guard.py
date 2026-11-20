"""
AURA Filesystem Security Guard
Enforces canonical path resolution, path traversal defense, symlink/reparse point checks,
sensitive directory boundaries, and automated shadow backup before destructive modifications.
"""

from typing import Tuple, List, Optional, Dict, Any
import os
import shutil
from pathlib import Path
import logging
from datetime import datetime
from backend.security.audit_logger import audit_logger

logger = logging.getLogger(__name__)


class FilesystemGuard:
    """Enforces strict directory-level boundaries and shadow backup for filesystem operations."""

    def __init__(self):
        user_home = Path(os.environ.get("USERPROFILE", os.path.expanduser("~"))).resolve()
        project_root = Path(__file__).resolve().parent.parent.parent

        # Approved functional boundaries
        self.allowed_roots: List[Path] = [
            project_root,
            user_home / "Desktop",
            user_home / "Downloads",
            user_home / "Documents",
            user_home / "Pictures",
            user_home / "Videos",
            user_home / "Music",
            user_home / "AppData" / "Local" / "AURA",
            user_home / "AppData" / "Roaming" / "AURA",
        ]

        # Sensitive directories strictly blocked from read/write/traversal
        self.blocked_directories: List[Path] = [
            Path(os.environ.get("SystemRoot", r"C:\Windows")).resolve(),
            Path(r"C:\Windows\System32").resolve(),
            Path(r"C:\Windows\SysWOW64").resolve(),
            Path(r"C:\ProgramData\Microsoft\Windows Defender").resolve(),
            user_home / ".ssh",
            user_home / ".aws",
            user_home / ".azure",
            user_home / ".gnupg",
            user_home / "AppData" / "Local" / "Google" / "Chrome" / "User Data",
            user_home / "AppData" / "Local" / "Microsoft" / "Edge" / "User Data",
            user_home / "AppData" / "Roaming" / "Mozilla" / "Firefox" / "Profiles",
        ]

        # Shadow backup directory for rollback
        self.backup_dir = user_home / "AppData" / "Local" / "AURA" / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def validate_path_access(self, target_path: str, write_operation: bool = False) -> Tuple[bool, str, Optional[Path]]:
        """
        Validates target path against canonical resolution, path traversal,
        reparse point / symlink escapes, and boundary allowlists.
        Returns (is_valid, reason, resolved_path).
        """
        if not target_path or not isinstance(target_path, str):
            return False, "Target path is empty or invalid", None

        # 1. Null byte & ADS stream injection check
        if "\x00" in target_path or (":$" in target_path or target_path.count(":") > 1):
            reason = "Illegal characters or NTFS alternative data stream detected in path"
            audit_logger.log_event("FILESYSTEM_BLOCKED", "HIGH", target_path, "BLOCKED", reason)
            return False, reason, None

        # 2. Canonical path resolution
        try:
            canonical = Path(target_path).resolve()
        except Exception as e:
            reason = f"Could not resolve canonical path: {e}"
            audit_logger.log_event("FILESYSTEM_BLOCKED", "MEDIUM", target_path, "BLOCKED", reason)
            return False, reason, None

        # 3. Check for symlink / reparse point target escape
        if canonical.is_symlink():
            try:
                sym_target = canonical.readlink().resolve()
                canonical = sym_target
            except Exception as e:
                reason = f"Failed to verify symlink target: {e}"
                audit_logger.log_event("FILESYSTEM_BLOCKED", "HIGH", target_path, "BLOCKED", reason)
                return False, reason, None

        canonical_str = str(canonical).lower()

        # 4. Sensitive Directory Blocklist Check
        for blocked in self.blocked_directories:
            blocked_str = str(blocked).lower()
            if canonical_str == blocked_str or canonical_str.startswith(blocked_str + os.sep):
                reason = f"Access to sensitive directory '{blocked.name}' is prohibited by policy"
                audit_logger.log_event("FILESYSTEM_BLOCKED", "CRITICAL", str(canonical), "BLOCKED", reason)
                return False, reason, canonical

        # 5. Boundary Allowlist Check (for write operations)
        if write_operation:
            in_allowed_boundary = any(
                canonical_str == str(allowed).lower() or canonical_str.startswith(str(allowed).lower() + os.sep)
                for allowed in self.allowed_roots
            )
            if not in_allowed_boundary:
                reason = f"Target location '{canonical}' is outside approved write boundaries"
                audit_logger.log_event("FILESYSTEM_BLOCKED", "HIGH", str(canonical), "BLOCKED", reason)
                return False, reason, canonical

        return True, "Path access authorized", canonical

    def create_shadow_backup(self, file_path: Path) -> Optional[Path]:
        """
        Creates a timestamped shadow copy of a file before any modification or deletion.
        Enables user recovery from accidental changes.
        """
        if not file_path.exists() or not file_path.is_file():
            return None

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
            dest = self.backup_dir / backup_name
            shutil.copy2(file_path, dest)
            audit_logger.log_event(
                "SHADOW_BACKUP_CREATED",
                "LOW",
                str(file_path),
                "BACKUP_SAVED",
                f"Shadow copy saved to {backup_name}",
                details={"original": str(file_path), "backup": str(dest)},
            )
            return dest
        except Exception as e:
            logger.error(f"Failed to create shadow backup for '{file_path}': {e}")
            return None

    def list_backups(self) -> List[Dict[str, Any]]:
        """List available shadow backups."""
        backups = []
        if self.backup_dir.exists():
            for f in self.backup_dir.glob("*"):
                if f.is_file():
                    stat = f.stat()
                    backups.append({
                        "name": f.name,
                        "path": str(f),
                        "size_bytes": stat.st_size,
                        "modified": stat.st_mtime,
                    })
        backups.sort(key=lambda x: x["modified"], reverse=True)
        return backups


# Global filesystem guard instance
filesystem_guard = FilesystemGuard()
