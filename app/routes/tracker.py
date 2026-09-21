"""Tracking link / grabber blueprint.

Public endpoints  (/t/...):  visited by targets — no login required, CSRF-exempt.
Management UI     (/tracker): investigator-facing — login required.
"""
import io
import json
import os
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, abort, jsonify, make_response, session)
from flask_login import login_required, current_user

from app.repositories.tracking_repository import (
    create_link, get_link_by_token, get_link, list_links,
    delete_link, record_hit, update_hit_fingerprint, list_hits, count_hits,
    update_link, set_active,
)
from app.repositories.case_repository import list_cases
from app.utils.authz import verify_current_password

_HITS_PAGE_SIZE = 50


def _public_base_url() -> str:
    """The base URL to build a shareable tracking link from. Prefers an
    explicitly configured PUBLIC_BASE_URL (set this when the app is
    reachable through a tunnel — ngrok, Cloudflare Tunnel — or a reverse
    proxy whose forwarded headers aren't trusted, so a shared link always
    points at the address the target can actually reach, not the
    server's own local host/scheme) over the incoming request's own host,
    which is only correct when TRUST_PROXY_HEADERS is also set (see
    app/__init__.py) or there's no proxy in front at all."""
    configured = os.getenv("PUBLIC_BASE_URL", "").strip()
    return configured.rstrip("/") if configured else request.host_url.rstrip("/")

tracker_bp = Blueprint("tracker", __name__)

# Minimal transparent 1×1 GIF
_GIF1X1 = bytes([
    0x47,0x49,0x46,0x38,0x39,0x61,0x01,0x00,0x01,0x00,0x80,0x00,0x00,
    0xff,0xff,0xff,0x00,0x00,0x00,0x21,0xf9,0x04,0x01,0x00,0x00,0x00,
    0x00,0x2c,0x00,0x00,0x00,0x00,0x01,0x00,0x01,0x00,0x00,0x02,0x02,
    0x44,0x01,0x00,0x3b,
])


def _real_ip() -> str:
    for header in ("X-Forwarded-For", "X-Real-IP"):
        val = request.headers.get(header)
        if val:
            return val.split(",")[0].strip()
    return request.remote_addr or ""


def _geolocate(ip: str) -> dict:
    """Return geo dict from existing ip_client; never raises."""
    try:
        from app.services.ip_client import fetch_ip
        geo = fetch_ip(ip)
        return geo or {}
    except Exception:
        return {}


# ── Public tracking endpoints (no auth, CSRF-exempt) ─────────────────────────

@tracker_bp.route("/t/<token>")
def land(token):
    link = get_link_by_token(token)
    if not link or not link.active:
        abort(404)

    ip = _real_ip()
    geo = _geolocate(ip)
    hit = record_hit(
        link_id=link.id,
        hit_type="link",
        ip=ip,
        user_agent=request.headers.get("User-Agent", ""),
        referrer=request.headers.get("Referer", ""),
        country=geo.get("country", ""),
        city=geo.get("city", ""),
        isp=geo.get("isp", ""),
        lat=geo.get("lat"),
        lon=geo.get("lon"),
    )

    return render_template("tracker/land.html",
                           link=link, hit_id=hit.id, token=token)


@tracker_bp.route("/t/<token>/px.gif")
def pixel(token):
    link = get_link_by_token(token)
    if not link or not link.active:
        resp = make_response(_GIF1X1)
        resp.headers["Content-Type"] = "image/gif"
        resp.headers["Cache-Control"] = "no-store, no-cache"
        return resp

    ip = _real_ip()
    geo = _geolocate(ip)
    record_hit(
        link_id=link.id,
        hit_type="pixel",
        ip=ip,
        user_agent=request.headers.get("User-Agent", ""),
        referrer=request.headers.get("Referer", ""),
        country=geo.get("country", ""),
        city=geo.get("city", ""),
        isp=geo.get("isp", ""),
        lat=geo.get("lat"),
        lon=geo.get("lon"),
    )

    resp = make_response(_GIF1X1)
    resp.headers["Content-Type"] = "image/gif"
    resp.headers["Cache-Control"] = "no-store, no-cache"
    return resp


@tracker_bp.route("/t/<token>/fp", methods=["POST"])
def collect_fingerprint(token):
    """Receive JS fingerprint + optional GPS from target browser."""
    link = get_link_by_token(token)
    if not link:
        return jsonify({"ok": False}), 404

    try:
        data = request.get_json(force=True, silent=True) or {}
    except Exception:
        data = {}

    hit_id = data.get("hit_id")
    if hit_id:
        update_hit_fingerprint(
            hit_id,
            screen=data.get("screen", ""),
            timezone=data.get("timezone", ""),
            language=data.get("language", ""),
            platform=data.get("platform", ""),
            browser=data.get("browser", ""),
            plugins=data.get("plugins", ""),
            gps_lat=data.get("gps_lat"),
            gps_lon=data.get("gps_lon"),
            gps_accuracy=data.get("gps_accuracy"),
        )
    return jsonify({"ok": True})


# ── Management UI (login required) ───────────────────────────────────────────

