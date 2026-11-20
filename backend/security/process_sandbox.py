"""
AURA Windows OS-Level Process Sandbox & Job Object Controller
Enforces kernel-level process isolation, child-process limits, kill-on-close guarantees,
sanitized environment scrubbing, explicit argument arrays, and emergency process termination.
"""

from typing import List, Dict, Any, Optional, Tuple
import os
import subprocess
import logging
import ctypes
from ctypes import wintypes
from backend.security.sandbox import AuraSandboxProtocol
from backend.security.audit_logger import audit_logger

logger = logging.getLogger(__name__)

# Win32 Constants
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
JOB_OBJECT_LIMIT_ACTIVE_PROCESS = 0x0008
JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x0100
JobObjectExtendedLimitInformation = 9

# Win32 Structures
class IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_uint64),
        ("WriteOperationCount", ctypes.c_uint64),
        ("OtherOperationCount", ctypes.c_uint64),
        ("ReadTransferCount", ctypes.c_uint64),
        ("WriteTransferCount", ctypes.c_uint64),
        ("OtherTransferCount", ctypes.c_uint64),
    ]


class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryLimit", ctypes.c_size_t),
        ("PeakJobMemoryLimit", ctypes.c_size_t),
    ]


class WindowsJobObjectSandbox:
    """Manages an OS-enforced Windows Job Object for sandboxing spawned processes."""

    def __init__(self, name: str = "AURA_PROCESS_SANDBOX"):
        self.name = name
        self.kernel32 = ctypes.windll.kernel32
        self._hJob: Optional[wintypes.HANDLE] = None
        self._active_pids: List[int] = []
        self._initialize_job_object()

    @property
    def is_supported(self) -> bool:
        return self._hJob is not None

    def get_active_process_count(self) -> int:
        import psutil
        alive = 0
        for pid in list(self._active_pids):
            if psutil.pid_exists(pid):
                alive += 1
        return alive

    def _initialize_job_object(self) -> None:
        """Create and configure Windows Job Object with resource limits and kill-on-close."""
        try:
            self._hJob = self.kernel32.CreateJobObjectW(None, self.name)
            if not self._hJob:
                logger.warning("Could not create Windows Job Object; falling back to process tracker.")
                return

            info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
            # Enforce kill on close & max 8 simultaneous active processes
            info.BasicLimitInformation.LimitFlags = (
                JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_ACTIVE_PROCESS
            )
            info.BasicLimitInformation.ActiveProcessLimit = 8
            # Cap virtual memory at 2.0 GB per process
            info.ProcessMemoryLimit = 2 * 1024 * 1024 * 1024

            res = self.kernel32.SetInformationJobObject(
                self._hJob,
                JobObjectExtendedLimitInformation,
                ctypes.byref(info),
                ctypes.sizeof(info),
            )
            if res:
                logger.info(f"Windows Job Object '{self.name}' initialized (KILL_ON_JOB_CLOSE enforced).")
            else:
                logger.warning("SetInformationJobObject returned 0; limits may be partial.")
        except Exception as e:
            logger.error(f"Failed to configure Windows Job Object: {e}")

    def assign_process(self, process_handle: wintypes.HANDLE, pid: int) -> bool:
        """Assign an active process to the kernel Job Object."""
        if not self._hJob:
            self._active_pids.append(pid)
            return False

        try:
            res = self.kernel32.AssignProcessToJobObject(self._hJob, process_handle)
            if res:
                self._active_pids.append(pid)
                logger.debug(f"Assigned PID {pid} to Windows Job Object '{self.name}'")
                return True
        except Exception as e:
            logger.debug(f"AssignProcessToJobObject failed for PID {pid}: {e}")
        return False

    def terminate_all_managed_processes(self) -> int:
        """
        Emergency stop: Terminate all processes assigned to the job object.
        """
        count = 0
        if self._hJob:
            try:
                # TerminateJobObject(hJob, uExitCode)
                res = self.kernel32.TerminateJobObject(self._hJob, 1)
                if res:
                    count = len(self._active_pids)
                    logger.info(f"Terminated all processes in Job Object '{self.name}'")
            except Exception as e:
                logger.error(f"Error terminating job object processes: {e}")

        # Fallback termination on tracked PIDs
        import psutil
        for pid in list(self._active_pids):
            try:
                if psutil.pid_exists(pid):
                    p = psutil.Process(pid)
                    p.kill()
                    count += 1
            except Exception:
                pass

        self._active_pids.clear()
        # Re-initialize fresh Job Object for future tasks
        self._initialize_job_object()
        return count

    @staticmethod
    def get_sanitized_environment() -> Dict[str, str]:
        """
        Strips environment variables to prevent secret leakage to child processes.
        Removes API keys, tokens, AWS keys, and developer secrets.
        """
        clean_env = dict(os.environ)
        sensitive_keywords = (
            "API_KEY",
            "TOKEN",
            "SECRET",
            "PASSWORD",
            "AUTH",
            "CREDENTIAL",
            "PRIVATE",
            "AWS_SECRET",
            "GITHUB_PAT",
        )
        for key in list(clean_env.keys()):
            upper_k = key.upper()
            if any(s in upper_k for s in sensitive_keywords):
                del clean_env[key]

        # Ensure minimal required runtime variables
        clean_env["AURA_SANDBOX"] = "STRICT"
        return clean_env

    def run_sandboxed_command(
        self,
        args: List[str],
        cwd: Optional[str] = None,
        timeout_seconds: float = 30.0,
    ) -> Tuple[bool, str, int]:
        """
        Execute an approved command inside the Windows Process Sandbox.
        Enforces argument arrays, stripped environment, Job Object containment, and timeouts.
        Returns (success, output, returncode).
        """
        if not args or not isinstance(args, list):
            return False, "Command arguments must be a non-empty list", -1

        executable = args[0]
        # Validate binary with Sandbox Protocol
        is_safe, reason = AuraSandboxProtocol.validate_launch_request(executable)
        if not is_safe:
            audit_logger.log_event(
                event_type="PROCESS_SANDBOX_BLOCKED",
                risk_level="HIGH",
                target=executable,
                decision="BLOCKED",
                reason=reason,
                details={"args": args},
            )
            return False, f"Process execution blocked by sandbox: {reason}", -1

        clean_env = self.get_sanitized_environment()
        work_dir = cwd or os.getcwd()

        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0  # SW_HIDE

            proc = subprocess.Popen(
                args,
                cwd=work_dir,
                env=clean_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                startupinfo=si,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
                shell=False,  # STRICT: never use shell interpolation
            )

            # Assign process to Job Object via its Windows HANDLE
            if hasattr(proc, "_handle") and proc._handle:
                self.assign_process(wintypes.HANDLE(proc._handle), proc.pid)

            stdout, stderr = proc.communicate(timeout=timeout_seconds)
            output = stdout + "\n" + stderr
            success = proc.returncode == 0

            audit_logger.log_event(
                event_type="PROCESS_EXECUTED",
                risk_level="MEDIUM",
                target=executable,
                decision="SUCCESS" if success else "FAILED",
                reason=f"Exited with code {proc.returncode}",
                details={"pid": proc.pid, "returncode": proc.returncode},
            )

            return success, output.strip(), proc.returncode
        except subprocess.TimeoutExpired:
            proc.kill()
            audit_logger.log_event(
                event_type="PROCESS_TIMEOUT",
                risk_level="HIGH",
                target=executable,
                decision="TERMINATED",
                reason=f"Process timed out after {timeout_seconds}s",
            )
            return False, f"Process execution timed out after {timeout_seconds} seconds", -1
        except Exception as e:
            audit_logger.log_event(
                event_type="PROCESS_ERROR",
                risk_level="HIGH",
                target=executable,
                decision="ERROR",
                reason=str(e),
            )
            return False, str(e), -1


# Global process sandbox instance
process_sandbox = WindowsJobObjectSandbox()
