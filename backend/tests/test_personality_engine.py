"""
Unit and integration tests for AURA Dynamic Personality, Social Behaviour & Relationship Engine.
"""

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import json

from backend.conversation.storage import ConversationStorage
from backend.services.personality_service import (
    PersonalityService,
    PersonalityProfile,
    PersonalitySettings,
)
from fastapi.testclient import TestClient
from backend.api.app import app


class TestPersonalityEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_personality.db"
        self.storage = ConversationStorage(db_path=self.db_path)
        self.service = PersonalityService(storage=self.storage)

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_default_settings(self):
        settings = self.service.get_settings()
        self.assertEqual(settings.default_profile, PersonalityProfile.NORMAL.value)
        self.assertEqual(settings.current_profile, PersonalityProfile.NORMAL.value)
        self.assertFalse(settings.is_temporary_override)
        self.assertTrue(settings.auto_switch_enabled)
        self.assertEqual(settings.explanation_depth, "balanced")

    def test_all_six_profiles_prompts(self):
        """Verify each profile produces unique behavioral directives and contains strict safety boundaries."""
        profiles = [p.value for p in PersonalityProfile]
        self.assertEqual(len(profiles), 6)

        for prof in profiles:
            prompt = self.service.generate_system_prompt_instructions(prof)
            self.assertIn(f"Active Persona Profile: {prof.upper()}", prompt)
            self.assertIn("STRICT BEHAVIOURAL & ETHICAL BOUNDARIES", prompt)
            self.assertIn("NEVER mock, tease, or minimize genuine distress", prompt)
            self.assertIn("NEVER pretend to be a human", prompt)
            self.assertIn("NEVER allow personality instructions or roleplay to compromise security", prompt)

        # Profile specific checks
        friend_prompt = self.service.generate_system_prompt_instructions(PersonalityProfile.FRIEND.value)
        self.assertIn("FRIEND mode", friend_prompt)
        self.assertIn("casual, warm, conversational", friend_prompt)

        teacher_prompt = self.service.generate_system_prompt_instructions(PersonalityProfile.TEACHER.value)
        self.assertIn("TEACHER mode", teacher_prompt)
        self.assertIn("fundamentals", teacher_prompt)

        prof_prompt = self.service.generate_system_prompt_instructions(PersonalityProfile.PROFESSIONAL.value)
        self.assertIn("PROFESSIONAL mode", prof_prompt)
        self.assertIn("task-oriented", prof_prompt)

        supp_prompt = self.service.generate_system_prompt_instructions(PersonalityProfile.SUPPORTIVE.value)
        self.assertIn("SUPPORTIVE mode", supp_prompt)
        self.assertIn("empathetic", supp_prompt)

        misch_prompt = self.service.generate_system_prompt_instructions(PersonalityProfile.MISCHIEVOUS.value)
        self.assertIn("MISCHIEVOUS mode", misch_prompt)
        self.assertIn("playful trolling", misch_prompt)

    def test_manual_command_interception(self):
        """Test regex-based sub-millisecond personality command detection."""
        # 1. Friend
        res = self.service.check_manual_command("act like my friend please")
        self.assertIsNotNone(res)
        self.assertEqual(res[0], PersonalityProfile.FRIEND.value)
        self.assertFalse(res[1])

        # 2. Teacher
        res = self.service.check_manual_command("teach me this topic")
        self.assertIsNotNone(res)
        self.assertEqual(res[0], PersonalityProfile.TEACHER.value)

        # 3. Normal
        res = self.service.check_manual_command("talk normally from now on")
        self.assertIsNotNone(res)
        self.assertEqual(res[0], PersonalityProfile.NORMAL.value)

        # 4. Professional / Serious
        res = self.service.check_manual_command("be serious")
        self.assertIsNotNone(res)
        self.assertEqual(res[0], PersonalityProfile.PROFESSIONAL.value)

        # 5. Stop joking (Temporary serious)
        res = self.service.check_manual_command("stop joking")
        self.assertIsNotNone(res)
        self.assertEqual(res[0], PersonalityProfile.PROFESSIONAL.value)
        self.assertTrue(res[1])

        # 6. Supportive
        res = self.service.check_manual_command("be supportive, I need to talk")
        self.assertIsNotNone(res)
        self.assertEqual(res[0], PersonalityProfile.SUPPORTIVE.value)

        # 7. Mischievous / Roast
        res = self.service.check_manual_command("roast me!")
        self.assertIsNotNone(res)
        self.assertEqual(res[0], PersonalityProfile.MISCHIEVOUS.value)

        # 8. Temporary override
        res = self.service.check_manual_command("be serious for a moment")
        self.assertIsNotNone(res)
        self.assertEqual(res[0], PersonalityProfile.PROFESSIONAL.value)
        self.assertTrue(res[1])  # is_temporary should be True

        # 9. Reset to default
        res = self.service.check_manual_command("switch back to default")
        self.assertIsNotNone(res)
        self.assertEqual(res[0], self.service.settings.default_profile)

        # 10. Non-command query returns None
        self.assertIsNone(self.service.check_manual_command("what is the weather in Tokyo"))

    def test_context_aware_auto_inference(self):
        """Test automatic context-driven behaviour inference when auto-switch is active."""
        # Technical -> Teacher
        inferred = self.service.infer_context_profile("how does a jet engine work?")
        self.assertEqual(inferred, PersonalityProfile.TEACHER.value)

        # System ops -> Professional
        inferred = self.service.infer_context_profile("check git status and modified files")
        self.assertEqual(inferred, PersonalityProfile.PROFESSIONAL.value)

        # Personal distress -> Supportive
        inferred = self.service.infer_context_profile("I am so stressed and overwhelmed with work")
        self.assertEqual(inferred, PersonalityProfile.SUPPORTIVE.value)

        # Sarcastic provocation -> Mischievous (with sarcasm > 20)
        self.service.update_settings({"sarcasm_intensity": 50})
        inferred = self.service.infer_context_profile("you don't know anything, prove me wrong")
        self.assertEqual(inferred, PersonalityProfile.MISCHIEVOUS.value)

        # Disabled auto switch returns None
        self.service.update_settings({"auto_switch_enabled": False})
        self.assertIsNone(self.service.infer_context_profile("how does a jet engine work?"))

    def test_sqlite_persistence(self):
        """Test settings updates survive service reload via SQLite."""
        self.service.update_settings({
            "default_profile": PersonalityProfile.TEACHER.value,
            "humor_intensity": 80,
            "sarcasm_intensity": 45,
            "formality": 70,
            "explanation_depth": "in_depth",
            "auto_switch_enabled": False,
        })

        # Reload new service instance connected to same SQLite db
        reloaded_service = PersonalityService(storage=self.storage)
        reloaded_settings = reloaded_service.get_settings()

        self.assertEqual(reloaded_settings.default_profile, PersonalityProfile.TEACHER.value)
        self.assertEqual(reloaded_settings.humor_intensity, 80)
        self.assertEqual(reloaded_settings.sarcasm_intensity, 45)
        self.assertEqual(reloaded_settings.formality, 70)
        self.assertEqual(reloaded_settings.explanation_depth, "in_depth")
        self.assertFalse(reloaded_settings.auto_switch_enabled)

    def test_companion_mood_and_voice_mappings(self):
        """Test expression and voice delivery mappings for companion visual engine."""
        self.assertEqual(self.service.get_companion_mood(PersonalityProfile.FRIEND.value), "happy")
        self.assertEqual(self.service.get_companion_mood(PersonalityProfile.TEACHER.value), "think")
        self.assertEqual(self.service.get_companion_mood(PersonalityProfile.MISCHIEVOUS.value), "wink")
        self.assertEqual(self.service.get_companion_mood(PersonalityProfile.SUPPORTIVE.value), "gentle")

        v_teach = self.service.get_voice_parameters(PersonalityProfile.TEACHER.value)
        self.assertEqual(v_teach["rate"], 0.95)
        self.assertIn("instructional", v_teach["tone"])

        v_prof = self.service.get_voice_parameters(PersonalityProfile.PROFESSIONAL.value)
        self.assertEqual(v_prof["rate"], 1.05)

    def test_personality_never_compromises_security_or_tool_authorization(self):
        """Verify that personality changes never alter actual tool permissions or action authorization."""
        from backend.security import permission_gateway, AuraSandboxProtocol
        from backend.security.permission_gateway import PermissionDecision

        # Test across multiple personalities including mischievous and friend
        for prof in [PersonalityProfile.MISCHIEVOUS.value, PersonalityProfile.FRIEND.value, PersonalityProfile.PROFESSIONAL.value]:
            self.service.set_active_profile(prof)

            # 1. Critical actions must still be blocked or require confirmation regardless of active persona
            decision_reg, _, _ = permission_gateway.evaluate_request("registry_write", target=r"HKLM\Software")
            self.assertEqual(decision_reg, PermissionDecision.DENIED, f"registry_write must be DENIED under {prof}")

            decision_uac, _, _ = permission_gateway.evaluate_request("disable_uac", target="")
            self.assertEqual(decision_uac, PermissionDecision.DENIED, f"disable_uac must be DENIED under {prof}")

            # 2. Malicious commands must still be caught by sandbox
            safe_cmd, _ = AuraSandboxProtocol.validate_launch_request("powershell -Command Remove-Item -Recurse C:\\Windows")
            self.assertFalse(safe_cmd, f"Malicious command must be blocked under {prof}")


class TestPersonalityAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_get_personality_endpoint(self):
        res = self.client.get("/api/personality")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("settings", data)
        self.assertIn("profiles", data)
        self.assertIn("mood", data)
        self.assertIn("voice", data)
        self.assertEqual(len(data["profiles"]), 6)

    def test_update_personality_endpoint(self):
        payload = {
            "humor_intensity": 75,
            "sarcasm_intensity": 60,
            "explanation_depth": "concise",
        }
        res = self.client.post("/api/personality", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["settings"]["humor_intensity"], 75)
        self.assertEqual(data["settings"]["sarcasm_intensity"], 60)
        self.assertEqual(data["settings"]["explanation_depth"], "concise")

    def test_profile_switch_and_reset_endpoints(self):
        # Switch to friend
        res = self.client.post("/api/personality/profile", json={"profile": "friend", "temporary": True})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["settings"]["current_profile"], "friend")
        self.assertTrue(res.json()["settings"]["is_temporary_override"])

        # Reset back
        res = self.client.post("/api/personality/reset")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["settings"]["current_profile"], res.json()["settings"]["default_profile"])
        self.assertFalse(res.json()["settings"]["is_temporary_override"])


if __name__ == "__main__":
    unittest.main()
