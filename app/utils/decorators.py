"""Shared route decorators.

`admin_required` used to be defined identically in both
app/routes/settings.py and app/routes/admin.py — consolidated here so the
two copies can't drift. Both modules now import it from here.
"""
from functools import wraps
from flask import abort, request, g, jsonify
from flask_login import current_user


def admin_required(f):
    """Require the current user to be a site-wide admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, "is_admin", False):
            abort(403)
        return f(*args, **kwargs)
    return decorated


def team_member_required(f):
    """Require the current user to be a member (any role) of the team
    identified by the route's `team_id` URL parameter."""
    @wraps(f)
    def decorated(*args, **kwargs):
        from app.repositories.team_repository import get_membership
        team_id = kwargs.get("team_id")
        if not current_user.is_authenticated or team_id is None or not get_membership(team_id, current_user.id):
            abort(403)
        return f(*args, **kwargs)
    return decorated


def api_key_required(f):
    """Require a valid API key on the request (X-API-Key header, or
    Authorization: Bearer <key>), for the stateless /api/v1 surface.

    Deliberately does NOT touch flask_login/current_user or the session —
    API-key auth is per-request and stateless, unlike the cookie-based
    browser session. On success, the resolved user is attached to
    flask.g.api_user (and the key row to flask.g.api_key) for the view
    to use.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        from app.repositories.api_key_repository import get_by_raw_key, touch_last_used
        from app.repositories.user_repository import get_by_id

        raw_key = request.headers.get("X-API-Key", "")
        if not raw_key:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                raw_key = auth_header[len("Bearer "):].strip()

        def _unauthorized():
            return jsonify({"error": "Unauthorized"}), 401

        if not raw_key:
            return _unauthorized()

        key = get_by_raw_key(raw_key)
        if not key or key.revoked:
            return _unauthorized()

        user = get_by_id(key.user_id)
        if not user or not getattr(user, "is_active", True):
            return _unauthorized()

        g.api_key = key
        g.api_user = user
        touch_last_used(key.id)
        return f(*args, **kwargs)
    return decorated


def team_role_required(*roles):
    """Require the current user to hold one of `roles` in the team
    identified by the route's `team_id` URL parameter."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            from app.repositories.team_repository import get_membership
            team_id = kwargs.get("team_id")
            if not current_user.is_authenticated or team_id is None:
                abort(403)
            membership = get_membership(team_id, current_user.id)
            if not membership or membership.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator
