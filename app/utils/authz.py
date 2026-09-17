"""Case-level authorization.

Replaces the ~10 duplicated `if case.owner_user_id != current_user.id:
abort(403)` checks that used to be scattered across app/routes/cases.py
(one per route, plus a one-off `_get_case_owned_by_user()` helper used
only by the export routes) with a single, team-aware predicate.
"""
from app.repositories.team_repository import get_membership

# What each team role may do with a case shared to that team. The case's
# own owner_user_id always has full access regardless of this matrix (see
# can_access_case below) — this only governs *team member* access to a
# case they don't personally own.
_ROLE_PERMISSIONS = {
    "owner":   {"read", "comment", "export", "edit", "delete"},
    "admin":   {"read", "comment", "export", "edit"},
    "analyst": {"read", "comment", "export"},
    "member":  {"read", "comment"},
}


def can_access_case(case, user, action: str = "read") -> bool:
    """Return True if `user` may perform `action` on `case`.

    action is one of: "read", "comment", "export", "edit", "delete".

    - The case's owner always has full access.
    - A case with no recorded owner (owner_user_id is None/falsy) is
      treated as accessible — this matches the pre-existing behavior in
      close_case/reopen_case/bulk_import ("if case.owner_user_id and
      case.owner_user_id != current_user.id"), which never 403'd a
      case with no owner on file.
    - Otherwise, if the case is shared with a team (case.team_id set)
      and `user` is a member of that team, access follows _ROLE_PERMISSIONS
      for their role in that team.
    - Anything else is denied.
    """
    if case is None or user is None:
        return False

    owner_id = getattr(case, "owner_user_id", None)
    if owner_id == user.id:
        return True
    if not owner_id:
        return True

    team_id = getattr(case, "team_id", None)
    if not team_id:
        return False

    membership = get_membership(team_id, user.id)
    if not membership:
        return False

    return action in _ROLE_PERMISSIONS.get(membership.role, set())
