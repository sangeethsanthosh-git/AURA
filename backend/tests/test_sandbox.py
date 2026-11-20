"""
Unit tests for AURA Security Sandbox Protocol (v1.0).
Tests URI allowlist, executable denylist, shell injection prevention,
filesystem boundaries, SystemToolService integration, and API telemetry.
"""

import os
import unittest
from backend.security.sandbox import AuraSandboxProtocol
from backend.services.system_tool_service import SystemToolService
from fastapi.testclient import TestClient
from backend.api.app import app


class TestAuraSandboxProtocol(unittest.TestCase):
    """Test suite for AuraSandboxProtocol validation engine."""

    def test_allowed_uri_protocols(self):
        """Verify standard safe web & app protocols pass validation."""
        safe_urls = [
            "https://www.youtube.com",
            "https://www.google.com/search?q=test",
            "http://127.0.0.1:8000/health",
            "spotify:",
            "discord:",
            "steam:",
            "mailto:support@example.com",
            "ms-settings:",
            "microsoft.windows.camera:",
        ]
        for url in safe_urls:
            is_valid, reason = AuraSandboxProtocol.validate_url(url)
            self.assertTrue(is_valid, f"Expected '{url}' to be approved, but got: {reason}")

    def test_blocked_dangerous_uri_protocols(self):
        """Verify dangerous schemes (file, javascript, data, shell, etc.) are strictly blocked."""
        dangerous_urls = [
            "file:///C:/Windows/System32/cmd.exe",
            "file://localhost/etc/passwd",
            "javascript:alert(document.cookie)",
            "vbscript:MsgBox('pwned')",
            "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
            "shell:startup",
            "ms-msdt:/id PCWDiagnostic",
            "search-ms:crumb=location:C:\\",
            "ws://malicious-c2.com",
            "about:blank",
            "view-source:https://google.com",
        ]
        for url in dangerous_urls:
            is_valid, reason = AuraSandboxProtocol.validate_url(url)
            self.assertFalse(is_valid, f"Expected dangerous URL '{url}' to be blocked, but it passed.")
            self.assertIn("prohibited", reason.lower())

    def test_denied_binaries_and_interpreters(self):
        """Verify command line interpreters and administrative tools are blocked."""
        denied_targets = [
            "cmd",
            "cmd.exe",
            "powershell",
            "powershell.exe",
            "pwsh",
            "pwsh.exe",
            "regedit.exe",
            "format.com",
            "vssadmin.exe",
            "cipher.exe",
            "rundll32.exe",
            "mshta.exe",
            "certutil.exe",
            "bitsadmin.exe",
            "taskkill.exe",
        ]
        for binary in denied_targets:
            is_safe, reason = AuraSandboxProtocol.validate_launch_request(binary)
            self.assertFalse(is_safe, f"Expected binary '{binary}' to be blocked, but it was approved.")
            self.assertIn("prohibited", reason.lower())

    def test_shell_injection_metacharacter_prevention(self):
        """Verify that shell piping, chaining, and redirection are blocked."""
        malicious_inputs = [
            "calc.exe & del /f /q C:\\*",
            "notepad.exe | dir",
            "calc; ping 127.0.0.1",
            "code && echo pwned",
            "app > output.txt",
            "run `whoami`",
            "launch $(dir)",
            "calc\nnotepad",
            "calc\r\ncmd.exe",
        ]
        for cmd in malicious_inputs:
            is_safe, reason = AuraSandboxProtocol.validate_launch_request(cmd)
            self.assertFalse(is_safe, f"Expected shell injection '{cmd}' to be blocked.")
            self.assertIn("shell metacharacters", reason.lower())

    def test_temp_directory_execution_blocked(self):
        """Verify that binaries in temp directories are rejected."""
        temp_dir = os.environ.get("TEMP", r"C:\Windows\Temp")
        malicious_temp_path = os.path.join(temp_dir, "untrusted_payload.exe")
        is_safe, reason = AuraSandboxProtocol.validate_executable_path(malicious_temp_path)
        self.assertFalse(is_safe)
        self.assertIn("temporary directory", reason.lower())

    def test_system_tool_service_launches_safe_apps(self):
        """Verify safe apps still launch without sandbox interference."""
        # YouTube
        res_yt = SystemToolService.launch_app("youtube")
        self.assertTrue(res_yt.get("handled"))
        self.assertEqual(res_yt.get("action"), "app_launch")

        # Spotify
        res_spot = SystemToolService.launch_app("spotify")
        self.assertTrue(res_spot.get("handled"))
        self.assertEqual(res_spot.get("action"), "app_launch")

    def test_system_tool_service_blocks_cmd_and_powershell(self):
        """Verify SystemToolService returns sandbox_blocked for cmd and powershell."""
        res_cmd = SystemToolService.launch_app("cmd")
        self.assertTrue(res_cmd.get("handled"))
        self.assertEqual(res_cmd.get("action"), "sandbox_blocked")
        self.assertIn("Sandbox Alert", res_cmd.get("title", ""))
        self.assertEqual(res_cmd.get("data", {}).get("status"), "BLOCKED")

        res_ps = SystemToolService.launch_app("powershell")
        self.assertTrue(res_ps.get("handled"))
        self.assertEqual(res_ps.get("action"), "sandbox_blocked")
        self.assertEqual(res_ps.get("data", {}).get("status"), "BLOCKED")

    def test_system_tool_service_blocks_injection_attempt(self):
        """Verify SystemToolService catches piped commands."""
        res_inj = SystemToolService.launch_app("notepad & format c:")
        self.assertTrue(res_inj.get("handled"))
        self.assertEqual(res_inj.get("action"), "sandbox_blocked")
        self.assertEqual(res_inj.get("data", {}).get("status"), "BLOCKED")

    def test_api_sandbox_status(self):
        """Verify /api/sandbox/status endpoint returns active status and policy."""
        client = TestClient(app)
        res = client.get("/api/sandbox/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("active"))
        self.assertEqual(data.get("policy"), "AURA-SANDBOX-v1.0")
        self.assertEqual(data.get("enforcement"), "STRICT")
        self.assertIn("https:", data.get("allowed_protocols", []))
        self.assertTrue(data.get("shell_injection_protection"))
        self.assertTrue(data.get("electron_sandbox_enforced"))


if __name__ == "__main__":
    unittest.main()
