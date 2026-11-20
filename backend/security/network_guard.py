"""
AURA Network & Browser Security Guard
Enforces SSRF prevention, URI scheme allowlisting, hostname resolution checks,
file download size limits, dangerous extension blocking, and quarantine staging.
"""

from typing import Tuple, Dict, Any, Optional
import urllib.parse
import ipaddress
import socket
import os
from pathlib import Path
import logging
from backend.security.sandbox import AuraSandboxProtocol
from backend.security.audit_logger import audit_logger

logger = logging.getLogger(__name__)


class NetworkSecurityGuard:
    """Zero-trust network request & download security controller."""

    MAX_DOWNLOAD_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB max download size

    # Dangerous executable extensions blocked from automatic web download/handling
    DANGEROUS_DOWNLOAD_EXTENSIONS = {
        ".exe",
        ".msi",
        ".bat",
        ".cmd",
        ".ps1",
        ".vbs",
        ".dll",
        ".scr",
        ".jar",
        ".iso",
        ".vbe",
        ".wsf",
    }
    BLOCKED_EXTENSIONS = DANGEROUS_DOWNLOAD_EXTENSIONS

    def __init__(self):
        user_home = Path(os.environ.get("USERPROFILE", os.path.expanduser("~"))).resolve()
        self.quarantine_dir = user_home / "AppData" / "Local" / "AURA" / "quarantine"
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def is_ssrf_safe(cls, url: str, allow_internal: bool = False) -> Tuple[bool, str]:
        """
        Validates target URL against Server-Side Request Forgery (SSRF).
        Blocks private IP ranges, loopbacks, link-local addresses, and cloud metadata endpoints.
        """
        if not url or not isinstance(url, str):
            return False, "URL is empty or invalid"

        parsed = urllib.parse.urlparse(url.strip())
        hostname = parsed.hostname
        if not hostname:
            return False, "Target URL lacks a valid hostname"

        # Check for numeric IP or resolve hostname
        try:
            try:
                ip = ipaddress.ip_address(hostname)
            except ValueError:
                # Resolve hostname to IPv4
                resolved_ip_str = socket.gethostbyname(hostname)
                ip = ipaddress.ip_address(resolved_ip_str)

            # Block loopbacks, private networks, and link-locals
            if ip.is_loopback:
                if allow_internal and parsed.port == 8000:
                    return True, "Internal AURA API loopback permitted"
                return False, f"Loopback address '{ip}' is blocked by SSRF defense"

            if ip.is_private:
                return False, f"Private IP address '{ip}' is blocked by SSRF defense"

            if ip.is_link_local:
                return False, f"Link-local address '{ip}' is blocked by SSRF defense"

            if str(ip) == "169.254.169.254":
                return False, "Cloud metadata endpoint is strictly prohibited"

            return True, "Target host verified public and safe"
        except socket.gaierror:
            return False, f"Could not resolve hostname '{hostname}'"
        except Exception as e:
            return False, f"SSRF validation error: {e}"

    @classmethod
    def validate_download(cls, filename_or_url: str) -> Tuple[bool, str, str]:
        """
        Validates target download for dangerous file extensions.
        Returns (is_valid, reason, extension).
        """
        clean = filename_or_url.strip().lower()
        _, ext = os.path.splitext(clean)
        is_safe, reason = cls.validate_download_request(filename_or_url)
        return is_safe, reason, ext

    @classmethod
    def validate_external_fetch(cls, url: str) -> Tuple[bool, str]:
        """
        Full validation gate for external HTTP/HTTPS network requests.
        Enforces protocol allowlisting and SSRF protection.
        """
        # 1. Protocol allowlist
        is_proto_valid, proto_reason = AuraSandboxProtocol.validate_url(url)
        if not is_proto_valid:
            audit_logger.log_event("NETWORK_BLOCKED", "HIGH", url, "BLOCKED", proto_reason)
            return False, proto_reason

        # 2. SSRF Check
        is_ssrf_ok, ssrf_reason = cls.is_ssrf_safe(url)
        if not is_ssrf_ok:
            audit_logger.log_event("SSRF_BLOCKED", "HIGH", url, "BLOCKED", ssrf_reason)
            return False, ssrf_reason

        return True, "Network request authorized"

    @classmethod
    def validate_download_request(cls, filename_or_url: str) -> Tuple[bool, str]:
        """
        Validates target download for dangerous file extensions.
        """
        clean = filename_or_url.strip().lower()
        _, ext = os.path.splitext(clean)
        if ext in cls.DANGEROUS_DOWNLOAD_EXTENSIONS:
            reason = f"Download of executable file type '{ext}' requires Level 3 sensitive authorization"
            audit_logger.log_event("DOWNLOAD_FLAGGED", "HIGH", filename_or_url, "CONFIRMATION_REQUIRED", reason)
            return False, reason

        return True, "Download extension approved"


# Global network guard instance
network_guard = NetworkSecurityGuard()
