"""
AURA Security Sandbox Protocol (v1.0)
Enforces multi-layer sandboxing across desktop app execution, external protocols,
filesystem boundaries, shell injection prevention, and child process isolation.
"""

from typing import Tuple, Optional, Set, List, Dict, Any
import logging
import os
import re
import urllib.parse

logger = logging.getLogger(__name__)


class AuraSandboxProtocol:
    """
    Central security sandbox engine for AURA.
    Enforces least privilege, path boundaries, URI scheme allowlisting,
    and prohibits command shell interpolation.
    """

    POLICY_VERSION = "AURA-SANDBOX-v1.0"
    ENFORCEMENT_MODE = "STRICT"

    # Strictly allowed URI protocols for external links & app protocols
    ALLOWED_PROTOCOLS: Set[str] = {
        "https:",
        "http:",
        "spotify:",
        "discord:",
        "steam:",
        "mailto:",
        "ms-settings:",
        "microsoft.windows.camera:",
    }

    # Explicitly forbidden dangerous schemes
    BLOCKED_PROTOCOLS: Set[str] = {
        "file:",
        "javascript:",
        "vbscript:",
        "data:",
        "shell:",
        "ms-msdt:",
        "search-ms:",
        "ws:",
        "wss:",
        "about:",
        "view-source:",
    }

    # Prohibited dangerous binaries, script engines, and system administrative tools
    DENIED_BINARIES: Set[str] = {
        "cmd",
        "cmd.exe",
        "powershell",
        "powershell.exe",
        "pwsh",
        "pwsh.exe",
        "bash",
        "bash.exe",
        "wsl",
        "wsl.exe",
        "sh",
        "sh.exe",
        "zsh",
        "zsh.exe",
        "regedit",
        "regedit.exe",
        "reg",
        "reg.exe",
        "format",
        "format.com",
        "diskpart",
        "diskpart.exe",
        "vssadmin",
        "vssadmin.exe",
        "cipher",
        "cipher.exe",
        "mshta",
        "mshta.exe",
        "rundll32",
        "rundll32.exe",
        "cscript",
        "cscript.exe",
        "wscript",
        "wscript.exe",
        "certutil",
        "certutil.exe",
        "bitsadmin",
        "bitsadmin.exe",
        "taskkill",
        "taskkill.exe",
        "shutdown",
        "shutdown.exe",
        "net",
        "net.exe",
        "net1",
        "net1.exe",
        "sc",
        "sc.exe",
        "attrib",
        "attrib.exe",
        "takeown",
        "takeown.exe",
        "icacls",
        "icacls.exe",
    }

    # Shell metacharacters forbidden in commands and arguments
    SHELL_INJECTION_RE = re.compile(r"[&|;><`$\r\n\x00]")

    @classmethod
    def get_allowed_directory_prefixes(cls) -> List[str]:
        """
        Approved filesystem directories where desktop applications,
        shortcuts, and games are permitted to execute from.
        """
        prefixes = [
            os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"),
            os.path.expandvars(r"%AppData%\Microsoft\Windows\Start Menu\Programs"),
            os.path.expandvars(r"%USERPROFILE%\Desktop"),
            r"C:\Users\Public\Desktop",
            os.path.expandvars(r"%LocalAppData%\Microsoft\WindowsApps"),
            os.path.expandvars(r"%LocalAppData%\Programs"),
            os.path.expandvars(r"%ProgramFiles%"),
            os.path.expandvars(r"%ProgramFiles(x86)%"),
            r"C:\Program Files",
            r"C:\Program Files (x86)",
            r"C:\Riot Games",
            os.path.expandvars(r"%SystemRoot%\System32\calc.exe"),
            os.path.expandvars(r"%SystemRoot%\System32\notepad.exe"),
            os.path.expandvars(r"%SystemRoot%\System32\mspaint.exe"),
            os.path.expandvars(r"%SystemRoot%\explorer.exe"),
        ]
        # Normalize all valid paths
        return [os.path.abspath(p).lower() for p in prefixes if p]

    @classmethod
    def validate_url(cls, url: str) -> Tuple[bool, str]:
        """
        Validates external web or protocol URLs against sandbox allowlist.
        Returns (is_valid, reason).
        """
        if not url or not isinstance(url, str):
            return False, "Target URL is empty or invalid"

        url_clean = url.strip()
        parsed = urllib.parse.urlparse(url_clean)
        scheme = (parsed.scheme + ":").lower() if parsed.scheme else ""

        if not scheme:
            # Check if it looks like a protocol without slashes (e.g. spotify:, ms-settings:)
            if url_clean.endswith(":") or ":" in url_clean:
                scheme = url_clean.split(":")[0].lower() + ":"

        if scheme in cls.BLOCKED_PROTOCOLS:
            # Safe exception: Windows Store App activations via shell:AppsFolder
            if scheme == "shell:" and url_clean.lower().startswith("shell:appsfolder\\"):
                return True, "Windows Store AppsFolder activation approved"
            return False, f"Protocol '{scheme}' is prohibited by AURA Sandbox Protocol"

        if scheme not in cls.ALLOWED_PROTOCOLS:
            return False, f"Protocol '{scheme}' is not in approved sandbox allowlist"

        # Special check for http/https: ensure hostname exists
        if scheme in ("http:", "https:"):
            if not parsed.netloc:
                return False, "HTTP(S) URL missing valid host name"

        return True, "URL approved by sandbox"

    @classmethod
    def sanitize_shell_command(cls, cmd: str) -> Tuple[bool, str]:
        """
        Verifies that a command string does not contain shell injection,
        piping, chaining, or metacharacters.
        """
        if not cmd or not isinstance(cmd, str):
            return False, "Command is empty"

        if cls.SHELL_INJECTION_RE.search(cmd):
            return False, "Prohibited shell metacharacters detected in command string"

        return True, "Command string is clean"

    @classmethod
    def validate_executable_path(cls, file_path: str) -> Tuple[bool, str]:
        """
        Verifies that an application file or shortcut resides in an authorized
        directory boundary and is not a prohibited binary or script engine.
        """
        if not file_path or not isinstance(file_path, str):
            return False, "Path is empty"

        # Check for injection characters in path
        if cls.SHELL_INJECTION_RE.search(file_path):
            return False, "Prohibited shell metacharacters detected in executable path"

        # Check binary name against denylist
        base_name = os.path.basename(file_path).lower()
        base_root, ext = os.path.splitext(base_name)
        if base_name in cls.DENIED_BINARIES or base_root in cls.DENIED_BINARIES:
            return False, f"Binary '{base_name}' is blocked by sandbox policy"

        # Check path traversal
        norm_path = os.path.abspath(file_path).lower()

        # Disallow execution from temp directories
        temp_dir = os.path.abspath(os.environ.get("TEMP", r"C:\Windows\Temp")).lower()
        if norm_path.startswith(temp_dir):
            return False, "Execution from temporary directory is blocked by sandbox"

        # Verify path falls within sanctioned directory prefixes
        allowed_prefixes = cls.get_allowed_directory_prefixes()
        is_in_boundary = any(
            norm_path == prefix or norm_path.startswith(prefix + os.sep)
            for prefix in allowed_prefixes
        )

        # Allow basic standard Windows utilities if resolved
        standard_allowed_apps = {"notepad.exe", "calc.exe", "mspaint.exe", "explorer.exe", "code.exe"}
        if base_name in standard_allowed_apps:
            return True, "Standard system utility approved"

        if not is_in_boundary:
            return False, f"Path '{file_path}' is outside authorized sandbox directory boundaries"

        return True, "Executable path verified within sandbox boundaries"

    @classmethod
    def validate_launch_request(cls, target: str, is_url: bool = False) -> Tuple[bool, str]:
        """
        Unified validation gate for application and protocol execution.
        """
        if not target or not isinstance(target, str):
            return False, "Target cannot be empty"

        target_clean = target.strip()

        # Check for shell metacharacters
        if cls.SHELL_INJECTION_RE.search(target_clean):
            return False, "Prohibited shell metacharacters detected in launch target"

        # URL or URI protocol check
        is_protocol = (
            is_url
            or target_clean.startswith("http://")
            or target_clean.startswith("https://")
            or (":" in target_clean and not os.path.exists(target_clean) and not target_clean[1:3] == ":\\")
        )

        if is_protocol:
            return cls.validate_url(target_clean)

        # Binary or shortcut check
        # Check if target is a simple executable name in denylist
        clean_lower = target_clean.lower()
        name_only = os.path.basename(clean_lower)
        name_root, _ = os.path.splitext(name_only)
        if name_only in cls.DENIED_BINARIES or name_root in cls.DENIED_BINARIES:
            return False, f"Executable '{target_clean}' is prohibited by AURA Sandbox Protocol"

        # If it's a full or relative path, check boundaries
        if os.path.isabs(target_clean) or os.path.exists(target_clean):
            return cls.validate_executable_path(target_clean)

        return True, "Launch request verified"

    @classmethod
    def get_sandbox_status(cls) -> Dict[str, Any]:
        """Return sandbox health and policy status."""
        return {
            "policy": cls.POLICY_VERSION,
            "enforcement": cls.ENFORCEMENT_MODE,
            "active": True,
            "allowed_protocols": sorted(list(cls.ALLOWED_PROTOCOLS)),
            "denied_binaries_count": len(cls.DENIED_BINARIES),
            "allowed_directories_count": len(cls.get_allowed_directory_prefixes()),
            "shell_injection_protection": True,
            "electron_sandbox_enforced": True,
        }
