import base64
import httpx
from pathlib import Path
from typing import Optional, Dict
from app.repositories.api_config_repository import get_by_service

try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False


def extract_image_metadata(image_path: Path) -> Dict[str, str]:
    """Extract EXIF and metadata from an image file using Pillow."""
    if not PILLOW_AVAILABLE:
        return {"error": "Pillow not installed. Run: pip install Pillow"}

    if not image_path.exists():
        return {"error": f"Image file not found at: {image_path}"}

    metadata = {}

    try:
        with Image.open(image_path) as img:
            metadata["Format"] = img.format or "Unknown"
            metadata["Mode"] = img.mode
            metadata["Size"] = f"{img.width}x{img.height}"
            metadata["Width"] = str(img.width)
            metadata["Height"] = str(img.height)
            if hasattr(img, "filename"):
                metadata["Filename"] = str(image_path.name)

            exif_data = None
            try:
                exif_data = img.getexif()
            except AttributeError:
                pass
            if not exif_data:
                try:
                    exif_data = img._getexif()
                except AttributeError:
                    pass
            if not exif_data and hasattr(img, "info"):
                info = img.info
                if info:
                    for key, value in info.items():
                        if isinstance(value, (str, int, float)):
                            metadata[f"Info_{key}"] = str(value)

            if exif_data:
                exif_count = 0
                for tag_id, value in exif_data.items():
                    try:
                        tag = TAGS.get(tag_id, str(tag_id))
                        if tag == "GPSInfo":
                            gps_data = {}
                            try:
                                for gps_tag_id in value:
                                    gps_tag = GPSTAGS.get(gps_tag_id, str(gps_tag_id))
                                    gps_data[gps_tag] = value[gps_tag_id]
                                if "GPSLatitude" in gps_data and "GPSLongitude" in gps_data:
                                    lat_ref = gps_data.get("GPSLatitudeRef", "N")
                                    lon_ref = gps_data.get("GPSLongitudeRef", "E")
                                    lat = gps_data["GPSLatitude"]
                                    lon = gps_data["GPSLongitude"]
                                    try:
                                        lat_d = float(lat[0]) + float(lat[1]) / 60 + float(lat[2]) / 3600
                                        if lat_ref == "S":
                                            lat_d = -lat_d
                                        lon_d = float(lon[0]) + float(lon[1]) / 60 + float(lon[2]) / 3600
                                        if lon_ref == "W":
                                            lon_d = -lon_d
                                        metadata["GPS_Latitude"] = f"{lat_d:.6f}"
                                        metadata["GPS_Longitude"] = f"{lon_d:.6f}"
                                        metadata["GPS_Location"] = f"{lat_d:.6f}, {lon_d:.6f}"
                                    except Exception as gps_err:
                                        metadata["GPS_Error"] = str(gps_err)
                            except Exception as gps_parse_err:
                                metadata["GPS_Parse_Error"] = str(gps_parse_err)
                            continue
                        if value is None:
                            continue
                        if isinstance(value, bytes):
                            try:
                                value_str = value.decode("utf-8", errors="ignore").strip()
                                if value_str:
                                    metadata[str(tag)] = value_str
                                    exif_count += 1
                            except Exception:
                                pass
                        elif isinstance(value, (tuple, list, str, int, float)):
                            metadata[str(tag)] = str(value)
                            exif_count += 1
                        else:
                            try:
                                metadata[str(tag)] = str(value)
                                exif_count += 1
                            except Exception:
                                pass
                    except Exception:
                        continue
                if exif_count == 0:
                    metadata["EXIF_Status"] = "No readable EXIF data found in image"
                else:
                    metadata["EXIF_Fields_Found"] = str(exif_count)
            else:
                metadata["EXIF_Status"] = "No EXIF data - image may be a screenshot, edited, or format doesn't support EXIF"
    except Exception as e:
        metadata["extraction_error"] = f"Error reading image: {str(e)}"

    return metadata


def map_exif_to_ui_fields(raw_exif: dict) -> dict:
    mapped = {}
    make = raw_exif.get("Make", "")
    model = raw_exif.get("Model", "")
    if make or model:
        mapped["Device"] = f"{make} {model}".strip()
    if "DateTime" in raw_exif:
        mapped["Date Taken"] = raw_exif["DateTime"]
    elif "DateTimeOriginal" in raw_exif:
        mapped["Date Taken"] = raw_exif["DateTimeOriginal"]
    if "GPS_Location" in raw_exif:
        mapped["Location"] = raw_exif["GPS_Location"]
    for key, value in raw_exif.items():
        if key not in ("Make", "Model", "DateTime", "DateTimeOriginal", "GPS_Location"):
            mapped[key] = value
    return mapped


