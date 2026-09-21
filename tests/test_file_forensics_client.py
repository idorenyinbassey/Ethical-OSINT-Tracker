"""app.services.file_forensics_client — EXIF GPS parsing and metadata
extraction for the File Forensics tool.

Covers the fix for a real bug: a GPS seconds value encoded as 0/0 (a
common Android/OPPO camera-stack convention for "exact whole-minute
reading, no fractional part") previously discarded the entire GPS
coordinate with a "malformed/zero-denominator" error, even though the
fix was completely valid. Confirmed empirically against Pillow that by
the time a GPS rational reaches our code it has already been resolved to
a bare float, and Pillow itself collapses any zero-denominator rational
(0/0 or otherwise) into float('nan') — so both the low-level rational
helpers and a full synthetic-image round trip are tested here.
"""
import math
import os
import tempfile
from pathlib import Path

import pytest
from PIL import Image
from PIL.TiffImagePlugin import IFDRational

from app.services.file_forensics_client import _safe_rational, _dms_to_decimal, _image


# ── _safe_rational ───────────────────────────────────────────────────────────

def test_safe_rational_ifdrational_zero_over_zero_is_zero():
    assert _safe_rational(IFDRational(0, 0)) == 0.0


def test_safe_rational_tuple_zero_over_zero_is_zero():
    assert _safe_rational((0, 0)) == 0.0


def test_safe_rational_nan_is_treated_as_zero():
    # Pillow's own resolved form of any zero-denominator rational.
    assert _safe_rational(float("nan")) == 0.0


def test_safe_rational_nonzero_over_zero_tuple_is_none():
    # Defense in depth for an unresolved (num, den) tuple with a genuinely
    # undefined value — distinguishable only when Pillow hasn't already
    # collapsed it to nan (see module docstring).
    assert _safe_rational((5, 0)) is None


def test_safe_rational_ifdrational_normal_value():
    assert _safe_rational(IFDRational(30, 1)) == 30.0


def test_safe_rational_plain_number_passthrough():
    assert _safe_rational(100) == 100.0
    assert _safe_rational(1.8) == 1.8


def test_safe_rational_unconvertible_value_is_none():
    assert _safe_rational("not-a-number") is None


# ── _dms_to_decimal ──────────────────────────────────────────────────────────

def test_dms_to_decimal_resolves_with_zero_over_zero_seconds():
    dms = ((51, 1), (30, 1), (0, 0))
    assert _dms_to_decimal(dms, "N") == 51.5


def test_dms_to_decimal_negates_for_south_and_west():
    dms = ((51, 1), (30, 1), (0, 0))
    assert _dms_to_decimal(dms, "S") == -51.5


def test_dms_to_decimal_none_on_genuinely_malformed_component():
    dms = ((51, 1), (30, 1), (5, 0))
    assert _dms_to_decimal(dms, "N") is None


def test_dms_to_decimal_none_on_missing_tuple():
    assert _dms_to_decimal(None, "N") is None
    assert _dms_to_decimal((1, 2), "N") is None  # too short


# ── Full _image() round trip via a real synthetic JPEG ──────────────────────

def _build_jpeg_with_exif(gps_ifd: dict | None = None, exif_ifd: dict | None = None,
                           top_level: dict | None = None) -> Path:
    img = Image.new("RGB", (4, 4), color="red")
    exif = img.getexif()
    for tag, val in (top_level or {}).items():
        exif[tag] = val
    if gps_ifd is not None:
        exif[0x8825] = gps_ifd
    if exif_ifd is not None:
        exif[0x8769] = exif_ifd
    fd, name = tempfile.mkstemp(suffix=".jpg")
    os.close(fd)
    path = Path(name)
    img.save(path, format="JPEG", exif=exif)
    return path


def test_image_resolves_whole_minute_gps_with_zero_seconds_denominator():
    # Reproduces the real-world OPPO A6x case: latitude/longitude seconds
    # encoded as 0/0 on an exact whole-minute GPS fix.
    path = _build_jpeg_with_exif(gps_ifd={
        1: "N", 2: (IFDRational(51, 1), IFDRational(30, 1), IFDRational(0, 0)),
        3: "E", 4: (IFDRational(0, 1), IFDRational(7, 1), IFDRational(0, 0)),
        6: IFDRational(10, 1),
    })
    try:
        result = _image(path)
        meta = result["metadata"]
        assert "GPS_Error" not in meta
        assert meta["GPS_Coordinates"] == "51.500000, 0.116667"
        assert meta["GPS_Altitude"] == "10.0"
    finally:
        path.unlink()


def test_image_extracts_gps_structural_fields():
    path = _build_jpeg_with_exif(gps_ifd={
        1: "N", 2: (IFDRational(51, 1), IFDRational(30, 1), IFDRational(0, 1)),
        3: "E", 4: (IFDRational(0, 1), IFDRational(7, 1), IFDRational(0, 1)),
        17: IFDRational(90, 1),   # GPSImgDirection
        13: IFDRational(5, 1),    # GPSSpeed
        8: "3",                   # GPSSatellites
        11: IFDRational(2, 1),    # GPSDOP
    })
    try:
        meta = _image(path)["metadata"]
        assert meta["GPS_Direction"] == "90.0"
        assert meta["GPS_Speed"] == "5.0"
        assert meta["GPS_Satellites"] == "3"
        assert meta["GPS_DOP"] == "2.0"
    finally:
        path.unlink()


def test_image_extracts_exif_sub_ifd_camera_settings():
    path = _build_jpeg_with_exif(exif_ifd={
        0x8827: 100,                   # ISOSpeedRatings
        0x829A: IFDRational(1, 100),   # ExposureTime
        0x829D: IFDRational(18, 10),   # FNumber
    })
    try:
        meta = _image(path)["metadata"]
        assert meta["ISOSpeedRatings"] == "100.0"
        assert meta["ExposureTime"] == "0.01"
        assert meta["FNumber"] == "1.8"
    finally:
        path.unlink()


def test_image_with_no_gps_tag_has_no_gps_fields():
    path = _build_jpeg_with_exif(top_level={0x0110: "Generic Camera"})
    try:
        result = _image(path)
        assert result["device_model"] == "Generic Camera"
        assert "GPS_Coordinates" not in result["metadata"]
        assert "GPS_Error" not in result["metadata"]
    finally:
        path.unlink()
