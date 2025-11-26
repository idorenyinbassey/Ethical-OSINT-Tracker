import httpx
from typing import Optional, Dict
from pathlib import Path
import reflex as rx
from app.repositories.api_config_repository import get_by_service

try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False


def extract_image_metadata(image_path: Path) -> Dict[str, str]:
    """Extract EXIF and metadata from an image file using Pillow.
    
    Returns dict with camera info, GPS, timestamp, dimensions, etc.
    """
    if not PILLOW_AVAILABLE:
        return {"error": "Pillow not installed. Run: pip install Pillow"}
    
    if not image_path.exists():
        return {"error": f"Image file not found at: {image_path}"}
    
    metadata = {}
    
    try:
        with Image.open(image_path) as img:
            # Basic image info (always available)
            metadata["Format"] = img.format or "Unknown"
            metadata["Mode"] = img.mode
            metadata["Size"] = f"{img.width}x{img.height}"
            metadata["Width"] = str(img.width)
            metadata["Height"] = str(img.height)
            
            # Add file info
            if hasattr(img, 'filename'):
                metadata["Filename"] = str(image_path.name)
            
            # Try multiple methods to get EXIF data
            exif_data = None
            
            # Method 1: Try getexif() (modern PIL)
            try:
                exif_data = img.getexif()
            except AttributeError:
                pass
            
            # Method 2: Try _getexif() (older PIL)
            if not exif_data:
                try:
                    exif_data = img._getexif()
                except AttributeError:
                    pass
            
            # Method 3: Try img.info (fallback)
            if not exif_data and hasattr(img, 'info'):
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
                        
                        # Handle GPS data specially
                        if tag == "GPSInfo":
                            gps_data = {}
                            try:
                                for gps_tag_id in value:
                                    gps_tag = GPSTAGS.get(gps_tag_id, str(gps_tag_id))
                                    gps_data[gps_tag] = value[gps_tag_id]
                                
                                # Extract GPS coordinates if available
                                if "GPSLatitude" in gps_data and "GPSLongitude" in gps_data:
                                    lat_ref = gps_data.get("GPSLatitudeRef", "N")
                                    lon_ref = gps_data.get("GPSLongitudeRef", "E")
                                    lat = gps_data["GPSLatitude"]
                                    lon = gps_data["GPSLongitude"]
                                    
                                    # Convert to decimal degrees
                                    try:
                                        lat_decimal = float(lat[0]) + float(lat[1])/60 + float(lat[2])/3600
                                        if lat_ref == "S":
                                            lat_decimal = -lat_decimal
                                        lon_decimal = float(lon[0]) + float(lon[1])/60 + float(lon[2])/3600
                                        if lon_ref == "W":
                                            lon_decimal = -lon_decimal
                                        
                                        metadata["GPS_Latitude"] = f"{lat_decimal:.6f}"
                                        metadata["GPS_Longitude"] = f"{lon_decimal:.6f}"
                                        metadata["GPS_Location"] = f"{lat_decimal:.6f}, {lon_decimal:.6f}"
                                    except Exception as gps_err:
                                        metadata["GPS_Error"] = str(gps_err)
                            except Exception as gps_parse_err:
                                metadata["GPS_Parse_Error"] = str(gps_parse_err)
                            continue
                        
                        # Skip problematic or unreadable values
                        if value is None:
                            continue
                        
                        # Convert value to string, handling special types
                        if isinstance(value, bytes):
                            try:
                                # Try to decode as UTF-8
                                value_str = value.decode('utf-8', errors='ignore').strip()
                                if value_str:
                                    metadata[str(tag)] = value_str
                                    exif_count += 1
                            except:
                                # If decode fails, skip binary data
                                pass
                        elif isinstance(value, (tuple, list)):
                            # Format tuples/lists nicely
                            metadata[str(tag)] = str(value)
                            exif_count += 1
                        elif isinstance(value, (str, int, float)):
                            metadata[str(tag)] = str(value)
                            exif_count += 1
                        else:
                            # Try to convert other types
                            try:
                                metadata[str(tag)] = str(value)
                                exif_count += 1
                            except:
                                pass
                    except Exception as tag_err:
                        # Skip problematic tags
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