def validate_google_vision_key(api_key: str) -> tuple[bool, str]:
    """Validate Google Cloud Vision API key format (AIza prefix, 39 chars)."""
    if not api_key:
        return False, "API key is empty"
    api_key = api_key.strip()
    if not api_key.startswith("AIza"):
        return False, "Invalid format: Google Cloud API keys must start with 'AIza'"
    if len(api_key) != 39:
        return False, f"Invalid length: Expected 39 characters, got {len(api_key)}"
    import re
    if not re.match(r"^[A-Za-z0-9_-]+$", api_key):
        return False, "Invalid characters in API key"
    return True, ""


def analyze_image(image_path: Path) -> Optional[Dict]:
    """Analyze an uploaded image: extract EXIF metadata and optionally call Google Cloud Vision."""
    raw_exif_data = extract_image_metadata(image_path)
    exif_data = map_exif_to_ui_fields(raw_exif_data)

    result = {
        "identified_person": "Unknown",
        "confidence": "0%",
        "emails": [],
        "social_profiles": [],
        "media_mentions": [],
        "recent_posts": [],
        "exif": exif_data,
    }

    cfg = get_by_service("ImageRecognition")
    if cfg and cfg.is_enabled and cfg.api_key:
        api_key = cfg.api_key.strip()
        is_valid, error_msg = validate_google_vision_key(api_key)
        if not is_valid:
            result["exif"]["api_error"] = f"Configuration Error: {error_msg}"
            result["identified_person"] = "API key validation failed"
            result["confidence"] = "N/A"
            return result

        endpoint = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"

        try:
            with open(image_path, "rb") as image_file:
                image_content = base64.b64encode(image_file.read()).decode("utf-8")

            request_body = {
                "requests": [{
                    "image": {"content": image_content},
                    "features": [
                        {"type": "FACE_DETECTION", "maxResults": 10},
                        {"type": "LABEL_DETECTION", "maxResults": 10},
                        {"type": "WEB_DETECTION", "maxResults": 10},
                        {"type": "TEXT_DETECTION"},
                        {"type": "SAFE_SEARCH_DETECTION"},
                    ],
                }]
            }

            with httpx.Client(timeout=30) as client:
                response = client.post(endpoint, headers={"Content-Type": "application/json"}, json=request_body)
                response.raise_for_status()
                api_data = response.json()

            if "responses" in api_data and api_data["responses"]:
                vision_response = api_data["responses"][0]
                faces = vision_response.get("faceAnnotations", [])
                if faces:
                    result["identified_person"] = f"{len(faces)} face(s) detected via Google Vision AI"
                    if faces[0].get("detectionConfidence"):
                        result["confidence"] = f"{faces[0]['detectionConfidence'] * 100:.1f}%"
                    else:
                        result["confidence"] = "High"
                    result["exif"]["faces_detected"] = str(len(faces))
                    for i, face in enumerate(faces[:3], 1):
                        emotions = []
                        for emo in ("joyLikelihood", "sorrowLikelihood", "angerLikelihood", "surpriseLikelihood"):
                            val = face.get(emo)
                            if val not in (None, "UNKNOWN", "VERY_UNLIKELY"):
                                emotions.append(f"{emo.replace('Likelihood', '')}: {val}")
                        if emotions:
                            result["exif"][f"face_{i}_emotions"] = ", ".join(emotions)
                else:
                    result["identified_person"] = "No faces detected (Google Vision AI)"
                    result["confidence"] = "N/A"

                labels = vision_response.get("labelAnnotations", [])
                if labels:
                    result["exif"]["detected_labels"] = ", ".join(l.get("description", "") for l in labels[:5])

                web_entities = vision_response.get("webDetection", {}).get("webEntities", [])
                if web_entities:
                    names = [e.get("description", "") for e in web_entities[:3] if e.get("description")]
                    if names:
                        result["exif"]["web_entities"] = ", ".join(names)

                text_annotations = vision_response.get("textAnnotations", [])
                if text_annotations:
                    text = text_annotations[0].get("description", "").strip()
                    if text:
                        result["exif"]["detected_text"] = text[:200] + ("..." if len(text) > 200 else "")

                safe_search = vision_response.get("safeSearchAnnotation", {})
                if safe_search:
                    result["exif"]["safe_search_adult"] = safe_search.get("adult", "UNKNOWN")
                    result["exif"]["safe_search_violence"] = safe_search.get("violence", "UNKNOWN")

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            msg = {401: "Authentication Failed (401): Invalid API key.",
                   403: "Access Denied (403): Vision API not enabled or quota exceeded.",
                   429: "Rate Limit Exceeded (429): Too many requests."}.get(status_code, f"HTTP Error ({status_code})")
            result["exif"]["api_error"] = msg
            result["identified_person"] = "API request failed"
            result["confidence"] = "N/A"
        except Exception as e:
            result["exif"]["api_error"] = f"Error: {str(e)}"
            result["identified_person"] = "Analysis failed"
            result["confidence"] = "N/A"
    else:
        result["identified_person"] = "Metadata extracted (no API configured)"
        result["confidence"] = "N/A"

    return result
