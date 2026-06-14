"""Multi-format file/document metadata extractor.

Supports: images (EXIF), audio (ID3/Vorbis), video (hachoir), PDF, DOCX, XLSX, generic.
All analysis is local — no API calls needed.
"""
import os
import stat
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ExifTags
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False


def _file_base(path: Path) -> dict:
    s = path.stat()
    return {
        "file_name": path.name,
        "file_size_bytes": s.st_size,
        "file_size_human": _human_size(s.st_size),
        "extension": path.suffix.lower(),
    }


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _image(path: Path) -> dict:
    result = {"file_type": "image", **_file_base(path)}
    if not PILLOW_AVAILABLE:
        result["error"] = "Pillow not installed"
        return result
    try:
        with Image.open(path) as img:
            result["format"] = img.format or path.suffix.lstrip(".")
            result["mode"] = img.mode
            result["dimensions"] = f"{img.width}x{img.height}"
            result["width"] = img.width
            result["height"] = img.height

            exif: dict[str, Any] = {}
            try:
                raw = img.getexif()
                if raw:
                    for tag_id, val in raw.items():
                        tag = ExifTags.TAGS.get(tag_id, str(tag_id))
                        if tag == "GPSInfo":
                            try:
                                from PIL.ExifTags import GPSTAGS
                                if not isinstance(val, dict):
                                    continue
                                gps = {GPSTAGS.get(k, k): v for k, v in val.items()}
                                if "GPSLatitude" in gps and "GPSLongitude" in gps:
                                    lat = val.get(2)
                                    lon = val.get(4)
                                    lat_ref = str(val.get(1, "N"))
                                    lon_ref = str(val.get(3, "E"))
                                    if lat and lon:
                                        ld = float(lat[0]) + float(lat[1]) / 60 + float(lat[2]) / 3600
                                        lo = float(lon[0]) + float(lon[1]) / 60 + float(lon[2]) / 3600
                                        if lat_ref == "S":
                                            ld = -ld
                                        if lon_ref == "W":
                                            lo = -lo
                                        exif["GPS_Coordinates"] = f"{ld:.6f}, {lo:.6f}"
                            except Exception:
                                pass
                        elif val is None:
                            continue
                        elif isinstance(val, bytes):
                            decoded = val.decode("utf-8", errors="ignore").strip()
                            if decoded:
                                exif[str(tag)] = decoded
                        else:
                            exif[str(tag)] = str(val)
            except Exception:
                pass
            result["metadata"] = exif
    except Exception as exc:
        result["error"] = str(exc)
    return result


def _audio(path: Path) -> dict:
    result = {"file_type": "audio", **_file_base(path)}
    try:
        import mutagen
        audio = mutagen.File(path, easy=True)
        if audio is None:
            result["error"] = "Could not parse audio file"
            return result
        info: dict = {}
        if hasattr(audio, "info"):
            ai = audio.info
            if hasattr(ai, "length"):
                info["duration_seconds"] = round(float(ai.length), 2)
            if hasattr(ai, "bitrate"):
                info["bitrate_kbps"] = getattr(ai, "bitrate", None)
            if hasattr(ai, "sample_rate"):
                info["sample_rate_hz"] = getattr(ai, "sample_rate", None)
            if hasattr(ai, "channels"):
                info["channels"] = getattr(ai, "channels", None)
        tags = {}
        for k, v in audio.items():
            tags[k] = str(v[0]) if isinstance(v, list) and v else str(v)
        result["audio_info"] = info
        result["metadata"] = tags
    except ImportError:
        result["error"] = "mutagen not installed. Run: pip install mutagen"
    except Exception as exc:
        result["error"] = str(exc)
    return result


def _video(path: Path) -> dict:
    result = {"file_type": "video", **_file_base(path)}
    try:
        from hachoir.parser import createParser  # type: ignore
        from hachoir.metadata import extractMetadata  # type: ignore
        parser = createParser(str(path))
        if parser:
            with parser:
                metadata = extractMetadata(parser)
            if metadata:
                items = {}
                for line in metadata.exportPlaintext():
                    if ": " in line:
                        k, _, v = line.partition(": ")
                        items[k.strip("- ").strip()] = v.strip()
                result["metadata"] = items
                return result
    except ImportError:
        pass
    except Exception:
        pass
    result["metadata"] = {}
    result["note"] = "Install hachoir for deeper video metadata: pip install hachoir"
    return result


def _pdf(path: Path) -> dict:
    result = {"file_type": "pdf", **_file_base(path)}
    try:
        from pypdf import PdfReader  # type: ignore
        reader = PdfReader(str(path))
        meta = reader.metadata or {}
        result["page_count"] = len(reader.pages)
        result["encrypted"] = reader.is_encrypted
        result["metadata"] = {k.lstrip("/"): str(v) for k, v in meta.items()}
    except ImportError:
        result["error"] = "pypdf not installed. Run: pip install pypdf"
    except Exception as exc:
        result["error"] = str(exc)
    return result


def _docx(path: Path) -> dict:
    result = {"file_type": "docx", **_file_base(path)}
    try:
        from docx import Document  # type: ignore
        doc = Document(str(path))
        cp = doc.core_properties
        result["metadata"] = {
            "author": cp.author or "",
            "last_modified_by": cp.last_modified_by or "",
            "created": str(cp.created) if cp.created else "",
            "modified": str(cp.modified) if cp.modified else "",
            "title": cp.title or "",
            "subject": cp.subject or "",
            "description": cp.description or "",
            "revision": cp.revision,
            "word_count": sum(len(p.text.split()) for p in doc.paragraphs),
        }
    except ImportError:
        result["error"] = "python-docx not installed. Run: pip install python-docx"
    except Exception as exc:
        result["error"] = str(exc)
    return result


def _xlsx(path: Path) -> dict:
    result = {"file_type": "xlsx", **_file_base(path)}
    try:
        import openpyxl  # type: ignore
        wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
        cp = wb.properties
        result["sheet_count"] = len(wb.sheetnames)
        result["sheets"] = wb.sheetnames
        result["metadata"] = {
            "creator": cp.creator or "",
            "last_modified_by": cp.lastModifiedBy or "",
            "created": str(cp.created) if cp.created else "",
            "modified": str(cp.modified) if cp.modified else "",
            "title": cp.title or "",
            "subject": cp.subject or "",
        }
    except ImportError:
        result["error"] = "openpyxl not installed. Run: pip install openpyxl"
    except Exception as exc:
        result["error"] = str(exc)
    return result


_DISPATCH = {
    ".jpg": _image, ".jpeg": _image, ".png": _image, ".gif": _image,
    ".bmp": _image, ".tiff": _image, ".tif": _image, ".webp": _image,
    ".mp3": _audio, ".flac": _audio, ".wav": _audio, ".ogg": _audio,
    ".aac": _audio, ".m4a": _audio, ".wma": _audio,
    ".mp4": _video, ".avi": _video, ".mov": _video, ".mkv": _video,
    ".wmv": _video, ".flv": _video, ".webm": _video,
    ".pdf": _pdf,
    ".docx": _docx,
    ".xlsx": _xlsx, ".xls": _xlsx,
}


def analyse_file(path: Path) -> dict:
    """Dispatch to the appropriate extractor based on file extension."""
    ext = path.suffix.lower()
    handler = _DISPATCH.get(ext)
    if handler:
        return handler(path)
    result = {"file_type": "unknown", **_file_base(path)}
    result["note"] = f"No metadata extractor available for {ext or 'unknown'} files"
    return result


SUPPORTED_EXTENSIONS = set(_DISPATCH.keys())
