"""Shared route decorators.

`admin_required` used to be defined identically in both
app/routes/settings.py and app/routes/admin.py — consolidated here so the
two copies can't drift. Both modules now import it from here.
"""
from functools import wraps
from flask import abort
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
