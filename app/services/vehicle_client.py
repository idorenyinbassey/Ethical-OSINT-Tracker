"""Vehicle / VIN decoder — NHTSA vPIC public API (free, no key required)."""
from typing import Optional
import httpx

_NHTSA_URL = "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/{vin}?format=json"

# Fields to extract for the summary block, in display order.
_SUMMARY_MAP = {
    "ModelYear": "year",
    "Make": "make",
    "Model": "model",
    "BodyClass": "body_class",
    "VehicleType": "vehicle_type",
    "EngineCylinders": "engine_cylinders",
    "DisplacementL": "displacement_l",
    "FuelTypePrimary": "fuel_type",
    "DriveType": "drive_type",
    "TransmissionStyle": "transmission",
    "PlantCountry": "country",
    "Manufacturer": "manufacturer",
    "ErrorCode": "error_code",
    "ErrorText": "error_text",
}

# Values that indicate an empty / not-applicable field in the NHTSA response.
_EMPTY_VALUES = {"", "0", "Not Applicable", "not applicable", "None", "null"}


def _is_empty(value: object) -> bool:
    """Return True when a field value carries no useful information."""
    if value is None:
        return True
    s = str(value).strip()
    return s in _EMPTY_VALUES


def decode_vin(vin: str) -> dict:
    """Decode a VIN using the NHTSA vPIC public API.

    Returns a dict with keys:
      - vin      : cleaned VIN string
      - error    : None on success, error message string on failure
      - summary  : dict of key decoded fields (empty/NA values omitted)
      - details  : dict of all non-empty fields from the API response
    """
    vin = vin.strip().upper()

    summary: dict = {k: None for k in _SUMMARY_MAP.values()}
    details: dict = {}
    error: Optional[str] = None

    try:
        url = _NHTSA_URL.format(vin=vin)
        with httpx.Client(timeout=15) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException:
        return {"vin": vin, "error": "Request timed out after 15 seconds.", "summary": summary, "details": details}
    except httpx.HTTPStatusError as exc:
        return {"vin": vin, "error": f"HTTP {exc.response.status_code} from NHTSA API.", "summary": summary, "details": details}
    except Exception as exc:
        return {"vin": vin, "error": f"Request failed: {exc}", "summary": summary, "details": details}

    try:
        results = data.get("Results", [])
        if not results:
            return {"vin": vin, "error": "No results returned by NHTSA API.", "summary": summary, "details": details}

        raw: dict = results[0]
    except (KeyError, IndexError, TypeError) as exc:
        return {"vin": vin, "error": f"Unexpected API response structure: {exc}", "summary": summary, "details": details}

    # Build details — all non-empty fields.
    for key, value in raw.items():
        if not _is_empty(value):
            details[key] = str(value).strip()

    # Build summary — map selected NHTSA field names to friendly keys.
    for nhtsa_key, friendly_key in _SUMMARY_MAP.items():
        raw_value = raw.get(nhtsa_key)
        if not _is_empty(raw_value):
            summary[friendly_key] = str(raw_value).strip()

    # Surface any decode error text from the API itself, but don't treat it
    # as a hard failure — partial data is still useful.
    api_error_code = raw.get("ErrorCode", "")
    if api_error_code and api_error_code not in ("0", "", "None"):
        error_text = raw.get("ErrorText", "")
        error = f"NHTSA decode note ({api_error_code}): {error_text}".strip(": ")

    return {
        "vin": vin,
        "error": error,
        "summary": summary,
        "details": details,
    }
