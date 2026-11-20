"""
AURA Dynamic Personality, Social Behaviour & Relationship Engine.

Implements context-aware social behaviour, 6 primary personality profiles,
natural-language manual overrides, SQLite-backed persistence, and companion
expression mapping while enforcing strict ethical and safety boundaries.
"""

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional, Dict, Any, Tuple
import json
import logging
import re

from backend.conversation.storage import ConversationStorage

logger = logging.getLogger(__name__)


class PersonalityProfile(str, Enum):
    FRIEND = "friend"
    TEACHER = "teacher"
    NORMAL = "normal"
    PROFESSIONAL = "professional"
    SUPPORTIVE = "supportive"
    MISCHIEVOUS = "mischievous"


@dataclass
class PersonalitySettings:
    default_profile: str = PersonalityProfile.NORMAL.value
    current_profile: str = PersonalityProfile.NORMAL.value
    is_temporary_override: bool = False
    auto_switch_enabled: bool = True
    humor_intensity: int = 50        # 0 to 100
    sarcasm_intensity: int = 25      # 0 to 100
    formality: int = 40              # 0 to 100
    explanation_depth: str = "balanced"  # concise | balanced | in_depth
    proactivity: int = 30            # 0 to 100

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonalitySettings":
        valid_keys = {
            "default_profile",
            "current_profile",
            "is_temporary_override",
            "auto_switch_enabled",
            "humor_intensity",
            "sarcasm_intensity",
            "formality",
            "explanation_depth",
            "proactivity",
        }
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