def map_exif_to_ui_fields(raw_exif: dict[str, str]) -> dict[str, str]:
    """Transform PIL EXIF field names to UI-expected field names.
    
    Args:
        raw_exif: Dictionary with PIL standard field names
        
    Returns:
        Dictionary with UI-friendly field names
    """
    mapped = {}
    
    # Map Make + Model to Device
    make = raw_exif.get("Make", "")
    model = raw_exif.get("Model", "")
    if make or model:
        mapped["Device"] = f"{make} {model}".strip()
    
    # Map DateTime to Date Taken
    if "DateTime" in raw_exif:
        mapped["Date Taken"] = raw_exif["DateTime"]
    elif "DateTimeOriginal" in raw_exif:
        mapped["Date Taken"] = raw_exif["DateTimeOriginal"]
    
    # Map GPS_Location to Location
    if "GPS_Location" in raw_exif:
        mapped["Location"] = raw_exif["GPS_Location"]
    
    # Preserve all other fields for full metadata view
    for key, value in raw_exif.items():
        if key not in ["Make", "Model", "DateTime", "DateTimeOriginal", "GPS_Location"]:
            mapped[key] = value
    
    return mapped


def validate_google_vision_key(api_key: str) -> tuple[bool, str]:
    """Validate Google Cloud Vision API key format.
    
    Google Cloud API keys have a specific format:
    - Start with 'AIza' prefix
    - Exactly 39 characters long
    - Contain only alphanumeric characters, underscores, and hyphens
    
    Args:
        api_key: The API key to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        - (True, "") if valid
        - (False, error_message) if invalid
    """
    if not api_key:
        return False, "API key is empty"
    
    # Remove whitespace
    api_key = api_key.strip()
    
    # Google Cloud API keys start with "AIza" and are 39 chars
    if not api_key.startswith("AIza"):
        return False, "Invalid format: Google Cloud API keys must start with 'AIza'"
    
    if len(api_key) != 39:
        return False, f"Invalid length: Expected 39 characters, got {len(api_key)}"
    
    # Check for valid characters (alphanumeric, _, -)
    import re
    if not re.match(r'^[A-Za-z0-9_-]+$', api_key):
        return False, "Invalid characters: API key contains invalid characters"
    
    return True, ""


