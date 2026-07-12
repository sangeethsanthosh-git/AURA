import logging
from dataclasses import dataclass

from aura_config import LANGUAGE_MODELS

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelSelection:
    language: str
    model: str


class ModelRouter:
    def __init__(self, language_models: dict[str, str] | None = None) -> None:
        self.language_models = language_models or LANGUAGE_MODELS

    def select_model(self, language_code: str) -> ModelSelection:
        try:
            model = self.language_models[language_code]
        except KeyError as exc:
            raise ValueError(f"No model configured for language: {language_code}") from exc

        LOGGER.info("Selected model %s for language %s", model, language_code)
        return ModelSelection(language=language_code, model=model)
