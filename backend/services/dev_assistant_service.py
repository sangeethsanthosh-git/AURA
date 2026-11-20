"""
AURA Development and Programming Assistant Service
Inspects Git status, summarized code diffs, project structure,
and executes approved project test commands under AURA Sandbox Protocol.
"""

from typing import Dict, Any, List, Optional
import os
import subprocess
import logging
from pathlib import Path
from backend.security.sandbox import AuraSandboxProtocol
from backend.security.process_sandbox import process_sandbox

logger = logging.getLogger(__name__)


class DevAssistantService:
    """Developer companion service for project inspection, Git telemetry, and test execution."""

    @staticmethod
    def get_project_root() -> Path:
        """Resolve current active project root."""
        return Path(__file__).resolve().parent.parent.parent

    @classmethod
    def get_git_status(cls, repo_dir: Optional[str] = None) -> Dict[str, Any]:
        """Inspect Git repository branch and modified files."""
        target_dir = Path(repo_dir) if repo_dir else cls.get_project_root()
        if not (target_dir / ".git").exists():
            return {
                "handled": True,
                "action": "git_status",
                "title": "Git Not Found",
                "message": f"'{target_dir}' is not a Git repository.",
                "spoken_response": "This project directory is not a Git repository.",
                "data": {"is_git": False},
            }

        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

            # 1. Branch name
            branch = subprocess.check_output(
                ["git", "branch", "--show-current"],
                cwd=str(target_dir),
                stderr=subprocess.DEVNULL,
                shell=False,
                startupinfo=si,
                creationflags=flags,
            ).decode("utf-8").strip() or "HEAD"

            # 2. Status short
            status_raw = subprocess.check_output(
                ["git", "status", "--porcelain"],
                cwd=str(target_dir),
                stderr=subprocess.DEVNULL,
                shell=False,
                startupinfo=si,
                creationflags=flags,
            ).decode("utf-8").strip()

            lines = [l for l in status_raw.splitlines() if l.strip()]
            modified = [l[3:] for l in lines if l[:2].strip() in ("M", "MM", "AM")]
            untracked = [l[3:] for l in lines if l[:2] == "??"]
            staged = [l[3:] for l in lines if l[0] in ("A", "M", "D", "R")]

            spoken = (
                f"On branch {branch}. Working tree is clean."
                if not lines
                else f"On branch {branch}. You have {len(modified)} modified file(s) and {len(untracked)} untracked file(s)."
            )

            return {
                "handled": True,
                "action": "git_status",
                "title": f"Git: {branch} ({len(lines)} changes)",
                "message": f"Branch '{branch}' · {len(modified)} modified · {len(untracked)} untracked · {len(staged)} staged",
                "spoken_response": spoken,
                "data": {
                    "is_git": True,
                    "branch": branch,
                    "total_changes": len(lines),
                    "modified": modified[:15],
                    "untracked": untracked[:15],
                    "staged": staged[:15],
                },
            }
        except Exception as e:
            logger.error(f"Error querying Git status: {e}")
            return {
                "handled": True,
                "action": "git_status",
                "title": "Git Query Error",
                "message": f"Could not inspect Git status: {e}",
                "spoken_response": "I encountered an error while inspecting Git status.",
                "data": {"error": str(e)},
            }

    @classmethod
    def get_git_diff_summary(cls, repo_dir: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve summarized diff statistics for uncommitted changes."""
        target_dir = Path(repo_dir) if repo_dir else cls.get_project_root()
        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
            stat_out = subprocess.check_output(
                ["git", "diff", "--stat"],
                cwd=str(target_dir),
                stderr=subprocess.DEVNULL,
                shell=False,
                startupinfo=si,
                creationflags=flags,
            ).decode("utf-8").strip()

            if not stat_out:
                return {
                    "handled": True,
                    "action": "git_diff",
                    "title": "Git Diff: Clean",
                    "message": "No uncommitted code changes in working tree.",
                    "spoken_response": "There are no uncommitted code changes.",
                    "data": {"has_changes": False},
                }

            lines = stat_out.splitlines()
            summary_line = lines[-1] if lines else ""
            file_summaries = lines[:-1][:10]

            spoken = f"Git diff summary: {summary_line}"

            return {
                "handled": True,
                "action": "git_diff",
                "title": f"Git Diff: {summary_line}",
                "message": "\n".join(file_summaries),
                "spoken_response": spoken,
                "data": {
                    "has_changes": True,
                    "summary": summary_line,
                    "files": file_summaries,
                },
            }
        except Exception as e:
            logger.error(f"Error querying Git diff: {e}")
            return {
                "handled": True,
                "action": "git_diff",
                "title": "Git Diff Error",
                "message": str(e),
                "spoken_response": "Could not retrieve Git diff.",
                "data": {"error": str(e)},
            }

    @classmethod
    def run_approved_unit_tests(cls) -> Dict[str, Any]:
        """Execute approved Python test suite in sandboxed non-interactive mode."""
        root = cls.get_project_root()
        venv_python = root / ".venv" / "Scripts" / "python.exe"
        python_bin = str(venv_python) if venv_python.exists() else "python"

        try:
            cmd = [python_bin, "-m", "unittest", "discover", "-s", "backend/tests", "-p", "test_*.py"]
            success, output, returncode = process_sandbox.run_sandboxed_command(
                cmd,
                cwd=str(root),
                timeout_seconds=45.0,
            )

            passed = "OK" in output and returncode == 0

            # Extract test count
            import re
            m = re.search(r"Ran (\d+) tests in ([\d.]+)s", output)
            count = m.group(1) if m else "all"
            elapsed = m.group(2) if m else "several"

            if passed:
                spoken = f"All {count} unit tests passed successfully in {elapsed} seconds."
                msg = f"PASSED: Ran {count} tests in {elapsed}s (All OK)"
            else:
                spoken = "Some unit tests failed or had errors. Check the test results card."
                msg = f"FAILED: Exit code {proc.returncode}\n{output[-300:]}"

            return {
                "handled": True,
                "action": "unit_tests",
                "title": f"Tests: {'PASSED' if passed else 'FAILED'}",
                "message": msg,
                "spoken_response": spoken,
                "data": {
                    "passed": passed,
                    "test_count": count,
                    "elapsed_seconds": elapsed,
                    "returncode": proc.returncode,
                },
            }
        except subprocess.TimeoutExpired:
            return {
                "handled": True,
                "action": "unit_tests",
                "title": "Tests: Timeout",
                "message": "Unit tests timed out after 45 seconds.",
                "spoken_response": "Test execution timed out.",
                "data": {"passed": False, "timeout": True},
            }
        except Exception as e:
            return {
                "handled": True,
                "action": "unit_tests",
                "title": "Test Runner Error",
                "message": str(e),
                "spoken_response": f"Failed to execute tests: {e}",
                "data": {"passed": False, "error": str(e)},
            }
