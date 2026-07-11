"""Image forensics uses synthetic fixtures, never real committed photos (Issue #9)."""
from app.services.image_client import extract_image_metadata


def test_extract_metadata_from_synthetic_image(synthetic_image):
    meta = extract_image_metadata(synthetic_image)
    assert meta["Format"] == "PNG"
    assert meta["Size"] == "32x32"
    # A freshly generated image carries no camera EXIF / GPS.
    assert "GPS_Latitude" not in meta


def test_no_real_photos_tracked_in_repo():
    """Guard against re-committing real photos under uploaded_files/."""
    import subprocess

    tracked = subprocess.run(
        ["git", "ls-files", "uploaded_files/"],
        capture_output=True, text=True,
    ).stdout.strip()
    assert tracked == "", f"real files must not be tracked: {tracked}"