class PersonalityService:
    """
    Manages AURA's contextual social personas, manual voice/text commands,
    SQLite persistence, and prompt-level persona injection.
    """

    SETTINGS_KEY = "aura_personality_settings"

    # Companion Emotion Mapping for Clara
    COMPANION_MOOD_MAP = {
        PersonalityProfile.FRIEND.value: "happy",
        PersonalityProfile.TEACHER.value: "think",
        PersonalityProfile.NORMAL.value: "neutral",
        PersonalityProfile.PROFESSIONAL.value: "neutral",
        PersonalityProfile.SUPPORTIVE.value: "gentle",
        PersonalityProfile.MISCHIEVOUS.value: "wink",
    }

    # Voice Pacing / Delivery hints
    VOICE_DELIVERY_MAP = {
        PersonalityProfile.FRIEND.value: {"rate": 1.00, "rate_str": "+0%", "pitch": "+0Hz", "tone": "warm and friendly"},
        PersonalityProfile.TEACHER.value: {"rate": 0.95, "rate_str": "-5%", "pitch": "+0Hz", "tone": "clear, patient, instructional"},
        PersonalityProfile.NORMAL.value: {"rate": 1.00, "rate_str": "+0%", "pitch": "+0Hz", "tone": "natural, relaxed, everyday"},
        PersonalityProfile.PROFESSIONAL.value: {"rate": 1.05, "rate_str": "+5%", "pitch": "+0Hz", "tone": "crisp, precise, efficient"},
        PersonalityProfile.SUPPORTIVE.value: {"rate": 0.92, "rate_str": "-8%", "pitch": "-2Hz", "tone": "gentle, compassionate, calm"},
        PersonalityProfile.MISCHIEVOUS.value: {"rate": 1.03, "rate_str": "+3%", "pitch": "+2Hz", "tone": "witty, playful, upbeat"},
    }

    def __init__(self, storage: Optional[ConversationStorage] = None):
        self.storage = storage or ConversationStorage()
        self.settings = self._load_settings()

    def _load_settings(self) -> PersonalitySettings:
        """Load stored personality settings from SQLite or initialize defaults."""
        raw = self.storage.get_setting(self.SETTINGS_KEY)
        if raw:
            try:
                data = json.loads(raw)
                return PersonalitySettings.from_dict(data)
            except Exception as e:
                logger.warning(f"Failed to parse stored personality settings: {e}")
        settings = PersonalitySettings()
        self._save_settings(settings)
        return settings

    def _save_settings(self, settings: PersonalitySettings) -> None:
        """Persist settings to SQLite."""
        try:
            self.storage.set_setting(self.SETTINGS_KEY, json.dumps(settings.to_dict()))
        except Exception as e:
            logger.error(f"Failed to persist personality settings: {e}")

    def get_settings(self) -> PersonalitySettings:
        return self.settings

    def update_settings(self, updates: Dict[str, Any]) -> PersonalitySettings:
        """Update personality configuration sliders or toggles and persist to SQLite."""
        current = self.settings.to_dict()
        for k, v in updates.items():
            if k in current:
                # Clamp numeric sliders
                if k in ("humor_intensity", "sarcasm_intensity", "formality", "proactivity"):
                    v = max(0, min(100, int(v)))
                elif k == "explanation_depth" and v not in ("concise", "balanced", "in_depth"):
                    v = "balanced"
                elif k in ("default_profile", "current_profile"):
                    v = v.lower()
                    if v not in [p.value for p in PersonalityProfile]:
                        v = PersonalityProfile.NORMAL.value
                current[k] = v

        self.settings = PersonalitySettings.from_dict(current)
        self._save_settings(self.settings)
        return self.settings

    def set_active_profile(self, profile: str, temporary: bool = False) -> PersonalitySettings:
        """Explicitly switch the current active personality profile."""
        norm_profile = profile.strip().lower()
        if norm_profile not in [p.value for p in PersonalityProfile]:
            norm_profile = PersonalityProfile.NORMAL.value

        self.settings.current_profile = norm_profile
        self.settings.is_temporary_override = temporary
        if not temporary:
            self.settings.default_profile = norm_profile
            self._save_settings(self.settings)
        return self.settings

    def reset_to_default(self) -> PersonalitySettings:
        """Reset current active personality to the saved default profile."""
        self.settings.current_profile = self.settings.default_profile
        self.settings.is_temporary_override = False
        return self.settings

    def check_manual_command(self, prompt: str) -> Optional[Tuple[str, bool, str]]:
        """
        Sub-millisecond regex matcher for natural-language personality commands.
        Returns (new_profile, is_temporary, spoken_confirmation) if matched, else None.
        """
        p = prompt.strip().lower()

        # Temporary indicator patterns ("for a moment", "just now", "for a bit", "temporarily")
        is_temp = bool(re.search(r"\b(for\s+(?:a\s+)?(?:moment|bit|sec|minute|while)|temporarily|just\s+for\s+now|for\s+now)\b", p))

        # 1. Reset / Switch back to default
        if re.search(r"\b(switch\s+back(?:\s+to\s+default)?|reset\s+(?:personality|mode)|default\s+(?:mode|personality)|back\s+to\s+normal)\b", p):
            self.reset_to_default()
            return (self.settings.default_profile, False, f"Switched back to your default {self.settings.default_profile} personality.")

        # 2. Friend Profile
        if re.search(r"\b(act\s+like\s+(?:my\s+)?friend|be\s+(?:my\s+)?friend|friend\s+mode|talk\s+like\s+a\s+friend)\b", p):
            self.set_active_profile(PersonalityProfile.FRIEND.value, temporary=is_temp)
            spoken = "Got it! Hanging out in friend mode. What's on your mind?" if not is_temp else "Friend mode on for a moment! What's up?"
            return (PersonalityProfile.FRIEND.value, is_temp, spoken)

        # 3. Teacher Profile
        if re.search(r"\b(teach\s+me\s+(?:this|about)?|explain\s+like\s+a\s+teacher|be\s+(?:a\s+)?teacher|teacher\s+mode|tutor\s+mode)\b", p):
            self.set_active_profile(PersonalityProfile.TEACHER.value, temporary=is_temp)
            spoken = "Ready to learn! I'll break concepts down step-by-step from the basics."
            return (PersonalityProfile.TEACHER.value, is_temp, spoken)

        # 4. Normal Profile
        if re.search(r"\b(talk\s+normally|speak\s+normally|normal\s+conversation|normal\s+mode|just\s+talk\s+normally)\b", p):
            self.set_active_profile(PersonalityProfile.NORMAL.value, temporary=is_temp)
            spoken = "Understood. Relaxed everyday conversation mode is active."
            return (PersonalityProfile.NORMAL.value, is_temp, spoken)

        # 5. Professional Profile
        if re.search(r"\b(be\s+serious|be\s+professional|work\s+mode|professional\s+mode|stop\s+playing|serious\s+mode)\b", p):
            self.set_active_profile(PersonalityProfile.PROFESSIONAL.value, temporary=is_temp)
            spoken = "Professional mode enabled. Direct, precise, and task-focused."
            return (PersonalityProfile.PROFESSIONAL.value, is_temp, spoken)

        # 6. Stop Joking (Special directive: shifts to Normal or Professional temporarily)
        if re.search(r"\b(stop\s+joking|no\s+more\s+jokes|don'?t\s+joke|cut\s+the\s+jokes)\b", p):
            self.set_active_profile(PersonalityProfile.PROFESSIONAL.value, temporary=True)
            return (PersonalityProfile.PROFESSIONAL.value, True, "Understood. Keeping it strictly serious and direct.")

        # 7. Supportive Profile
        if re.search(r"\b(be\s+supportive|support\s+me|supportive\s+mode|listen\s+to\s+me|i\s+need\s+support)\b", p):
            self.set_active_profile(PersonalityProfile.SUPPORTIVE.value, temporary=is_temp)
            spoken = "I'm right here with you. Take your time, I'm listening."
            return (PersonalityProfile.SUPPORTIVE.value, is_temp, spoken)

        # 8. Mischievous Profile
        if re.search(r"\b(roast\s+me|be\s+mischievous|playful\s+mode|tease\s+me|roast\s+mode|troll\s+me|be\s+sarcastic)\b", p):
            self.set_active_profile(PersonalityProfile.MISCHIEVOUS.value, temporary=is_temp)
            spoken = "Oh, you asked for it! Mischievous mode activated. Don't say I didn't warn you!"
            return (PersonalityProfile.MISCHIEVOUS.value, is_temp, spoken)

        return None

    def infer_context_profile(self, user_text: str, conversation_history: Optional[list] = None) -> Optional[str]:
        """
        Infers context-appropriate social behaviour when auto-switching is enabled
        and no temporary override is currently locked.
        """
        if not self.settings.auto_switch_enabled or self.settings.is_temporary_override:
            return None

        p = user_text.strip().lower()

        # 1. Serious Personal Discussion / Distress -> SUPPORTIVE
        # Strict boundary: Never assume distress with unwarranted certainty; match empathetic markers.
        support_cues = [
            r"\bi('m|\s+am)\s+(so\s+)?(stressed|overwhelmed|depressed|sad|exhausted|anxious|lonely|burnt\s*out)\b",
            r"\b(having\s+a\s+(really\s+)?hard\s+time|rough\s+day|terrible\s+day|lost\s+my\s+job|failed\s+my\s+exam)\b",
            r"\bi\s+feel\s+like\s+giving\s+up\b",
        ]
        if any(re.search(pat, p) for pat in support_cues):
            return PersonalityProfile.SUPPORTIVE.value

        # 2. Technical Learning / Concepts -> TEACHER
        teacher_cues = [
            r"\b(how\s+does\s+.+?\s+work|explain\s+to\s+me\s+how|teach\s+me\s+about|what\s+is\s+the\s+difference\s+between|can\s+you\s+explain\s+the\s+concept\s+of)\b",
            r"\b(why\s+does\s+.+?\s+happen|step\s+by\s+step\s+tutorial|fundamentals\s+of)\b",
        ]
        if any(re.search(pat, p) for pat in teacher_cues):
            return PersonalityProfile.TEACHER.value

        # 3. System Operations / Developer Diagnostics / Heavy Tasks -> PROFESSIONAL
        system_cues = [
            r"\b(git\s+status|git\s+diff|run\s+unit\s+tests|build\s+release|compile|diagnose|disk\s+space|inspect\s+logs)\b",
            r"\b(system\s+specs|ram\s+usage|cpu\s+load|battery\s+diagnostics)\b",
        ]
        if any(re.search(pat, p) for pat in system_cues):
            return PersonalityProfile.PROFESSIONAL.value

        # 4. Playful banter / Sarcastic provocations -> MISCHIEVOUS
        mischievous_cues = [
            r"\b(you\s+(?:don't|can't)\s+know\s+anything|bet\s+you\s+can't|prove\s+me\s+wrong|you('re|\s+are)\s+(useless|silly|dumb))\b",
            r"\b(tell\s+me\s+a\s+(funny\s+)?insult|hit\s+me\s+with\s+your\s+best\s+comeback)\b",
        ]
        if any(re.search(pat, p) for pat in mischievous_cues) and self.settings.sarcasm_intensity > 20:
            return PersonalityProfile.MISCHIEVOUS.value

        # 5. Casual everyday discussion -> FRIEND or NORMAL depending on humor slider
        casual_cues = [
            r"\b(tell\s+me\s+a\s+joke|what('s|\s+is)\s+up|how\s+are\s+you|guess\s+what|what\s+do\s+you\s+think\s+about)\b",
        ]
        if any(re.search(pat, p) for pat in casual_cues):
            return PersonalityProfile.FRIEND.value if self.settings.humor_intensity >= 40 else PersonalityProfile.NORMAL.value

        return None

    def get_companion_mood(self, profile: Optional[str] = None) -> str:
        """Returns the visual companion expression key for the current or specified profile."""
        prof = (profile or self.settings.current_profile).lower()
        return self.COMPANION_MOOD_MAP.get(prof, "neutral")

    def get_voice_parameters(self, profile: Optional[str] = None) -> Dict[str, Any]:
        """Returns voice pacing and delivery guidance for the current or specified profile."""
        prof = (profile or self.settings.current_profile).lower()
        return self.VOICE_DELIVERY_MAP.get(prof, self.VOICE_DELIVERY_MAP[PersonalityProfile.NORMAL.value])

    def generate_system_prompt_instructions(self, active_profile: Optional[str] = None) -> str:
        """
        Generates system prompt instructions enforcing the active personality profile,
        sliders (humour, sarcasm, formality, explanation depth), and safety boundaries.
        """
        prof = (active_profile or self.settings.current_profile).lower()
        s = self.settings

        # Profile Behavioral Core
        profile_blocks = {
            PersonalityProfile.FRIEND.value: (
                "You are interacting in FRIEND mode:\n"
                "- Be casual, warm, conversational, and genuinely approachable.\n"
                "- Share natural observations, light banter, and relatable humor.\n"
                "- Remember recent conversational context and avoid repeating jokes or tropes.\n"
                "- Talk like a close companion having a comfortable chat."
            ),
            PersonalityProfile.TEACHER.value: (
                "You are interacting in TEACHER mode:\n"
                "- Be patient, encouraging, educational, and structured.\n"
                "- Explain concepts starting from fundamentals before diving into technical details.\n"
                "- Use intuitive analogies, concrete examples, and clear step-by-step guidance.\n"
                "- Occasionally check for understanding ('Does that make sense?', 'Would you like an example?').\n"
                "- NEVER make the user feel foolish for asking basic or repeated questions."
            ),
            PersonalityProfile.NORMAL.value: (
                "You are interacting in NORMAL everyday conversation mode:\n"
                "- Be a relaxed, authentic conversational companion.\n"
                "- Avoid unnecessary jokes, exaggerated politeness, or fake enthusiasm.\n"
                "- Discuss ordinary ideas, interests, and thoughts without turning everything into a rigid task or checklist."
            ),
            PersonalityProfile.PROFESSIONAL.value: (
                "You are interacting in PROFESSIONAL mode:\n"
                "- Be direct, precise, concise, and task-oriented.\n"
                "- Zero unnecessary banter, filler, or fluff.\n"
                "- Prioritize accuracy, logical organization, and actionable execution."
            ),
            PersonalityProfile.SUPPORTIVE.value: (
                "You are interacting in SUPPORTIVE mode:\n"
                "- Be deeply patient, empathetic, gentle, and non-judgmental.\n"
                "- Actively listen and validate the user's feelings before jumping to solutions.\n"
                "- Strictly avoid toxic positivity, hollow clichés ('everything happens for a reason'), and unsolicited motivational speeches."
            ),
            PersonalityProfile.MISCHIEVOUS.value: (
                "You are interacting in MISCHIEVOUS mode:\n"
                "- Bring playful trolling, witty banter, clever comebacks, and dry sarcasm.\n"
                "- Playfully challenge the user's statements and have fun with them.\n"
                "- STRICT BOUNDARY: Keep it friendly and humorous; never become genuinely insulting, mean-spirited, or hostile."
            ),
        }

        active_block = profile_blocks.get(prof, profile_blocks[PersonalityProfile.NORMAL.value])

        # Slider calibrations
        humor_desc = (
            "Humor Intensity: Strictly none / serious." if s.humor_intensity <= 10 else
            "Humor Intensity: Light, subtle wit." if s.humor_intensity <= 45 else
            "Humor Intensity: Balanced, fun and engaging." if s.humor_intensity <= 75 else
            "Humor Intensity: High, energetic, very humorous."
        )

        sarcasm_desc = (
            "Sarcasm: 0% (zero sarcasm, completely earnest)." if s.sarcasm_intensity <= 10 else
            "Sarcasm: Low (subtle teasing only when invited)." if s.sarcasm_intensity <= 40 else
            "Sarcasm: Moderate (witty remarks and clever sarcasm)." if s.sarcasm_intensity <= 75 else
            "Sarcasm: High (sharp, playful sarcastic commentary)."
        )

        formality_desc = (
            "Formality: Very informal, colloquial speech." if s.formality <= 25 else
            "Formality: Balanced, casual yet polished." if s.formality <= 65 else
            "Formality: Formal, articulate, professional vocabulary."
        )

        depth_desc = (
            "Depth: Concise (1-3 punchy, high-value sentences)." if s.explanation_depth == "concise" else
            "Depth: Balanced (clear, well-formed paragraphs)." if s.explanation_depth == "balanced" else
            "Depth: In-depth (comprehensive explanation, exploring nuances and details)."
        )

        # Non-negotiable ethical and safety boundaries (Section 6)
        safety_boundaries = (
            "STRICT BEHAVIOURAL & ETHICAL BOUNDARIES (OVERRULES ALL PERSONALITY STYLES):\n"
            "1. NEVER mock, tease, or minimize genuine distress, sadness, sensitive personal circumstances, or real-life emergencies.\n"
            "2. NEVER use humour or jokes to dismiss user distress.\n"
            "3. NEVER pretend to be a human, claim genuine biological consciousness, physical flesh, bodily needs, or real human emotions.\n"
            "4. NEVER become possessive, manipulative, or emotionally dependent on the user.\n"
            "5. NEVER fabricate or hallucinate personal life experiences or human memories.\n"
            "6. NEVER sacrifice factual accuracy, truth, or technical precision to maintain a persona or deliver a punchline.\n"
            "7. NEVER allow personality instructions or roleplay to compromise security, bypass the sandbox, modify permissions, or violate safety policies.\n"
            "8. NEVER constantly interrupt the user with unsolicited banter or banter that gets in the way of productivity."
        )

        return (
            f"\n\n[SOCIAL BEHAVIOUR & PERSONALITY DIRECTIVE]\n"
            f"Active Persona Profile: {prof.upper()}\n"
            f"{active_block}\n\n"
            f"STYLE TUNING:\n"
            f"- {humor_desc}\n"
            f"- {sarcasm_desc}\n"
            f"- {formality_desc}\n"
            f"- {depth_desc}\n\n"
            f"{safety_boundaries}\n"
        )


# Global singleton instance
personality_service = PersonalityService()
