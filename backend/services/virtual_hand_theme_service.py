"""
AURA Virtual Hand Theme Manager & Skin Service
Manages customizable cursor skins and animations for AURA's independent virtual assistant hand.
Supports .ani, .cur, .gif, .png, .webp, .apng, and .zip cursor packages.
Strictly local, safe parsing, no administrator privileges required.
Never alters the user's personal Windows mouse cursor scheme.
"""

import os
import io
import json
import uuid
import struct
import shutil
import base64
import logging
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image

logger = logging.getLogger(__name__)

# Dangerous extensions strictly forbidden in uploaded archives
FORBIDDEN_EXTENSIONS = {
    ".exe", ".dll", ".bat", ".cmd", ".vbs", ".ps1", ".sh",
    ".jar", ".msi", ".scr", ".com", ".pif", ".hta", ".cpl",
    ".js", ".mjs", ".reg", ".wsf", ".wsh"
}

SUPPORTED_EXTENSIONS = {".ani", ".cur", ".png", ".gif", ".webp", ".apng"}


class VirtualHandThemeService:
    """Manages themes, skins, asset decoding, and variants for AURA's virtual hand."""

    def __init__(self):
        user_home = Path(os.environ.get("USERPROFILE", os.path.expanduser("~"))).resolve()
        self.themes_dir = user_home / "AppData" / "Local" / "AURA" / "virtual_hand_themes"
        self.themes_dir.mkdir(parents=True, exist_ok=True)

        self.active_config_path = self.themes_dir / "active_theme.json"

        # Initialize built-in themes
        self._ensure_default_themes()

    def _ensure_default_themes(self) -> None:
        """Seeds built-in themes (Kawaii Cat Paw and Cyber Glow)."""
        cat_paw_dir = self.themes_dir / "kawaii_cat_paw"
        manifest_path = cat_paw_dir / "manifest.json"

        # Check existing cursor assets directory
        user_home = Path(os.environ.get("USERPROFILE", os.path.expanduser("~"))).resolve()
        source_paw_dir = user_home / "AppData" / "Local" / "AURA" / "cursors" / "kawaii_cat_paw"

        if not cat_paw_dir.exists():
            cat_paw_dir.mkdir(parents=True, exist_ok=True)

        if not manifest_path.exists():
            # Copy assets from source_paw_dir if available
            if source_paw_dir.exists():
                for item in source_paw_dir.glob("*.*"):
                    try:
                        dest = cat_paw_dir / item.name
                        if not dest.exists():
                            shutil.copy2(item, dest)
                    except Exception as e:
                        logger.debug(f"Note copying paw asset {item.name}: {e}")

            # Generate preview base64
            preview_b64 = ""
            gif_file = cat_paw_dir / "cat_paw_animated.gif"
            png_file = cat_paw_dir / "cursor_48x48.png"
            if gif_file.exists():
                try:
                    with open(gif_file, "rb") as f:
                        preview_b64 = f"data:image/gif;base64,{base64.b64encode(f.read()).decode('ascii')}"
                except Exception:
                    pass
            elif png_file.exists():
                try:
                    with open(png_file, "rb") as f:
                        preview_b64 = f"data:image/png;base64,{base64.b64encode(f.read()).decode('ascii')}"
                except Exception:
                    pass

            default_manifest = {
                "id": "kawaii_cat_paw",
                "name": "Kawaii Pixel Cat Paw",
                "author": "Sweezy Cursors",
                "description": "Original animated pixel cat paw claw for AURA's virtual desktop assistant hand.",
                "is_builtin": True,
                "variants": {
                    "normal": {
                        "file": "cat_paw_animated.gif" if gif_file.exists() else "cursor_48x48.png",
                        "hotspot": [8, 3],
                        "animated": True,
                    },
                    "pointer": {
                        "file": "pointer_48x48.png" if (cat_paw_dir / "pointer_48x48.png").exists() else "cat_paw_animated.gif",
                        "hotspot": [12, 4],
                        "animated": False,
                    },
                    "click": {
                        "file": "cat_paw_animated.gif" if gif_file.exists() else "cursor_48x48.png",
                        "hotspot": [8, 3],
                        "animated": True,
                    },
                    "typing": {
                        "file": "cat_paw_animated.gif" if gif_file.exists() else "cursor_48x48.png",
                        "hotspot": [8, 3],
                        "animated": True,
                    },
                    "waiting": {
                        "file": "cat_paw_animated.gif" if gif_file.exists() else "cursor_48x48.png",
                        "hotspot": [8, 3],
                        "animated": True,
                    },
                },
                "settings": {
                    "size": 44,
                    "speed": 1.0,
                    "hotspot": [8, 3],
                    "animated": True,
                },
                "preview": preview_b64,
            }

            try:
                with open(manifest_path, "w", encoding="utf-8") as f:
                    json.dump(default_manifest, f, indent=2)
            except Exception as e:
                logger.error(f"Failed to write default manifest: {e}")

        # Ensure active_theme.json exists
        if not self.active_config_path.exists():
            self.set_active_theme("kawaii_cat_paw")

    def get_active_theme_id(self) -> str:
        """Returns the ID of the current active theme."""
        if self.active_config_path.exists():
            try:
                with open(self.active_config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("active_theme_id", "kawaii_cat_paw")
            except Exception:
                pass
        return "kawaii_cat_paw"

    def set_active_theme(self, theme_id: str) -> bool:
        """Sets the active theme ID."""
        theme_dir = self.themes_dir / theme_id
        if not theme_dir.exists():
            logger.warning(f"Theme '{theme_id}' does not exist.")
            return False

        try:
            with open(self.active_config_path, "w", encoding="utf-8") as f:
                json.dump({"active_theme_id": theme_id}, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to persist active theme ID: {e}")
            return False

    def get_active_theme(self) -> Dict[str, Any]:
        """Returns full data and resolved asset URLs for the active theme."""
        theme_id = self.get_active_theme_id()
        theme = self.get_theme(theme_id)
        if not theme:
            theme = self.get_theme("kawaii_cat_paw")
        return theme or {}

    def get_theme(self, theme_id: str) -> Optional[Dict[str, Any]]:
        """Loads and returns the manifest of a specific theme."""
        manifest_path = self.themes_dir / theme_id / "manifest.json"
        if not manifest_path.exists():
            return None

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Resolve variant file URLs or base64 data
            theme_dir = self.themes_dir / theme_id
            variants = data.get("variants", {})
            resolved_variants = {}

            for state, var_info in variants.items():
                fname = var_info.get("file", "")
                fpath = theme_dir / fname
                resolved_info = dict(var_info)
                if fpath.exists():
                    try:
                        ext = fpath.suffix.lower()
                        mime = "image/gif" if ext == ".gif" else "image/webp" if ext == ".webp" else "image/png"
                        with open(fpath, "rb") as img_f:
                            resolved_info["data_url"] = f"data:{mime};base64,{base64.b64encode(img_f.read()).decode('ascii')}"
                    except Exception:
                        resolved_info["data_url"] = ""
                resolved_variants[state] = resolved_info

            data["variants"] = resolved_variants
            data["is_active"] = (theme_id == self.get_active_theme_id())
            return data
        except Exception as e:
            logger.error(f"Failed to load theme manifest for '{theme_id}': {e}")
            return None

    def list_themes(self) -> List[Dict[str, Any]]:
        """Returns a list of all installed themes."""
        active_id = self.get_active_theme_id()
        results = []

        for p in self.themes_dir.iterdir():
            if p.is_dir() and (p / "manifest.json").exists():
                try:
                    with open(p / "manifest.json", "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    meta["is_active"] = (meta.get("id") == active_id)
                    results.append(meta)
                except Exception as e:
                    logger.debug(f"Error reading theme in {p.name}: {e}")

        # Sort with active first, then built-in, then alphabetically
        results.sort(key=lambda x: (not x.get("is_active", False), not x.get("is_builtin", False), x.get("name", "")))
        return results

    def update_theme_settings(self, theme_id: str, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Updates size, speed, hotspot, and animation settings for a theme."""
        manifest_path = self.themes_dir / theme_id / "manifest.json"
        if not manifest_path.exists():
            return {"success": False, "error": f"Theme '{theme_id}' not found."}

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            settings = data.setdefault("settings", {})
            if "size" in new_settings:
                settings["size"] = max(16, min(128, int(new_settings["size"])))
            if "speed" in new_settings:
                settings["speed"] = max(0.2, min(5.0, float(new_settings["speed"])))
            if "hotspot" in new_settings and isinstance(new_settings["hotspot"], (list, tuple)) and len(new_settings["hotspot"]) >= 2:
                settings["hotspot"] = [int(new_settings["hotspot"][0]), int(new_settings["hotspot"][1])]
            if "animated" in new_settings:
                settings["animated"] = bool(new_settings["animated"])

            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            return {"success": True, "theme": data}
        except Exception as e:
            logger.error(f"Failed to update theme settings for '{theme_id}': {e}")
            return {"success": False, "error": str(e)}

    def delete_theme(self, theme_id: str) -> Dict[str, Any]:
        """Deletes a custom user theme (built-ins are protected)."""
        theme_dir = self.themes_dir / theme_id
        if not theme_dir.exists():
            return {"success": False, "error": f"Theme '{theme_id}' not found."}

        manifest_path = theme_dir / "manifest.json"
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("is_builtin", False):
                return {"success": False, "error": "Built-in default themes cannot be deleted."}

            # If deleting active theme, fall back to kawaii_cat_paw
            if self.get_active_theme_id() == theme_id:
                self.set_active_theme("kawaii_cat_paw")

            shutil.rmtree(theme_dir)
            return {"success": True, "message": f"Theme '{data.get('name', theme_id)}' deleted successfully."}
        except Exception as e:
            logger.error(f"Failed to delete theme '{theme_id}': {e}")
            return {"success": False, "error": str(e)}

    # ==========================================
    # UPLOAD & PARSING PIPELINE
    # ==========================================

    def import_theme(self, filename: str, content_bytes: bytes, custom_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Safely inspects and imports cursor skin files (.zip, .ani, .cur, .gif, .png, .webp).
        Never executes code. Protects against Zip Slip path traversal attacks.
        """
        if not content_bytes or len(content_bytes) < 8:
            return {"success": False, "error": "Invalid or empty file content."}

        ext = Path(filename).suffix.lower()
        theme_slug = f"theme_{uuid.uuid4().hex[:8]}"
        theme_dir = self.themes_dir / theme_slug
        theme_dir.mkdir(parents=True, exist_ok=True)

        try:
            if ext == ".zip":
                return self._import_from_zip(content_bytes, theme_dir, theme_slug, custom_name or Path(filename).stem)
            elif ext in SUPPORTED_EXTENSIONS:
                return self._import_single_file(filename, content_bytes, theme_dir, theme_slug, custom_name)
            else:
                shutil.rmtree(theme_dir, ignore_errors=True)
                return {
                    "success": False,
                    "error": f"Unsupported file format '{ext}'. Supported: .zip, .ani, .cur, .png, .gif, .webp",
                }
        except Exception as e:
            shutil.rmtree(theme_dir, ignore_errors=True)
            logger.error(f"Theme import failed: {e}", exc_info=True)
            return {"success": False, "error": f"Import failed: {str(e)}"}

    def _import_single_file(
        self,
        filename: str,
        content_bytes: bytes,
        theme_dir: Path,
        theme_slug: str,
        custom_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Imports a single cursor asset file (.ani, .cur, .png, .gif, .webp)."""
        ext = Path(filename).suffix.lower()
        display_name = custom_name or Path(filename).stem.replace("_", " ").replace("-", " ").title()

        preview_b64 = ""
        hotspot = [0, 0]
        is_animated = False
        primary_file = f"normal{ext}"

        if ext == ".ani":
            # Parse .ani: extract frames, hotspot, rate, and render animated GIF
            frames, rates, ani_hotspot, default_rate = self._parse_ani_file(content_bytes)
            if frames:
                hotspot = list(ani_hotspot)
                is_animated = len(frames) > 1
                primary_file = "normal.gif"
                gif_path = theme_dir / primary_file
                # Save as animated GIF
                duration_ms = int((default_rate / 60.0) * 1000) if default_rate > 0 else 100
                frames[0].save(
                    gif_path,
                    save_all=True,
                    append_images=frames[1:],
                    optimize=False,
                    duration=duration_ms,
                    loop=0,
                    disposal=2,
                )
                with open(gif_path, "rb") as f:
                    preview_b64 = f"data:image/gif;base64,{base64.b64encode(f.read()).decode('ascii')}"
            else:
                # Save raw .ani
                with open(theme_dir / "normal.ani", "wb") as f:
                    f.write(content_bytes)
                primary_file = "normal.ani"

        elif ext == ".cur":
            # Parse .cur: extract image and hotspot
            img, cur_hotspot = self._parse_cur_file(content_bytes)
            if img:
                hotspot = list(cur_hotspot)
                primary_file = "normal.png"
                img.save(theme_dir / primary_file, format="PNG")
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                preview_b64 = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"
            else:
                with open(theme_dir / "normal.cur", "wb") as f:
                    f.write(content_bytes)
                primary_file = "normal.cur"

        elif ext in (".gif", ".png", ".webp", ".apng"):
            dest_file = theme_dir / f"normal{ext}"
            with open(dest_file, "wb") as f:
                f.write(content_bytes)
            try:
                img = Image.open(io.BytesIO(content_bytes))
                is_animated = getattr(img, "is_animated", False)
                mime = "image/gif" if ext == ".gif" else "image/webp" if ext == ".webp" else "image/png"
                preview_b64 = f"data:{mime};base64,{base64.b64encode(content_bytes).decode('ascii')}"
            except Exception:
                pass

        manifest = {
            "id": theme_slug,
            "name": display_name,
            "author": "User Imported",
            "is_builtin": False,
            "variants": {
                "normal": {"file": primary_file, "hotspot": hotspot, "animated": is_animated},
                "pointer": {"file": primary_file, "hotspot": hotspot, "animated": is_animated},
                "click": {"file": primary_file, "hotspot": hotspot, "animated": is_animated},
                "typing": {"file": primary_file, "hotspot": hotspot, "animated": is_animated},
                "waiting": {"file": primary_file, "hotspot": hotspot, "animated": is_animated},
            },
            "settings": {
                "size": 44,
                "speed": 1.0,
                "hotspot": hotspot,
                "animated": is_animated,
            },
            "preview": preview_b64,
        }

        with open(theme_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return {"success": True, "theme": manifest}

    def _import_from_zip(
        self,
        content_bytes: bytes,
        theme_dir: Path,
        theme_slug: str,
        theme_name: str
    ) -> Dict[str, Any]:
        """
        Safely inspects and extracts a cursor ZIP package.
        Detects variants (normal, pointer, text, waiting, drag) and builds a theme manifest.
        """
        try:
            zip_buffer = io.BytesIO(content_bytes)
            with zipfile.ZipFile(zip_buffer, "r") as zf:
                # 1. Security Pre-Scan: Prevent Zip-Slip and dangerous binaries
                infolist = zf.infolist()
                for info in infolist:
                    filename = info.filename
                    # Normalize and detect directory traversal attempts
                    clean_name = os.path.normpath(filename).replace("\\", "/")
                    if clean_name.startswith("/") or clean_name.startswith("../") or "/../" in clean_name:
                        return {"success": False, "error": f"Security violation: Malicious path traversal in '{filename}'"}

                    ext = Path(filename).suffix.lower()
                    if ext in FORBIDDEN_EXTENSIONS:
                        return {"success": False, "error": f"Security violation: Forbidden executable file type '{ext}' detected in archive."}

                # 2. Extract allowed assets safely
                extracted_files: List[Path] = []
                for info in infolist:
                    if info.is_dir():
                        continue
                    ext = Path(info.filename).suffix.lower()
                    if ext in SUPPORTED_EXTENSIONS:
                        safe_stem = Path(info.filename).name
                        target_path = theme_dir / safe_stem
                        with zf.open(info) as src, open(target_path, "wb") as dst:
                            dst.write(src.read())
                        extracted_files.append(target_path)

                if not extracted_files:
                    return {
                        "success": False,
                        "error": "No valid cursor assets found in ZIP archive (.ani, .cur, .png, .gif, .webp).",
                    }

                # 3. Classify variants by filename keywords
                variants = {}
                preview_b64 = ""
                primary_hotspot = [0, 0]

                def _classify(path: Path) -> str:
                    name = path.name.lower()
                    if any(k in name for k in ("pointer", "hand", "link")):
                        return "pointer"
                    elif any(k in name for k in ("beam", "text", "type")):
                        return "typing"
                    elif any(k in name for k in ("wait", "busy", "load", "working")):
                        return "waiting"
                    elif any(k in name for k in ("drag", "move", "grab")):
                        return "drag"
                    else:
                        return "normal"

                # Process all extracted files
                classified_files = {}
                for f in extracted_files:
                    v_type = _classify(f)
                    classified_files.setdefault(v_type, []).append(f)

                # Select best file for normal
                normal_cands = classified_files.get("normal", extracted_files)
                # Prefer animated GIF or .ani if present
                normal_file = next((f for f in normal_cands if f.suffix.lower() in (".gif", ".ani")), normal_cands[0])

                # Process normal file for preview & hotspot
                ext = normal_file.suffix.lower()
                is_animated = False
                final_normal_name = normal_file.name

                if ext == ".ani":
                    frames, rates, hspot, def_rate = self._parse_ani_file(normal_file.read_bytes())
                    if frames:
                        primary_hotspot = list(hspot)
                        is_animated = len(frames) > 1
                        final_normal_name = "normal.gif"
                        gif_path = theme_dir / final_normal_name
                        dur = int((def_rate / 60.0) * 1000) if def_rate > 0 else 100
                        frames[0].save(gif_path, save_all=True, append_images=frames[1:], duration=dur, loop=0, disposal=2)
                        with open(gif_path, "rb") as gf:
                            preview_b64 = f"data:image/gif;base64,{base64.b64encode(gf.read()).decode('ascii')}"
                elif ext == ".cur":
                    img, hspot = self._parse_cur_file(normal_file.read_bytes())
                    if img:
                        primary_hotspot = list(hspot)
                        final_normal_name = "normal.png"
                        img.save(theme_dir / final_normal_name, format="PNG")
                        buf = io.BytesIO()
                        img.save(buf, format="PNG")
                        preview_b64 = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"
                else:
                    try:
                        b = normal_file.read_bytes()
                        img = Image.open(io.BytesIO(b))
                        is_animated = getattr(img, "is_animated", False)
                        mime = "image/gif" if ext == ".gif" else "image/webp" if ext == ".webp" else "image/png"
                        preview_b64 = f"data:{mime};base64,{base64.b64encode(b).decode('ascii')}"
                    except Exception:
                        pass

                # Set variants
                for st in ("normal", "pointer", "click", "typing", "waiting", "drag"):
                    var_cands = classified_files.get(st, [normal_file])
                    sel_file = var_cands[0]
                    variants[st] = {
                        "file": final_normal_name if sel_file == normal_file else sel_file.name,
                        "hotspot": primary_hotspot,
                        "animated": is_animated,
                    }

                clean_title = theme_name.replace("_", " ").replace("-", " ").title()
                manifest = {
                    "id": theme_slug,
                    "name": clean_title,
                    "author": "Imported ZIP",
                    "is_builtin": False,
                    "variants": variants,
                    "settings": {
                        "size": 44,
                        "speed": 1.0,
                        "hotspot": primary_hotspot,
                        "animated": is_animated,
                    },
                    "preview": preview_b64,
                }

                with open(theme_dir / "manifest.json", "w", encoding="utf-8") as f:
                    json.dump(manifest, f, indent=2)

                return {"success": True, "theme": manifest}

        except zipfile.BadZipFile:
            return {"success": False, "error": "The uploaded file is not a valid ZIP archive."}

    # ==========================================
    # CURSOR FORMAT PARSERS (.ANI & .CUR)
    # ==========================================

    @staticmethod
    def _parse_cur_file(data: bytes) -> Tuple[Optional[Image.Image], Tuple[int, int]]:
        """Parses a Windows .cur file to extract its hotspot and PIL Image."""
        try:
            if len(data) < 16:
                return None, (0, 0)

            # CUR header: 0-2: reserved, 2-4: type (2=CUR), 4-6: count
            res, c_type, count = struct.unpack("<HHH", data[:6])
            if c_type != 2 or count < 1:
                return None, (0, 0)

            # First ICONDIRENTRY:
            # bWidth(1), bHeight(1), bColorCount(1), bReserved(1), wXHotspot(2), wYHotspot(2), dwBytes(4), dwOffset(4)
            w, h, _, _, hx, hy, dw_bytes, offset = struct.unpack("<BBBBHHII", data[6:22])

            # Adjust hotspot if coordinates are packed scaled
            hotspot = (hx, hy)

            # Trick: Convert type byte from 2 (CUR) to 1 (ICO) so PIL handles BMP/PNG payload cleanly
            ico_data = data[:2] + b"\x01\x00" + data[4:]
            img = Image.open(io.BytesIO(ico_data))
            return img.copy(), hotspot
        except Exception as e:
            logger.debug(f"Failed to parse .cur file: {e}")
            return None, (0, 0)

    @classmethod
    def _parse_ani_file(cls, data: bytes) -> Tuple[List[Image.Image], List[int], Tuple[int, int], int]:
        """
        Parses a Windows .ani (RIFF/ACON) file to extract:
        - List of frame PIL Images
        - List of frame rates
        - Hotspot (x, y)
        - Default display rate in jiffies (1/60s)
        """
        frames: List[Image.Image] = []
        rates: List[int] = []
        hotspot = (0, 0)
        default_rate = 10

        try:
            if len(data) < 24 or data[:4] != b"RIFF" or data[8:12] != b"ACON":
                return frames, rates, hotspot, default_rate

            idx = 12
            total_len = len(data)

            while idx < total_len - 8:
                cid = data[idx:idx + 4]
                csize = struct.unpack("<I", data[idx + 4:idx + 8])[0]

                if cid == b"anih" and csize >= 36:
                    anih = struct.unpack("<IIIIIIIII", data[idx + 8:idx + 8 + 36])
                    default_rate = anih[7]  # iDispRate
                elif cid == b"rate":
                    n_rates = csize // 4
                    rates = list(struct.unpack(f"<{n_rates}I", data[idx + 8:idx + 8 + csize]))
                elif cid == b"LIST" and data[idx + 8:idx + 12] == b"fram":
                    fidx = idx + 12
                    f_end = idx + 8 + csize
                    while fidx < f_end - 8:
                        fcid = data[fidx:fidx + 4]
                        fcsize = struct.unpack("<I", data[fidx + 4:fidx + 8])[0]
                        if fcid == b"icon":
                            icon_bytes = data[fidx + 8:fidx + 8 + fcsize]
                            if len(icon_bytes) > 16 and icon_bytes[2:4] == b"\x02\x00":
                                # Extract hotspot from first entry
                                hx, hy = struct.unpack("<HH", icon_bytes[10:14])
                                if hotspot == (0, 0):
                                    hotspot = (hx, hy)
                                # Convert to ICO header so PIL opens it
                                ico_bytes = icon_bytes[:2] + b"\x01\x00" + icon_bytes[4:]
                                try:
                                    img = Image.open(io.BytesIO(ico_bytes))
                                    frames.append(img.copy())
                                except Exception:
                                    pass
                        fidx += 8 + fcsize
                        if fcsize % 2 == 1:
                            fidx += 1

                idx += 8 + csize
                if csize % 2 == 1:
                    idx += 1

            return frames, rates, hotspot, default_rate
        except Exception as e:
            logger.debug(f"Failed to parse .ani file: {e}")
            return frames, rates, hotspot, default_rate


# Global singleton instance
virtual_hand_theme_service = VirtualHandThemeService()
