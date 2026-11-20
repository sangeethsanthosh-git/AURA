"""
AURA File and Folder Management Service
Implements intelligent file search, storage analysis, duplicate detection,
folder organization, document text extraction (PDF, DOCX, TXT, MD, CSV),
and safe preview-before-action execution under AURA Sandbox Protocol.
"""

from typing import Dict, Any, List, Optional
import os
import hashlib
import shutil
import logging
from pathlib import Path
from backend.security.filesystem_guard import filesystem_guard

logger = logging.getLogger(__name__)

# File type classification for folder organization
FILE_CATEGORIES = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico"],
    "Documents": [".pdf", ".docx", ".doc", ".txt", ".rtf", ".odt", ".pptx", ".xlsx", ".csv", ".md"],
    "Videos": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm", ".flv"],
    "Audio": [".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".wma"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
    "Code": [".py", ".ts", ".tsx", ".js", ".jsx", ".html", ".css", ".json", ".xml", ".yaml", ".yml", ".sql"],
    "Installers": [".exe", ".msi", ".iso"],
}


class FileManagerService:
    """Intelligent desktop file management, organization, and inspection service."""

    @staticmethod
    def get_user_directories() -> Dict[str, str]:
        """Resolve standard user desktop directories."""
        user_profile = os.environ.get("USERPROFILE", os.path.expanduser("~"))
        return {
            "downloads": os.path.join(user_profile, "Downloads"),
            "desktop": os.path.join(user_profile, "Desktop"),
            "documents": os.path.join(user_profile, "Documents"),
            "pictures": os.path.join(user_profile, "Pictures"),
            "videos": os.path.join(user_profile, "Videos"),
            "music": os.path.join(user_profile, "Music"),
        }

    @classmethod
    def search_files(
        cls,
        query: str,
        search_dir: Optional[str] = None,
        max_results: int = 15,
    ) -> Dict[str, Any]:
        """Search for files by filename substring or extension."""
        clean_q = query.strip().lower()
        if not clean_q:
            return {"handled": True, "files": [], "count": 0, "query": query}

        user_dirs = cls.get_user_directories()
        roots_to_scan = [search_dir] if search_dir and os.path.isdir(search_dir) else [
            user_dirs["documents"],
            user_dirs["desktop"],
            user_dirs["downloads"],
        ]

        matches: List[Dict[str, Any]] = []

        for root_dir in roots_to_scan:
            if not os.path.exists(root_dir):
                continue
            try:
                for root, _, files in os.walk(root_dir):
                    # Avoid traversing deep package or git directories
                    if any(ign in root.lower() for ign in ("node_modules", ".git", ".venv", "__pycache__", "appdata")):
                        continue

                    for f in files:
                        if clean_q in f.lower():
                            full_path = os.path.join(root, f)
                            try:
                                stat = os.stat(full_path)
                                matches.append({
                                    "name": f,
                                    "path": full_path,
                                    "size_bytes": stat.st_size,
                                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                                    "modified": stat.st_mtime,
                                    "extension": os.path.splitext(f)[1].lower(),
                                })
                            except Exception:
                                continue

                            if len(matches) >= max_results:
                                break
                    if len(matches) >= max_results:
                        break
            except Exception as e:
                logger.debug(f"Error scanning directory {root_dir}: {e}")

        # Sort matches by most recently modified
        matches.sort(key=lambda x: x["modified"], reverse=True)

        spoken = (
            f"Found {len(matches)} files matching '{query}'."
            if matches
            else f"No files matching '{query}' were found in your standard directories."
        )

        return {
            "handled": True,
            "action": "file_search",
            "title": f"File Search: {query}",
            "message": f"Found {len(matches)} file(s) matching '{query}'.",
            "spoken_response": spoken,
            "data": {
                "query": query,
                "count": len(matches),
                "files": matches[:max_results],
            },
        }

    @classmethod
    def find_large_files(
        cls,
        min_mb: int = 500,
        target_dir: Optional[str] = None,
        max_results: int = 10,
    ) -> Dict[str, Any]:
        """Find files larger than min_mb megabytes."""
        user_dirs = cls.get_user_directories()
        scan_dir = target_dir or user_dirs["downloads"]
        if not os.path.exists(scan_dir):
            scan_dir = user_dirs["desktop"]

        min_bytes = min_mb * 1024 * 1024
        large_files: List[Dict[str, Any]] = []

        try:
            for root, _, files in os.walk(scan_dir):
                if any(ign in root.lower() for ign in ("node_modules", ".git", ".venv", "__pycache__")):
                    continue
                for f in files:
                    full_path = os.path.join(root, f)
                    try:
                        size = os.path.getsize(full_path)
                        if size >= min_bytes:
                            large_files.append({
                                "name": f,
                                "path": full_path,
                                "size_mb": round(size / (1024 * 1024), 1),
                                "size_gb": round(size / (1024 * 1024 * 1024), 2),
                            })
                    except Exception:
                        continue
        except Exception as e:
            logger.debug(f"Error scanning for large files: {e}")

        large_files.sort(key=lambda x: x["size_mb"], reverse=True)
        top = large_files[:max_results]

        spoken = (
            f"Found {len(top)} files larger than {min_mb} megabytes in {os.path.basename(scan_dir)}."
            if top
            else f"No files larger than {min_mb} megabytes found."
        )

        return {
            "handled": True,
            "action": "large_files",
            "title": f"Large Files (> {min_mb} MB)",
            "message": f"Found {len(top)} large file(s) occupying significant space.",
            "spoken_response": spoken,
            "data": {
                "scan_directory": scan_dir,
                "threshold_mb": min_mb,
                "count": len(top),
                "files": top,
            },
        }

    @classmethod
    def find_duplicate_files(
        cls,
        target_dir: Optional[str] = None,
        max_results: int = 15,
    ) -> Dict[str, Any]:
        """Identify duplicate files based on size and MD5 hash."""
        user_dirs = cls.get_user_directories()
        scan_dir = target_dir or user_dirs["downloads"]

        size_map: Dict[int, List[str]] = {}
        try:
            for root, _, files in os.walk(scan_dir):
                if any(ign in root.lower() for ign in ("node_modules", ".git", ".venv")):
                    continue
                for f in files:
                    full_path = os.path.join(root, f)
                    try:
                        sz = os.path.getsize(full_path)
                        if sz > 1024:  # Ignore empty or tiny files
                            size_map.setdefault(sz, []).append(full_path)
                    except Exception:
                        continue
        except Exception as e:
            logger.debug(f"Error checking file sizes for duplicates: {e}")

        # Filter to sizes that appear more than once
        potential_dups = {sz: paths for sz, paths in size_map.items() if len(paths) > 1}
        duplicate_groups: List[Dict[str, Any]] = []

        for sz, paths in potential_dups.items():
            hash_map: Dict[str, List[str]] = {}
            for p in paths:
                try:
                    # Quick partial MD5 hash of first 64KB for speed
                    h = hashlib.md5()
                    with open(p, "rb") as f_obj:
                        h.update(f_obj.read(65536))
                    digest = h.hexdigest()
                    hash_map.setdefault(digest, []).append(p)
                except Exception:
                    continue

            for digest, dup_paths in hash_map.items():
                if len(dup_paths) > 1:
                    duplicate_groups.append({
                        "size_mb": round(sz / (1024 * 1024), 2),
                        "count": len(dup_paths),
                        "paths": dup_paths,
                        "filenames": [os.path.basename(p) for p in dup_paths],
                    })
                    if len(duplicate_groups) >= max_results:
                        break
            if len(duplicate_groups) >= max_results:
                break

        spoken = (
            f"Found {len(duplicate_groups)} sets of duplicate files in {os.path.basename(scan_dir)}."
            if duplicate_groups
            else "No duplicate files found in that folder."
        )

        return {
            "handled": True,
            "action": "duplicate_files",
            "title": f"Duplicate Files ({len(duplicate_groups)} groups)",
            "message": f"Found {len(duplicate_groups)} groups of identical files.",
            "spoken_response": spoken,
            "data": {
                "scan_directory": scan_dir,
                "duplicates": duplicate_groups,
            },
        }

    @classmethod
    def organize_downloads(
        cls,
        preview: bool = True,
        target_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Organize files in Downloads folder into categorized subfolders
        (Images, Documents, Videos, Audio, Archives, Code, Installers).
        By default returns a preview plan without altering files.
        """
        user_dirs = cls.get_user_directories()
        folder = target_dir or user_dirs["downloads"]
        if not os.path.exists(folder):
            return {
                "handled": True,
                "action": "file_organize",
                "title": "Folder Not Found",
                "message": f"The target folder '{folder}' does not exist.",
                "spoken_response": "I couldn't locate your Downloads folder.",
                "data": {},
            }

        plan: List[Dict[str, str]] = []
        try:
            for item in os.listdir(folder):
                item_path = os.path.join(folder, item)
                if os.path.isfile(item_path):
                    _, ext = os.path.splitext(item.lower())
                    target_category = "Other"
                    for cat, extensions in FILE_CATEGORIES.items():
                        if ext in extensions:
                            target_category = cat
                            break

                    if target_category != "Other":
                        plan.append({
                            "file": item,
                            "source": item_path,
                            "category": target_category,
                            "destination": os.path.join(folder, target_category, item),
                        })
        except Exception as e:
            logger.error(f"Error scanning folder for organization: {e}")

        if preview:
            spoken = (
                f"I've prepared a plan to organize {len(plan)} files into categorized folders. Review the preview card to confirm."
                if plan
                else "Your Downloads folder is already organized. No loose categorized files found."
            )
            return {
                "handled": True,
                "action": "file_organize",
                "type": "preview",
                "title": f"Organize Downloads ({len(plan)} files)",
                "message": f"Prepared preview plan to organize {len(plan)} files into categorized folders.",
                "spoken_response": spoken,
                "data": {
                    "preview": True,
                    "folder": folder,
                    "total_files": len(plan),
                    "plan": plan[:25],
                },
            }

        # User confirmed execution
        moved_count = 0
        for item in plan:
            cat_dir = os.path.join(folder, item["category"])
            os.makedirs(cat_dir, exist_ok=True)
            try:
                dest = os.path.join(cat_dir, item["file"])
                # Create shadow backup before moving
                filesystem_guard.create_shadow_backup(Path(item["source"]))
                # Avoid overwriting existing files
                if not os.path.exists(dest):
                    shutil.move(item["source"], dest)
                    moved_count += 1
            except Exception as me:
                logger.debug(f"Failed to move {item['file']}: {me}")

        spoken = f"Successfully organized {moved_count} files in your Downloads folder."
        return {
            "handled": True,
            "action": "file_organize",
            "type": "completed",
            "title": f"Downloads Organized ({moved_count} files)",
            "message": f"Organized {moved_count} files into categorized folders.",
            "spoken_response": spoken,
            "data": {
                "preview": False,
                "folder": folder,
                "moved_count": moved_count,
            },
        }

    @classmethod
    def read_document_summary(cls, file_path: str, max_chars: int = 1500) -> Dict[str, Any]:
        """Read and extract text from supported documents (.txt, .md, .csv, .py, .pdf, .docx)."""
        # Validate path against sensitive directories and traversal
        is_safe, reason, resolved = filesystem_guard.validate_path_access(file_path, write_operation=False)
        if not is_safe:
            return {
                "handled": True,
                "action": "read_document",
                "title": "Access Blocked",
                "message": reason,
                "spoken_response": "Access to that file was blocked by my security sandbox.",
                "data": {"found": False, "blocked": True, "reason": reason},
            }

        if not os.path.exists(file_path):
            return {
                "handled": True,
                "action": "read_document",
                "title": "File Not Found",
                "message": f"Could not find file at '{file_path}'.",
                "spoken_response": "I couldn't find that document on your computer.",
                "data": {"found": False},
            }

        _, ext = os.path.splitext(file_path.lower())
        filename = os.path.basename(file_path)
        content = ""

        try:
            if ext in (".txt", ".md", ".csv", ".json", ".py", ".html", ".xml", ".yaml", ".yml"):
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read(max_chars)
            elif ext == ".pdf":
                # Basic text extraction from PDF
                try:
                    import pypdf
                    reader = pypdf.PdfReader(file_path)
                    text_parts = [page.extract_text() or "" for page in reader.pages[:5]]
                    content = "\n".join(text_parts)[:max_chars]
                except Exception:
                    # Fallback to binary string extraction
                    with open(file_path, "rb") as f:
                        raw = f.read(100000)
                        import re
                        texts = re.findall(rb"[\w\s.,;:?!'\"-]{4,}", raw)
                        content = " ".join(t.decode("utf-8", errors="ignore") for t in texts[:50])[:max_chars]
            elif ext == ".docx":
                try:
                    import docx
                    doc = docx.Document(file_path)
                    content = "\n".join(p.text for p in doc.paragraphs[:20])[:max_chars]
                except Exception:
                    content = f"Microsoft Word document: {filename}"
            else:
                content = f"Document file: {filename} ({ext})"
        except Exception as e:
            logger.error(f"Failed to read document {file_path}: {e}")
            return {
                "handled": True,
                "action": "read_document",
                "title": f"Read Error: {filename}",
                "message": f"Could not read content from '{filename}': {e}",
                "spoken_response": f"I couldn't read the contents of {filename}.",
                "data": {"found": True, "error": str(e)},
            }

        preview = content[:250].strip().replace("\n", " ") + ("…" if len(content) > 250 else "")
        spoken = f"I've read {filename}. Here is an excerpt: {preview[:120]}"

        return {
            "handled": True,
            "action": "read_document",
            "title": f"Document: {filename}",
            "message": preview,
            "spoken_response": spoken,
            "data": {
                "filename": filename,
                "path": file_path,
                "content_preview": content,
                "length": len(content),
            },
        }

    @staticmethod
    def get_storage_drives() -> Dict[str, Any]:
        """Inspect storage drives and disk space."""
        import psutil
        drives: List[Dict[str, Any]] = []
        try:
            partitions = psutil.disk_partitions(all=False)
            for part in partitions:
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    total_gb = round(usage.total / (1024**3), 1)
                    free_gb = round(usage.free / (1024**3), 1)
                    used_gb = round(usage.used / (1024**3), 1)
                    pct = int(usage.percent)
                    drives.append({
                        "device": part.device,
                        "mount": part.mountpoint,
                        "fstype": part.fstype,
                        "total_gb": total_gb,
                        "free_gb": free_gb,
                        "used_gb": used_gb,
                        "percent_used": pct,
                    })
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"Error inspecting disk partitions: {e}")

        spoken_parts = [f"Drive {d['device']} has {d['free_gb']} GB free out of {d['total_gb']} GB" for d in drives[:2]]
        spoken = " · ".join(spoken_parts) if spoken_parts else "Storage information is available."

        return {
            "handled": True,
            "action": "storage_analysis",
            "title": "Storage Drives",
            "message": " · ".join(f"{d['device']} ({d['percent_used']}% used, {d['free_gb']} GB free)" for d in drives),
            "spoken_response": spoken,
            "data": {"drives": drives},
        }