@tracker_bp.route("/tracker")
@login_required
def index():
    links = list_links(user_id=current_user.id)
    hit_counts = {lnk.id: count_hits(lnk.id) for lnk in links}
    return render_template("tracker/index.html", links=links, hit_counts=hit_counts)


@tracker_bp.route("/tracker/new", methods=["GET", "POST"])
@login_required
def new_link():
    cases = list_cases(owner_user_id=current_user.id)
    if request.method == "POST":
        label = request.form.get("label", "").strip()
        case_id_raw = request.form.get("case_id", "")
        decoy_mode = request.form.get("decoy_mode", "404")
        redirect_url = request.form.get("redirect_url", "").strip()
        notes = request.form.get("notes", "").strip()

        if not label:
            flash("Label is required.", "error")
            return render_template("tracker/new.html", cases=cases)

        try:
            case_id = int(case_id_raw) if case_id_raw else None
        except ValueError:
            case_id = None

        link = create_link(label=label, user_id=current_user.id, case_id=case_id,
                           decoy_mode=decoy_mode, redirect_url=redirect_url, notes=notes)
        flash(f"Tracking link created.", "success")
        return redirect(url_for("tracker.detail", token=link.token))

    return render_template("tracker/new.html", cases=cases)


@tracker_bp.route("/tracker/<token>")
@login_required
def detail(token):
    link = get_link_by_token(token)
    if not link or link.user_id != current_user.id:
        abort(404)
    page = request.args.get("page", 1, type=int)
    page = max(page, 1)
    total_hits = count_hits(link.id)
    hits = list_hits(link.id, limit=_HITS_PAGE_SIZE, offset=(page - 1) * _HITS_PAGE_SIZE)
    base = _public_base_url()
    tracking_url = base + url_for("tracker.land", token=token)
    pixel_url = base + url_for("tracker.pixel", token=token)
    return render_template("tracker/detail.html", link=link, hits=hits,
                           tracking_url=tracking_url, pixel_url=pixel_url,
                           page=page, total_hits=total_hits, page_size=_HITS_PAGE_SIZE,
                           has_more=(page * _HITS_PAGE_SIZE) < total_hits)


@tracker_bp.route("/tracker/<token>/edit", methods=["GET", "POST"])
@login_required
def edit_link(token):
    link = get_link_by_token(token)
    if not link or link.user_id != current_user.id:
        abort(404)

    if request.method == "GET":
        return render_template("tracker/edit.html", link=link)

    label = request.form.get("label", "").strip()
    decoy_mode = request.form.get("decoy_mode", "404")
    redirect_url = request.form.get("redirect_url", "").strip()
    notes = request.form.get("notes", "").strip()

    if not label:
        flash("Label is required.", "error")
        return redirect(url_for("tracker.edit_link", token=token))

    update_link(link.id, label=label, decoy_mode=decoy_mode, redirect_url=redirect_url, notes=notes)
    flash("Tracking link updated.", "success")
    return redirect(url_for("tracker.detail", token=token))


@tracker_bp.route("/tracker/<token>/toggle", methods=["POST"])
@login_required
def toggle_active(token):
    """Pause or resume a link without deleting it — a paused link 404s
    for visitors and stops recording new hits, but its existing hit
    history stays intact (unlike delete, which wipes both)."""
    link = get_link_by_token(token)
    if not link or link.user_id != current_user.id:
        abort(404)
    set_active(link.id, not link.active)
    flash(f"Tracking link {'resumed' if not link.active else 'paused'}.", "success")
    return redirect(url_for("tracker.detail", token=token))


@tracker_bp.route("/tracker/<token>/hits.json")
@login_required
def hits_json(token):
    link = get_link_by_token(token)
    if not link or link.user_id != current_user.id:
        return jsonify([]), 404
    hits = list_hits(link.id, limit=_HITS_PAGE_SIZE)
    return jsonify([{
        "id":           h.id,
        "hit_type":     h.hit_type,
        "ip":           h.ip,
        "isp":          h.isp,
        "country":      h.country,
        "city":         h.city,
        "lat":          h.lat,
        "lon":          h.lon,
        "screen":       h.screen,
        "platform":     h.platform,
        "browser":      h.browser,
        "timezone":     h.timezone,
        "language":     h.language,
        "plugins":      h.plugins,
        "gps_lat":      h.gps_lat,
        "gps_lon":      h.gps_lon,
        "gps_accuracy": h.gps_accuracy,
        "user_agent":   h.user_agent,
        "referrer":     h.referrer,
        "created_at":   h.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    } for h in hits])


@tracker_bp.route("/tracker/<token>/delete", methods=["POST"])
@login_required
def delete(token):
    link = get_link_by_token(token)
    if not link or link.user_id != current_user.id:
        abort(404)
    if not verify_current_password(current_user, request.form.get("password", "")):
        flash("Incorrect password — tracking link was not deleted.", "error")
        return redirect(url_for("tracker.detail", token=token))
    delete_link(link.id)
    flash("Tracking link deleted.", "success")
    return redirect(url_for("tracker.index"))
