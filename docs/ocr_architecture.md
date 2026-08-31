# AURA Eyes OCR Architecture

## Decision

AURA should use **Surya OCR as the primary OCR engine** for screen and document
text extraction, with **RapidOCR or PaddleOCR as an optional fast English/UI
fallback** only after their Malayalam support is verified for the exact model
bundle in use. Tesseract should not be installed and should not be treated as a
primary OCR path.

This recommendation is driven by the Malayalam requirement. Surya publishes
language-level evaluation data and reports Malayalam (`ml`) at 84.7% in its
multilingual benchmark, while EasyOCR's public language configuration does not
list Malayalam and PaddleOCR/RapidOCR public quickstart docs do not clearly
confirm Malayalam recognition in the standard multilingual bundle.

## Candidate Comparison

| Engine | Offline | Malayalam evidence | English/UI OCR | GPU/CPU fit for RTX 2050 4GB | Storage control | License notes | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Surya OCR | Yes after models are cached | Strongest: official multilingual benchmark lists Malayalam at 84.7% | Good document and scene text OCR | Model is larger; prefer CPU/quantized or careful GPU testing on 4GB VRAM | Use project-local HF/XDG cache env before import/download | Code Apache 2.0; model weights have OpenRAIL-style terms and commercial limits | Primary for Malayalam + mixed English/Malayalam |
| PaddleOCR | Yes after models are cached | Unverified in official multilingual table reviewed; table includes several Indic scripts but not Malayalam | Strong for English and many document layouts | Lightweight PP-OCR models are practical on CPU/GPU | Prefer explicit model directories when initializing | Apache 2.0 | Optional fallback for English/UI after exact language model check |
| RapidOCR | Yes after ONNX models are cached | Unverified; based on PaddleOCR ONNX models, default docs emphasize Chinese/English | Fast local CPU OCR for simple UI text | Best lightweight fallback profile | Supports explicit ONNX model paths in integrations | Apache 2.0 code; OCR models from Baidu/Paddle | Optional fast fallback, not Malayalam primary |
| EasyOCR | Yes after models are cached | Not suitable: current public config reviewed does not list `ml` | Good for English and supported scripts | Moderate; PyTorch setup on Windows needs care | `EASYOCR_MODULE_PATH` can redirect models | Apache 2.0 | Keep out of first OCR stack unless needed for another supported language |

## Project-Local Storage

Model directories:

- `models/ocr/primary`
- `models/ocr/malayalam`
- `models/ocr/fallback`
- `models/ocr/detection`
- `models/ocr/recognition`

Runtime data directories:

- `data/ocr/cache`
- `data/ocr/temporary`

Code module:

- `backend/vision/ocr`

The helper `backend.vision.ocr.paths.ocr_environment()` returns environment
overrides for OCR subprocesses and lazy imports. Apply these before importing
OCR libraries so downloads and temporary files stay inside the project:

- `HF_HOME`
- `HF_HUB_CACHE`
- `TRANSFORMERS_CACHE`
- `XDG_CACHE_HOME`
- `EASYOCR_MODULE_PATH`
- `TMP`
- `TEMP`
- `AURA_OCR_MODEL_DIR`
- `AURA_OCR_CACHE_DIR`
- `AURA_OCR_TEMP_DIR`

## Runtime Architecture

1. `ScreenCaptureProvider` captures the current window, selected region, or full
   desktop frame.
2. `OcrPreprocessor` normalizes scale, contrast, rotation, and crops probable
   text regions without saving user images permanently.
3. `OcrRouter` selects the engine:
   - Malayalam or mixed Malayalam/English: Surya.
   - English-only UI snippets: fast fallback if installed and verified.
   - Low-confidence fallback: rerun with Surya at a larger crop/scale.
4. `OcrResultNormalizer` returns text blocks, reading order, confidence, boxes,
   language hints, and source metadata.
5. `VisionManager` exposes OCR text to AURA Eyes and the agent context. Temporary
   screenshots are deleted after processing unless debug capture is explicitly
   enabled.

## Implemented V1 Scaffold

- `backend.vision.ocr.base` defines the stable OCR provider/result interface.
- `backend.vision.ocr.manager.OCRManager` performs language routing,
  preprocessing, result normalization, confidence preservation, and bounding-box
  forwarding.
- `backend.vision.ocr.providers.primary.SuryaOCRProvider` is the lazy local
  Surya adapter. It is optional at runtime and reports Malayalam OCR unavailable
  honestly when Surya/model files are not installed.
- `backend.vision.manager.VisionManager` now uses `OCRManager` for OCR tasks
  instead of a Tesseract path.
- `backend.vision.capture.ScreenCaptureManager` defaults temporary screenshots
  to `data/ocr/temporary` and deletes them after processing.
- `ui.vision_page.VisionPage` and `ui/qml/pages/VisionPage.qml` expose Eyes
  status and on-demand screen actions without starting continuous capture.

## Installation Plan

Do not install anything until the user approves the chosen OCR stack.

1. Create directories with `ensure_ocr_directories()`.
2. Start with a Surya-only proof of concept in a clean branch or optional extra.
3. Before the first Surya import/download, merge `ocr_environment()` into the
   process environment.
4. Download/cache models into `models/ocr` or `data/ocr/cache`, then verify no
   OCR files were written to the user profile cache directories.
5. Benchmark three local sample groups:
   - English UI screenshots.
   - Malayalam UI/document screenshots.
   - Mixed Malayalam + English screenshots.
6. Add RapidOCR only if English/UI latency is too high with Surya.
7. Integrate OCR behind an interface so the app can run even when OCR packages
   are absent.

## Verification Plan

- Storage test: `python backend/tests/ocr_storage_test.py`
- Existing vision regression: `python backend/tests/vision_system_test.py`
- Full backend regression: `python -m unittest discover -s backend/tests -p "*_test.py"`
- Manual OCR check: run a Malayalam screenshot, an English settings screenshot,
  and a mixed chat screenshot; verify text, bounding boxes, and no persistent
  screenshots in `data/ocr/temporary`.

## Sources Reviewed

- Surya GitHub README and multilingual benchmark:
  https://github.com/datalab-to/surya
- Surya multilingual scores:
  https://github.com/datalab-to/surya/blob/master/static/docs/multilingual.md
- PaddleOCR GitHub and multilingual docs:
  https://github.com/PaddlePaddle/PaddleOCR
  https://paddlepaddle.github.io/PaddleOCR/v2.10.0/en/ppocr/blog/multi_languages.html
- RapidOCR GitHub:
  https://github.com/RapidAI/RapidOCR
- EasyOCR GitHub and config:
  https://github.com/JaidedAI/EasyOCR
  https://raw.githubusercontent.com/JaidedAI/EasyOCR/master/easyocr/config.py