async def analyze_image(image_name: str) -> Optional[Dict]:
    """Analyze an uploaded image for facial recognition and extract metadata.
    
    Combines:
    1. Built-in metadata extraction (EXIF, GPS, camera info)
    2. Optional API-based facial recognition (if configured)
    
    Returns ImageResult dict with identified_person, confidence, and EXIF data.
    """
    # Get the uploaded file path
    upload_dir = rx.get_upload_dir()
    image_path = upload_dir / image_name
    
    # Extract metadata first (always works, no API needed)
    raw_exif_data = extract_image_metadata(image_path)
    exif_data = map_exif_to_ui_fields(raw_exif_data)
    
    # Initialize result
    result = {
        "identified_person": "Unknown",
        "confidence": "0%",
        "emails": [],
        "social_profiles": [],
        "media_mentions": [],
        "recent_posts": [],
        "exif": exif_data
    }
    
    # Try API-based recognition if configured (Google Cloud Vision AI)
    cfg = get_by_service("ImageRecognition")
    if cfg and cfg.is_enabled and cfg.api_key:
        api_key = cfg.api_key.strip()
        
        # Validate API key format before making request
        is_valid, error_msg = validate_google_vision_key(api_key)
        if not is_valid:
            result["exif"]["api_error"] = f"Configuration Error: {error_msg}. Get a valid key from Google Cloud Console."
            result["identified_person"] = "API key validation failed"
            result["confidence"] = "N/A"
            return result
        
        # Google Cloud Vision API endpoint
        endpoint = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
        
        try:
            import base64
            
            async with httpx.AsyncClient(timeout=30) as client:
                # Read and encode image to base64 for Google Vision API
                with open(image_path, "rb") as image_file:
                    image_content = base64.b64encode(image_file.read()).decode('utf-8')
                
                # Google Vision API request structure
                request_body = {
                    "requests": [
                        {
                            "image": {
                                "content": image_content
                            },
                            "features": [
                                {"type": "FACE_DETECTION", "maxResults": 10},
                                {"type": "LABEL_DETECTION", "maxResults": 10},
                                {"type": "WEB_DETECTION", "maxResults": 10},
                                {"type": "TEXT_DETECTION"},
                                {"type": "SAFE_SEARCH_DETECTION"}
                            ]
                        }
                    ]
                }
                
                headers = {"Content-Type": "application/json"}
                response = await client.post(endpoint, headers=headers, json=request_body)
                response.raise_for_status()
                
                api_data = response.json()
                
                # Parse Google Vision API response
                if "responses" in api_data and len(api_data["responses"]) > 0:
                    vision_response = api_data["responses"][0]
                    
                    # Face detection
                    faces = vision_response.get("faceAnnotations", [])
                    if faces:
                        faces_count = len(faces)
                        result["identified_person"] = f"{faces_count} face(s) detected via Google Vision AI"
                        
                        # Get confidence from first face
                        if faces[0].get("detectionConfidence"):
                            confidence_val = faces[0]["detectionConfidence"] * 100
                            result["confidence"] = f"{confidence_val:.1f}%"
                        else:
                            result["confidence"] = "High"
                        
                        # Add face details to EXIF
                        result["exif"]["faces_detected"] = str(faces_count)
                        for i, face in enumerate(faces[:3], 1):  # First 3 faces
                            emotions = []
                            if face.get("joyLikelihood") not in ["UNKNOWN", "VERY_UNLIKELY"]:
                                emotions.append(f"Joy: {face.get('joyLikelihood', 'N/A')}")
                            if face.get("sorrowLikelihood") not in ["UNKNOWN", "VERY_UNLIKELY"]:
                                emotions.append(f"Sorrow: {face.get('sorrowLikelihood', 'N/A')}")
                            if face.get("angerLikelihood") not in ["UNKNOWN", "VERY_UNLIKELY"]:
                                emotions.append(f"Anger: {face.get('angerLikelihood', 'N/A')}")
                            if face.get("surpriseLikelihood") not in ["UNKNOWN", "VERY_UNLIKELY"]:
                                emotions.append(f"Surprise: {face.get('surpriseLikelihood', 'N/A')}")
                            
                            if emotions:
                                result["exif"][f"face_{i}_emotions"] = ", ".join(emotions)
                    
                    # Label detection (objects/scenes in image)
                    labels = vision_response.get("labelAnnotations", [])
                    if labels:
                        label_names = [label.get("description", "") for label in labels[:5]]
                        result["exif"]["detected_labels"] = ", ".join(label_names)
                    
                    # Web detection (similar images/entities)
                    web_detection = vision_response.get("webDetection", {})
                    web_entities = web_detection.get("webEntities", [])
                    if web_entities:
                        entity_names = [entity.get("description", "") for entity in web_entities[:3] if entity.get("description")]
                        if entity_names:
                            result["exif"]["web_entities"] = ", ".join(entity_names)
                    
                    # Text detection (OCR)
                    text_annotations = vision_response.get("textAnnotations", [])
                    if text_annotations and len(text_annotations) > 0:
                        detected_text = text_annotations[0].get("description", "").strip()
                        if detected_text:
                            # Truncate if too long
                            result["exif"]["detected_text"] = detected_text[:200] + ("..." if len(detected_text) > 200 else "")
                    
                    # Safe search detection
                    safe_search = vision_response.get("safeSearchAnnotation", {})
                    if safe_search:
                        result["exif"]["safe_search_adult"] = safe_search.get("adult", "UNKNOWN")
                        result["exif"]["safe_search_violence"] = safe_search.get("violence", "UNKNOWN")
                    
                    if not faces:
                        result["identified_person"] = "No faces detected (Google Vision AI)"
                        result["confidence"] = "N/A"
                    
        except httpx.HTTPStatusError as e:
            # Specific HTTP error handling with actionable messages
            status_code = e.response.status_code
            
            if status_code == 400:
                error_detail = "Invalid request format or parameters"
                try:
                    error_data = e.response.json()
                    if "error" in error_data:
                        error_detail = error_data["error"].get("message", error_detail)
                except:
                    pass
                result["exif"]["api_error"] = f"Bad Request (400): {error_detail}. Check API key format and request structure."
                
            elif status_code == 401:
                result["exif"]["api_error"] = "Authentication Failed (401): Invalid API key. Generate a new key in Google Cloud Console → APIs & Services → Credentials."
                
            elif status_code == 403:
                result["exif"]["api_error"] = "Access Denied (403): Cloud Vision API may not be enabled for your project, or quota exceeded. Check Google Cloud Console."
                
            elif status_code == 429:
                result["exif"]["api_error"] = "Rate Limit Exceeded (429): Too many requests. Free tier: 1,000/month. Wait before retrying."
                
            else:
                result["exif"]["api_error"] = f"HTTP Error ({status_code}): {str(e)}"
            
            result["identified_person"] = "API request failed"
            result["confidence"] = "N/A"
                
        except httpx.RequestError as e:
            # Network/connection errors
            result["exif"]["api_error"] = f"Network Error: {str(e)}. Check internet connection."
            result["identified_person"] = "Connection failed"
            result["confidence"] = "N/A"
            
        except Exception as e:
            # Unexpected errors
            result["exif"]["api_error"] = f"Unexpected Error: {str(e)}"
            result["identified_person"] = "Analysis failed"
            result["confidence"] = "N/A"
    else:
        # No API configured, metadata-only mode
        result["identified_person"] = "Metadata extracted (no API configured)"
        result["confidence"] = "N/A"
    
    return result
