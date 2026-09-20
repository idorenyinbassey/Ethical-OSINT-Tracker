"""Case-level authorization.

Replaces the ~10 duplicated `if case.owner_user_id != current_user.id:
abort(403)` checks that used to be scattered across app/routes/cases.py
(one per route, plus a one-off `_get_case_owned_by_user()` helper used
only by the export routes) with a single, team-aware predicate.
"""
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.repositories.team_repository import get_membership

_ph = PasswordHasher()

# What each team role may do with a case shared to that team. The case's
# own owner_user_id always has full access regardless of this matrix (see
# can_access_case below) — this only governs *team member* access to a
# case they don't personally own. Deleting (and closing, which cascades
# to the same data wipe) a case is no longer part of this matrix at all —
# it's gated to site-wide admins only, checked directly against
# current_user.is_admin at the route level, regardless of case ownership
# or team role.
_ROLE_PERMISSIONS = {
    "owner":   {"read", "comment", "export", "edit"},
    "admin":   {"read", "comment", "export", "edit"},
    "analyst": {"read", "comment", "export"},
    "member":  {"read", "comment"},
}


def can_access_case(case, user, action: str = "read") -> bool:
    """Return True if `user` may perform `action` on `case`.

    action is one of: "read", "comment", "export", "edit". ("delete" is
    deliberately not handled here — see the module docstring above;
    checking it would always be False and could look like a permission
    check that's actually doing something.)

    - A site-wide admin (user.is_admin) always has full access to every
      case, regardless of ownership or team — the same blanket reach an
      admin already has over every user via /admin/*. This is what makes
      the admin-gated delete/close actually usable: an admin has to be
      able to find and open a case they don't own before they can act on
      it, not just be allowed to POST to its delete/close route blindly.
    - The case's owner always has full access.
    - A case with no recorded owner (owner_user_id is None/falsy) is only
      accessible to a site-wide admin — an ownerless case has no one to
      vouch for who may act on it, so it defaults to the same admin-only
      posture as case deletion, not to "anyone."
    - Otherwise, if the case is shared with a team (case.team_id set)
      and `user` is a member of that team, access follows _ROLE_PERMISSIONS
      for their role in that team.
    - Anything else is denied.
    """
    if case is None or user is None:
        return False

    if getattr(user, "is_admin", False):
        return True

    owner_id = getattr(case, "owner_user_id", None)
    if owner_id == user.id:
        return True
    if not owner_id:
        return False

    team_id = getattr(case, "team_id", None)
    if not team_id:
        return False

    membership = get_membership(team_id, user.id)
    if not membership:
        return False

    return action in _ROLE_PERMISSIONS.get(membership.role, set())


def verify_current_password(user, raw_password: str) -> bool:
    """Re-check a user's own current password against their stored hash —
    a confirmation step before an irreversible admin action (case
    delete/close, audit log clear), mirroring the same re-verification
    settings.py's 2FA-disable flow already requires before it will act."""
    if not user or not raw_password:
        return False
    try:
        _ph.verify(user.password_hash, raw_password)
        return True
    except VerifyMismatchError:
        return False
